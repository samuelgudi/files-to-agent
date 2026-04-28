import asyncio
import logging
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI
from telegram.ext import Application

from files_to_agent.bot.app import build_application, register_slash_menu
from files_to_agent.config import Settings
from files_to_agent.core import Core
from files_to_agent.db import connect, init_schema
from files_to_agent.resolver.api import build_app as build_resolver
from files_to_agent.storage import StagingStorage

log = logging.getLogger(__name__)


@dataclass
class Components:
    settings: Settings
    core: Core
    bot_app: Application
    resolver_app: FastAPI


def build_components(settings: Settings | None = None) -> Components:
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level)
    conn = connect(settings.db_path)
    init_schema(conn)
    storage = StagingStorage(settings.staging_dir)
    core = Core(conn=conn, storage=storage)
    bot_app = build_application(settings, core)
    resolver_app = build_resolver(core=core, settings=settings)
    return Components(
        settings=settings, core=core, bot_app=bot_app, resolver_app=resolver_app
    )


async def run(settings: Settings | None = None) -> None:
    components = build_components(settings)
    s = components.settings

    config = uvicorn.Config(
        app=components.resolver_app,
        host=s.resolver_host,
        port=s.resolver_port,
        log_level=s.log_level.lower(),
        access_log=False,
    )
    server = uvicorn.Server(config)

    bot = components.bot_app
    await bot.initialize()
    # PTB only auto-runs post_init from run_polling/run_webhook; we manage the
    # lifecycle manually (co-hosted with FastAPI), so register the menu directly.
    await register_slash_menu(bot)
    await bot.start()
    await bot.updater.start_polling()
    log.info("bot polling started")

    try:
        await server.serve()
    finally:
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()


def run_blocking() -> None:
    asyncio.run(run())
