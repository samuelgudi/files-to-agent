# Phase 3 — Remove the Self-Update Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 1 + Phase 2 must be merged + pushed first. The image-pull workflow (Phase 1) and semver pipeline (Phase 2) replace what `/update` was doing — Phase 3 deletes the now-dead code.

**Goal:** Remove the self-modifying-bot machinery. Container images are immutable; updates happen at the orchestrator layer (Watchtower / `docker compose pull`). The bot itself becomes a stateless container that exits cleanly when asked to restart, and that's it. Net deletion: ~600 lines of code, two scripts, one systemd unit, one cron job, ~12 message strings × 2 locales, the `update-flag` Docker volume.

**Architecture:** After Phase 3, `/version` is read-only (just reports current version + commit SHA — no upstream check, no update prompt). `/restart` stays (still useful for any supervised deploy). The `updater.py` module is deleted entirely. `version.py` loses `fetch_upstream` + `commits_behind` (kept only `_read_distribution_version`, `is_git_checkout`, `short_sha`, `commit_sha`, `get_version_info`). The `_daily_update_check` job is removed from `app.py`. The `update-flag` mount is removed from `docker-compose.yml`. `scripts/` directory is gone.

**Tech Stack:** No new tech — pure deletion + simplification.

**Codebase context the executor needs:**
- `src/files_to_agent/updater.py` — entire file gets deleted. Contains: `DeployMode` Literal, `DOCKER_FLAG_DIR`, `DOCKER_FLAG_FILE`, `UpdateResult`, `in_docker`, `has_supervisor`, `detect_mode`, `mode_description`, `run_git_update`, `_find_uv`, `write_docker_flag`, `schedule_self_exit`. **`schedule_self_exit` is used by `/restart`** — relocate it to a small helper module before deleting `updater.py`. See Task 2.
- `src/files_to_agent/bot/handlers.py` — has `handle_update`, `_run_update_flow`, `handle_version` (keep, simplify), `handle_restart` (keep, but its `detect_mode` import goes away). Callback dispatcher has `update:go`, `update:skip`, `del:` branches. The `update:*` ones go away.
- `src/files_to_agent/bot/keyboards.py` — `kb_update_confirm` factory. Goes away.
- `src/files_to_agent/bot/app.py` — imports `handle_update`, registers `/update` slash command, sets up `_daily_update_check` job. All gone.
- `src/files_to_agent/messages.py` — `update_confirm`, `update_starting`, `update_no_changes`, `update_failed`, `update_docker_instructions`, `update_docker_triggered`, `update_no_supervisor`, `update_notify_daily`, `version_behind`, `btn_update_now`, `btn_update_later`. All gone (× 2 locales).
- `src/files_to_agent/version.py` — `fetch_upstream`, `commits_behind`. Gone (the comments saying "scheduled for removal in Phase 3" are doing exactly what's described).
- `src/files_to_agent/config.py` (line 50ish) — may have `staging_dir`-style settings. **Check** for `update_check_daily` or similar before this phase; remove if present.
- `src/files_to_agent/runner.py` — should be unaffected.
- `tests/` — many tests reference these symbols. They all need updating or deletion.
- `scripts/update-host.sh`, `scripts/files-to-agent-update-host.service` — both deleted; entire `scripts/` folder may be empty after.
- `docs/deployment.md` — already partly rewritten in Phase 1. The "Self-update" sections (lines ~80-118 of the original; verify after Phase 1 lands) get deleted.
- `README.md` — line ~20 mentions "Self-update". Replace with a note about Watchtower / `docker compose pull`.
- `docker-compose.yml` — has `./update-flag:/var/lib/files-to-agent` mount. Remove. Same for `update-flag/` directory if present in the repo.
- The `handle_restart` handler today uses `detect_mode()` to pick between supervised_git/docker (exit) vs bare_git/unknown (warn). After Phase 3, `handle_restart` simplifies: assume the container is supervised (which it is on every supported deploy mode now — Docker has `restart: unless-stopped`, process-compose has `availability.restart: always`, systemd has the unit). Just call `schedule_self_exit()`. If the user runs the bot bare with no supervisor, that's their problem; `/restart` will indeed kill the bot — same as `pkill files-to-agent` would.

**External prerequisites (USER must do):** None. After Phase 3 ships and is deployed, instruct any user with the `update-host.sh` systemd service to disable + remove it: `sudo systemctl disable --now files-to-agent-update-host && sudo rm /usr/local/bin/files-to-agent-update-host /etc/systemd/system/files-to-agent-update-host.service`. Document this in the migration notes.

---

## File Structure

**Delete:**
- `src/files_to_agent/updater.py`
- `scripts/update-host.sh`
- `scripts/files-to-agent-update-host.service`
- The `scripts/` directory if empty

**Modify:**
- `src/files_to_agent/bot/handlers.py` — remove `handle_update`, `_run_update_flow`, `update:*` callback branches; simplify `handle_version` (no upstream check); simplify `handle_restart` (always call `schedule_self_exit`).
- `src/files_to_agent/bot/keyboards.py` — remove `kb_update_confirm` and its `Callback codes` doc entries.
- `src/files_to_agent/bot/app.py` — remove imports for `handle_update`, the `/update` `CommandHandler`, the `BotCommand("update", ...)` entries, the `_daily_update_check` async function and its `job_queue.run_daily(...)` call.
- `src/files_to_agent/messages.py` — remove all the message keys listed above, in both `_IT` and `_EN`. Update `help` text to no longer mention `/update`.
- `src/files_to_agent/version.py` — remove `fetch_upstream`, `commits_behind`, the `behind` field of `VersionInfo`, and the `check_upstream` parameter of `get_version_info`.
- `src/files_to_agent/config.py` — verify no update-related settings remain (especially `UPDATE_CHECK_DAILY`).
- `docker-compose.yml` — remove the `./update-flag:/var/lib/files-to-agent` mount.
- `docker-compose.dev.yml` — verify it doesn't add the same mount; if it does, remove.
- `tests/test_version_updater.py` — remove tests for deleted functions; rename file to `tests/test_version.py` since it's no longer about the updater.
- `tests/test_bot_handlers.py` — remove `test_update_owner_only`, `test_restart_bare_git_warns_no_supervisor` (the bare-git path is gone). Update `test_restart_supervised_calls_schedule_exit` and `test_restart_docker_calls_schedule_exit` — they probably collapse into one.
- `tests/test_messages.py` — update `REQUIRED_KEYS` to remove the deleted keys.
- `README.md` — remove the "Self-update" bullet (line ~20).
- `docs/deployment.md` — remove the entire "Self-update" section.

**Add:**
- `src/files_to_agent/lifecycle.py` (new tiny module) — relocates `schedule_self_exit` from `updater.py`. Single function, ~6 lines. Better home now that `updater.py` is gone.
- `docs/migration-from-self-update.md` — one-page note for users on legacy installs explaining how to disable the host watcher service.

**Don't touch:**
- `runner.py`, `core.py`, `models.py`, `db.py`, `storage.py`, `resolver/*`, the upload/cleanup/list/info handlers, `bot/format.py`, `bot/auth.py`, `__main__.py`.

---

## Task 1: Relocate `schedule_self_exit` to a new `lifecycle.py`

**Files:**
- Add: `src/files_to_agent/lifecycle.py`
- Modify: `src/files_to_agent/bot/handlers.py` (the `from files_to_agent.updater import ...` line)

- [ ] **Step 1: Create `lifecycle.py`**

Create `src/files_to_agent/lifecycle.py`:

```python
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
```

- [ ] **Step 2: Update the import in `handlers.py`**

In `src/files_to_agent/bot/handlers.py`, locate the imports from `updater`:

```python
from files_to_agent.updater import (
    detect_mode,
    mode_description,
    run_git_update,
    schedule_self_exit,
    write_docker_flag,
)
```

Replace with just:

```python
from files_to_agent.lifecycle import schedule_self_exit
```

- [ ] **Step 3: Run the existing `restart` test to verify nothing else breaks yet**

Run: `uv run pytest tests/test_bot_handlers.py -k "restart" -v`

Expected: some tests will FAIL because `handle_update`, `detect_mode`, etc. are still expected by other code paths in `handlers.py` (which we haven't deleted yet). **That's OK** — Task 2 fixes the rest. For now, just verify there are no *import* errors when collecting tests.

If pytest can't even collect the test file, stop and inspect — likely a missing import we haven't accounted for.

- [ ] **Step 4: Commit**

```bash
git add src/files_to_agent/lifecycle.py src/files_to_agent/bot/handlers.py
git commit -m "refactor: extract schedule_self_exit to lifecycle module"
```

---

## Task 2: Delete the `/update` handler + simplify `/version` and `/restart`

**Files:**
- Modify: `src/files_to_agent/bot/handlers.py`
- Modify: `src/files_to_agent/bot/keyboards.py`
- Modify: `src/files_to_agent/bot/app.py`
- Modify: `src/files_to_agent/messages.py`
- Modify: `src/files_to_agent/version.py`

- [ ] **Step 1: Simplify `handle_version` in `handlers.py`**

Find the current `handle_version` (around line 568). It currently calls `get_version_info(check_upstream=True)`, branches on `info.behind` to decide which message to show, and presents `kb_update_confirm` if behind > 0.

Replace the entire `handle_version` body with:

```python
@require_owner
async def handle_version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    info = get_version_info()
    await _reply_html(
        update,
        _tr(
            update, context, "version_block",
            version=info.version, sha=info.sha,
        ),
        kb.kb_idle(_lang(update, context)),
    )
```

Note the call signature: `get_version_info()` — no `check_upstream` arg. Phase 2 left it in; Phase 3 (Task 6 of this plan) removes it from `version.py`.

The new `version_block` template no longer has a `{mode}` or `{status}` slot — see Task 3.

- [ ] **Step 2: Delete `handle_update` and `_run_update_flow`**

In `handlers.py`, find and **delete entirely**:

```python
@require_owner
async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ...

async def _run_update_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ...
```

(They span ~30 lines combined.)

- [ ] **Step 3: Simplify `handle_restart`**

Find `handle_restart` (added in the prior plan, around line 633 originally — line numbers will have shifted after Step 2). Replace its body with:

```python
@require_owner
async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit the bot process so the supervisor restarts it.

    All supported deploy modes (Docker, process-compose, systemd) auto-restart
    the bot on exit. If you're running the bot bare, /restart will kill it —
    that's expected; bare runs aren't a supported deployment mode.
    """
    _clear_awaiting(context)
    await _reply_html(update, _tr(update, context, "restart_starting"))
    schedule_self_exit()
```

The `detect_mode()` call and the `update_no_supervisor` warning are gone.

- [ ] **Step 4: Remove `update:*` callback branches**

Find the `handle_callback` dispatcher (around line 632 originally). Locate these branches:

```python
    elif data == "update:go":
        # Only the owner can actually run the update.
        ...
    elif data == "update:skip":
        ...
```

Delete both elif blocks entirely.

- [ ] **Step 5: Delete `kb_update_confirm` from `keyboards.py`**

In `src/files_to_agent/bot/keyboards.py`, find:

```python
def kb_update_confirm(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_update_now", lang), callback_data="update:go"),
                InlineKeyboardButton(t("btn_update_later", lang), callback_data="update:skip"),
            ],
        ]
    )
```

Delete the entire function. Also update the `Callback codes:` block at the top of the file to remove the `update:go` and `update:skip` lines.

- [ ] **Step 6: Update `app.py`**

In `src/files_to_agent/bot/app.py`:

(a) Remove `handle_update` from the imports.
(b) Remove the `BotCommand("update", ...)` line from both `_COMMANDS_IT` and `_COMMANDS_EN`.
(c) Remove `app.add_handler(CommandHandler(["update"], handle_update))`.
(d) Remove the entire `_daily_update_check` function definition.
(e) Remove the `if os.environ.get("UPDATE_CHECK_DAILY", ...)` block at the bottom of `build_application`.
(f) Remove unused imports left over: `from datetime import time as dtime`, the `os` import (only if no longer used elsewhere — check first), `from files_to_agent.version import (commits_behind, fetch_upstream, is_git_checkout)` — replace with whatever's still needed (probably nothing).

After this, `app.py` should be ~30 lines shorter.

- [ ] **Step 7: Strip update-related message keys from `messages.py`**

In `src/files_to_agent/messages.py`, in both `_IT` and `_EN`, **delete** these keys:
- `update_confirm`
- `update_starting`
- `update_no_changes`
- `update_failed`
- `update_docker_instructions`
- `update_docker_triggered`
- `update_no_supervisor`
- `update_notify_daily`
- `version_behind`
- `version_unknown`
- `btn_update_now`
- `btn_update_later`

Also update the `help` text in both locales to remove the `• /update — ...` line.

Update `version_block` to drop the `{mode}` and `{status}` placeholders. The new IT version_block:

```python
    "version_block": (
        "📦 <b>files-to-agent {version}</b>\n"
        "Commit: <code>{sha}</code>"
    ),
```

EN identical (just translated, but actually it's just text — make sure the EN block matches structure):

```python
    "version_block": (
        "📦 <b>files-to-agent {version}</b>\n"
        "Commit: <code>{sha}</code>"
    ),
```

- [ ] **Step 8: Delete the upstream functions from `version.py`**

In `src/files_to_agent/version.py`:

(a) Remove `fetch_upstream` and `commits_behind` function definitions.
(b) Remove the `behind` field from `VersionInfo` dataclass.
(c) Remove the `check_upstream` parameter of `get_version_info()` and the body lines that use it. New body:

```python
def get_version_info() -> VersionInfo:
    return VersionInfo(
        version=_read_distribution_version(),
        sha=commit_sha(),
        is_git=is_git_checkout(),
    )
```

The `subprocess` import may still be needed by `_git()` (used by `short_sha`). Verify before removing.

- [ ] **Step 9: Run tests, expect failures, then update them**

Run: `uv run pytest tests/ -v 2>&1 | tail -40`

You'll see failures across `test_bot_handlers.py`, `test_messages.py`, `test_version_updater.py`. Fix them in this order:

(a) **Rename `tests/test_version_updater.py` to `tests/test_version.py`:**

```bash
git mv tests/test_version_updater.py tests/test_version.py
```

Then in `tests/test_version.py`, delete tests for `fetch_upstream`, `commits_behind`, `detect_mode`, `has_supervisor`, `write_docker_flag`, `_find_uv`, `run_git_update`. Keep tests for `_read_distribution_version`, `commit_sha`, `short_sha`, `is_git_checkout`. Drop the `import` of `updater` (if any remains).

(b) **In `tests/test_bot_handlers.py`:** delete `test_update_owner_only` (the test references `from files_to_agent.bot.handlers import handle_update`). Delete `test_restart_bare_git_warns_no_supervisor`. Collapse `test_restart_supervised_calls_schedule_exit` and `test_restart_docker_calls_schedule_exit` into a single test:

```python
async def test_restart_calls_schedule_exit(core: Core, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from files_to_agent.bot import handlers as handlers_mod

    called = {"exit": False}

    monkeypatch.setattr(
        handlers_mod, "schedule_self_exit",
        lambda: called.__setitem__("exit", True),
    )

    upd = _fake_update(user_id=1, chat_id=10)
    ctx = _fake_context(core, allowed=[1])
    await handlers_mod.handle_restart(upd, ctx)

    assert called["exit"] is True
    text = _last_text(upd)
    assert "Riavvio" in text or "Restart" in text
```

(c) **In `tests/test_messages.py`:** update `REQUIRED_KEYS` — remove `version_unknown`, the `update_*` and `version_behind`, `btn_update_*` if any are listed.

- [ ] **Step 10: Run the suite again until green**

Run: `uv run pytest tests/ -v`

Expected: all PASS. Adjust any remaining failures by deleting/updating the offending test rather than re-introducing the deleted code.

- [ ] **Step 11: Lint**

Run: `uv run ruff check src/ tests/`

Fix any "imported but unused" warnings — likely culprits are `os`, `time`, `subprocess`, `Path` that may have lost their last user.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: remove self-update stack — bot is now stateless, updates via orchestrator"
```

---

## Task 3: Delete `updater.py`, scripts, and `update-flag` mount

**Files:**
- Delete: `src/files_to_agent/updater.py`
- Delete: `scripts/update-host.sh`, `scripts/files-to-agent-update-host.service`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Confirm `updater.py` is unused**

Run: `grep -rn "files_to_agent.updater\|from files_to_agent import updater" src/ tests/ 2>&1 | grep -v "\.pyc"`

Expected: no results. If anything turns up, **stop and fix** that import first.

- [ ] **Step 2: Delete `updater.py`**

```bash
rm src/files_to_agent/updater.py
```

- [ ] **Step 3: Delete the host scripts**

```bash
rm scripts/update-host.sh scripts/files-to-agent-update-host.service
rmdir scripts/ 2>/dev/null || true
```

If `scripts/` has other files, leave the directory alone — `rmdir` only removes empty dirs.

- [ ] **Step 4: Remove the `update-flag` volume from `docker-compose.yml`**

Edit `docker-compose.yml`. Remove these three lines:

```yaml
      # Update-flag volume — bot writes ./update-flag/update.requested
      # which the host script (scripts/update-host.sh) polls.
      - ./update-flag:/var/lib/files-to-agent
```

Also remove the `update-flag/` directory from the repo (or leave as a stale artifact for users with existing deploys; doesn't matter for the image):

```bash
rm -rf update-flag/ 2>/dev/null || true
```

- [ ] **Step 5: Run the suite**

Run: `uv run pytest tests/ -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: delete updater.py, host watcher scripts, and update-flag mount"
```

---

## Task 4: Documentation cleanup

**Files:**
- Modify: `README.md`
- Modify: `docs/deployment.md`
- Add: `docs/migration-from-self-update.md`

- [ ] **Step 1: Strip self-update mentions from README**

Find the `## Features` list in `README.md`. Remove the bullet:

> - Self-update — `/version` checks origin, `/update` pulls and restarts (git checkouts) or signals the host helper script (Docker)

Replace it with:

> - Stateless container — updates via orchestrator (Watchtower / `docker compose pull`); no in-process git operations

- [ ] **Step 2: Strip the self-update section from `deployment.md`**

In `docs/deployment.md`, delete the entire `## Self-update` section and its subsections (`### process-compose / standalone with restart-on-exit`, `### Docker`, `### Daily upstream check`). Replace with:

```markdown
## Updating

The bot is a stateless container. Updates happen at the orchestrator layer.

### Manual

`​`​`​bash
docker compose pull
docker compose up -d
`​`​`​

### Automatic

Run [Watchtower](https://containrrr.dev/watchtower/) on the host. It polls
the registry for new image tags and restarts the container automatically.

`​`​`​bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  files-to-agent
`​`​`​

If you're running with `image: ghcr.io/samuelgudi/files-to-agent:latest`,
Watchtower picks up new pushes within the polling interval. If you're
pinned to `:vX.Y.Z`, Watchtower won't update across versions — you bump
the tag yourself.

For non-Docker deploys (process-compose, standalone Python), update by
re-running `git pull && uv sync` and bouncing the process. The `/restart`
command does the bounce part for you on supervised runs.
```

(Unescape the triple-backtick fences when writing.)

- [ ] **Step 3: Add the migration note**

Create `docs/migration-from-self-update.md`:

```markdown
# Migrating from the self-update mechanism

If you installed `files-to-agent` before v0.2.0, you may have:
- The host watcher systemd service (`files-to-agent-update-host`) running
- A `./update-flag/` directory in your compose folder
- A `/var/lib/files-to-agent/update.requested` flag file
- An `UPDATE_CHECK_DAILY` env var in your `.env`

These are all obsolete. Clean them up:

`​`​`​bash
sudo systemctl disable --now files-to-agent-update-host 2>/dev/null || true
sudo rm -f /usr/local/bin/files-to-agent-update-host \
           /etc/systemd/system/files-to-agent-update-host.service
sudo systemctl daemon-reload
rm -rf ./update-flag/
sed -i '/^UPDATE_CHECK_DAILY=/d' .env
`​`​`​

The new update flow is in [deployment.md](deployment.md#updating).

The `/update` command and the daily upstream-check DM no longer exist. `/version`
now just reports the current version and commit SHA. To trigger an update,
pull the new image at the orchestrator layer (or let Watchtower do it).
```

(Unescape the fences.)

- [ ] **Step 4: Commit**

```bash
git add README.md docs/deployment.md docs/migration-from-self-update.md
git commit -m "docs: remove self-update sections; add migration guide"
```

---

## Task 5: Final push

- [ ] **Step 1: Run the full suite one more time**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`

Expected: all green.

- [ ] **Step 2: Push**

```bash
git push
```

- [ ] **Step 3: Smoke-test by reading the changed files**

Briefly cat each modified file and confirm:
- `src/files_to_agent/version.py` — only has the metadata-based version reader, `commit_sha`, and basic git helpers. No `fetch_upstream`, no `commits_behind`.
- `src/files_to_agent/bot/handlers.py` — no `handle_update`, no `_run_update_flow`. `handle_version` is a single short function. `handle_restart` is a single short function.
- `src/files_to_agent/bot/app.py` — no `_daily_update_check`, no `BotCommand("update", ...)`.
- `docker-compose.yml` — no `update-flag` mount.
- `src/files_to_agent/updater.py` — does not exist (`ls src/files_to_agent/`).

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Removed code (Tasks 2-3), removed scripts (Task 3), removed mount (Task 3), removed messages + slash menu (Task 2), removed daily job (Task 2), updated docs (Task 4). All deletion targets covered.
- [x] **`/restart` preserved:** It's the one piece of the supervised-restart story that survives because it's still useful diagnostically. Now lives in its own `lifecycle.py` module instead of being buried in `updater.py`.
- [x] **Tests updated:** Several tests deleted, others rewritten — explicit instructions in Task 2 Step 9.
- [x] **No silent imports left:** Task 3 Step 1 explicitly greps for stale `updater` imports before deletion.
- [x] **Migration documented:** Task 4 Step 3 adds `migration-from-self-update.md` so any existing deployer knows what to clean up.
- [x] **Phase boundary:** Doesn't add CHANGELOG/CONTRIBUTING (Phase 4); doesn't touch image build (Phase 1).
- [x] **Naming:** `lifecycle.py` (Task 1) is a bit of a one-function module, which is usually a code smell — but the alternative (jamming `schedule_self_exit` into `runner.py` or `__main__.py`) creates worse import cycles. A small focused module is the right call.
