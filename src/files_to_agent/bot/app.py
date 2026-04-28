from telegram.ext import Application, CommandHandler, MessageHandler, filters

from files_to_agent.bot.handlers import (
    handle_annulla,
    handle_conferma,
    handle_contesto,
    handle_info,
    handle_lista,
    handle_media,
    handle_nuova,
    handle_pulizia,
    handle_rinomina,
    handle_start,
)
from files_to_agent.config import Settings
from files_to_agent.core import Core


def build_application(settings: Settings, core: Core) -> Application:
    app = Application.builder().token(settings.bot_token).build()
    app.bot_data["core"] = core
    app.bot_data["allowed_user_ids"] = settings.bot_allowed_user_ids
    app.bot_data["max_upload_size_bytes"] = settings.max_upload_size_bytes
    app.bot_data["bot_lang"] = settings.bot_lang
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("nuova", handle_nuova))
    app.add_handler(CommandHandler("conferma", handle_conferma))
    app.add_handler(CommandHandler("annulla", handle_annulla))
    app.add_handler(CommandHandler("rinomina", handle_rinomina))
    app.add_handler(CommandHandler("contesto", handle_contesto))
    app.add_handler(CommandHandler("lista", handle_lista))
    app.add_handler(CommandHandler("info", handle_info))
    app.add_handler(CommandHandler("pulizia", handle_pulizia))
    app.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
            handle_media,
        )
    )
    return app
