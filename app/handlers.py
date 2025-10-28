import asyncio, logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters
from .config import DEFAULT_MODE, DEFAULT_PREFIX
from .store import FileStore
from .llm import chat_with_llm
from .filters import CHAT_CFG, get_bot_username, is_addressed, strip_addressing
from .context_builders import build_live_prompt, update_state_from_exchange

logger = logging.getLogger("bot")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao! In gruppo rispondo se menzionato o col prefisso.\n"
        "Comandi: /mode, /prefix, /board, /recap, /debug_context"
    )

async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = (context.args or [])
    if not args or args[0] not in ("mention", "prefix", "mention_or_reply"):
        await update.message.reply_text("Uso: /mode <mention|prefix|mention_or_reply>"); return
    CHAT_CFG.setdefault(chat_id, {})["mode"] = args[0]
    await update.message.reply_text(f"Modalità impostata su: {args[0]}")

async def cmd_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = (context.args or [])
    if not args: await update.message.reply_text("Uso: /prefix <prefisso>"); return
    CHAT_CFG.setdefault(chat_id, {})["prefix"] = args[0]
    await update.message.reply_text(f"Prefisso impostato su: {args[0]}")

async def cmd_debug_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store = FileStore(update.effective_chat.id)
    rows = store.tail_msgs(10)
    lines = [f'{r["user"] or "utente"}: {r["text"]}' for r in rows]
    await update.message.reply_text("Ultime 10:\n" + ("\n".join(lines) or "(vuoto)"))

async def reply_and_log(msg, context, text: str):
    bot_username = await get_bot_username(context)
    for i in range(0, len(text), 3500):
        chunk = text[i:i+3500]
        await msg.reply_text(chunk)
        FileStore(msg.chat.id).append_msg(bot_username, chunk, is_bot=1)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()
    speaker = (msg.from_user.username or (msg.from_user.full_name if msg.from_user else "utente"))

    logger.info(f"[RX] chat={msg.chat.id} msg_id={msg.message_id} user={speaker} text='{text}'")

    store = FileStore(msg.chat.id)
    store.append_msg(speaker, text, is_bot=0)

    if not await is_addressed(msg, context, DEFAULT_MODE, DEFAULT_PREFIX):
        return

    bot_username = await get_bot_username(context)
    cfg = CHAT_CFG.get(msg.chat.id, {"mode": DEFAULT_MODE, "prefix": DEFAULT_PREFIX})
    clean = strip_addressing(text, bot_username, cfg.get("prefix", DEFAULT_PREFIX))
    if not clean: return

    prompt = build_live_prompt(store, speaker, clean)
    try:
        reply = await asyncio.to_thread(chat_with_llm, prompt)
        await reply_and_log(msg, context, reply)
        await asyncio.to_thread(update_state_from_exchange, store, speaker, clean, reply)
    except Exception as e:
        await msg.reply_text(f"Ops, errore: {e}")

def register_all(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mode", cmd_mode))
    app.add_handler(CommandHandler("prefix", cmd_prefix))
    app.add_handler(CommandHandler("debug_context", cmd_debug_context))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
