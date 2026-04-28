import secrets
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from files_to_agent.models import Upload, UploadStatus, UsageLogEntry
from files_to_agent.storage import StagingStorage


class CoreError(Exception):
    pass


class ActiveDraftExists(CoreError):  # noqa: N818
    pass


class NoActiveDraft(CoreError):  # noqa: N818
    pass


class UploadNotFound(CoreError):  # noqa: N818
    pass


class InvalidStatusTransition(CoreError):  # noqa: N818
    pass


class NameAlreadyTaken(CoreError):  # noqa: N818
    pass


class RenameBlockedAfterUse(CoreError):  # noqa: N818
    pass


def _new_id() -> str:
    return secrets.token_urlsafe(6)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _row_to_upload(row: sqlite3.Row) -> Upload:
    return Upload(
        id=row["id"],
        name=row["name"],
        chat_id=row["chat_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        confirmed_at=datetime.fromisoformat(row["confirmed_at"]) if row["confirmed_at"] else None,
        last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
        size_bytes=row["size_bytes"],
        file_count=row["file_count"],
        status=UploadStatus(row["status"]),
    )


class Core:
    def __init__(
        self,
        conn: sqlite3.Connection,
        storage: StagingStorage,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.conn = conn
        self.storage = storage
        self._now = now

    # ---------- queries ----------

    def get_upload(self, upload_id: str) -> Upload:
        row = self.conn.execute(
            "SELECT * FROM uploads WHERE id = ?", (upload_id,)
        ).fetchone()
        if row is None:
            raise UploadNotFound(upload_id)
        return _row_to_upload(row)

    def get_active_draft(self, chat_id: int) -> Upload | None:
        row = self.conn.execute(
            "SELECT * FROM uploads WHERE chat_id=? AND status='draft' "
            "ORDER BY created_at DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        return _row_to_upload(row) if row else None

    def find_by_ref(self, ref: str) -> Upload:
        row = self.conn.execute(
            "SELECT * FROM uploads WHERE id=? OR name=? LIMIT 1", (ref, ref)
        ).fetchone()
        if row is None:
            raise UploadNotFound(ref)
        return _row_to_upload(row)

    # ---------- lifecycle ----------

    def create_upload(self, chat_id: int) -> Upload:
        if self.get_active_draft(chat_id):
            raise ActiveDraftExists(chat_id)
        upload_id = _new_id()
        while self.conn.execute(
            "SELECT 1 FROM uploads WHERE id=?", (upload_id,)
        ).fetchone():
            upload_id = _new_id()
        now = self._now()
        self.storage.create_folder(upload_id)
        self.conn.execute(
            "INSERT INTO uploads (id, chat_id, created_at, status) VALUES (?, ?, ?, 'draft')",
            (upload_id, chat_id, now.isoformat()),
        )
        return self.get_upload(upload_id)

    def add_file_to_upload(self, upload_id: str, filename: str, payload: bytes) -> Upload:
        u = self.get_upload(upload_id)
        if u.status != UploadStatus.DRAFT:
            raise InvalidStatusTransition(f"cannot add file when status={u.status.value}")
        self.storage.save_file(upload_id, filename, payload)
        size = self.storage.folder_size(upload_id)
        count = self.storage.file_count(upload_id)
        self.conn.execute(
            "UPDATE uploads SET size_bytes=?, file_count=? WHERE id=?",
            (size, count, upload_id),
        )
        return self.get_upload(upload_id)

    def confirm_upload(self, upload_id: str) -> Upload:
        u = self.get_upload(upload_id)
        if u.status != UploadStatus.DRAFT:
            raise InvalidStatusTransition(f"cannot confirm when status={u.status.value}")
        self.conn.execute(
            "UPDATE uploads SET status='confirmed', confirmed_at=? WHERE id=?",
            (self._now().isoformat(), upload_id),
        )
        return self.get_upload(upload_id)

    def cancel_active_draft(self, chat_id: int) -> None:
        u = self.get_active_draft(chat_id)
        if u is None:
            raise NoActiveDraft(chat_id)
        self.storage.delete_folder(u.id)
        self.conn.execute("DELETE FROM uploads WHERE id=?", (u.id,))

    # ---------- rename ----------

    def rename_upload(self, ref: str, new_name: str) -> Upload:
        u = self.find_by_ref(ref)
        if u.status == UploadStatus.USED:
            raise RenameBlockedAfterUse(u.id)
        existing = self.conn.execute(
            "SELECT id FROM uploads WHERE name=? AND id<>?", (new_name, u.id)
        ).fetchone()
        if existing:
            raise NameAlreadyTaken(new_name)
        self.conn.execute("UPDATE uploads SET name=? WHERE id=?", (new_name, u.id))
        return self.get_upload(u.id)

    # ---------- usage ----------

    def mark_used(
        self,
        upload_id: str,
        action: str,
        details: dict | None,
    ) -> Upload:
        import json

        u = self.get_upload(upload_id)
        if u.status not in (UploadStatus.CONFIRMED, UploadStatus.USED):
            raise InvalidStatusTransition(
                f"cannot mark_used when status={u.status.value}"
            )
        now = self._now().isoformat()
        self.conn.execute(
            "INSERT INTO usage_log (upload_id, used_at, action, details_json) "
            "VALUES (?, ?, ?, ?)",
            (
                u.id,
                now,
                action,
                json.dumps(details) if details is not None else None,
            ),
        )
        self.conn.execute(
            "UPDATE uploads SET status='used', last_used_at=? WHERE id=?",
            (now, u.id),
        )
        return self.get_upload(upload_id)

    def usage_log(self, upload_id: str) -> list[UsageLogEntry]:
        import json

        rows = self.conn.execute(
            "SELECT * FROM usage_log WHERE upload_id=? ORDER BY id ASC",
            (upload_id,),
        ).fetchall()
        out: list[UsageLogEntry] = []
        for r in rows:
            details = json.loads(r["details_json"]) if r["details_json"] else None
            out.append(
                UsageLogEntry(
                    id=r["id"],
                    upload_id=r["upload_id"],
                    used_at=datetime.fromisoformat(r["used_at"]),
                    action=r["action"],
                    details=details,
                )
            )
        return out

    # ---------- listing & cleanup ----------

    def list_uploads(self, chat_id: int) -> list[Upload]:
        rows = self.conn.execute(
            "SELECT * FROM uploads WHERE chat_id=? ORDER BY created_at DESC",
            (chat_id,),
        ).fetchall()
        return [_row_to_upload(r) for r in rows]

    def oldest_uploads(self, chat_id: int, limit: int) -> list[Upload]:
        rows = self.conn.execute(
            "SELECT * FROM uploads WHERE chat_id=? ORDER BY created_at ASC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [_row_to_upload(r) for r in rows]

    def biggest_uploads(self, chat_id: int, limit: int) -> list[Upload]:
        rows = self.conn.execute(
            "SELECT * FROM uploads WHERE chat_id=? ORDER BY size_bytes DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [_row_to_upload(r) for r in rows]

    def uploads_older_than(self, chat_id: int, days: int) -> list[Upload]:
        cutoff = (self._now() - timedelta(days=days)).isoformat()
        rows = self.conn.execute(
            "SELECT * FROM uploads WHERE chat_id=? AND created_at < ? "
            "ORDER BY created_at ASC",
            (chat_id, cutoff),
        ).fetchall()
        return [_row_to_upload(r) for r in rows]

    def delete_upload(self, upload_id: str) -> None:
        u = self.get_upload(upload_id)
        self.storage.delete_folder(u.id)
        self.conn.execute("DELETE FROM uploads WHERE id=?", (u.id,))
        # usage_log rows cascade via FK ON DELETE CASCADE
