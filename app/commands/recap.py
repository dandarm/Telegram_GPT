import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from ..store import FileStore
from ..llm import chat_with_llm

def format_transcript(rows):
    return "\n".join(f'{r["user"] or "utente"}: {r["text"]}' for r in rows)

def chunk_text(text: str, n: int = 3000):
    return [text[i:i+n] for i in range(0, len(text), n)]

def summarize_chunk(chunk: str, goal: str):
    prompt = (
        "Riassumi accuratamente l'estratto di chat.\n"
        f"Obiettivo: {goal}\n\nTESTO:\n{chunk}\n\n"
        "Output con sezioni: • Temi • Decisioni • TODO • Punti aperti • Tono."
    )
    return chat_with_llm(prompt)

def fuse_summaries(partials: list[str]):
    prompt = (
        "Fondi i seguenti riassunti parziali in un unico riassunto non ridondante:\n\n" +
        "\n\n".join(partials)
    )
    return chat_with_llm(prompt)

async def cmd_recap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store = FileStore(update.effective_chat.id)
    arg = (context.args[0].lower() if context.args else None)
    limit = int(arg) if (arg and arg.isdigit()) else 250
    rows = store.tail_msgs(limit)
    if not rows:
        await update.message.reply_text("Non ho abbastanza messaggi registrati."); return
    txt = format_transcript(rows)
    chunks = chunk_text(txt, 3000)
    partials = await asyncio.gather(*[asyncio.to_thread(summarize_chunk, c, "Recap recente") for c in chunks])
    final = await asyncio.to_thread(fuse_summaries, partials)
    await update.message.reply_text(final[:3500])

def register(app):
    app.add_handler(CommandHandler("recap", cmd_recap))
