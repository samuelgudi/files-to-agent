from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from files_to_agent.config import Settings
from files_to_agent.core import Core
from files_to_agent.db import connect, init_schema
from files_to_agent.resolver.api import build_app
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


@pytest.fixture
def settings_no_auth(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("RESOLVER_AUTH", "none")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    return Settings()


@pytest.fixture
def settings_apikey(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("RESOLVER_AUTH", "apikey")
    monkeypatch.setenv("RESOLVER_API_KEY", "secret-xyz")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    return Settings()


def test_healthz(core: Core, settings_no_auth: Settings) -> None:
    client = TestClient(build_app(core=core, settings=settings_no_auth))
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_resolve_by_id(core: Core, settings_no_auth: Settings) -> None:
    u = core.create_upload(chat_id=1)
    core.add_file_to_upload(u.id, "f.txt", b"hello")
    core.set_context(u.id, "Marco invoice attachments")

    client = TestClient(build_app(core=core, settings=settings_no_auth))
    r = client.get(f"/resolve?ref={u.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == u.id
    assert body["status"] == "draft"
    assert body["files"] == ["f.txt"]
    assert body["size_bytes"] == 5
    assert body["context"] == "Marco invoice attachments"


def test_resolve_returns_null_context_when_unset(core: Core, settings_no_auth: Settings) -> None:
    u = core.create_upload(chat_id=1)
    client = TestClient(build_app(core=core, settings=settings_no_auth))
    r = client.get(f"/resolve?ref={u.id}")
    assert r.status_code == 200
    assert r.json()["context"] is None


def test_resolve_unknown_returns_404(core: Core, settings_no_auth: Settings) -> None:
    client = TestClient(build_app(core=core, settings=settings_no_auth))
    r = client.get("/resolve?ref=nope")
    assert r.status_code == 404


def test_use_marks_used(core: Core, settings_no_auth: Settings) -> None:
    u = core.create_upload(chat_id=1)
    core.add_file_to_upload(u.id, "f.txt", b"hello")
    core.confirm_upload(u.id)

    client = TestClient(build_app(core=core, settings=settings_no_auth))
    r = client.post(
        "/use",
        json={"ref": u.id, "action": "email_send", "details": {"to": "x@y.z"}},
    )
    assert r.status_code == 200
    refreshed = core.get_upload(u.id)
    assert refreshed.status.value == "used"
    log = core.usage_log(u.id)
    assert log[0].action == "email_send"


def test_use_rejects_when_not_confirmed(core: Core, settings_no_auth: Settings) -> None:
    u = core.create_upload(chat_id=1)
    client = TestClient(build_app(core=core, settings=settings_no_auth))
    r = client.post("/use", json={"ref": u.id, "action": "email_send"})
    assert r.status_code == 409


def test_apikey_required(core: Core, settings_apikey: Settings) -> None:
    client = TestClient(build_app(core=core, settings=settings_apikey))
    r = client.get("/resolve?ref=anything")
    assert r.status_code == 401


def test_apikey_accepted(core: Core, settings_apikey: Settings) -> None:
    u = core.create_upload(chat_id=1)
    client = TestClient(build_app(core=core, settings=settings_apikey))
    r = client.get(
        f"/resolve?ref={u.id}",
        headers={"Authorization": "Bearer secret-xyz"},
    )
    assert r.status_code == 200


def test_healthz_no_auth_required(core: Core, settings_apikey: Settings) -> None:
    client = TestClient(build_app(core=core, settings=settings_apikey))
    r = client.get("/healthz")
    assert r.status_code == 200
