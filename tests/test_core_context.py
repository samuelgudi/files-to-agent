from datetime import UTC, datetime
from pathlib import Path

import pytest

from files_to_agent.core import Core, UploadNotFound
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


def test_set_context(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    updated = core.set_context(u.id, "Fatture aprile per Marco")
    assert updated.context == "Fatture aprile per Marco"


def test_set_context_clear(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.set_context(u.id, "x")
    cleared = core.set_context(u.id, None)
    assert cleared.context is None


def test_set_context_allowed_after_use(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.confirm_upload(u.id)
    core.mark_used(u.id, action="email_send", details=None)
    updated = core.set_context(u.id, "post-hoc note")
    assert updated.context == "post-hoc note"


def test_set_context_unknown_ref_raises(core: Core) -> None:
    with pytest.raises(UploadNotFound):
        core.set_context("nope", "x")


def test_set_context_by_name(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.rename_upload(u.id, "FattureAprile")
    updated = core.set_context("FattureAprile", "ctx")
    assert updated.id == u.id
    assert updated.context == "ctx"
