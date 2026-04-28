from datetime import UTC, datetime

from files_to_agent.models import Upload, UploadStatus, UsageLogEntry


def test_upload_minimal_fields() -> None:
    u = Upload(
        id="abc12345",
        name=None,
        chat_id=42,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        confirmed_at=None,
        last_used_at=None,
        size_bytes=0,
        file_count=0,
        status=UploadStatus.DRAFT,
    )
    assert u.is_active_draft is True
    assert u.is_used is False


def test_upload_used_flag() -> None:
    u = Upload(
        id="x", name=None, chat_id=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        confirmed_at=None, last_used_at=None,
        size_bytes=0, file_count=0,
        status=UploadStatus.USED,
    )
    assert u.is_used is True


def test_upload_context_default_none() -> None:
    u = Upload(
        id="x", name=None, chat_id=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        confirmed_at=None, last_used_at=None,
        size_bytes=0, file_count=0,
        status=UploadStatus.DRAFT,
    )
    assert u.context is None


def test_usage_log_entry() -> None:
    e = UsageLogEntry(
        id=1,
        upload_id="abc",
        used_at=datetime(2026, 1, 1, tzinfo=UTC),
        action="email_send",
        details={"to": "x@y.z"},
    )
    assert e.action == "email_send"
    assert e.details == {"to": "x@y.z"}
