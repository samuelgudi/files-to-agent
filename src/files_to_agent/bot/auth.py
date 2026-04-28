from collections.abc import Awaitable, Callable
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from files_to_agent.messages import t


def require_allowed_user(
    fn: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed: list[int] = context.bot_data["allowed_user_ids"]
        user = update.effective_user
        if user is None or user.id not in allowed:
            if update.message:
                lang = context.bot_data.get("bot_lang", "it")
                await update.message.reply_text(t("not_authorized", lang))
            return
        await fn(update, context)

    return wrapper
