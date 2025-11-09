import asyncio, logging
from app.config import LOG_LEVEL
from app.lifecycle import run

_LOG_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=_LOG_LEVEL,
)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except RuntimeError as exc:
        logging.getLogger("main").error(str(exc))
        raise SystemExit(1)
