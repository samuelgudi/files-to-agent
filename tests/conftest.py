import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Per-test isolated data directory with staging/ subfolder."""
    staging = tmp_path / "staging"
    staging.mkdir()
    return tmp_path


@pytest.fixture(autouse=True)
def _set_min_env(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide minimum env vars so config.Settings() never fails in tests."""
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "1")
    monkeypatch.setenv("STAGING_DIR", str(tmp_data_dir / "staging"))
    monkeypatch.setenv("DB_PATH", str(tmp_data_dir / "test.db"))
