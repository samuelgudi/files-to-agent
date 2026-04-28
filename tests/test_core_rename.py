from datetime import UTC, datetime
from pathlib import Path

import pytest

from files_to_agent.core import (
    Core,
    NameAlreadyTaken,
    RenameBlockedAfterUse,
    UploadNotFound,
)
from files_to_agent.db import connect, init_schema
from files_to_agent.storage import StagingStorage


@pytest.fixture
def core(tmp_path: Path) -> Core:
    conn = connect(tmp_path / "t.db")
    init_schema(conn)
    return Core(
        conn=conn,
        storage=StagingStorage(tmp_path / "staging"),
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_rename_active_draft(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    renamed = core.rename_upload(u.id, "FattureAprile")
    assert renamed.name == "FattureAprile"


def test_rename_by_name(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.rename_upload(u.id, "first")
    renamed = core.rename_upload("first", "second")
    assert renamed.name == "second"


def test_find_by_id(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    found = core.find_by_ref(u.id)
    assert found.id == u.id


def test_find_by_name(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.rename_upload(u.id, "alpha")
    found = core.find_by_ref("alpha")
    assert found.id == u.id


def test_find_unknown_raises(core: Core) -> None:
    with pytest.raises(UploadNotFound):
        core.find_by_ref("nonexist")


def test_rename_rejects_duplicate(core: Core) -> None:
    u1 = core.create_upload(chat_id=1)
    core.rename_upload(u1.id, "samename")
    u2 = core.create_upload(chat_id=2)
    with pytest.raises(NameAlreadyTaken):
        core.rename_upload(u2.id, "samename")


def test_rename_blocked_after_use(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.confirm_upload(u.id)
    core.mark_used(u.id, action="email_send", details=None)
    with pytest.raises(RenameBlockedAfterUse):
        core.rename_upload(u.id, "newname")
