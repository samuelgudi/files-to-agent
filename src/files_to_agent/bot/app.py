import logging
import os
from datetime import time as dtime

from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from files_to_agent.bot.handlers import (
    handle_callback,
    handle_cancel,
    handle_cleanup,
    handle_confirm,
    handle_context,
    handle_help,
    handle_info,
    handle_language,
    handle_list_uploads,
    handle_media,
    handle_new,
    handle_pending_text,
    handle_rename,
    handle_restart,
    handle_start,
    handle_update,
    handle_version,
)
from files_to_agent.config import Settings
from files_to_agent.core import Core
from files_to_agent.version import (
    commits_behind,
    fetch_upstream,
    is_git_checkout,
)

log = logging.getLogger(__name__)


# Italian-locale menu — shown to users with Telegram in Italian.
_COMMANDS_IT: list[BotCommand] = [
    BotCommand("nuova",    "Inizia un nuovo upload"),
    BotCommand("conferma", "Finalizza l'upload attivo"),
    BotCommand("annulla",  "Scarta l'upload attivo"),
    BotCommand("rinomina", "Rinomina l'upload (es. /rinomina FattureAprile)"),
    BotCommand("contesto", "Aggiungi una descrizione (es. /contesto Fatture aprile)"),
    BotCommand("lista",    "Elenca i tuoi upload"),
    BotCommand("info",     "Dettagli di un upload (/info <id|nome>)"),
    BotCommand("pulizia",  "Libera spazio (/pulizia 30g per età)"),
    BotCommand("lingua",   "Cambia lingua (italiano / english)"),
    BotCommand("version",  "Versione corrente e aggiornamenti"),
    BotCommand("update",   "Aggiorna il bot (solo proprietario)"),
    BotCommand("riavvia",  "Riavvia il bot (solo proprietario)"),
    BotCommand("help",     "Guida ai comandi"),
    BotCommand("start",    "Mostra il menu principale"),
]

# English-locale menu — shown to users with Telegram in English.
_COMMANDS_EN: list[BotCommand] = [
    BotCommand("new",      "Start a new upload"),
    BotCommand("confirm",  "Finalize the active upload"),
    BotCommand("cancel",   "Discard the active upload"),
    BotCommand("rename",   "Rename the upload (e.g. /rename AprilInvoices)"),
    BotCommand("context",  "Add a description (e.g. /context April invoices)"),
    BotCommand("list",     "List your uploads"),
    BotCommand("info",     "Upload details (/info <id|name>)"),
    BotCommand("cleanup",  "Free space (/cleanup 30g by age)"),
    BotCommand("language", "Change language (English / italiano)"),
    BotCommand("version",  "Current version and updates"),
    BotCommand("update",   "Update the bot (owner only)"),
    BotCommand("restart",  "Restart the bot (owner only)"),
    BotCommand("help",     "Command reference"),
    BotCommand("start",    "Show the main menu"),
]


async def _post_init(app: Application) -> None:
    """Register the slash menu in both languages."""
    try:
        await app.bot.set_my_commands(_COMMANDS_IT)  # default
        await app.bot.set_my_commands(_COMMANDS_EN, language_code="en")
        log.info("slash menu registered (it default + en)")
    except Exception:  # noqa: BLE001
        log.exception("failed to register slash menu")


async def _daily_update_check(context) -> None:  # type: ignore[no-untyped-def]
    """Once a day: fetch origin, DM owner if there are new commits."""
    if not is_git_checkout():
        return
    if not fetch_upstream():
        return
    behind = commits_behind()
    if not behind:
        return
    allowed: list[int] = context.bot_data.get("allowed_user_ids", [])
    if not allowed:
        return
    owner_id = allowed[0]
    from files_to_agent.messages import t  # local import to avoid cycle
    lang = context.bot_data.get("default_lang", "it")
    text = t("update_notify_daily", lang, n=behind)
    try:
        await context.bot.send_message(chat_id=owner_id, text=text, parse_mode="HTML")
    except Exception:  # noqa: BLE001
        log.exception("daily update notify failed")


def build_application(settings: Settings, core: Core) -> Application:
    builder = Application.builder().token(settings.bot_token).post_init(_post_init)
    app = builder.build()
    app.bot_data["core"] = core
    app.bot_data["allowed_user_ids"] = settings.bot_allowed_user_ids
    app.bot_data["max_upload_size_bytes"] = settings.max_upload_size_bytes
    app.bot_data["default_lang"] = settings.bot_lang

    # Bilingual command registrations — both names hit the same handler.
    app.add_handler(CommandHandler(["start"], handle_start))
    app.add_handler(CommandHandler(["help"], handle_help))
    app.add_handler(CommandHandler(["nuova", "new"], handle_new))
    app.add_handler(CommandHandler(["conferma", "confirm"], handle_confirm))
    app.add_handler(CommandHandler(["annulla", "cancel"], handle_cancel))
    app.add_handler(CommandHandler(["rinomina", "rename"], handle_rename))
    app.add_handler(CommandHandler(["contesto", "context"], handle_context))
    app.add_handler(CommandHandler(["lista", "list"], handle_list_uploads))
    app.add_handler(CommandHandler(["info"], handle_info))
    app.add_handler(CommandHandler(["pulizia", "cleanup"], handle_cleanup))
    app.add_handler(CommandHandler(["lingua", "language"], handle_language))
    app.add_handler(CommandHandler(["version"], handle_version))
    app.add_handler(CommandHandler(["update"], handle_update))
    app.add_handler(CommandHandler(["riavvia", "restart"], handle_restart))

    # Inline buttons.
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Media intake.
    app.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
            handle_media,
        )
    )

    # Plain text — only acts when a button has set user_data['awaiting'].
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pending_text))

    # Daily upstream check (toggle via UPDATE_CHECK_DAILY env, default on).
    if os.environ.get("UPDATE_CHECK_DAILY", "true").lower() in ("1", "true", "yes"):
        if app.job_queue is not None:
            # Run once a day at 09:00 UTC.
            app.job_queue.run_daily(_daily_update_check, time=dtime(hour=9, minute=0))
            log.info("daily update check scheduled at 09:00 UTC")
        else:
            log.warning("job_queue not available — install python-telegram-bot[job-queue]")

    return app
