import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv; load_dotenv()
import asyncio
from collections import defaultdict, deque



BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

#client = OpenAI(api_key=OPENAI_API_KEY)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = "Sei un assistente utile, conciso e amichevole. Rispondi in italiano."

# --- configurazione per-chat in memoria ---
CHAT_CFG = {}  # { chat_id: {"mode": "mention_or_reply"|"mention"|"prefix", "prefix": "!ai"} }
DEFAULT_MODE = "mention_or_reply"
DEFAULT_PREFIX = "!ai"

CHAT_BUFFER = defaultdict(lambda: deque(maxlen=50))

def push_context_line(chat_id, username, text):
    name = username or "utente"
    CHAT_BUFFER[chat_id].append(f"{name}: {text}")

def build_context(chat_id, max_lines=20):
    return "\n".join(list(CHAT_BUFFER[chat_id])[-max_lines:])

async def cmd_debug_context(update, context):
    chat_id = update.effective_chat.id
    ctx = build_context(chat_id, max_lines=100) or "(vuoto)"
    await update.message.reply_text(f"Ultime 100 righe di contesto:\n{ctx}")

async def cmd_debug_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = build_context(update.effective_chat.id, max_lines=100) or "(vuoto)"
    print(f"/debug_context richiesto in chat {update.effective_chat.id}")
    await update.message.reply_text(f"Ultime 100 righe:\n{ctx}")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Comando sconosciuto: {update.effective_message.text}")
    await update.message.reply_text("Comando non riconosciuto.")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Inviami un messaggio o menzionami in un gruppo.")



# region per sapere se è interpellato

async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    # cache in bot_data per evitare chiamate ripetute
    if "me_username" not in context.bot_data:
        me = await context.bot.get_me()
        context.bot_data["me_username"] = me.username
        context.bot_data["me_id"] = me.id
    return context.bot_data["me_username"]

async def is_addressed(msg, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_type = msg.chat.type
    text = (msg.text or msg.caption or "").strip()

    # in private chat: sempre vero
    if chat_type == "private":
        return True

    # recupera config della chat
    cfg = CHAT_CFG.get(msg.chat.id, {"mode": DEFAULT_MODE, "prefix": DEFAULT_PREFIX})
    mode = cfg.get("mode", DEFAULT_MODE)
    prefix = cfg.get("prefix", DEFAULT_PREFIX)

    bot_username = await get_bot_username(context)
    bot_id = context.bot_data["me_id"]

    # regole base per gruppi
    mentioned = f"@{bot_username}" in text
    replied_to_bot = bool(msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.id == bot_id)
    has_prefix = text.startswith(prefix) or text.startswith("/ask")  # es: supporta anche /ask

    if mode == "mention":
        return mentioned or replied_to_bot
    elif mode == "prefix":
        return has_prefix
    else:  # mention_or_reply (default)
        return mentioned or replied_to_bot or has_prefix

def strip_addressing(text: str, bot_username: str, prefix: str) -> str:
    t = text.strip()
    if t.startswith(prefix):
        t = t[len(prefix):].lstrip()
    t = t.replace(f"@{bot_username}", "").strip()
    return t

#endregion 

# region cambiare comportamento in chat
async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = (context.args or [])
    if not args or args[0] not in ("mention", "prefix", "mention_or_reply"):
        await update.message.reply_text("Uso: /mode <mention|prefix|mention_or_reply>")
        return
    mode = args[0]
    cfg = CHAT_CFG.get(chat_id, {"mode": DEFAULT_MODE, "prefix": DEFAULT_PREFIX})
    cfg["mode"] = mode
    CHAT_CFG[chat_id] = cfg
    await update.message.reply_text(f"Modalità impostata su: {mode}")

async def cmd_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = (context.args or [])
    if not args:
        await update.message.reply_text("Uso: /prefix <prefisso> (es. !ai)")
        return
    pref = args[0]
    cfg = CHAT_CFG.get(chat_id, {"mode": DEFAULT_MODE, "prefix": DEFAULT_PREFIX})
    cfg["prefix"] = pref
    CHAT_CFG[chat_id] = cfg
    await update.message.reply_text(f"Prefisso impostato su: {pref}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao! In gruppo rispondo se mi menzioni, mi rispondi o usi il prefisso.\n"
        "Comandi:\n"
        "/mode <mention|prefix|mention_or_reply>\n"
        "/prefix <prefisso> (es. !ai)\n"
        "Esempi: @mio_bot ciao • !ai spiega cosa fa… • /ask riassumi…"
    )

# endregion

async def chat_with_llm_async(user_text: str) -> str:
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":user_text}
        ],
        temperature=0.4,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()

    #print(f"[RX] chat={msg.chat.id} msg_id={msg.message_id} user={msg.from_user.username} text='{text}'")
    push_context_line(msg.chat.id, msg.from_user.username if msg.from_user else "", text)



    # Filtra: rispondi solo se "interpellato"
    if not await is_addressed(msg, context):
        return

    bot_username = await get_bot_username(context)
    cfg = CHAT_CFG.get(msg.chat.id, {"mode": DEFAULT_MODE, "prefix": DEFAULT_PREFIX})
    clean = strip_addressing(text, bot_username, cfg.get("prefix", DEFAULT_PREFIX))
    if not clean:
        return
    
    context_text = build_context(msg.chat.id, max_lines=20)
    prompt = (
        "Sei un assistente in una chat di gruppo. Usa SOLO il contesto seguente.\n\n"
        f"CONTESTO:\n{context_text}\n\n"
        f"UTENTE ORA: {clean}\n\n"
        "RISPOSTA:"
    )

    try:
        reply = await chat_with_llm_async(prompt)  # ⬅️ IMPORTANTE: usare await
        print("DEBUG type(reply)=", type(reply))
        assert isinstance(reply, str), f"LLM reply type={type(reply)}"
        for i in range(0, len(reply), 3500):
            await msg.reply_text(reply[i:i+3500])
    except Exception as e:
        await msg.reply_text(f"Ops, errore: {e}")



def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mode", cmd_mode))
    app.add_handler(CommandHandler("prefix", cmd_prefix))
    app.add_handler(CommandHandler("debug_context", cmd_debug_context))

    # fallback per comandi non mappati (utile per capire se il bot li riceve)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

if __name__ == "__main__":
    main()
