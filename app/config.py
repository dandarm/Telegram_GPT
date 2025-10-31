import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))  # opzionale
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))

# comportamento chat
DEFAULT_MODE = "mention_or_reply"  # mention | prefix | mention_or_reply
DEFAULT_PREFIX = "!ai"
