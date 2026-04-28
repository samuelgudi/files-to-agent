from datetime import UTC, datetime
from pathlib import Path

import pytest

from files_to_agent.core import (
    ActiveDraftExists,
    Core,
    InvalidStatusTransition,
    NoActiveDraft,
    UploadNotFound,
)
from files_to_agent.db import connect, init_schema
from files_to_agent.models import UploadStatus
from files_to_agent.storage import StagingStorage


@pytest.fixture
def core(tmp_path: Path) -> Core:
    conn = connect(tmp_path / "t.db")
    init_schema(conn)
    storage = StagingStorage(tmp_path / "staging")
    return Core(conn=conn, storage=storage, now=lambda: datetime(2026, 1, 1, tzinfo=UTC))


def test_create_upload_returns_id(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    assert len(u.id) == 8
    assert u.chat_id == 42
    assert u.status == UploadStatus.DRAFT
    assert u.size_bytes == 0
    assert u.file_count == 0


def test_create_rejects_when_active_draft_exists(core: Core) -> None:
    core.create_upload(chat_id=42)
    with pytest.raises(ActiveDraftExists):
        core.create_upload(chat_id=42)


def test_create_allowed_when_other_chats_have_drafts(core: Core) -> None:
    core.create_upload(chat_id=42)
    other = core.create_upload(chat_id=99)
    assert other.chat_id == 99


def test_add_file_updates_size_and_count(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    updated = core.add_file_to_upload(u.id, "x.txt", b"hello")
    assert updated.size_bytes == 5
    assert updated.file_count == 1


def test_add_file_rejects_when_not_draft(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    core.confirm_upload(u.id)
    with pytest.raises(InvalidStatusTransition):
        core.add_file_to_upload(u.id, "x.txt", b"hi")


def test_confirm_transitions_to_confirmed(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    confirmed = core.confirm_upload(u.id)
    assert confirmed.status == UploadStatus.CONFIRMED
    assert confirmed.confirmed_at is not None


def test_confirm_rejects_unknown(core: Core) -> None:
    with pytest.raises(UploadNotFound):
        core.confirm_upload("nonexist")


def test_confirm_rejects_already_confirmed(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    core.confirm_upload(u.id)
    with pytest.raises(InvalidStatusTransition):
        core.confirm_upload(u.id)


def test_cancel_deletes_folder_and_row(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    core.add_file_to_upload(u.id, "a", b"x")
    core.cancel_active_draft(chat_id=42)
    with pytest.raises(UploadNotFound):
        core.get_upload(u.id)


def test_cancel_no_active_draft(core: Core) -> None:
    with pytest.raises(NoActiveDraft):
        core.cancel_active_draft(chat_id=42)


def test_get_active_draft(core: Core) -> None:
    u = core.create_upload(chat_id=42)
    found = core.get_active_draft(chat_id=42)
    assert found is not None
    assert found.id == u.id


def test_get_active_draft_returns_none(core: Core) -> None:
    assert core.get_active_draft(chat_id=42) is None
