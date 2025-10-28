from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from ..store import FileStore

async def cmd_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store = FileStore(update.effective_chat.id)
    args = context.args or []
    if not args:
        await update.message.reply_text("Uso: /board <list|show|add> ..."); return
    sub = args[0]
    if sub == "list":
        boards = [p.stem for p in (store.root/"boards").glob("*.md")]
        await update.message.reply_text("Boards:\n" + "\n".join(boards or ["(vuoto)"]))
    elif sub == "show" and len(args) >= 2:
        p = store.board_path(args[1])
        txt = p.read_text(encoding="utf-8") if p.exists() else "(vuoto)"
        await update.message.reply_text(txt[-3500:] if len(txt) > 3500 else txt)
    elif sub == "add" and len(args) >= 3:
        name = args[1]; content = " ".join(args[2:])
        store.append_board(name, f"- {content}")
        await update.message.reply_text(f"Ok, aggiunto a {name}.")
    else:
        await update.message.reply_text("Uso: /board <list|show|add> ...")

def register(app):
    app.add_handler(CommandHandler("board", cmd_board))
