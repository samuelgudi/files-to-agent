import logging

from files_to_agent.logging_filter import (
    TOKEN_PATTERN,
    TokenRedactionFilter,
    install_redaction_filter,
)

# A realistic-shaped fake token (digits:alnum_-) that won't actually authenticate.
FAKE_TOKEN = "1234567890:AAFakeFakeFakeFakeFakeFakeFakeFakeFak"


def test_token_pattern_matches_real_shape() -> None:
    assert TOKEN_PATTERN.search(f"https://api.telegram.org/bot{FAKE_TOKEN}/getMe")
    assert TOKEN_PATTERN.search(FAKE_TOKEN)


def test_token_pattern_does_not_match_short_strings() -> None:
    # Too short on either side.
    assert not TOKEN_PATTERN.search("123:short")
    assert not TOKEN_PATTERN.search("notatoken")
    assert not TOKEN_PATTERN.search("12345:")


def test_filter_redacts_msg() -> None:
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="httpx", level=logging.INFO, pathname="", lineno=0,
        msg=f"HTTP Request: POST https://api.telegram.org/bot{FAKE_TOKEN}/getMe",
        args=None, exc_info=None,
    )
    f.filter(record)
    assert FAKE_TOKEN not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_redacts_string_args() -> None:
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="httpx", level=logging.INFO, pathname="", lineno=0,
        msg="HTTP Request: %s",
        args=(f"POST https://api.telegram.org/bot{FAKE_TOKEN}/getUpdates",),
        exc_info=None,
    )
    f.filter(record)
    assert all(FAKE_TOKEN not in (a if isinstance(a, str) else "") for a in record.args)
    assert any("[REDACTED]" in a for a in record.args if isinstance(a, str))


def test_filter_passes_through_clean_messages() -> None:
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="files_to_agent", level=logging.INFO, pathname="", lineno=0,
        msg="bot polling started", args=None, exc_info=None,
    )
    f.filter(record)
    assert record.msg == "bot polling started"


def test_filter_returns_true_so_record_is_emitted() -> None:
    """Filter must let the record through (just modified).

    A False return would drop the record entirely.
    """
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname="", lineno=0,
        msg="something benign", args=None, exc_info=None,
    )
    assert f.filter(record) is True


def test_filter_handles_non_string_args() -> None:
    """Numeric / dict args should pass through untouched, not crash."""
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname="", lineno=0,
        msg="count=%d size=%d", args=(42, 1024), exc_info=None,
    )
    f.filter(record)
    assert record.args == (42, 1024)


def test_install_redaction_filter_attaches_to_handlers(caplog) -> None:  # type: ignore[no-untyped-def]
    # Reset state: configure a fresh root handler.
    root = logging.getLogger()
    original_filters = [list(h.filters) for h in root.handlers]

    try:
        install_redaction_filter()

        for handler in root.handlers:
            assert any(isinstance(f, TokenRedactionFilter) for f in handler.filters), (
                f"TokenRedactionFilter not on handler {handler}"
            )
    finally:
        for handler, original in zip(root.handlers, original_filters, strict=False):
            handler.filters = original


def test_install_redaction_filter_is_idempotent() -> None:
    """Calling install twice must not stack two filters."""
    root = logging.getLogger()
    original_filters = [list(h.filters) for h in root.handlers]

    try:
        install_redaction_filter()
        install_redaction_filter()

        for handler in root.handlers:
            count = sum(1 for f in handler.filters if isinstance(f, TokenRedactionFilter))
            assert count == 1, f"Filter installed {count} times on {handler}"
    finally:
        for handler, original in zip(root.handlers, original_filters, strict=False):
            handler.filters = original


def test_runner_installs_filter_on_build_components(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """build_components must install the redaction filter so the bot's
    very first httpx log can't leak the token."""
    monkeypatch.setenv("BOT_TOKEN", "test:placeholder")
    monkeypatch.setenv("BOT_ALLOWED_USER_IDS", "1")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))

    # Reset filters before / after so test isolation holds.
    root = logging.getLogger()
    pre = [list(h.filters) for h in root.handlers]
    try:
        from files_to_agent.runner import build_components

        build_components()

        for handler in root.handlers:
            assert any(isinstance(f, TokenRedactionFilter) for f in handler.filters), (
                f"build_components did not install the redaction filter on {handler}"
            )
    finally:
        for handler, original in zip(root.handlers, pre, strict=False):
            handler.filters = original
