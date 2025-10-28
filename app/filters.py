from telegram.ext import ContextTypes

CHAT_CFG = {}  # { chat_id: {"mode": "...", "prefix": "..."} }

async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    if "me_username" not in context.bot_data:
        me = await context.bot.get_me()
        context.bot_data["me_username"] = me.username
        context.bot_data["me_id"] = me.id
    return context.bot_data["me_username"]

async def is_addressed(msg, context: ContextTypes.DEFAULT_TYPE, default_mode: str, default_prefix: str) -> bool:
    chat_type = msg.chat.type
    text = (msg.text or msg.caption or "").strip()
    if chat_type == "private":
        return True

    cfg = CHAT_CFG.get(msg.chat.id, {"mode": default_mode, "prefix": default_prefix})
    mode = cfg.get("mode", default_mode)
    prefix = cfg.get("prefix", default_prefix)

    bot_username = await get_bot_username(context)
    bot_id = context.bot_data["me_id"]

    mentioned = f"@{bot_username}" in text
    replied_to_bot = bool(msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.id == bot_id)
    has_prefix = text.startswith(prefix) or text.startswith("/ask")

    if mode == "mention":
        return mentioned or replied_to_bot
    elif mode == "prefix":
        return has_prefix
    return mentioned or replied_to_bot or has_prefix

def strip_addressing(text: str, bot_username: str, prefix: str) -> str:
    t = text.strip()
    if t.startswith(prefix): t = t[len(prefix):].lstrip()
    t = t.replace(f"@{bot_username}", "").strip()
    return t
