"""Inline keyboard factories.

All callback_data strings live here so the handler module has a single place to
match against. Keep them short — Telegram caps callback_data at 64 bytes.

Callback codes:
  new          -> start a new upload
  list         -> /list
  cleanup      -> /cleanup (no args)
  confirm      -> /confirm
  cancel       -> /cancel
  rename       -> prompt for rename text
  context      -> prompt for context text
  language     -> open language picker
  lang:it      -> set language to Italian
  lang:en      -> set language to English
  help         -> /help
  update:go    -> run update
  update:skip  -> dismiss update prompt
  del:<id>     -> delete upload <id> (one tap, no confirm step)
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from files_to_agent.bot.format import human_size
from files_to_agent.messages import t
from files_to_agent.models import Upload


def kb_idle(lang: str) -> InlineKeyboardMarkup:
    """Shown on welcome / after confirm / after cancel — no active draft."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_new_upload", lang), callback_data="new"),
                InlineKeyboardButton(t("btn_list", lang), callback_data="list"),
            ],
            [
                InlineKeyboardButton(t("btn_cleanup", lang), callback_data="cleanup"),
                InlineKeyboardButton(t("btn_help", lang), callback_data="help"),
            ],
            [
                InlineKeyboardButton(t("btn_language", lang), callback_data="language"),
            ],
        ]
    )


def kb_draft_empty(lang: str) -> InlineKeyboardMarkup:
    """Active draft, no files yet — confirm hidden until something to confirm."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_context", lang), callback_data="context"),
                InlineKeyboardButton(t("btn_rename", lang), callback_data="rename"),
            ],
            [
                InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel"),
            ],
        ]
    )


def kb_draft_with_files(lang: str) -> InlineKeyboardMarkup:
    """Active draft with at least one file — full toolset."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_confirm", lang), callback_data="confirm"),
                InlineKeyboardButton(t("btn_context", lang), callback_data="context"),
            ],
            [
                InlineKeyboardButton(t("btn_rename", lang), callback_data="rename"),
                InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel"),
            ],
        ]
    )


def kb_confirmed(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_new_upload", lang), callback_data="new"),
                InlineKeyboardButton(t("btn_list", lang), callback_data="list"),
            ],
        ]
    )


def kb_list(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_new_upload", lang), callback_data="new"),
                InlineKeyboardButton(t("btn_cleanup", lang), callback_data="cleanup"),
            ],
        ]
    )


def kb_cleanup_items(
    oldest: list[Upload],
    biggest: list[Upload],
    lang: str,  # noqa: ARG001 — reserved for future localised labels
) -> InlineKeyboardMarkup:
    """One row per upload — dedupes ids that appear in both oldest and biggest.

    Button text is `🗑 <name-or-id> (<size>)`. Callback data is `del:<id>` —
    well under Telegram's 64-byte limit since ids are ~8 chars.
    """
    seen: set[str] = set()
    rows: list[list[InlineKeyboardButton]] = []
    for u in (*oldest, *biggest):
        if u.id in seen:
            continue
        seen.add(u.id)
        ref = u.name or u.id
        label = f"🗑 {ref} ({human_size(u.size_bytes)})"
        rows.append([InlineKeyboardButton(label, callback_data=f"del:{u.id}")])
    return InlineKeyboardMarkup(rows)


def kb_language() -> InlineKeyboardMarkup:
    """Language picker — flags only, no localised strings (it's the picker itself)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang:it"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
            ],
        ]
    )


def kb_update_confirm(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_update_now", lang), callback_data="update:go"),
                InlineKeyboardButton(t("btn_update_later", lang), callback_data="update:skip"),
            ],
        ]
    )
