import sqlite3
from pathlib import Path

import pytest

from files_to_agent.db import connect, init_schema


def test_init_creates_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "x.db"
    conn = connect(db_file)
    init_schema(conn)

    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    assert "uploads" in tables
    assert "usage_log" in tables


def test_wal_mode_enabled(tmp_path: Path) -> None:
    conn = connect(tmp_path / "x.db")
    init_schema(conn)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_status_check_constraint(tmp_path: Path) -> None:
    conn = connect(tmp_path / "x.db")
    init_schema(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO uploads (id, chat_id, created_at, status) "
            "VALUES ('a', 1, '2026-01-01T00:00:00Z', 'banana')"
        )


def test_init_is_idempotent(tmp_path: Path) -> None:
    db_file = tmp_path / "x.db"
    conn = connect(db_file)
    init_schema(conn)
    init_schema(conn)  # second call must not raise
