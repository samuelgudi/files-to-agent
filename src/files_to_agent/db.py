import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    id            TEXT PRIMARY KEY,
    name          TEXT UNIQUE,
    chat_id       INTEGER NOT NULL,
    created_at    TEXT NOT NULL,
    confirmed_at  TEXT,
    last_used_at  TEXT,
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    file_count    INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','confirmed','used'))
);
CREATE TABLE IF NOT EXISTS usage_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id    TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    used_at      TEXT NOT NULL,
    action       TEXT NOT NULL,
    details_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_uploads_chat_status ON uploads(chat_id, status);
CREATE INDEX IF NOT EXISTS idx_uploads_status     ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at);
CREATE INDEX IF NOT EXISTS idx_uploads_size       ON uploads(size_bytes);
CREATE INDEX IF NOT EXISTS idx_uploads_name       ON uploads(name);
CREATE INDEX IF NOT EXISTS idx_usage_log_upload   ON usage_log(upload_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
