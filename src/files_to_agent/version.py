"""Version inspection — reads pyproject + git, queries upstream."""
from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class VersionInfo:
    version: str           # from pyproject.toml [project] version
    sha: str               # short commit SHA, or "unknown"
    behind: int | None     # commits behind origin/main, None if undetermined
    is_git: bool


def _read_pyproject_version() -> str:
    pp = PROJECT_ROOT / "pyproject.toml"
    if not pp.exists():
        return "unknown"
    with pp.open("rb") as f:
        data = tomllib.load(f)
    return str(data.get("project", {}).get("version", "unknown"))


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
    if not is_git_checkout():
        return "unknown"
    code, out = _git("rev-parse", "--short", "HEAD")
    return out if code == 0 else "unknown"


def fetch_upstream() -> bool:
    """Run `git fetch origin`. Returns True on success."""
    if not is_git_checkout():
        return False
    code, _ = _git("fetch", "origin", "--quiet", timeout=30)
    return code == 0


def commits_behind() -> int | None:
    """Count of commits on origin/main not in HEAD. None if undetermined."""
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
    version = _read_pyproject_version()
    sha = short_sha()
    is_git = is_git_checkout()
    behind: int | None = None
    if is_git and check_upstream and fetch_upstream():
        behind = commits_behind()
    return VersionInfo(version=version, sha=sha, behind=behind, is_git=is_git)
