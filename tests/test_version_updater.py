"""Smoke tests for version.py and updater.py — verify they don't crash and
return sensible types regardless of git state / deploy mode."""
from __future__ import annotations

from unittest.mock import patch

from files_to_agent import updater, version

# ---------- version.py ----------


def test_read_version_from_metadata() -> None:
    """version.py should resolve the version via importlib.metadata, not pyproject.toml."""
    from files_to_agent import version as v

    info = v.get_version_info(check_upstream=False)
    # In a checkout-with-uv-sync run, this should be the pyproject version.
    # The exact value isn't asserted (it changes per release), but it must
    # NOT be "unknown" — that would indicate a packaging-metadata miss.
    assert info.version != "unknown", "importlib.metadata resolution failed"
    # And it must be a sane semver-ish string.
    assert info.version[0].isdigit() or info.version.startswith("v")


def test_commit_sha_from_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """When FILES_TO_AGENT_COMMIT_SHA is set, commit_sha() returns it."""
    from files_to_agent import version as v

    monkeypatch.setenv("FILES_TO_AGENT_COMMIT_SHA", "abc1234")
    assert v.commit_sha() == "abc1234"


def test_commit_sha_falls_back_to_git(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """When the env var is unset, commit_sha() falls back to short_sha (git)."""
    from files_to_agent import version as v

    monkeypatch.delenv("FILES_TO_AGENT_COMMIT_SHA", raising=False)
    monkeypatch.setattr(v, "short_sha", lambda: "deadbee")
    assert v.commit_sha() == "deadbee"


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


def test_find_uv_returns_which_result_when_available(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        updater.shutil, "which", lambda name: "/some/path/uv" if name == "uv" else None
    )
    assert updater._find_uv() == "/some/path/uv"


def test_find_uv_falls_back_to_common_install_path(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # PATH lookup fails.
    monkeypatch.setattr(updater.shutil, "which", lambda name: None)
    # Pretend the user's home has ~/.local/bin/uv as an executable file.
    fake_home = tmp_path / "home"
    bin_dir = fake_home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    fake_uv = bin_dir / "uv"
    fake_uv.write_text("#!/bin/sh\necho uv\n")
    fake_uv.chmod(0o755)
    monkeypatch.setattr(updater.Path, "home", staticmethod(lambda: fake_home))

    found = updater._find_uv()
    assert found == str(fake_uv)


def test_find_uv_returns_none_when_nothing_found(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(updater.shutil, "which", lambda name: None)
    # Empty home so no fallback path resolves.
    fake_home = tmp_path / "empty_home"
    fake_home.mkdir()
    monkeypatch.setattr(updater.Path, "home", staticmethod(lambda: fake_home))
    # Ensure /usr/local/bin/uv is also pretended-absent by giving the function only
    # the home-relative candidates that we control. The function's third candidate
    # (/usr/local/bin/uv) might exist on the test host — accept either None or a
    # string that points to /usr/local/bin/uv.
    found = updater._find_uv()
    assert found is None or found == "/usr/local/bin/uv"


def test_run_git_update_succeeds_when_uv_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Reproduces the Agent bug: git fetch + reset succeed, uv missing must not fail update."""
    from files_to_agent import updater as updater_mod

    # Force is_git_checkout() to True so we don't bail early.
    monkeypatch.setattr(updater_mod, "is_git_checkout", lambda: True)
    # Pretend uv is missing entirely.
    monkeypatch.setattr(updater_mod, "_find_uv", lambda: None)

    calls: list[list[str]] = []

    class _FakeCompleted:
        def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        # The first two calls are git fetch / git reset — succeed.
        return _FakeCompleted(returncode=0, stdout="HEAD is now at abcdef\n")

    monkeypatch.setattr(updater_mod.subprocess, "run", _fake_run)

    result = updater_mod.run_git_update()

    assert result.ok is True, f"expected ok=True, got {result}"
    # Verify uv was NOT invoked — only the two git commands ran.
    invoked_executables = [c[0] for c in calls]
    assert "uv" not in invoked_executables
    assert any("git" in c for c in invoked_executables)
