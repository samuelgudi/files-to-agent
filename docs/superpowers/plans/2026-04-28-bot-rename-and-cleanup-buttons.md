# Bot Rebrand + Cleanup Delete Buttons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the bot's welcome blurb from "staging file bot" to "File To Agent Bot" in both locales, and add per-item inline delete buttons to the `/pulizia` (cleanup) view so the "Tap an upload to delete" copy actually works.

**Architecture:** Two independent, small changes to the Telegram bot front-end:
1. String edit in `src/files_to_agent/messages.py` for the `welcome` key (IT + EN).
2. New `kb_cleanup_items(...)` factory in `src/files_to_agent/bot/keyboards.py`, attached by `handle_cleanup` (no-args branch) in `src/files_to_agent/bot/handlers.py`, plus a new `del:<id>` callback branch in `handle_callback` that calls the existing `core.delete_upload(...)`. UUIDs from `secrets.token_urlsafe(6)` produce ~8-char ids so `del:<id>` fits well under Telegram's 64-byte callback_data limit.

**Tech Stack:** Python 3.13, python-telegram-bot, pytest (async), uv. Follow the codebase's existing patterns: factories in `keyboards.py`, message strings in `messages.py`, handlers in `handlers.py`, tests in `tests/`.

**Codebase context the executor needs:**
- `src/files_to_agent/messages.py` holds bilingual string catalog `_IT` / `_EN`. Italian is canonical; English mirrors it. The `t(key, lang, **kwargs)` helper resolves with fallback to Italian. Both catalogs must stay in sync — every key present in `_IT` should also exist in `_EN`.
- `src/files_to_agent/bot/keyboards.py` contains all `InlineKeyboardMarkup` factories. Callback codes are documented in the module docstring; add new codes there too.
- `src/files_to_agent/bot/handlers.py` has `handle_cleanup` (line 482) and the callback dispatcher `handle_callback` (line 632). `handle_cleanup` with empty args lists oldest+biggest as plain text bullets and attaches `kb.kb_idle(...)` — that's the bug; it currently has no per-item buttons despite the message saying "Tocca un upload per eliminarlo".
- `tests/test_bot_handlers.py` has `_fake_update`, `_fake_context`, `_fake_callback_update`, and `_last_text` helpers. Mocked `reply_text` calls expose `reply_markup` via `call_args.kwargs["reply_markup"]`.
- `core.delete_upload(upload_id)` deletes both disk + DB. `core.oldest_uploads(chat_id, limit)` and `core.biggest_uploads(chat_id, limit)` return `Upload` objects.
- Run tests with: `uv run pytest tests/ -v` (or target a specific test).

---

## File Structure

**Modify:**
- `src/files_to_agent/messages.py` — update the `welcome` string in both `_IT` and `_EN`.
- `src/files_to_agent/bot/keyboards.py` — add `kb_cleanup_items(uploads, lang)` factory; document the new `del:<id>` callback code in the module docstring.
- `src/files_to_agent/bot/handlers.py` — modify `handle_cleanup` (no-args branch) to attach the new keyboard, and add a `del:` branch to `handle_callback`.

**Modify (tests):**
- `tests/test_messages.py` — add tests asserting the new welcome wording in both locales.
- `tests/test_bot_handlers.py` — add tests for cleanup keyboard attachment and `del:<id>` callback deletion.

No new files needed. No changes to `core.py`, `models.py`, `db.py`, `storage.py`.

---

## Task 1: Rebrand welcome message

**Files:**
- Modify: `src/files_to_agent/messages.py:7` (IT welcome) and `:186` (EN welcome)
- Test: `tests/test_messages.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_messages.py` (append after existing tests):

```python
def test_welcome_uses_file_to_agent_branding_it() -> None:
    out = t("welcome", "it")
    assert "File To Agent Bot" in out
    assert "staging" not in out.lower()


def test_welcome_uses_file_to_agent_branding_en() -> None:
    out = t("welcome", "en")
    assert "File To Agent Bot" in out
    assert "staging" not in out.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_messages.py::test_welcome_uses_file_to_agent_branding_it tests/test_messages.py::test_welcome_uses_file_to_agent_branding_en -v`

Expected: both FAIL — current strings contain "staging" and not "File To Agent Bot".

- [ ] **Step 3: Update IT welcome string**

In `src/files_to_agent/messages.py`, replace lines 6–9:

```python
    "welcome": (
        "👋 Ciao! Sono il File To Agent Bot.\n\n"
        "Usa i bottoni qui sotto per iniziare, oppure /help per la guida completa."
    ),
```

- [ ] **Step 4: Update EN welcome string**

In `src/files_to_agent/messages.py`, replace lines 185–188:

```python
    "welcome": (
        "👋 Hi! I'm the File To Agent Bot.\n\n"
        "Use the buttons below to start, or /help for the full guide."
    ),
```

- [ ] **Step 5: Run the new tests + the existing welcome tests**

Run: `uv run pytest tests/test_messages.py -v`

Expected: all pass, including `test_t_italian_default` and `test_t_english`.

- [ ] **Step 6: Run the full test suite to confirm no regressions**

Run: `uv run pytest tests/ -v`

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/files_to_agent/messages.py tests/test_messages.py
git commit -m "feat: rebrand welcome to 'File To Agent Bot' in both locales"
```

---

## Task 2: Cleanup keyboard factory

**Files:**
- Modify: `src/files_to_agent/bot/keyboards.py`
- Test: `tests/test_bot_handlers.py` (or a new `tests/test_keyboards.py` if preferred — see step 1 note)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_bot_handlers.py` (append at the end of the file). The test verifies the factory's button shape directly without going through a handler:

```python
from files_to_agent.bot.keyboards import kb_cleanup_items
from files_to_agent.models import Upload, UploadStatus
from datetime import UTC, datetime


def _fake_upload(upload_id: str, name: str | None = None, size: int = 100) -> Upload:
    return Upload(
        id=upload_id,
        name=name,
        chat_id=10,
        status=UploadStatus.CONFIRMED,
        context=None,
        file_count=1,
        size_bytes=size,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_used_at=None,
    )


def test_kb_cleanup_items_one_button_per_unique_upload() -> None:
    a = _fake_upload("aaaa1111", name="alpha", size=1000)
    b = _fake_upload("bbbb2222", name=None, size=2000)
    # Same id appears in both lists — must dedupe to a single button.
    markup = kb_cleanup_items([a, b], [a], lang="it")
    flat = [btn for row in markup.inline_keyboard for btn in row]
    callback_ids = [btn.callback_data for btn in flat]
    assert callback_ids.count("del:aaaa1111") == 1
    assert "del:bbbb2222" in callback_ids
    assert len(flat) == 2


def test_kb_cleanup_items_button_text_uses_name_or_id() -> None:
    a = _fake_upload("aaaa1111", name="alpha", size=1024)
    b = _fake_upload("bbbb2222", name=None, size=2048)
    markup = kb_cleanup_items([a], [b], lang="it")
    flat = [btn for row in markup.inline_keyboard for btn in row]
    by_id = {btn.callback_data: btn.text for btn in flat}
    assert "alpha" in by_id["del:aaaa1111"]
    assert "bbbb2222" in by_id["del:bbbb2222"]


def test_kb_cleanup_items_empty_returns_empty_keyboard() -> None:
    markup = kb_cleanup_items([], [], lang="it")
    flat = [btn for row in markup.inline_keyboard for btn in row]
    assert flat == []
```

(`Upload` and `UploadStatus` are imported from `files_to_agent.models`. The shape comes from `_row_to_upload` in `core.py`. If `Upload` has additional required fields, check `src/files_to_agent/models.py` and add them with safe defaults — it's a pydantic dataclass-like model.)

> **Note:** Before writing the helper, open `src/files_to_agent/models.py` to confirm the exact constructor signature for `Upload`. If any field above is wrong (extra/missing/renamed), correct the helper to match.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bot_handlers.py::test_kb_cleanup_items_one_button_per_unique_upload tests/test_bot_handlers.py::test_kb_cleanup_items_button_text_uses_name_or_id tests/test_bot_handlers.py::test_kb_cleanup_items_empty_returns_empty_keyboard -v`

Expected: ImportError — `kb_cleanup_items` does not exist yet.

- [ ] **Step 3: Implement the factory**

In `src/files_to_agent/bot/keyboards.py`:

(a) Update the module docstring's "Callback codes" section to add:

```
  del:<id>     -> delete upload <id> (one tap, no confirm step)
```

(b) Add at the top of the file (with the other imports):

```python
from files_to_agent.models import Upload
from files_to_agent.bot.format import human_size
```

(c) Append the new factory after `kb_list`:

```python
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
```

- [ ] **Step 4: Run the new tests**

Run: `uv run pytest tests/test_bot_handlers.py::test_kb_cleanup_items_one_button_per_unique_upload tests/test_bot_handlers.py::test_kb_cleanup_items_button_text_uses_name_or_id tests/test_bot_handlers.py::test_kb_cleanup_items_empty_returns_empty_keyboard -v`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/files_to_agent/bot/keyboards.py tests/test_bot_handlers.py
git commit -m "feat(bot): add kb_cleanup_items keyboard factory for delete buttons"
```

---

## Task 3: Wire keyboard into `handle_cleanup`

**Files:**
- Modify: `src/files_to_agent/bot/handlers.py:491-509` (the no-args branch of `handle_cleanup`)
- Test: `tests/test_bot_handlers.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_bot_handlers.py`:

```python
async def test_cleanup_no_args_attaches_per_item_delete_buttons(core: Core) -> None:
    u1 = core.create_upload(chat_id=10)
    core.add_file_to_upload(u1.id, "a", b"a" * 100)
    u2 = core.create_upload(chat_id=10)
    core.confirm_upload(u1.id)
    core.add_file_to_upload(u2.id, "b", b"b" * 200)
    core.confirm_upload(u2.id)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    ctx.args = []
    await handle_cleanup(upd, ctx)

    markup = upd.message.reply_text.call_args.kwargs["reply_markup"]
    flat = [btn for row in markup.inline_keyboard for btn in row]
    callback_data = {btn.callback_data for btn in flat}
    assert f"del:{u1.id}" in callback_data
    assert f"del:{u2.id}" in callback_data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bot_handlers.py::test_cleanup_no_args_attaches_per_item_delete_buttons -v`

Expected: FAIL — current `handle_cleanup` attaches `kb_idle` (no `del:` callbacks).

- [ ] **Step 3: Modify `handle_cleanup`**

In `src/files_to_agent/bot/handlers.py`, replace the no-args branch (the `if not args:` block starting around line 491). The existing code is:

```python
    if not args:
        oldest = core.oldest_uploads(chat_id=chat.id, limit=10)
        biggest = core.biggest_uploads(chat_id=chat.id, limit=10)
        if not oldest and not biggest:
            await _reply_html(
                update,
                _tr(update, context, "list_empty"),
                kb.kb_idle(_lang(update, context)),
            )
            return
        lines = [_tr(update, context, "cleanup_header"), _tr(update, context, "cleanup_oldest")]
        for r in oldest:
            ref = r.name or r.id
            lines.append(f"  - {ref}  ({r.status.value}, {human_size(r.size_bytes)})")
        lines.append(_tr(update, context, "cleanup_biggest"))
        for r in biggest:
            ref = r.name or r.id
            lines.append(f"  - {ref}  ({r.status.value}, {human_size(r.size_bytes)})")
        await _reply_html(update, "\n".join(lines), kb.kb_idle(_lang(update, context)))
        return
```

Replace the final `await _reply_html(...)` line with one that uses `kb_cleanup_items`:

```python
        await _reply_html(
            update,
            "\n".join(lines),
            kb.kb_cleanup_items(oldest, biggest, _lang(update, context)),
        )
        return
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_bot_handlers.py::test_cleanup_no_args_attaches_per_item_delete_buttons -v`

Expected: PASS.

- [ ] **Step 5: Run the existing cleanup tests**

Run: `uv run pytest tests/test_bot_handlers.py -k cleanup -v`

Expected: all PASS (existing `test_cleanup_no_args_shows_candidates`, `test_cleanup_by_ref_deletes`, `test_cleanup_older_than`).

- [ ] **Step 6: Commit**

```bash
git add src/files_to_agent/bot/handlers.py tests/test_bot_handlers.py
git commit -m "feat(bot): attach per-item delete buttons to cleanup view"
```

---

## Task 4: `del:<id>` callback branch

**Files:**
- Modify: `src/files_to_agent/bot/handlers.py` — `handle_callback` dispatcher (around line 632)
- Test: `tests/test_bot_handlers.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_bot_handlers.py`:

```python
async def test_callback_del_deletes_upload(core: Core) -> None:
    u = core.create_upload(chat_id=10)
    core.add_file_to_upload(u.id, "x", b"x" * 100)
    core.confirm_upload(u.id)

    upd = _fake_callback_update(user_id=1, chat_id=10, data=f"del:{u.id}")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)

    from files_to_agent.core import UploadNotFound
    with pytest.raises(UploadNotFound):
        core.get_upload(u.id)


async def test_callback_del_unknown_id_replies_not_found(core: Core) -> None:
    upd = _fake_callback_update(user_id=1, chat_id=10, data="del:doesnotexist")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)

    text_calls = upd.callback_query.message.reply_text.call_args_list
    combined = " ".join(
        (call.args[0] if call.args else call.kwargs.get("text", ""))
        for call in text_calls
    )
    # Reuses the existing info_not_found template.
    assert "doesnotexist" in combined


async def test_callback_del_other_chat_blocked(core: Core) -> None:
    # Upload created in chat 999 must not be deletable from chat 10.
    u = core.create_upload(chat_id=999)
    core.add_file_to_upload(u.id, "x", b"x" * 10)
    core.confirm_upload(u.id)

    upd = _fake_callback_update(user_id=1, chat_id=10, data=f"del:{u.id}")
    ctx = _fake_context(core, allowed=[1])
    await handle_callback(upd, ctx)

    # Upload still exists.
    assert core.get_upload(u.id).id == u.id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bot_handlers.py -k "callback_del" -v`

Expected: all FAIL — `del:` is an unknown callback (currently logged as warning, no action).

- [ ] **Step 3: Add the `del:` branch to `handle_callback`**

In `src/files_to_agent/bot/handlers.py`, in `handle_callback` (around line 632), add the new branch BEFORE the final `else: log.warning(...)` clause. After the `data == "update:skip"` branch:

```python
    elif data.startswith("del:"):
        upload_id = data[len("del:"):]
        chat = update.effective_chat
        if chat is None:
            return
        core = _core(context)
        try:
            u = core.find_by_ref(upload_id)
        except UploadNotFound:
            await _reply_html(update, _tr(update, context, "info_not_found", ref=upload_id))
            return
        if u.chat_id != chat.id:
            # Refuse to delete uploads belonging to a different chat.
            await _reply_html(update, _tr(update, context, "info_not_found", ref=upload_id))
            return
        freed = u.size_bytes
        core.delete_upload(u.id)
        await _reply_html(
            update,
            _tr(update, context, "cleanup_done", n=1, size=human_size(freed)),
            kb.kb_idle(_lang(update, context)),
        )
```

(`UploadNotFound` is already imported at the top of `handlers.py` from `files_to_agent.core`. `human_size` and `kb` are already imported. No new imports required.)

- [ ] **Step 4: Run the new tests**

Run: `uv run pytest tests/test_bot_handlers.py -k "callback_del" -v`

Expected: all PASS.

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest tests/ -v`

Expected: all green.

- [ ] **Step 6: Lint**

Run: `uv run ruff check src/ tests/`

Expected: no errors. Fix any issues that surface (most likely import ordering in `keyboards.py`).

- [ ] **Step 7: Commit**

```bash
git add src/files_to_agent/bot/handlers.py tests/test_bot_handlers.py
git commit -m "feat(bot): handle del:<id> callback to delete uploads from cleanup view"
```

- [ ] **Step 8: Push**

Per project convention (always push after commit):

```bash
git push
```

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Both user requests are covered — Task 1 = rename welcome; Tasks 2-4 = per-item delete buttons.
- [x] **Placeholder scan:** No "TBD"/"add error handling" — all code blocks contain real implementation.
- [x] **Type consistency:** `kb_cleanup_items(oldest, biggest, lang)` signature is identical across the factory definition (Task 2 step 3) and the call site (Task 3 step 3) and tests (Task 2 step 1).
- [x] **Callback data fits Telegram limit:** `del:` (4 bytes) + ~8-char id = 12 bytes, well under 64.
- [x] **Existing tests not broken:** Tasks 1-4 don't change existing behavior of `/pulizia <id>` or `/pulizia Ng` — those branches are untouched.
- [x] **Cross-chat isolation:** Task 4 step 3 explicitly checks `u.chat_id != chat.id` to prevent deletion of another chat's upload via crafted callback (defense in depth — buttons are only ever generated for one's own uploads, but the callback is still chat-scoped).
