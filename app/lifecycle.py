import asyncio, signal, logging
from telegram.ext import ApplicationBuilder
from .config import TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID
from .handlers import register_all
from .commands import boards, recap

logger = logging.getLogger("bot")

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
    if ADMIN_CHAT_ID:
        try: await app.bot.send_message(ADMIN_CHAT_ID, "✅ Bot avviato.")
        except Exception as e: logger.warning(f"Notify avvio fallita: {e}")

    await app.updater.start_polling(allowed_updates=None, timeout=30)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(sig, stop.set)
        except NotImplementedError: pass
    await stop.wait()

    if ADMIN_CHAT_ID:
        try: await app.bot.send_message(ADMIN_CHAT_ID, "🛑 Bot in arresto...")
        except Exception as e: logger.warning(f"Notify arresto fallita: {e}")

    await app.updater.stop(); await app.stop(); await app.shutdown()
