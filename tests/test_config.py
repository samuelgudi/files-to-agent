from pathlib import Path

import pytest

from files_to_agent.config import Settings


def test_settings_loads_required_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOT_TOKEN", "abc123")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "111,222,333")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "x.db"))

    s = Settings()

    assert s.bot_token == "abc123"
    assert s.bot_allowed_user_ids == [111, 222, 333]
    assert s.staging_dir == tmp_path / "staging"
    assert s.resolver_port == 8080
    assert s.resolver_auth == "none"


def test_apikey_auth_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESOLVER_AUTH", "apikey")
    monkeypatch.delenv("RESOLVER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="RESOLVER_API_KEY"):
        Settings()


def test_invalid_auth_value_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESOLVER_AUTH", "totally_invalid")
    with pytest.raises(ValueError):
        Settings()


def test_bot_lang_default_italian(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOT_TOKEN", "x")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "1")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "x.db"))
    s = Settings()
    assert s.bot_lang == "it"


def test_bot_lang_english_via_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOT_TOKEN", "x")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "1")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("BOT_LANG", "en")
    s = Settings()
    assert s.bot_lang == "en"


def test_bot_lang_invalid_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOT_TOKEN", "x")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "1")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("BOT_LANG", "fr")
    with pytest.raises(ValueError):
        Settings()
