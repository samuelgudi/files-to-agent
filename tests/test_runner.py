from pathlib import Path

import pytest

from files_to_agent.runner import build_components


def test_build_components_returns_core_app_resolver(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("BOT_TOKEN", "tkn")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "1")
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))

    components = build_components()
    assert components.core is not None
    assert components.bot_app is not None
    assert components.resolver_app is not None
    assert components.settings.bot_token == "tkn"
