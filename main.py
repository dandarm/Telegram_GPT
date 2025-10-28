import asyncio, logging
logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
from app.lifecycle import run

if __name__ == "__main__":
    asyncio.run(run())
