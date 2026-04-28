from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from files_to_agent.core import Core, UploadNotFound
from files_to_agent.db import connect, init_schema
from files_to_agent.storage import StagingStorage


@pytest.fixture
def core(tmp_path: Path) -> Core:
    conn = connect(tmp_path / "t.db")
    init_schema(conn)
    # Mutable clock for time-travel tests.
    state = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
    c = Core(
        conn=conn,
        storage=StagingStorage(tmp_path / "staging"),
        now=lambda: state["now"],
    )
    c._clock_state = state  # type: ignore[attr-defined]
    return c


def test_list_uploads_filters_by_chat(core: Core) -> None:
    a1 = core.create_upload(chat_id=1)
    core.confirm_upload(a1.id)
    core._clock_state["now"] += timedelta(minutes=1)  # type: ignore[attr-defined]
    a2 = core.create_upload(chat_id=1)
    b = core.create_upload(chat_id=2)

    rows = core.list_uploads(chat_id=1)
    ids = [r.id for r in rows]
    assert set(ids) == {a1.id, a2.id}
    assert b.id not in ids


def test_list_uploads_orders_newest_first(core: Core) -> None:
    a = core.create_upload(chat_id=1)
    core.confirm_upload(a.id)
    core._clock_state["now"] += timedelta(minutes=1)  # type: ignore[attr-defined]
    b = core.create_upload(chat_id=1)
    rows = core.list_uploads(chat_id=1)
    assert [r.id for r in rows] == [b.id, a.id]


def test_delete_upload_removes_folder_and_row(core: Core) -> None:
    u = core.create_upload(chat_id=1)
    core.add_file_to_upload(u.id, "a", b"x")
    core.delete_upload(u.id)
    with pytest.raises(UploadNotFound):
        core.get_upload(u.id)
    assert not (core.storage.folder(u.id)).exists()


def test_oldest_uploads(core: Core) -> None:
    a = core.create_upload(chat_id=1)
    core.confirm_upload(a.id)
    core._clock_state["now"] += timedelta(minutes=1)  # type: ignore[attr-defined]
    b = core.create_upload(chat_id=1)
    core.confirm_upload(b.id)
    rows = core.oldest_uploads(chat_id=1, limit=10)
    assert [r.id for r in rows] == [a.id, b.id]


def test_biggest_uploads(core: Core) -> None:
    a = core.create_upload(chat_id=1)
    core.add_file_to_upload(a.id, "x", b"x" * 10)
    core.confirm_upload(a.id)
    b = core.create_upload(chat_id=1)
    core.add_file_to_upload(b.id, "y", b"y" * 100)
    rows = core.biggest_uploads(chat_id=1, limit=10)
    assert [r.id for r in rows] == [b.id, a.id]


def test_uploads_older_than_days(core: Core) -> None:
    a = core.create_upload(chat_id=1)
    core.confirm_upload(a.id)
    core._clock_state["now"] += timedelta(days=10)  # type: ignore[attr-defined]
    core.create_upload(chat_id=1)
    rows = core.uploads_older_than(chat_id=1, days=5)
    assert [r.id for r in rows] == [a.id]
