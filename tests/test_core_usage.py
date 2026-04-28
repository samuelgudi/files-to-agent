from datetime import UTC, datetime
from pathlib import Path

import pytest

from files_to_agent.core import Core, InvalidStatusTransition
from files_to_agent.db import connect, init_schema
from files_to_agent.models import UploadStatus
from files_to_agent.storage import StagingStorage


@pytest.fixture
def core(tmp_path: Path) -> Core:
    conn = connect(tmp_path / "t.db")
    init_schema(conn)
    return Core(
        conn=conn,
        storage=StagingStorage(tmp_path / "staging"),
        now=lambda: datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


def test_mark_used_requires_confirmed_status(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    with pytest.raises(InvalidStatusTransition):
        core.mark_used(u.id, action="email_send", details=None)


def test_mark_used_first_time_sets_status_and_writes_log(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.confirm_upload(u.id)
    after = core.mark_used(u.id, action="email_send", details={"to": "x@y.z"})
    assert after.status == UploadStatus.USED
    assert after.last_used_at is not None
    log = core.usage_log(u.id)
    assert len(log) == 1
    assert log[0].action == "email_send"
    assert log[0].details == {"to": "x@y.z"}


def test_mark_used_subsequent_calls_append_log(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.confirm_upload(u.id)
    core.mark_used(u.id, action="email_send", details=None)
    core.mark_used(u.id, action="forward", details=None)
    log = core.usage_log(u.id)
    assert [e.action for e in log] == ["email_send", "forward"]


def test_usage_log_empty(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    assert core.usage_log(u.id) == []
