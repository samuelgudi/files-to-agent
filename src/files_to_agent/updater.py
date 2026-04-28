"""Self-updater — detects deploy mode and runs the appropriate update path."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from files_to_agent.version import PROJECT_ROOT, is_git_checkout

DeployMode = Literal["docker", "supervised_git", "bare_git", "unknown"]

DOCKER_FLAG_DIR = Path("/var/lib/files-to-agent")
DOCKER_FLAG_FILE = DOCKER_FLAG_DIR / "update.requested"


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    mode: DeployMode
    message: str


def in_docker() -> bool:
    """Detect Docker via the canonical /.dockerenv marker."""
    return Path("/.dockerenv").exists()


def has_supervisor() -> bool:
    """Heuristic: are we likely to be auto-restarted on exit?

    True if running under systemd, process-compose, or similar that we
    detect via env vars. Conservative — false negatives just produce a
    "no supervisor" message instead of killing the bot.
    """
    if os.environ.get("INVOCATION_ID"):  # set by systemd
        return True
    if os.environ.get("PC_PROCESS_NAME") or os.environ.get("PC_LOG_PATH"):
        return True
    return os.environ.get("FILES_TO_AGENT_SUPERVISED") == "1"


def detect_mode() -> DeployMode:
    if in_docker():
        return "docker"
    if is_git_checkout():
        return "supervised_git" if has_supervisor() else "bare_git"
    return "unknown"


def mode_description(mode: DeployMode) -> str:
    return {
        "docker": "Docker",
        "supervised_git": "Git checkout (supervised)",
        "bare_git": "Git checkout (bare)",
        "unknown": "Unknown",
    }.get(mode, "Unknown")


def _find_uv() -> str | None:
    """Locate the `uv` executable, falling back to common install paths.

    Supervised processes (systemd, process-compose) often run with a stripped
    PATH that excludes ~/.local/bin and ~/.cargo/bin where uv typically lives.
    Returns an absolute path string if found, or None if uv is missing.
    """
    found = shutil.which("uv")
    if found:
        return found
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
        Path("/usr/local/bin/uv"),
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def run_git_update() -> UpdateResult:
    """Pull latest origin/main and sync deps. Caller must restart the process."""
    if not is_git_checkout():
        return UpdateResult(False, "unknown", "Not a git checkout.")
    try:
        r1 = subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        if r1.returncode != 0:
            return UpdateResult(False, detect_mode(), f"git fetch: {r1.stderr.strip()}")
        r2 = subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        if r2.returncode != 0:
            return UpdateResult(False, detect_mode(), f"git reset: {r2.stderr.strip()}")
        # uv sync if available — best effort, don't fail update if uv missing
        subprocess.run(
            ["uv", "sync", "--frozen"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180, check=False,
        )
        return UpdateResult(True, detect_mode(), r2.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return UpdateResult(False, detect_mode(), str(e))


def write_docker_flag() -> bool:
    """Drop a flag file the host watcher script polls. Mounted volume required."""
    try:
        DOCKER_FLAG_DIR.mkdir(parents=True, exist_ok=True)
        DOCKER_FLAG_FILE.write_text(f"requested at {time.time()}\n", encoding="utf-8")
        return True
    except OSError:
        return False


def schedule_self_exit(delay_seconds: float = 1.5) -> None:
    """Exit after a brief delay so the reply has time to send."""
    import threading
    def _kill() -> None:
        time.sleep(delay_seconds)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
