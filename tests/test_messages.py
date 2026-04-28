import pytest

from files_to_agent.messages import MESSAGES, t

REQUIRED_KEYS = {
    "welcome", "not_authorized",
    "session_started", "session_already_active",
    "no_active_session",
    "file_received", "file_too_big", "disk_full",
    "session_confirmed", "session_cancelled",
    "rename_done", "rename_taken", "rename_blocked_after_use",
    "context_set", "context_cleared", "context_usage",
    "list_empty", "list_header", "list_row",
    "info_not_found", "info_block", "info_no_usage",
    "pulizia_header", "pulizia_confirm", "pulizia_done",
    "disk_warning",
}


@pytest.mark.parametrize("lang", ["it", "en"])
def test_all_required_keys_present_for_each_language(lang: str) -> None:
    missing = REQUIRED_KEYS - set(MESSAGES[lang].keys())
    assert not missing, f"missing keys in {lang}: {missing}"


def test_t_italian_default() -> None:
    assert "Ciao" in t("welcome", "it") or "ciao" in t("welcome", "it").lower()


def test_t_english() -> None:
    assert "Hi" in t("welcome", "en") or "Hello" in t("welcome", "en")


def test_t_format_args() -> None:
    out = t(
        "session_confirmed", "it", id="abc12345", name="—", count=3, size="12.3 MB", context="—"
    )
    assert "abc12345" in out and "12.3 MB" in out


def test_t_unknown_lang_falls_back_to_italian() -> None:
    # Spec: any unknown lang falls back to "it"
    assert t("welcome", "fr") == t("welcome", "it")


def test_t_unknown_key_returns_marker() -> None:
    out = t("nonexistent_key", "it")
    assert "nonexistent_key" in out
