# `/restart` Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an owner-only `/restart` (`/riavvia` in Italian) command that exits the bot process so the supervisor (systemd / process-compose / Docker `restart: unless-stopped`) brings it back. Useful when code is on disk but the bot is still running on stale memory — e.g. after a partial `/update`.

**Architecture:** Reuses the existing `schedule_self_exit()` primitive from `updater.py` and the `detect_mode()` dispatch already used by `/update`. New handler delegates to that primitive on `supervised_git` and `docker` modes; on `bare_git` / `unknown` it shows the existing `update_no_supervisor` warning instead of exiting (which would leave the bot dead). No changes to the updater module itself, no new dependencies.

**Tech Stack:** Python 3.13, python-telegram-bot, pytest async, uv. Match the patterns of `handle_update` / `handle_version` exactly — owner-only via `@require_owner`, mode dispatch identical to `_run_update_flow` minus the `git pull` step.

**Codebase context the executor needs:**
- `src/files_to_agent/bot/handlers.py:592-626` — `handle_update` and `_run_update_flow`. The new `handle_restart` follows the same shape.
- `src/files_to_agent/updater.py:99-105` — `schedule_self_exit(delay_seconds=1.5)` exits via `os._exit(0)` from a daemon thread. Already imported in `handlers.py:25-29`.
- `src/files_to_agent/messages.py` — bilingual catalog. `update_no_supervisor` (lines 174-177 IT, 343-346 EN) is reused for the bare/unknown case. Need a new `restart_starting` key in both locales.
- `src/files_to_agent/bot/app.py:44-75` — slash-menu `BotCommand` lists. Append the new command to both. Lines 110-156 — handler registration. Add a `CommandHandler(["riavvia", "restart"], handle_restart)`.
- `docker-compose.yml` has `restart: unless-stopped` so container exit triggers an automatic restart — `/restart` works in Docker without any host-side flag-file dance (unlike `/update`, which needs the watcher to rebuild the image).
- Owner check: `@require_owner` (already used by `handle_version` / `handle_update`). Owner is `allowed_user_ids[0]`.
- Tests live in `tests/test_bot_handlers.py`. `_fake_update`, `_fake_context`, `_last_text` helpers exist. The pattern for owner-only tests is at lines 559-575 (`test_version_owner_only`, `test_update_owner_only`).
- Run tests with `uv run pytest tests/ -v`. Lint with `uv run ruff check src/ tests/`.

---

## File Structure

**Modify:**
- `src/files_to_agent/messages.py` — add `restart_starting` key to `_IT` (after the update-related keys, around line 181) and `_EN` (after the equivalent EN keys, around line 350). Update the `help` string in both locales to document `/restart`.
- `src/files_to_agent/bot/handlers.py` — add `handle_restart` after `handle_update` (around line 604).
- `src/files_to_agent/bot/app.py` — import `handle_restart`, append to `_COMMANDS_IT` and `_COMMANDS_EN`, register a `CommandHandler`.

**Modify (tests):**
- `tests/test_bot_handlers.py` — append three new tests in the "owner-only" section.

No new files. No changes to `core.py`, `models.py`, `db.py`, `storage.py`, `updater.py`, `keyboards.py`.

---

## Task 1: Message strings

**Files:**
- Modify: `src/files_to_agent/messages.py`

- [ ] **Step 1: Add `restart_starting` to IT catalog**

In `src/files_to_agent/messages.py`, in the `_IT` dict, after the `"update_notify_daily"` entry (around line 181), add:

```python
    "restart_starting": "🔄 Riavvio in corso… Il bot tornerà online tra qualche secondo.",
```

- [ ] **Step 2: Add `restart_starting` to EN catalog**

In the `_EN` dict, after the `"update_notify_daily"` entry (around line 350), add:

```python
    "restart_starting": "🔄 Restarting… The bot will be back in a few seconds.",
```

- [ ] **Step 3: Update IT help text**

In the `_IT["help"]` string, in the `<b>Sistema</b>` section, append a line for `/restart`. Replace:

```python
        "• /update — aggiorna il bot all'ultima versione (solo proprietario)"
```

with:

```python
        "• /update — aggiorna il bot all'ultima versione (solo proprietario)\n"
        "• /riavvia — riavvia il bot (solo proprietario)"
```

- [ ] **Step 4: Update EN help text**

In the `_EN["help"]` string, replace:

```python
        "• /update — update the bot to the latest version (owner only)"
```

with:

```python
        "• /update — update the bot to the latest version (owner only)\n"
        "• /restart — restart the bot (owner only)"
```

- [ ] **Step 5: Run the messages test suite**

Run: `uv run pytest tests/test_messages.py -v`

Expected: all PASS. (No new test added yet — this just confirms the catalog is still well-formed.)

- [ ] **Step 6: Commit**

```bash
git add src/files_to_agent/messages.py
git commit -m "feat(bot): add restart_starting message key + help-text entry"
```

---

## Task 2: `handle_restart` handler

**Files:**
- Modify: `src/files_to_agent/bot/handlers.py`
- Test: `tests/test_bot_handlers.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bot_handlers.py` (after the existing owner-only tests, around line 575):

```python
async def test_restart_owner_only(core: Core) -> None:
    from files_to_agent.bot.handlers import handle_restart

    upd = _fake_update(user_id=42, chat_id=10)
    ctx = _fake_context(core, allowed=[1, 42])  # 42 is allowed but not the owner
    await handle_restart(upd, ctx)
    assert "proprietario" in _last_text(upd) or "owner" in _last_text(upd).lower()


async def test_restart_supervised_calls_schedule_exit(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    def _fake_exit() -> None:
        called["exit"] = True

    monkeypatch.setattr(handlers_mod, "detect_mode", lambda: "supervised_git")
    monkeypatch.setattr(handlers_mod, "schedule_self_exit", _fake_exit)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is True
    assert "Riavvio" in _last_text(upd) or "Restart" in _last_text(upd)


async def test_restart_docker_calls_schedule_exit(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    def _fake_exit() -> None:
        called["exit"] = True

    monkeypatch.setattr(handlers_mod, "detect_mode", lambda: "docker")
    monkeypatch.setattr(handlers_mod, "schedule_self_exit", _fake_exit)

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is True


async def test_restart_bare_git_warns_no_supervisor(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    monkeypatch.setattr(handlers_mod, "detect_mode", lambda: "bare_git")
    monkeypatch.setattr(handlers_mod, "schedule_self_exit", lambda: called.__setitem__("exit", True))

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is False
    text = _last_text(upd)
    # Reuses update_no_supervisor — Italian wording "supervisore" or English "supervisor".
    assert "supervisor" in text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bot_handlers.py -k "restart" -v`

Expected: ImportError on `handle_restart` — function doesn't exist.

- [ ] **Step 3: Implement `handle_restart`**

In `src/files_to_agent/bot/handlers.py`, append a new handler after `_run_update_flow` (around line 627, immediately before the `# ---------- callback dispatcher ----------` comment):

```python
@require_owner
async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit the bot process so the supervisor restarts it.

    Works on supervised_git (systemd / process-compose) and docker
    (`restart: unless-stopped`). On bare_git / unknown there's no
    supervisor to bring the bot back, so we refuse with the same warning
    used by /update.
    """
    _clear_awaiting(context)
    mode = detect_mode()
    if mode in ("supervised_git", "docker"):
        await _reply_html(update, _tr(update, context, "restart_starting"))
        schedule_self_exit()
        return
    await _reply_html(update, _tr(update, context, "update_no_supervisor"))
```

(`detect_mode`, `schedule_self_exit`, `_clear_awaiting`, `_reply_html`, `_tr`, and `require_owner` are all already imported / defined in `handlers.py` — no new imports needed.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_bot_handlers.py -k "restart" -v`

Expected: all four PASS.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`

Expected: all green (140+ tests).

- [ ] **Step 6: Commit**

```bash
git add src/files_to_agent/bot/handlers.py tests/test_bot_handlers.py
git commit -m "feat(bot): add handle_restart owner-only handler"
```

---

## Task 3: Wire `/restart` into the app

**Files:**
- Modify: `src/files_to_agent/bot/app.py`

- [ ] **Step 1: Import `handle_restart`**

In `src/files_to_agent/bot/app.py`, in the import block from `files_to_agent.bot.handlers` (lines 14-31), add `handle_restart` alphabetically. Replace:

```python
from files_to_agent.bot.handlers import (
    handle_callback,
    handle_cancel,
    handle_cleanup,
    handle_confirm,
    handle_context,
    handle_help,
    handle_info,
    handle_language,
    handle_list_uploads,
    handle_media,
    handle_new,
    handle_pending_text,
    handle_rename,
    handle_start,
    handle_update,
    handle_version,
)
```

with:

```python
from files_to_agent.bot.handlers import (
    handle_callback,
    handle_cancel,
    handle_cleanup,
    handle_confirm,
    handle_context,
    handle_help,
    handle_info,
    handle_language,
    handle_list_uploads,
    handle_media,
    handle_new,
    handle_pending_text,
    handle_rename,
    handle_restart,
    handle_start,
    handle_update,
    handle_version,
)
```

- [ ] **Step 2: Add to IT slash menu**

In `_COMMANDS_IT` (around line 44), insert after the `BotCommand("update", ...)` line (so it stays grouped with other system commands):

```python
    BotCommand("riavvia",  "Riavvia il bot (solo proprietario)"),
```

The full `_COMMANDS_IT` list should now read (showing only the changed/adjacent lines):

```python
    BotCommand("update",   "Aggiorna il bot (solo proprietario)"),
    BotCommand("riavvia",  "Riavvia il bot (solo proprietario)"),
    BotCommand("help",     "Guida ai comandi"),
```

- [ ] **Step 3: Add to EN slash menu**

In `_COMMANDS_EN` (around line 61), insert after the `BotCommand("update", ...)` line:

```python
    BotCommand("restart",  "Restart the bot (owner only)"),
```

- [ ] **Step 4: Register the command handler**

In `build_application` (around line 131), after the `app.add_handler(CommandHandler(["update"], handle_update))` line, add:

```python
    app.add_handler(CommandHandler(["riavvia", "restart"], handle_restart))
```

- [ ] **Step 5: Smoke-test the import + run lint**

Run: `uv run python -c "from files_to_agent.bot.app import build_application; print('ok')"`

Expected: `ok` (no import errors).

Run: `uv run ruff check src/ tests/`

Expected: no errors. If ruff complains about import ordering in `app.py`, accept its `--fix` suggestion or reorder manually to match.

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v`

Expected: all green. The slash-menu registration is not directly tested but `build_application` import was just smoke-tested.

- [ ] **Step 7: Commit**

```bash
git add src/files_to_agent/bot/app.py
git commit -m "feat(bot): register /restart and /riavvia commands"
```

- [ ] **Step 8: Push**

Per project convention (always push after commit):

```bash
git push
```

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Owner-only check → Task 2 (test + `@require_owner`). Mode dispatch → Task 2 (3 cases tested). Slash menu → Task 3. Help text → Task 1. Bilingual command names (`/restart`, `/riavvia`) → Task 3.
- [x] **Placeholder scan:** No "TBD" — every code block has real content.
- [x] **Type consistency:** `handle_restart(update, context)` signature matches every other handler. `detect_mode()` returns `DeployMode` literals matching what's checked.
- [x] **Reuses primitives:** `schedule_self_exit`, `detect_mode`, `update_no_supervisor` — all existing. No new abstractions.
- [x] **Docker correctness:** `docker-compose.yml` has `restart: unless-stopped`, so `os._exit(0)` triggers a clean container restart. No host watcher needed (unlike `/update`).
- [x] **Bare-git safety:** `bare_git` and `unknown` modes show the warning instead of exiting — prevents bricking unsupervised deploys.
- [x] **Test for the negative path:** `test_restart_bare_git_warns_no_supervisor` asserts `schedule_self_exit` is NOT called — protects against future refactors that accidentally always exit.
