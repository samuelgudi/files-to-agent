"""Smoke tests for version.py — verify they don't crash and return sensible types."""
from __future__ import annotations

from files_to_agent import version


def test_read_version_from_metadata() -> None:
    """version.py should resolve the version via importlib.metadata, not pyproject.toml."""
    info = version.get_version_info()
    # In a checkout-with-uv-sync run, this should be the pyproject version.
    # The exact value isn't asserted (it changes per release), but it must
    # NOT be "unknown" — that would indicate a packaging-metadata miss.
    assert info.version != "unknown", "importlib.metadata resolution failed"
    # And it must be a sane semver-ish string.
    assert info.version[0].isdigit() or info.version.startswith("v")


def test_commit_sha_from_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """When FILES_TO_AGENT_COMMIT_SHA is set, commit_sha() returns it."""
    monkeypatch.setenv("FILES_TO_AGENT_COMMIT_SHA", "abc1234")
    assert version.commit_sha() == "abc1234"


def test_commit_sha_falls_back_to_git(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """When the env var is unset, commit_sha() falls back to short_sha (git)."""
    monkeypatch.delenv("FILES_TO_AGENT_COMMIT_SHA", raising=False)
    monkeypatch.setattr(version, "short_sha", lambda: "deadbee")
    assert version.commit_sha() == "deadbee"


def test_short_sha_returns_string() -> None:
    sha = version.short_sha()
    assert isinstance(sha, str)


def test_get_version_info_returns_sensible_types() -> None:
    info = version.get_version_info()
    assert isinstance(info.version, str)
    assert isinstance(info.sha, str)


def test_is_git_checkout_returns_bool() -> None:
    assert isinstance(version.is_git_checkout(), bool)
