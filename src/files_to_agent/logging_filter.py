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
    """Replace Telegram-token-shaped substrings in a record's msg + args.

    Returns True so the record still propagates — we modify the payload,
    we don't drop the record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = TOKEN_PATTERN.sub(REDACTED, record.msg)
        if record.args:
            record.args = tuple(
                TOKEN_PATTERN.sub(REDACTED, a) if isinstance(a, str) else a
                for a in record.args
            )
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
