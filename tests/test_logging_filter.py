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
    assert FAKE_TOKEN not in record.getMessage()
    assert "[REDACTED]" in record.getMessage()


def test_filter_redacts_object_args_via_str() -> None:
    """Real-world: httpx logs URL *objects*, not strings.

    Previous implementation only checked isinstance(arg, str) and let
    URL objects slip through. The fix uses record.getMessage() which
    invokes __str__ on every arg before redaction.
    """
    class FakeUrl:
        def __init__(self, value: str) -> None:
            self._value = value
        def __str__(self) -> str:
            return self._value

    fake_url = FakeUrl(f"https://api.telegram.org/bot{FAKE_TOKEN}/getMe")
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="httpx", level=logging.INFO, pathname="", lineno=0,
        msg="HTTP Request: %s %s", args=("POST", fake_url), exc_info=None,
    )
    f.filter(record)
    assert FAKE_TOKEN not in record.getMessage()
    assert "[REDACTED]" in record.getMessage()


def test_filter_mimics_real_httpx_call() -> None:
    """Reproduce the exact arg shape httpx uses: 5 positional args incl. URL object."""
    class FakeUrl:
        def __init__(self, value: str) -> None:
            self._value = value
        def __str__(self) -> str:
            return self._value

    fake_url = FakeUrl(f"https://api.telegram.org/bot{FAKE_TOKEN}/getUpdates")
    f = TokenRedactionFilter()
    # httpx logs as: 'HTTP Request: %s %s "HTTP/%s %d %s"' % (method, url, ver, status, reason)
    record = logging.LogRecord(
        name="httpx", level=logging.INFO, pathname="", lineno=0,
        msg='HTTP Request: %s %s "HTTP/%s %d %s"',
        args=("POST", fake_url, "1.1", 200, "OK"),
        exc_info=None,
    )
    f.filter(record)
    final = record.getMessage()
    assert FAKE_TOKEN not in final
    assert "[REDACTED]" in final
    assert "POST" in final
    assert "200" in final  # other args still preserved


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


def test_filter_handles_non_string_args_without_crashing() -> None:
    """Numeric args without tokens should not crash the filter and the
    formatted message should be preserved."""
    f = TokenRedactionFilter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname="", lineno=0,
        msg="count=%d size=%d", args=(42, 1024), exc_info=None,
    )
    f.filter(record)
    assert record.getMessage() == "count=42 size=1024"


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
