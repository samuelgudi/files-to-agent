"""Smoke tests for version.py and updater.py — verify they don't crash and
return sensible types regardless of git state / deploy mode."""
from __future__ import annotations

from unittest.mock import patch

from files_to_agent import updater, version

# ---------- version.py ----------


def test_read_pyproject_version_returns_string() -> None:
    v = version._read_pyproject_version()
    assert isinstance(v, str)
    assert v != ""


def test_short_sha_returns_string() -> None:
    sha = version.short_sha()
    assert isinstance(sha, str)


def test_get_version_info_no_upstream_check() -> None:
    info = version.get_version_info(check_upstream=False)
    assert isinstance(info.version, str)
    assert isinstance(info.sha, str)
    assert isinstance(info.is_git, bool)
    # No upstream check requested → behind must be None.
    assert info.behind is None


def test_get_version_info_handles_offline() -> None:
    """If fetch_upstream returns False (offline), behind stays None."""
    with patch.object(version, "fetch_upstream", return_value=False):
        info = version.get_version_info(check_upstream=True)
    assert info.behind is None


# ---------- updater.py ----------


def test_detect_mode_returns_known_value() -> None:
    mode = updater.detect_mode()
    assert mode in ("docker", "supervised_git", "bare_git", "unknown")


def test_mode_description_covers_all_modes() -> None:
    for m in ("docker", "supervised_git", "bare_git", "unknown"):
        d = updater.mode_description(m)  # type: ignore[arg-type]
        assert isinstance(d, str) and d


def test_has_supervisor_via_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("INVOCATION_ID", raising=False)
    monkeypatch.delenv("PC_PROCESS_NAME", raising=False)
    monkeypatch.delenv("PC_LOG_PATH", raising=False)
    monkeypatch.delenv("FILES_TO_AGENT_SUPERVISED", raising=False)
    assert updater.has_supervisor() is False
    monkeypatch.setenv("FILES_TO_AGENT_SUPERVISED", "1")
    assert updater.has_supervisor() is True


def test_has_supervisor_under_systemd(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("PC_PROCESS_NAME", raising=False)
    monkeypatch.delenv("PC_LOG_PATH", raising=False)
    monkeypatch.delenv("FILES_TO_AGENT_SUPERVISED", raising=False)
    monkeypatch.setenv("INVOCATION_ID", "abcdef")
    assert updater.has_supervisor() is True


def test_write_docker_flag_writes_to_tmp(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Verify the flag-write path uses the configured directory."""
    flag_dir = tmp_path / "flag"
    flag_file = flag_dir / "update.requested"
    monkeypatch.setattr(updater, "DOCKER_FLAG_DIR", flag_dir)
    monkeypatch.setattr(updater, "DOCKER_FLAG_FILE", flag_file)
    assert updater.write_docker_flag() is True
    assert flag_file.exists()
    assert "requested at" in flag_file.read_text()
