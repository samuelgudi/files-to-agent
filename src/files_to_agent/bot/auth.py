from collections.abc import Awaitable, Callable
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from files_to_agent.messages import t

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


def _resolve_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return (
        (context.chat_data or {}).get("lang")
        or context.bot_data.get("default_lang", "it")
    )


async def _reply(update: Update, text: str) -> None:
    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.answer(text, show_alert=True)


def require_allowed_user(fn: Handler) -> Handler:
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed: list[int] = context.bot_data["allowed_user_ids"]
        user = update.effective_user
        if user is None or user.id not in allowed:
            await _reply(update, t("not_authorized", _resolve_lang(context)))
            return
        await fn(update, context)

    return wrapper


def require_owner(fn: Handler) -> Handler:
    """Stricter than allowed_user — only the FIRST id in allowed_user_ids.

    The first id is treated as the bot owner (self-admin commands like /version, /restart).
    """
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        allowed: list[int] = context.bot_data["allowed_user_ids"]
        owner_id = allowed[0] if allowed else None
        user = update.effective_user
        if user is None or owner_id is None or user.id != owner_id:
            await _reply(update, t("owner_only", _resolve_lang(context)))
            return
        await fn(update, context)

    return wrapper
