import asyncio
import json
import logging
import shutil
import time
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable, Optional, Tuple

from .config import (
    DATA_DIR,
    DAILY_SUMMARY_ENABLED,
    DAILY_SUMMARY_TIME,
    DAILY_SUMMARY_PROMPT,
    DAILY_SUMMARY_REPO,
    DAILY_SUMMARY_OUTPUT_FILE,
    DAILY_SUMMARY_MAX_WORDS,
    DAILY_SUMMARY_SCOPE_DIR,
    DAILY_SUMMARY_LOOKBACK_HOURS,
)

logger = logging.getLogger("daily_summary")

NotifyFn = Callable[[object, str], Awaitable[None]]


def start_daily_summary_task(bot, notify_fn: NotifyFn) -> Optional[asyncio.Task]:
    if not DAILY_SUMMARY_ENABLED:
        logger.info("Riassunto giornaliero disabilitato.")
        return None

    schedule = _parse_time(DAILY_SUMMARY_TIME)
    if not schedule:
        logger.error("Formato orario DAILY_SUMMARY_TIME non valido: %s", DAILY_SUMMARY_TIME)
        return None

    task = asyncio.create_task(_summary_loop(bot, notify_fn, schedule))
    task.set_name("daily-summary")
    logger.info("Riassunto giornaliero attivo: ogni giorno alle %02d:%02d.", *schedule)
    return task


def _parse_time(value: str) -> Optional[Tuple[int, int]]:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def _next_target(hour: int, minute: int) -> datetime:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


HEARTBEAT_SECONDS = 30
STREAM_LOG_MAX_CHARS = 400


async def _summary_loop(bot, notify_fn: NotifyFn, schedule: Tuple[int, int]):
    hour, minute = schedule
    try:
        while True:
            target = _next_target(hour, minute)
            wait_seconds = max(0, (target - datetime.now()).total_seconds())
            logger.info("Prossimo riassunto del giorno programmato per %s.", target.isoformat())
            try:
                logger.debug("Attendo %.0f secondi prima del prossimo riassunto.", wait_seconds)
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                raise
            logger.debug("Timer scaduto (%s), avvio procedura riassunto.", target.isoformat())
            await _run_summary_and_notify(bot, notify_fn)
    except asyncio.CancelledError:
        logger.info("Task riassunto giornaliero annullato.")
        raise


async def _run_summary_and_notify(bot, notify_fn: NotifyFn):
    try:
        logger.debug("Avvio generazione del riassunto giornaliero.")
        summary_text = await _generate_daily_summary()
    except Exception as exc:
        logger.exception("Esecuzione riassunto giornaliero fallita: %s", exc)
        return

    if not summary_text.strip():
        logger.warning("Riassunto giornaliero vuoto, nessun messaggio inviato.")
        return

    header = "📝 Riassunto del giorno\n\n"
    logger.info("Invio riassunto giornaliero a tutte le chat note (%d caratteri).", len(summary_text))
    await notify_fn(bot, header + summary_text.strip())


async def _generate_daily_summary() -> str:
    scope_dir = _prepare_scope_dir()
    scope_hint = (
        f"Consulta esclusivamente i file in {scope_dir.as_posix()}, "
        f"che contengono gli estratti delle ultime {DAILY_SUMMARY_LOOKBACK_HOURS} ore. "
        "Ignora gli altri file del repository."
    )
    dated_output_path, latest_output_path = _resolve_output_paths()
    dated_output_path.parent.mkdir(parents=True, exist_ok=True)
    latest_output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt_with_limit = (
        f"{DAILY_SUMMARY_PROMPT.rstrip()}\n\n"
        f"{scope_hint}\n\n"
        f"Scrivi non più di {DAILY_SUMMARY_MAX_WORDS} parole complessive."
    )

    cmd = [
        "codex",
        "exec",
        "-C",
        str(DAILY_SUMMARY_REPO),
        "--full-auto",
        "--json",
        "--output-last-message",
        str(dated_output_path),
        "--",
        prompt_with_limit,
    ]

    logger.info(
        "Eseguo Codex per il riassunto (repo=%s, output=%s).",
        DAILY_SUMMARY_REPO,
        dated_output_path,
    )
    logger.debug("Argomenti Codex: %s", cmd)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Comando 'codex' non trovato nel PATH.") from exc

    logger.debug("Codex avviato (pid=%s).", proc.pid)

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    last_output = datetime.now()

    def _bump_last_output():
        nonlocal last_output
        last_output = datetime.now()

    stdout_task = asyncio.create_task(
        _log_stream("stdout", proc.stdout, stdout_lines, _bump_last_output)
    )
    stderr_task = asyncio.create_task(
        _log_stream("stderr", proc.stderr, stderr_lines, _bump_last_output)
    )
    heartbeat_task = asyncio.create_task(_heartbeat(proc, lambda: last_output))

    returncode = await proc.wait()
    await asyncio.gather(stdout_task, stderr_task)
    heartbeat_task.cancel()
    with suppress(asyncio.CancelledError):
        await heartbeat_task

    if returncode != 0:
        stdout_excerpt = "\n".join(stdout_lines[-20:])
        stderr_excerpt = "\n".join(stderr_lines[-20:])
        raise RuntimeError(
            f"codex exec ha restituito exit code {returncode}. "
            f"stdout='{stdout_excerpt}' stderr='{stderr_excerpt}'"
        )

    try:
        summary = dated_output_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"File di output del riassunto mancante: {dated_output_path}"
        ) from exc

    latest_output_path.write_text(summary, encoding="utf-8")
    logger.debug("Copiato riassunto anche in %s per riferimento rapido.", latest_output_path)

    logger.debug("Lettura output Codex completata (%d caratteri).", len(summary))
    logger.info("Riassunto giornaliero completato.")
    return summary


def _resolve_output_paths() -> Tuple[Path, Path]:
    base = DAILY_SUMMARY_OUTPUT_FILE
    stamp = datetime.now().strftime("%Y%m%d")
    if base.suffix:
        dated_name = f"{base.stem}_{stamp}{base.suffix}"
    else:
        dated_name = f"{base.name}_{stamp}"
    return base.with_name(dated_name), base


def _prepare_scope_dir() -> Path:
    scope_root = DAILY_SUMMARY_SCOPE_DIR
    cutoff_ts = time.time() - (DAILY_SUMMARY_LOOKBACK_HOURS * 3600)
    if scope_root.exists():
        shutil.rmtree(scope_root)
    scope_root.mkdir(parents=True, exist_ok=True)

    chats_total = 0
    chats_with_recent = 0
    messages_total = 0

    for entry in DATA_DIR.iterdir():
        if not entry.is_dir():
            continue
        if not _is_chat_dir(entry):
            continue
        chats_total += 1
        scope_chat_dir = scope_root / entry.name
        scope_chat_dir.mkdir(parents=True, exist_ok=True)

        transcript_src = entry / "transcript.ndjson"
        transcript_dest = scope_chat_dir / "transcript_last_24h.ndjson"
        recent_count = _copy_recent_transcript(transcript_src, transcript_dest, cutoff_ts)
        if recent_count:
            chats_with_recent += 1
            messages_total += recent_count
        elif transcript_dest.exists():
            transcript_dest.unlink()

        state_src = entry / "state.md"
        if state_src.exists():
            shutil.copy2(state_src, scope_chat_dir / "state.md")

    metadata = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "lookback_hours": DAILY_SUMMARY_LOOKBACK_HOURS,
        "cutoff_timestamp": int(cutoff_ts),
        "chats_total": chats_total,
        "chats_with_recent_msgs": chats_with_recent,
        "messages_in_scope": messages_total,
    }
    (scope_root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        "Cartella scope aggiornata in %s: %d chat (%d con messaggi recenti), %d messaggi >= %dh.",
        scope_root,
        chats_total,
        chats_with_recent,
        messages_total,
        DAILY_SUMMARY_LOOKBACK_HOURS,
    )
    return scope_root


def _copy_recent_transcript(src: Path, dest: Path, cutoff_ts: float) -> int:
    if not src.exists():
        return 0
    lines = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("ts", 0) >= cutoff_ts:
                lines.append(json.dumps(data, ensure_ascii=False) + "\n")
    if not lines:
        return 0
    dest.write_text("".join(lines), encoding="utf-8")
    return len(lines)


def _is_chat_dir(path: Path) -> bool:
    try:
        int(path.name)
    except ValueError:
        return False
    return True


async def _log_stream(label: str, stream, buffer: list[str], on_line=None):
    if not stream:
        return
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode(errors="ignore").rstrip()
        if not text:
            continue
        buffer.append(text)
        display = text
        if len(display) > STREAM_LOG_MAX_CHARS:
            display = display[:STREAM_LOG_MAX_CHARS] + "... (troncato)"
        logger.info("Codex %s: %s", label, display)
        if on_line:
            on_line()


async def _heartbeat(proc, last_output_getter):
    start = datetime.now()
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            if proc.returncode is not None:
                return
            since_output = datetime.now() - last_output_getter()
            logger.info(
                "Codex ancora in esecuzione (pid=%s, runtime ~%ds, ultimo output ~%ds fa).",
                proc.pid,
                int((datetime.now() - start).total_seconds()),
                int(since_output.total_seconds()),
            )
    except asyncio.CancelledError:
        raise
