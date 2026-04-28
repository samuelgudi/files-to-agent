from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    handle_start,
)
from files_to_agent.bot.keyboards import kb_cleanup_items
from files_to_agent.core import Core
from files_to_agent.db import connect, init_schema
from files_to_agent.models import Upload, UploadStatus
from files_to_agent.storage import StagingStorage


def _fake_update(user_id: int, chat_id: int, text: str = "/start") -> MagicMock:
    upd = MagicMock()
    upd.effective_user.id = user_id
    upd.effective_chat.id = chat_id
    upd.message = MagicMock()
    upd.message.reply_text = AsyncMock()
    upd.message.text = text
    upd.callback_query = None
    return upd


def _fake_context(core: Core, allowed: list[int], lang: str = "it") -> MagicMock:
    ctx = MagicMock()
    ctx.bot_data = {
        "core": core,
        "allowed_user_ids": allowed,
        "default_lang": lang,
        "max_upload_size_bytes": 2_147_483_648,
    }
    ctx.chat_data = {}
    ctx.user_data = {}
    ctx.args = []
    return ctx


def _last_text(upd: MagicMock) -> str:
    """Get the text from the most recent reply_text call (positional or kw)."""
    args = upd.message.reply_text.call_args
    if args.args:
        return args.args[0]
    return args.kwargs.get("text", "")


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


# ---------- /start, /help, auth ----------


async def test_start_replies_with_welcome(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_start(upd, ctx)
    upd.message.reply_text.assert_called_once()
    assert "Ciao" in _last_text(upd)


async def test_unauthorized_user_rejected(core: Core) -> None:
    upd = _fake_update(user_id=999, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_start(upd, ctx)
    upd.message.reply_text.assert_called_once()
    assert "Non sei autorizzato" in _last_text(upd)


async def test_start_in_english(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1], lang="en")
    await handle_start(upd, ctx)
    assert "Hi" in _last_text(upd)


async def test_help_lists_commands(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_help(upd, ctx)
    text = _last_text(upd)
    # Each major command should be referenced in the help.
    for cmd in ("/nuova", "/conferma", "/rinomina", "/contesto", "/lista", "/pulizia"):
        assert cmd in text


# ---------- /new ----------


async def test_new_creates_session(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10, text="/new")
    ctx = _fake_context(core, allowed=[1])
    await handle_new(upd, ctx)
    assert core.get_active_draft(chat_id=10) is not None


async def test_new_rejects_when_active(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/new")
    ctx = _fake_context(core, allowed=[1])
    await handle_new(upd, ctx)
    assert "già un upload attivo" in _last_text(upd)


# ---------- media intake ----------


async def test_media_during_draft_saves_file(core: Core, tmp_path: Path) -> None:
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
    # Hint should be appended.
    assert "💡" in _last_text(upd)


async def test_media_hint_cycles(core: Core) -> None:
    """Two consecutive uploads should produce different hints (round-robin)."""
    from files_to_agent.bot import handlers as h
    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    file_obj = AsyncMock()

    async def _dl(path: Path) -> None:
        Path(path).write_bytes(b"x")

    file_obj.download_to_drive.side_effect = _dl
    ctx.bot.get_file = AsyncMock(return_value=file_obj)
    ctx.bot_data["max_upload_size_bytes"] = 1024

    upd.message.document = MagicMock(file_id="a", file_name="a.bin", file_size=1)
    upd.message.photo = []
    upd.message.video = upd.message.audio = upd.message.voice = None
    await h.handle_media(upd, ctx)
    first = _last_text(upd)
    upd.message.reply_text.reset_mock()
    upd.message.document = MagicMock(file_id="b", file_name="b.bin", file_size=1)
    await h.handle_media(upd, ctx)
    second = _last_text(upd)
    # The cycling means the hint line should differ between the two messages.
    hint1 = first.split("\n\n")[-1]
    hint2 = second.split("\n\n")[-1]
    assert hint1 != hint2


async def test_media_without_active_session_replies_hint(core: Core) -> None:
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
    assert "Nessun upload attivo" in _last_text(upd)


# ---------- /confirm /cancel ----------


async def test_confirm_finalizes_session(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/confirm")
    ctx = _fake_context(core, allowed=[1])
    await handle_confirm(upd, ctx)

    refreshed = core.get_upload(u.id)
    assert refreshed.status.value == "confirmed"
    text = _last_text(upd)
    assert u.id in text
    # ID must be wrapped in <code> for tap-to-copy.
    assert f"<code>{u.id}</code>" in text
    # The misleading email line must be gone.
    assert "Bozza email" not in text
    assert "Draft email" not in text


async def test_confirm_no_session(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10, text="/confirm")
    ctx = _fake_context(core, allowed=[1])
    await handle_confirm(upd, ctx)
    assert "Nessun upload attivo" in _last_text(upd)


async def test_cancel_discards_session(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/cancel")
    ctx = _fake_context(core, allowed=[1])
    await handle_cancel(upd, ctx)
    assert core.get_active_draft(chat_id=10) is None


async def test_cancel_no_session(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10, text="/cancel")
    ctx = _fake_context(core, allowed=[1])
    await handle_cancel(upd, ctx)
    assert "Nessun upload attivo" in _last_text(upd)


async def test_cancel_clears_pending_input(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/cancel")
    ctx = _fake_context(core, allowed=[1])
    ctx.user_data["awaiting"] = "rename"
    await handle_cancel(upd, ctx)
    # Draft NOT cancelled — only the pending input.
    assert core.get_active_draft(chat_id=10) is not None
    assert ctx.user_data.get("awaiting") is None


# ---------- /rename ----------


async def test_rename_one_arg_renames_active_draft(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/rename FattureAprile")
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["FattureAprile"]
    await handle_rename(upd, ctx)
    assert core.get_upload(u.id).name == "FattureAprile"


async def test_rename_two_args_renames_arbitrary(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    core.confirm_upload(u.id)
    upd = _fake_update(user_id=1, chat_id=10, text=f"/rename {u.id} Foo")
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id, "Foo"]
    await handle_rename(upd, ctx)
    assert core.get_upload(u.id).name == "Foo"


async def test_rename_taken_name(core: Core) -> None:
    u1 = core.create_upload(chat_id=10)
    core.rename_upload(u1.id, "X")
    core.confirm_upload(u1.id)
    core.create_upload(chat_id=10)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["X"]
    await handle_rename(upd, ctx)
    assert "già in uso" in _last_text(upd)


async def test_rename_no_active_draft_one_arg(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["X"]
    await handle_rename(upd, ctx)
    assert "Nessun upload attivo" in _last_text(upd)


# ---------- /context ----------


async def test_context_one_arg_sets_active_draft(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="/context Fatture aprile per Marco")
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["Fatture", "aprile", "per", "Marco"]
    await handle_context(upd, ctx)
    assert core.get_upload(u.id).context == "Fatture aprile per Marco"


async def test_context_with_ref_sets_arbitrary(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    core.confirm_upload(u.id)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id, "Contratto", "Marco"]
    await handle_context(upd, ctx)
    assert core.get_upload(u.id).context == "Contratto Marco"


async def test_context_clear_with_ref_only(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    core.set_context(u.id, "old context")
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id]
    await handle_context(upd, ctx)
    assert core.get_upload(u.id).context is None
    assert "rimosso" in _last_text(upd)


async def test_context_no_args_shows_usage(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = []
    await handle_context(upd, ctx)
    assert "Uso" in _last_text(upd)


# ---------- /list /info /cleanup ----------


async def test_list_empty(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_list_uploads(upd, ctx)
    assert "Nessun upload" in _last_text(upd)


async def test_list_shows_uploads(core: Core) -> None:
    u1 = core.create_upload(chat_id=10)
    core.confirm_upload(u1.id)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_list_uploads(upd, ctx)
    assert u1.id in _last_text(upd)


async def test_info_not_found(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["nope"]
    await handle_info(upd, ctx)
    assert "Upload non trovato" in _last_text(upd)


async def test_info_renders(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id]
    await handle_info(upd, ctx)
    text = _last_text(upd)
    assert u.id in text
    assert "draft" in text


async def test_cleanup_no_args_shows_candidates(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    core.add_file_to_upload(u.id, "x", b"x" * 100)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = []
    await handle_cleanup(upd, ctx)
    assert u.id in _last_text(upd)


async def test_cleanup_by_ref_deletes(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = [u.id]
    await handle_cleanup(upd, ctx)

    from files_to_agent.core import UploadNotFound

    with pytest.raises(UploadNotFound):
        core.get_upload(u.id)


async def test_cleanup_older_than(core: Core) -> None:
    u_old = core.create_upload(chat_id=10)
    core.confirm_upload(u_old.id)
    core._clock_state["now"] += timedelta(days=10)  # type: ignore[attr-defined]
    u_new = core.create_upload(chat_id=10)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = ["5g"]
    await handle_cleanup(upd, ctx)

    from files_to_agent.core import UploadNotFound

    with pytest.raises(UploadNotFound):
        core.get_upload(u_old.id)
    assert core.get_upload(u_new.id).id == u_new.id


# ---------- /language + callbacks ----------


async def test_language_command_replies_with_picker(core: Core) -> None:
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handle_language(upd, ctx)
    text = _last_text(upd)
    assert "lingua" in text.lower() or "language" in text.lower()


def _fake_callback_update(
    user_id: int, chat_id: int, data: str,
) -> MagicMock:
    upd = MagicMock()
    upd.effective_user.id = user_id
    upd.effective_chat.id = chat_id
    upd.message = MagicMock()  # used as fallback for replies
    upd.message.reply_text = AsyncMock()
    upd.callback_query = MagicMock()
    upd.callback_query.data = data
    upd.callback_query.answer = AsyncMock()
    upd.callback_query.message = MagicMock()
    upd.callback_query.message.reply_text = AsyncMock()
    return upd


async def test_callback_lang_en_persists(core: Core) -> None:
    upd = _fake_callback_update(user_id=1, chat_id=10, data="lang:en")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)
    assert core.get_chat_lang(10) == "en"
    assert ctx.chat_data["lang"] == "en"


async def test_callback_lang_it_persists(core: Core) -> None:
    upd = _fake_callback_update(user_id=1, chat_id=10, data="lang:it")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)
    assert core.get_chat_lang(10) == "it"


async def test_callback_new_creates_session(core: Core) -> None:
    upd = _fake_callback_update(user_id=1, chat_id=10, data="new")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)
    assert core.get_active_draft(chat_id=10) is not None


async def test_callback_rename_sets_awaiting(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_callback_update(user_id=1, chat_id=10, data="rename")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)
    assert ctx.user_data.get("awaiting") == "rename"


async def test_callback_context_sets_awaiting(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_callback_update(user_id=1, chat_id=10, data="context")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)
    assert ctx.user_data.get("awaiting") == "context"


# ---------- pending text flow ----------


async def test_pending_text_renames_after_button(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="MyName")
    ctx = _fake_context(core, allowed=[1])
    ctx.user_data["awaiting"] = "rename"
    await handle_pending_text(upd, ctx)
    assert core.get_upload(u.id).name == "MyName"
    assert ctx.user_data.get("awaiting") is None


async def test_pending_text_sets_context_after_button(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="context for the upload")
    ctx = _fake_context(core, allowed=[1])
    ctx.user_data["awaiting"] = "context"
    await handle_pending_text(upd, ctx)
    assert core.get_upload(u.id).context == "context for the upload"


async def test_pending_text_ignored_without_flag(core: Core) -> None:
    core.create_upload(chat_id=10)
    upd = _fake_update(user_id=1, chat_id=10, text="random message")
    ctx = _fake_context(core, allowed=[1])
    await handle_pending_text(upd, ctx)
    upd.message.reply_text.assert_not_called()


async def test_command_clears_stale_awaiting(core: Core) -> None:
    """If a user abandons a button-prompt (awaiting=rename) and runs /new,
    the stale flag must be cleared so their next plain text isn't misrouted."""
    core.create_upload(chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.user_data["awaiting"] = "rename"

    # Abandon: cancel the existing draft, then start a new one.
    upd_cancel = _fake_update(user_id=1, chat_id=10, text="/cancel")
    await handle_cancel(upd_cancel, ctx)  # this clears awaiting (input-cancel branch)
    # Stale flag re-applied (simulating a different abandonment path):
    ctx.user_data["awaiting"] = "rename"

    upd_new = _fake_update(user_id=1, chat_id=10, text="/new")
    await handle_new(upd_new, ctx)
    assert ctx.user_data.get("awaiting") is None


# ---------- per-chat language persistence ----------


async def test_per_chat_lang_overrides_default(core: Core) -> None:
    core.set_chat_lang(10, "en")
    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1], lang="it")
    await handle_start(upd, ctx)
    assert "Hi" in _last_text(upd)


# ---------- /version /update authorization ----------


async def test_version_owner_only(core: Core) -> None:
    """Non-owner users get a refusal."""
    from files_to_agent.bot.handlers import handle_version

    upd = _fake_update(user_id=42, chat_id=10)
    ctx = _fake_context(core, allowed=[1, 42])  # 42 is allowed but not the owner
    await handle_version(upd, ctx)
    assert "proprietario" in _last_text(upd) or "owner" in _last_text(upd).lower()


async def test_update_owner_only(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_update

    upd = _fake_update(user_id=42, chat_id=10)
    ctx = _fake_context(core, allowed=[1, 42])
    await handle_update(upd, ctx)
    assert "proprietario" in _last_text(upd) or "owner" in _last_text(upd).lower()


async def test_restart_owner_only(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_restart

    upd = _fake_update(user_id=42, chat_id=10)
    ctx = _fake_context(core, allowed=[1, 42])  # 42 is allowed but not the owner
    await handle_restart(upd, ctx)
    assert "proprietario" in _last_text(upd) or "owner" in _last_text(upd).lower()


async def test_restart_supervised_calls_schedule_exit(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    def _fake_exit() -> None:
        called["exit"] = True

    monkeypatch.setattr(handlers_mod, "detect_mode", lambda: "supervised_git")
    monkeypatch.setattr(handlers_mod, "schedule_self_exit", _fake_exit)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is True
    assert "Riavvio" in _last_text(upd) or "Restart" in _last_text(upd)


async def test_restart_docker_calls_schedule_exit(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    def _fake_exit() -> None:
        called["exit"] = True

    monkeypatch.setattr(handlers_mod, "detect_mode", lambda: "docker")
    monkeypatch.setattr(handlers_mod, "schedule_self_exit", _fake_exit)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is True


async def test_restart_bare_git_warns_no_supervisor(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    monkeypatch.setattr(handlers_mod, "detect_mode", lambda: "bare_git")
    monkeypatch.setattr(
        handlers_mod, "schedule_self_exit", lambda: called.__setitem__("exit", True)
    )

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is False
    text = _last_text(upd)
    # Reuses update_no_supervisor — Italian wording "supervisore" or English "supervisor".
    assert "supervisor" in text.lower()


# ---------- kb_cleanup_items factory ----------


def _fake_upload(upload_id: str, name: str | None = None, size: int = 100) -> Upload:
    return Upload(
        id=upload_id,
        name=name,
        chat_id=10,
        status=UploadStatus.CONFIRMED,
        context=None,
        file_count=1,
        size_bytes=size,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_used_at=None,
    )


def test_kb_cleanup_items_one_button_per_unique_upload() -> None:
    a = _fake_upload("aaaa1111", name="alpha", size=1000)
    b = _fake_upload("bbbb2222", name=None, size=2000)
    # Same id appears in both lists — must dedupe to a single button.
    markup = kb_cleanup_items([a, b], [a], lang="it")
    flat = [btn for row in markup.inline_keyboard for btn in row]
    callback_ids = [btn.callback_data for btn in flat]
    assert callback_ids.count("del:aaaa1111") == 1
    assert "del:bbbb2222" in callback_ids
    assert len(flat) == 2


def test_kb_cleanup_items_button_text_uses_name_or_id() -> None:
    a = _fake_upload("aaaa1111", name="alpha", size=1024)
    b = _fake_upload("bbbb2222", name=None, size=2048)
    markup = kb_cleanup_items([a], [b], lang="it")
    flat = [btn for row in markup.inline_keyboard for btn in row]
    by_id = {btn.callback_data: btn.text for btn in flat}
    assert "alpha" in by_id["del:aaaa1111"]
    assert "bbbb2222" in by_id["del:bbbb2222"]


def test_kb_cleanup_items_empty_returns_empty_keyboard() -> None:
    markup = kb_cleanup_items([], [], lang="it")
    flat = [btn for row in markup.inline_keyboard for btn in row]
    assert flat == []


# ---------- cleanup view attaches per-item delete buttons ----------


async def test_cleanup_no_args_attaches_per_item_delete_buttons(core: Core) -> None:
    u1 = core.create_upload(chat_id=10)
    core.add_file_to_upload(u1.id, "a", b"a" * 100)
    core.confirm_upload(u1.id)
    u2 = core.create_upload(chat_id=10)
    core.add_file_to_upload(u2.id, "b", b"b" * 200)
    core.confirm_upload(u2.id)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = []
    await handle_cleanup(upd, ctx)

    markup = upd.message.reply_text.call_args.kwargs["reply_markup"]
    flat = [btn for row in markup.inline_keyboard for btn in row]
    callback_data = {btn.callback_data for btn in flat}
    assert f"del:{u1.id}" in callback_data
    assert f"del:{u2.id}" in callback_data


# ---------- del:<id> callback ----------


async def test_callback_del_deletes_upload(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    core.add_file_to_upload(u.id, "x", b"x" * 100)
    core.confirm_upload(u.id)

    upd = _fake_callback_update(user_id=1, chat_id=10, data=f"del:{u.id}")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)

    from files_to_agent.core import UploadNotFound
    with pytest.raises(UploadNotFound):
        core.get_upload(u.id)


async def test_callback_del_unknown_id_replies_not_found(core: Core) -> None:
    upd = _fake_callback_update(user_id=1, chat_id=10, data="del:doesnotexist")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)

    text_calls = upd.message.reply_text.call_args_list
    combined = " ".join(
        (call.args[0] if call.args else call.kwargs.get("text", ""))
        for call in text_calls
    )
    # Reuses the existing info_not_found template.
    assert "doesnotexist" in combined


async def test_callback_del_other_chat_blocked(core: Core) -> None:
    # Upload created in chat 999 must not be deletable from chat 10.
    u = core.create_upload(chat_id=999)
    core.add_file_to_upload(u.id, "x", b"x" * 10)
    core.confirm_upload(u.id)

    upd = _fake_callback_update(user_id=1, chat_id=10, data=f"del:{u.id}")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)

    # Upload still exists.
    assert core.get_upload(u.id).id == u.id
