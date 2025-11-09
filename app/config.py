import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))

# comportamento chat
DEFAULT_MODE = "mention_or_reply"  # mention | prefix | mention_or_reply
DEFAULT_PREFIX = "!ai"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

def _env_flag(name: str, default: str = "0"):
    value = os.environ.get(name, default)
    if value is None:
        return False
    return value.strip().lower() in ("1", "true", "yes", "y", "on")

def _env_int(name: str, default: int):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

DAILY_SUMMARY_ENABLED = _env_flag("DAILY_SUMMARY_ENABLED", "0")
DAILY_SUMMARY_TIME = os.environ.get("DAILY_SUMMARY_TIME", "00:00")
DAILY_SUMMARY_REPO = Path(os.environ.get("DAILY_SUMMARY_REPO", str(PROJECT_ROOT)))
DAILY_SUMMARY_OUTPUT_FILE = Path(
    os.environ.get("DAILY_SUMMARY_OUTPUT_FILE", str(DATA_DIR / "daily_summary_last.txt"))
)
DAILY_SUMMARY_SCOPE_DIR = Path(
    os.environ.get("DAILY_SUMMARY_SCOPE_DIR", str(DATA_DIR / "_daily_summary_scope"))
)
DAILY_SUMMARY_LOOKBACK_HOURS = _env_int("DAILY_SUMMARY_LOOKBACK_HOURS", 24)
_scope_dir_str = DAILY_SUMMARY_SCOPE_DIR.as_posix()
_DEFAULT_SUMMARY_PROMPT = (
    f"Analizza solo gli estratti generati per l'ultima giornata presenti nella directory "
    f"{_scope_dir_str} (transcript filtrati sulle ultime {DAILY_SUMMARY_LOOKBACK_HOURS} ore e gli state.md correnti). "
    "Produci un riassunto giornaliero conciso ma completo, organizzato in sezioni: "
    "1) Aggiornamenti chiave, 2) Decisioni prese, 3) TODO e blocchi aperti, "
    "4) Rischi o escalation. Sii specifico citando i riferimenti essenziali e mantieni il tono professionale."
)
DAILY_SUMMARY_MAX_WORDS = _env_int("DAILY_SUMMARY_MAX_WORDS", 400)
DAILY_SUMMARY_PROMPT = os.environ.get("DAILY_SUMMARY_PROMPT", _DEFAULT_SUMMARY_PROMPT)
