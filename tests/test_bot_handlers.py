from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from files_to_agent.bot.handlers import handle_nuova, handle_start
from files_to_agent.core import Core
from files_to_agent.db import connect, init_schema
from files_to_agent.storage import StagingStorage


def _fake_update(user_id: int, chat_id: int, text: str = "/start") -> MagicMock:
    upd = MagicMock()
    upd.effective_user.id = user_id
    upd.effective_chat.id = chat_id
    upd.message = MagicMock()
    upd.message.reply_text = AsyncMock()
    upd.message.text = text
    return upd


def _fake_context(core: Core, allowed: list[int], lang: str = "it") -> MagicMock:
    ctx = MagicMock()
    ctx.bot_data = {"core": core, "allowed_user_ids": allowed, "bot_lang": lang}
    return ctx


@pytest.fixture
def core(tmp_path: Path) -> Core:
    conn = connect(tmp_path / "t.db")
    init_schema(conn)
    state = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
    c = Core(
        conn=conn,
        storage=StagingStorage(tmp_path / "staging"),
        now=lambda: state["now"],
    )
    c._clock_state = state  # type: ignore[attr-defined]
    return c


async def test_start_replies_with_welcome(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_start(upd, ctx)
    upd.message.reply_text.assert_called_once()
    assert "Ciao" in upd.message.reply_text.call_args[0][0]


async def test_unauthorized_user_rejected(core: Core) -> None:
    upd = _fake_update(user_id=999, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_start(upd, ctx)
    upd.message.reply_text.assert_called_once()
    assert "Non sei autorizzato" in upd.message.reply_text.call_args[0][0]


async def test_nuova_creates_session(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10, text="/nuova")
    ctx = _fake_context(core, allowed=[1])
    await handle_nuova(upd, ctx)
    assert core.get_active_draft(chat_id=10) is not None


async def test_nuova_rejects_when_active(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/nuova")
    ctx = _fake_context(core, allowed=[1])
    await handle_nuova(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert "già un upload attivo" in msg


async def test_start_in_english(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1], lang="en")
    await handle_start(upd, ctx)
    assert "Hi" in upd.message.reply_text.call_args[0][0]
