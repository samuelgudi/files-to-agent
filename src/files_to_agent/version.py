"""Version inspection — reads packaging metadata + commit SHA."""
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
    is_git: bool


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


def get_version_info() -> VersionInfo:
    return VersionInfo(
        version=_read_distribution_version(),
        sha=commit_sha(),
        is_git=is_git_checkout(),
    )
