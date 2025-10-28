import os, io, json, time, tempfile, shutil
from pathlib import Path
from .config import DATA_DIR

class FileStore:
    def __init__(self, chat_id: int):
        self.root = DATA_DIR / str(chat_id)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "boards").mkdir(exist_ok=True)
        (self.root / "checkpoints").mkdir(exist_ok=True)
        self.transcript = self.root / "transcript.ndjson"
        self.state = self.root / "state.md"
        if not self.state.exists():
            self.state.write_text(
                "# Stato della conversazione\n\n"
                "## Fatti confermati\n\n"
                "## Decisioni\n\n"
                "## Vincoli\n\n"
                "## TODO\n\n"
                "## Punti aperti\n\n",
                encoding="utf-8"
            )

    def _write_atomic(self, path: Path, text: str):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(text); tmp.flush(); os.fsync(tmp.fileno())
            tmp_path = tmp.name
        shutil.move(tmp_path, path)

    def append_msg(self, user: str, text: str, is_bot: int = 0):
        line = {"ts": int(time.time()), "user": user or "", "is_bot": int(is_bot), "text": text}
        with io.open(self.transcript, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def tail_msgs(self, max_lines: int = 80):
        if not self.transcript.exists(): return []
        with io.open(self.transcript, "r", encoding="utf-8") as f:
            lines = f.readlines()[-max_lines:]
        return [json.loads(x) for x in lines if x.strip()]

    def read_state(self) -> str:
        return self.state.read_text(encoding="utf-8")

    def write_state(self, text: str):
        self._write_atomic(self.state, text)

    # boards
    def board_path(self, name: str) -> Path:
        return self.root / "boards" / f"{name}.md"

    def append_board(self, name: str, text: str):
        p = self.board_path(name)
        with io.open(p, "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
