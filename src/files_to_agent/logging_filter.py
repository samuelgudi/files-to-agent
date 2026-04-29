"""Logging filter that redacts Telegram bot tokens from log records.

The Telegram API embeds the bot token in URL paths
(`https://api.telegram.org/bot<TOKEN>/getMe`), and `httpx` logs full request
URLs at INFO level by default. Every poll cycle writes the token to logs
unless this filter is installed.

Usage:
    from files_to_agent.logging_filter import install_redaction_filter
    logging.basicConfig(level=...)
    install_redaction_filter()  # AFTER basicConfig so handlers exist
"""
from __future__ import annotations

import logging
import re

# Telegram bot tokens are <bot_id>:<secret>:
#   bot_id   = 8-10 digits
#   secret   = 35+ chars from [A-Za-z0-9_-]
# The actual format used by current bots is consistently in this range.
TOKEN_PATTERN = re.compile(r"(\d{8,10}:[A-Za-z0-9_-]{35,})")
REDACTED = "[REDACTED]"


class TokenRedactionFilter(logging.Filter):
    """Replace Telegram-token-shaped substrings in a record's formatted message.

    Calls record.getMessage() to fully format msg % args (which invokes
    __str__ on every arg), then redacts. This catches tokens hidden inside
    non-string args — notably httpx.URL objects, which is how httpx actually
    logs Telegram URLs. After redaction the formatted string is written back
    as record.msg with empty args, so the emitter doesn't re-format and undo
    the redaction.

    Returns True so the record still propagates.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            formatted = record.getMessage()
        except Exception:  # noqa: BLE001 — never let logging filtering crash the bot
            return True
        redacted = TOKEN_PATTERN.sub(REDACTED, formatted)
        if redacted != formatted:
            record.msg = redacted
            record.args = ()
        return True


def install_redaction_filter() -> None:
    """Attach a TokenRedactionFilter to every handler on the root logger.

    Idempotent — calling more than once does not stack duplicate filters.
    Must be called AFTER logging.basicConfig() (or however the root handler
    gets installed), since basicConfig is a no-op once handlers exist.
    """
    root = logging.getLogger()
    for handler in root.handlers:
        if any(isinstance(f, TokenRedactionFilter) for f in handler.filters):
            continue
        handler.addFilter(TokenRedactionFilter())
