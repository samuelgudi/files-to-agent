"""Version inspection — reads packaging metadata + commit SHA, queries upstream."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISTRIBUTION_NAME = "files-to-agent"


@dataclass(frozen=True)
class VersionInfo:
    version: str           # from packaging metadata (importlib.metadata)
    sha: str               # short commit SHA, or "unknown"
    behind: int | None     # commits behind origin/main, None if undetermined
    is_git: bool


def _read_pyproject_version() -> str:
    """Legacy helper kept for backward compat with existing tests.

    Prefer _read_distribution_version() for new code — it works in containers.
    """
    pp = PROJECT_ROOT / "pyproject.toml"
    if not pp.exists():
        return "unknown"
    import tomllib
    with pp.open("rb") as f:
        data = tomllib.load(f)
    return str(data.get("project", {}).get("version", "unknown"))


def _read_distribution_version() -> str:
    """Read the version string from packaging metadata.

    Works in any environment where the package was installed (uv sync,
    pip install, container with the wheel installed). Returns "unknown"
    only if the package isn't installed in the current Python environment
    (which shouldn't happen in production).
    """
    try:
        return metadata.version(DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return "unknown"


def _git(*args: str, cwd: Path = PROJECT_ROOT, timeout: int = 10) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def is_git_checkout() -> bool:
    return (PROJECT_ROOT / ".git").exists()


def short_sha() -> str:
    """Live commit SHA from a git checkout. Returns 'unknown' if no .git or git fails."""
    if not is_git_checkout():
        return "unknown"
    code, out = _git("rev-parse", "--short", "HEAD")
    return out if code == 0 else "unknown"


def commit_sha() -> str:
    """Commit SHA the bot was built from.

    Resolution order:
      1. FILES_TO_AGENT_COMMIT_SHA env var (set at Docker build via build-arg)
      2. Live `git rev-parse --short HEAD` (for development checkouts)

    This lets containerised deployments report the actual commit they were
    built from (env var baked in at build time), while dev runs report HEAD.
    """
    baked = os.environ.get("FILES_TO_AGENT_COMMIT_SHA")
    if baked:
        return baked
    return short_sha()


def fetch_upstream() -> bool:
    """Run `git fetch origin`. Returns True on success.

    NOTE: scheduled for removal in Phase 3 along with the daily-update job.
    """
    if not is_git_checkout():
        return False
    code, _ = _git("fetch", "origin", "--quiet", timeout=30)
    return code == 0


def commits_behind() -> int | None:
    """Count of commits on origin/main not in HEAD. None if undetermined.

    NOTE: scheduled for removal in Phase 3 along with the daily-update job.
    """
    if not is_git_checkout():
        return None
    code, out = _git("rev-list", "--count", "HEAD..origin/main")
    if code != 0:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def get_version_info(check_upstream: bool = True) -> VersionInfo:
    version = _read_distribution_version()
    sha = commit_sha()
    is_git = is_git_checkout()
    behind: int | None = None
    if is_git and check_upstream and fetch_upstream():
        behind = commits_behind()
    return VersionInfo(version=version, sha=sha, behind=behind, is_git=is_git)
