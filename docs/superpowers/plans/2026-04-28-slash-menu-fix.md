# Slash-Menu Registration Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Telegram slash-command menu actually register at bot startup. Today the registration callback is wired via `Application.builder().post_init(_post_init)`, but PTB only invokes `post_init` from `run_polling()` / `run_webhook()`. The runner uses manual lifecycle (`initialize()` + `start()` + `updater.start_polling()`) because it's co-hosted with uvicorn FastAPI, so `_post_init` has never run since this wiring was introduced. Result: typing `/` in the bot shows nothing.

**Architecture:** Rename `_post_init` to `register_slash_menu` (the new name reflects what it actually does, and is honest about not being PTB's `post_init` hook anymore). Remove the now-misleading `.post_init(_post_init)` builder registration. Runner explicitly invokes `register_slash_menu(bot)` after `bot.initialize()` and before `bot.start()`. One round-trip to Telegram per language at startup, idempotent (safe to call again on restart).

**Tech Stack:** python-telegram-bot v20+, asyncio. No new deps.

**Codebase context the executor needs:**
- `src/files_to_agent/bot/app.py:78-86` — `_post_init` callback. Calls `app.bot.set_my_commands(_COMMANDS_IT)` (default), then `app.bot.set_my_commands(_COMMANDS_EN, language_code="en")`. Wrapped in try/except — never crashes on Telegram-side errors.
- `src/files_to_agent/bot/app.py:111` — `Application.builder()...post_init(_post_init)` registration. Remove this — it's dead code under our manual lifecycle.
- `src/files_to_agent/runner.py:54-58` — manual lifecycle:
  ```python
  bot = components.bot_app
  await bot.initialize()
  await bot.start()
  await bot.updater.start_polling()
  ```
  The fix inserts `await register_slash_menu(bot)` between `initialize()` and `start()`. Telegram bot calls require the bot to be initialized; ordering doesn't strictly matter as long as it's after `initialize()`.
- Verified PTB behavior: `.venv/Lib/site-packages/telegram/ext/_application.py:479` explicitly says: *"Does not call `post_init` - that is only done by `run_polling` and `run_webhook`"*, and `:1055-1056` shows it's invoked only from `__run`.
- Tests live in `tests/`. Use `unittest.mock.AsyncMock` for the bot's `set_my_commands` call. Run with `uv run pytest tests/ -v`. Lint with `uv run ruff check src/ tests/`.

---

## File Structure

**Modify:**
- `src/files_to_agent/bot/app.py` — rename `_post_init` → `register_slash_menu`, update its docstring, remove the `.post_init(_post_init)` from `build_application`.
- `src/files_to_agent/runner.py` — import `register_slash_menu`, call it after `bot.initialize()`.

**Add (test):**
- `tests/test_runner_slash_menu.py` — new file. One async test that asserts `register_slash_menu` calls `bot.set_my_commands` twice (default + `language_code="en"`).

(Putting it in a new file rather than `test_bot_handlers.py` because it's runner/wiring-level, not a handler test.)

---

## Task 1: Rename + remove dead registration

**Files:**
- Modify: `src/files_to_agent/bot/app.py`
- Test: `tests/test_runner_slash_menu.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_runner_slash_menu.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from files_to_agent.bot.app import register_slash_menu


@pytest.mark.asyncio
async def test_register_slash_menu_calls_set_my_commands_twice() -> None:
    """Registers default (Italian) menu and English-locale menu."""
    app = MagicMock()
    app.bot = MagicMock()
    app.bot.set_my_commands = AsyncMock()

    await register_slash_menu(app)

    assert app.bot.set_my_commands.call_count == 2
    # First call has no language_code → default (IT) menu.
    first_kwargs = app.bot.set_my_commands.call_args_list[0].kwargs
    assert "language_code" not in first_kwargs
    # Second call sets the EN-locale menu.
    second_kwargs = app.bot.set_my_commands.call_args_list[1].kwargs
    assert second_kwargs.get("language_code") == "en"


@pytest.mark.asyncio
async def test_register_slash_menu_swallows_telegram_errors() -> None:
    """A Telegram-side error must not crash the runner."""
    app = MagicMock()
    app.bot = MagicMock()
    app.bot.set_my_commands = AsyncMock(side_effect=RuntimeError("network down"))

    # Must not raise.
    await register_slash_menu(app)
    # And it tried at least once.
    assert app.bot.set_my_commands.call_count >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_runner_slash_menu.py -v`

Expected: ImportError — `register_slash_menu` doesn't exist (only `_post_init` does).

- [ ] **Step 3: Rename in `app.py`**

In `src/files_to_agent/bot/app.py`, replace the entire `_post_init` definition (lines ~78-86):

```python
async def _post_init(app: Application) -> None:
    """Register the slash menu in both languages."""
    try:
        await app.bot.set_my_commands(_COMMANDS_IT)  # default
        await app.bot.set_my_commands(_COMMANDS_EN, language_code="en")
        log.info("slash menu registered (it default + en)")
    except Exception:  # noqa: BLE001
        log.exception("failed to register slash menu")
```

with the renamed-and-clarified version:

```python
async def register_slash_menu(app: Application) -> None:
    """Register the bilingual slash-command menu with Telegram.

    Called explicitly from runner.py after Application.initialize(). We don't
    use Application.builder().post_init(...) because PTB only invokes that
    hook from Application.run_polling() / run_webhook(), and our runner uses
    manual lifecycle (initialize + start + updater.start_polling) because the
    bot is co-hosted with the uvicorn FastAPI resolver.
    """
    try:
        await app.bot.set_my_commands(_COMMANDS_IT)  # default
        await app.bot.set_my_commands(_COMMANDS_EN, language_code="en")
        log.info("slash menu registered (it default + en)")
    except Exception:  # noqa: BLE001
        log.exception("failed to register slash menu")
```

- [ ] **Step 4: Remove the dead `.post_init` registration**

In `build_application` (line ~111), replace:

```python
    builder = Application.builder().token(settings.bot_token).post_init(_post_init)
```

with:

```python
    builder = Application.builder().token(settings.bot_token)
```

(The `.post_init(...)` chain link is removed because the callback never fires under manual lifecycle. Any reader looking at this expecting it to register the menu is being misled — drop the misleading wiring.)

- [ ] **Step 5: Run the test**

Run: `uv run pytest tests/test_runner_slash_menu.py -v`

Expected: both tests PASS.

- [ ] **Step 6: Run full suite to confirm no regression**

Run: `uv run pytest tests/ -v`

Expected: 150 passed (148 previous + 2 new).

- [ ] **Step 7: Lint**

Run: `uv run ruff check src/ tests/`

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add src/files_to_agent/bot/app.py tests/test_runner_slash_menu.py
git commit -m "refactor(bot): rename _post_init to register_slash_menu, drop dead PTB hook"
```

---

## Task 2: Wire `register_slash_menu` into the runner

**Files:**
- Modify: `src/files_to_agent/runner.py`

- [ ] **Step 1: Add the import**

In `src/files_to_agent/runner.py`, change the existing import on line 9:

```python
from files_to_agent.bot.app import build_application
```

to:

```python
from files_to_agent.bot.app import build_application, register_slash_menu
```

- [ ] **Step 2: Invoke after `initialize()`**

In `run()` (around lines 54-58), the current sequence is:

```python
    bot = components.bot_app
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    log.info("bot polling started")
```

Insert the slash-menu registration between `initialize()` and `start()`:

```python
    bot = components.bot_app
    await bot.initialize()
    # PTB only auto-runs post_init from run_polling/run_webhook; we manage the
    # lifecycle manually (co-hosted with FastAPI), so register the menu directly.
    await register_slash_menu(bot)
    await bot.start()
    await bot.updater.start_polling()
    log.info("bot polling started")
```

- [ ] **Step 3: Smoke-test the import + run lint**

Run: `uv run python -c "from files_to_agent.runner import run; print('ok')"`

Expected: `ok`.

Run: `uv run ruff check src/ tests/`

Expected: no errors.

- [ ] **Step 4: Run the full suite again**

Run: `uv run pytest tests/ -v`

Expected: 150 passed.

- [ ] **Step 5: Commit**

```bash
git add src/files_to_agent/runner.py
git commit -m "fix(runner): explicitly register slash menu after bot.initialize()"
```

- [ ] **Step 6: Push**

```bash
git push
```

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Two reasons the menu wasn't appearing — (1) `post_init` not invoked under manual lifecycle, (2) callback was wired via the dead PTB hook. Both fixed: callback renamed and called directly; dead wiring removed.
- [x] **Placeholder scan:** No "TBD". Every code block is real.
- [x] **Type consistency:** `register_slash_menu(app: Application) -> None` matches both the call site (`runner.py`) and the test (passes a `MagicMock` simulating an `Application`).
- [x] **Failure isolation:** The function still wraps in `try/except Exception`, so Telegram outages don't crash the runner — verified by `test_register_slash_menu_swallows_telegram_errors`.
- [x] **Idempotent on restart:** `set_my_commands` is naturally idempotent; calling it on every bot startup is fine.
- [x] **No regression in existing tests:** No handler/runner tests assert on `_post_init` directly. The only references to `_post_init` are in `app.py` (renamed) and the now-removed builder call. A grep for `_post_init` after Task 1 should return zero hits in `src/` and `tests/`.
