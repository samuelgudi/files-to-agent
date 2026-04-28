from unittest.mock import AsyncMock, MagicMock

import pytest

from files_to_agent.bot.app import register_slash_menu


@pytest.mark.asyncio
async def test_register_slash_menu_calls_set_my_commands_twice() -> None:
    """Registers default (Italian) menu and English-locale menu."""
    app = MagicMock()
    app.bot = MagicMock()
    app.bot.set_my_commands = AsyncMock()

    await register_slash_menu(app)

    assert app.bot.set_my_commands.call_count == 2
    # First call has no language_code → default (IT) menu.
    first_kwargs = app.bot.set_my_commands.call_args_list[0].kwargs
    assert "language_code" not in first_kwargs
    # Second call sets the EN-locale menu.
    second_kwargs = app.bot.set_my_commands.call_args_list[1].kwargs
    assert second_kwargs.get("language_code") == "en"


@pytest.mark.asyncio
async def test_register_slash_menu_swallows_telegram_errors() -> None:
    """A Telegram-side error must not crash the runner."""
    app = MagicMock()
    app.bot = MagicMock()
    app.bot.set_my_commands = AsyncMock(side_effect=RuntimeError("network down"))

    # Must not raise.
    await register_slash_menu(app)
    # And it tried at least once.
    assert app.bot.set_my_commands.call_count >= 1
