import asyncio, signal, logging
from telegram.ext import ApplicationBuilder
from .config import TELEGRAM_BOT_TOKEN, DATA_DIR
from .handlers import register_all
from .commands import boards, recap

logger = logging.getLogger("bot")

def known_chat_ids():
    if not DATA_DIR.exists() or not DATA_DIR.is_dir():
        return []
    ids = []
    for entry in DATA_DIR.iterdir():
        if not entry.is_dir():
            continue
        try:
            ids.append(int(entry.name))
        except ValueError:
            logger.debug(f"Ignoro directory non numerica in DATA_DIR: {entry}")
    return ids

async def notify_all_chats(bot, text: str):
    chat_ids = known_chat_ids()
    if not chat_ids:
        logger.info("Nessuna chat nota per notificare: %s", text)
        return
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text)
        except Exception as e:
            logger.warning(f"Notify '{text}' fallita per chat {chat_id}: {e}")

async def run():
    # Telegram può mantenere aperta la long-polling per ~30s; se read_timeout è più
    # basso (default 5s) la libreria solleva TimedOut. Alziamo i timeout HTTP per
    # evitare l'errore durante il polling.
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    # registra comandi/handler
    register_all(app)
    boards.register(app)
    recap.register(app)

    await app.initialize(); await app.start()
    await notify_all_chats(app.bot, "✅ Bot avviato.")

    await app.updater.start_polling(allowed_updates=None, timeout=30)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(sig, stop.set)
        except NotImplementedError: pass
    await stop.wait()

    await notify_all_chats(app.bot, "🛑 Bot in arresto...")

    await app.updater.stop(); await app.stop(); await app.shutdown()
