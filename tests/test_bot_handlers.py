from datetime import UTC, datetime, timedelta
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


# --- Task 12: media intake ---

async def test_media_during_draft_saves_file(core: Core, tmp_path: Path) -> None:
    from files_to_agent.bot.handlers import handle_media

    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10)

    file_obj = AsyncMock()

    async def _download(path: Path) -> None:
        Path(path).write_bytes(b"hello")

    file_obj.download_to_drive.side_effect = _download
    upd.message.document = MagicMock()
    upd.message.document.file_id = "xyz"
    upd.message.document.file_name = "report.pdf"
    upd.message.document.file_size = 5
    upd.message.photo = []
    upd.message.video = None
    upd.message.audio = None
    upd.message.voice = None

    ctx = _fake_context(core, allowed=[1])
    ctx.bot.get_file = AsyncMock(return_value=file_obj)
    ctx.bot_data["max_upload_size_bytes"] = 1024

    await handle_media(upd, ctx)

    draft = core.get_active_draft(chat_id=10)
    assert draft.file_count == 1
    assert draft.size_bytes == 5


async def test_media_without_active_session_replies_hint(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_media

    upd = _fake_update(user_id=1, chat_id=10)
    upd.message.document = MagicMock()
    upd.message.document.file_id = "xyz"
    upd.message.document.file_name = "x.bin"
    upd.message.document.file_size = 1
    upd.message.photo = []
    upd.message.video = None
    upd.message.audio = None
    upd.message.voice = None

    ctx = _fake_context(core, allowed=[1])
    ctx.bot.get_file = AsyncMock()
    ctx.bot_data["max_upload_size_bytes"] = 1024

    await handle_media(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert "Nessun upload attivo" in msg


# --- Task 13: /conferma + /annulla ---

async def test_conferma_finalizes_session(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_conferma

    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/conferma")
    ctx = _fake_context(core, allowed=[1])
    await handle_conferma(upd, ctx)

    refreshed = core.get_upload(u.id)
    assert refreshed.status.value == "confirmed"
    msg = upd.message.reply_text.call_args[0][0]
    assert u.id in msg


async def test_conferma_no_session(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_conferma

    upd = _fake_update(user_id=1, chat_id=10, text="/conferma")
    ctx = _fake_context(core, allowed=[1])
    await handle_conferma(upd, ctx)
    assert "Nessun upload attivo" in upd.message.reply_text.call_args[0][0]


async def test_annulla_discards_session(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_annulla

    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/annulla")
    ctx = _fake_context(core, allowed=[1])
    await handle_annulla(upd, ctx)

    assert core.get_active_draft(chat_id=10) is None


async def test_annulla_no_session(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_annulla

    upd = _fake_update(user_id=1, chat_id=10, text="/annulla")
    ctx = _fake_context(core, allowed=[1])
    await handle_annulla(upd, ctx)
    assert "Nessun upload attivo" in upd.message.reply_text.call_args[0][0]


# --- Task 14: /rinomina ---

async def test_rinomina_one_arg_renames_active_draft(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_rinomina

    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/rinomina FattureAprile")
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["FattureAprile"]
    await handle_rinomina(upd, ctx)

    refreshed = core.get_upload(u.id)
    assert refreshed.name == "FattureAprile"


async def test_rinomina_two_args_renames_arbitrary(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_rinomina

    u = core.create_upload(chat_id=10)
    core.confirm_upload(u.id)
    upd = _fake_update(user_id=1, chat_id=10, text=f"/rinomina {u.id} Foo")
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id, "Foo"]
    await handle_rinomina(upd, ctx)

    refreshed = core.get_upload(u.id)
    assert refreshed.name == "Foo"


async def test_rinomina_taken_name(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_rinomina

    u1 = core.create_upload(chat_id=10)
    core.rename_upload(u1.id, "X")
    core.confirm_upload(u1.id)
    core.create_upload(chat_id=10)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["X"]
    await handle_rinomina(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert "già in uso" in msg


async def test_rinomina_no_active_draft_one_arg(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_rinomina

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["X"]
    await handle_rinomina(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert "Nessun upload attivo" in msg


# --- Task 14B: /contesto ---

async def test_contesto_one_arg_sets_active_draft(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_contesto

    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/contesto Fatture aprile per Marco")
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["Fatture", "aprile", "per", "Marco"]
    await handle_contesto(upd, ctx)

    refreshed = core.get_upload(u.id)
    assert refreshed.context == "Fatture aprile per Marco"


async def test_contesto_with_ref_sets_arbitrary(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_contesto

    u = core.create_upload(chat_id=10)
    core.confirm_upload(u.id)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id, "Contratto", "Marco"]
    await handle_contesto(upd, ctx)

    assert core.get_upload(u.id).context == "Contratto Marco"


async def test_contesto_clear_with_ref_only(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_contesto

    u = core.create_upload(chat_id=10)
    core.set_context(u.id, "old context")
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id]
    await handle_contesto(upd, ctx)

    assert core.get_upload(u.id).context is None
    assert "rimosso" in upd.message.reply_text.call_args[0][0]


async def test_contesto_allowed_after_use(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_contesto

    u = core.create_upload(chat_id=10)
    core.confirm_upload(u.id)
    core.mark_used(u.id, action="email_send", details=None)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id, "post-hoc", "note"]
    await handle_contesto(upd, ctx)

    assert core.get_upload(u.id).context == "post-hoc note"


async def test_contesto_no_args_shows_usage(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_contesto

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = []
    await handle_contesto(upd, ctx)
    assert "Uso" in upd.message.reply_text.call_args[0][0]


# --- Task 15: /lista + /info ---

async def test_lista_empty(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_lista

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_lista(upd, ctx)
    assert "Nessun upload" in upd.message.reply_text.call_args[0][0]


async def test_lista_shows_uploads(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_lista

    u1 = core.create_upload(chat_id=10)
    core.confirm_upload(u1.id)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_lista(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert u1.id in msg


async def test_info_not_found(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_info

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["nope"]
    await handle_info(upd, ctx)
    assert "Upload non trovato" in upd.message.reply_text.call_args[0][0]


async def test_info_renders(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_info

    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id]
    await handle_info(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert u.id in msg
    assert "draft" in msg


# --- Task 16: /pulizia ---


async def test_pulizia_no_args_shows_candidates(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_pulizia

    u = core.create_upload(chat_id=10)
    core.add_file_to_upload(u.id, "x", b"x" * 100)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = []
    await handle_pulizia(upd, ctx)
    msg = upd.message.reply_text.call_args[0][0]
    assert u.id in msg


async def test_pulizia_by_ref_deletes(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_pulizia

    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id]
    await handle_pulizia(upd, ctx)

    from files_to_agent.core import UploadNotFound

    with pytest.raises(UploadNotFound):
        core.get_upload(u.id)


async def test_pulizia_older_than(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_pulizia

    u_old = core.create_upload(chat_id=10)
    core.confirm_upload(u_old.id)
    core._clock_state["now"] += timedelta(days=10)  # type: ignore[attr-defined]
    u_new = core.create_upload(chat_id=10)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["5g"]
    await handle_pulizia(upd, ctx)

    from files_to_agent.core import UploadNotFound

    with pytest.raises(UploadNotFound):
        core.get_upload(u_old.id)
    assert core.get_upload(u_new.id).id == u_new.id
