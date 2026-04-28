"""Process lifecycle helpers."""
from __future__ import annotations

import os
import threading
import time


def schedule_self_exit(delay_seconds: float = 1.5) -> None:
    """Exit the process after a brief delay so any pending reply has time to send.

    Used by /restart. The supervisor (Docker `restart: unless-stopped`,
    systemd, process-compose) is responsible for bringing the bot back up.
    """
    def _kill() -> None:
        time.sleep(delay_seconds)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
