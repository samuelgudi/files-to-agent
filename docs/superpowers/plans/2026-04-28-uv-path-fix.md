# `uv` PATH Fix in `run_git_update` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `run_git_update()` actually fulfill its "best effort, don't fail update if uv missing" comment. Today, when `uv` isn't on the supervised process's `PATH` (common with systemd / process-compose), the `FileNotFoundError` from `subprocess.run(["uv", ...])` bubbles up to the outer except and reports the whole update as failed — even though `git reset --hard origin/main` already succeeded.

**Architecture:** Add a small `_find_uv()` helper that consults `shutil.which`, then falls back to common install locations (`~/.local/bin/uv`, `~/.cargo/bin/uv`, `/usr/local/bin/uv`). Refactor the uv branch in `run_git_update` to skip silently if no uv is found, and to invoke uv via the resolved absolute path otherwise. The outer `except FileNotFoundError` stays — it handles the rare case where `git` itself is missing.

**Tech Stack:** Python 3.13 stdlib (`shutil`, `os`, `pathlib.Path`), pytest with `monkeypatch` and `tmp_path`. No new dependencies.

**Codebase context the executor needs:**
- `src/files_to_agent/updater.py` — function under change. Imports already include `os`, `subprocess`, `Path`. **Need to add** `shutil` import.
- The current `run_git_update` (lines 62-86 — verify line numbers; the file is short and may have shifted) catches `FileNotFoundError` in the outer try/except, which converts a missing-uv into `UpdateResult(False, ...)`. The fix is: probe for uv before invoking subprocess; if not found, skip the call entirely.
- `tests/test_version_updater.py` — existing tests for `detect_mode`, `has_supervisor`, `write_docker_flag`. Uses `monkeypatch` for environment manipulation. Pattern lives at lines 53-76. Add new tests there.
- The bot's own pyproject keeps deps minimal — when `uv sync` is skipped on a deploy that DID add a new dep, the bot will fail at import time on next start. That's an acceptable trade — it's loud and the operator knows to install uv. The point of this fix is: **most updates don't add deps**, so silently skipping `uv sync` is fine for the common case.
- Run tests with `uv run pytest tests/ -v`. Lint with `uv run ruff check src/ tests/`.

---

## File Structure

**Modify:**
- `src/files_to_agent/updater.py` — add `shutil` import, add `_find_uv()` helper, refactor the uv branch in `run_git_update()`.

**Modify (tests):**
- `tests/test_version_updater.py` — add three tests: (1) `_find_uv()` returns `shutil.which` result when present; (2) `_find_uv()` falls back to a common path when PATH lookup fails; (3) `run_git_update()` returns `ok=True` when `uv` is missing entirely.

No new files.

---

## Task 1: `_find_uv()` helper

**Files:**
- Modify: `src/files_to_agent/updater.py`
- Test: `tests/test_version_updater.py`

- [ ] **Step 1: Read the current updater module**

Run: `cat src/files_to_agent/updater.py` (or use the Read tool).

Confirm:
- Imports: `import os`, `import subprocess`, `import time`, `from pathlib import Path`, etc.
- `run_git_update` body matches what the plan assumes (a try/except with `FileNotFoundError` in the outer except, and `subprocess.run(["uv", "sync", "--frozen"], ...)` as the third subprocess call).

If line numbers have drifted, adjust your edits accordingly — the plan's references are approximate.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_version_updater.py`:

```python
def test_find_uv_returns_which_result_when_available(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(updater.shutil, "which", lambda name: "/some/path/uv" if name == "uv" else None)
    assert updater._find_uv() == "/some/path/uv"


def test_find_uv_falls_back_to_common_install_path(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # PATH lookup fails.
    monkeypatch.setattr(updater.shutil, "which", lambda name: None)
    # Pretend the user's home has ~/.local/bin/uv as an executable file.
    fake_home = tmp_path / "home"
    bin_dir = fake_home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    fake_uv = bin_dir / "uv"
    fake_uv.write_text("#!/bin/sh\necho uv\n")
    fake_uv.chmod(0o755)
    monkeypatch.setattr(updater.Path, "home", staticmethod(lambda: fake_home))

    found = updater._find_uv()
    assert found == str(fake_uv)


def test_find_uv_returns_none_when_nothing_found(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(updater.shutil, "which", lambda name: None)
    # Empty home so no fallback path resolves.
    fake_home = tmp_path / "empty_home"
    fake_home.mkdir()
    monkeypatch.setattr(updater.Path, "home", staticmethod(lambda: fake_home))
    # Ensure /usr/local/bin/uv is also pretended-absent by giving the function only
    # the home-relative candidates that we control. The function's third candidate
    # (/usr/local/bin/uv) might exist on the test host — accept either None or a
    # string that points to /usr/local/bin/uv.
    found = updater._find_uv()
    assert found is None or found == "/usr/local/bin/uv"
```

> **Note on the third test:** the `/usr/local/bin/uv` candidate could exist on the developer's machine. The assertion accepts either outcome rather than forcing a brittle environmental assumption. If you want a stricter test, monkeypatch `Path.exists` — but that risks breaking unrelated stdlib behavior. The relaxed assertion is safer.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_version_updater.py -k "find_uv" -v`

Expected: AttributeError on `updater._find_uv` and `updater.shutil` — neither exists yet.

- [ ] **Step 4: Add `shutil` import to `updater.py`**

In `src/files_to_agent/updater.py`, add `import shutil` to the imports block. The current imports are (around lines 4-9):

```python
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
```

Insert `import shutil` after `import os` (alphabetical):

```python
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
```

- [ ] **Step 5: Add the `_find_uv()` helper**

In `src/files_to_agent/updater.py`, insert the helper above `def run_git_update()` (i.e., between `detect_mode` / `mode_description` and `run_git_update`):

```python
def _find_uv() -> str | None:
    """Locate the `uv` executable, falling back to common install paths.

    Supervised processes (systemd, process-compose) often run with a stripped
    PATH that excludes ~/.local/bin and ~/.cargo/bin where uv typically lives.
    Returns an absolute path string if found, or None if uv is missing.
    """
    found = shutil.which("uv")
    if found:
        return found
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
        Path("/usr/local/bin/uv"),
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_version_updater.py -k "find_uv" -v`

Expected: all three PASS.

- [ ] **Step 7: Commit**

```bash
git add src/files_to_agent/updater.py tests/test_version_updater.py
git commit -m "feat(updater): add _find_uv helper with PATH fallback for supervised deploys"
```

---

## Task 2: Make `uv sync` non-fatal in `run_git_update`

**Files:**
- Modify: `src/files_to_agent/updater.py`
- Test: `tests/test_version_updater.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_version_updater.py`:

```python
def test_run_git_update_succeeds_when_uv_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Reproduces the Agent bug: git fetch + reset succeed, uv missing must not fail update."""
    from files_to_agent import updater as updater_mod

    # Force is_git_checkout() to True so we don't bail early.
    monkeypatch.setattr(updater_mod, "is_git_checkout", lambda: True)
    # Pretend uv is missing entirely.
    monkeypatch.setattr(updater_mod, "_find_uv", lambda: None)

    calls: list[list[str]] = []

    class _FakeCompleted:
        def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        # The first two calls are git fetch / git reset — succeed.
        return _FakeCompleted(returncode=0, stdout="HEAD is now at abcdef\n")

    monkeypatch.setattr(updater_mod.subprocess, "run", _fake_run)

    result = updater_mod.run_git_update()

    assert result.ok is True, f"expected ok=True, got {result}"
    # Verify uv was NOT invoked — only the two git commands ran.
    invoked_executables = [c[0] for c in calls]
    assert "uv" not in invoked_executables
    assert any("git" in c for c in invoked_executables)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_version_updater.py::test_run_git_update_succeeds_when_uv_missing -v`

Expected: FAIL — current code calls `subprocess.run(["uv", ...])` unconditionally; the fake_run records `uv` in `invoked_executables`, breaking the assertion. (Or, depending on the order of monkeypatches, AttributeError on `_find_uv` if Task 1 isn't merged yet — but it is merged in our plan order, so just run after Task 1.)

- [ ] **Step 3: Refactor `run_git_update`**

In `src/files_to_agent/updater.py`, locate the `run_git_update()` function. Find this block (likely around lines 79-83):

```python
        # uv sync if available — best effort, don't fail update if uv missing
        subprocess.run(
            ["uv", "sync", "--frozen"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180, check=False,
        )
```

Replace it with:

```python
        # uv sync if available — best effort, don't fail update if uv missing.
        # Supervised processes often have a stripped PATH; _find_uv probes
        # common install locations as a fallback.
        uv_path = _find_uv()
        if uv_path is not None:
            subprocess.run(
                [uv_path, "sync", "--frozen"],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180, check=False,
            )
```

Leave the rest of the function unchanged. The outer `except (FileNotFoundError, subprocess.TimeoutExpired)` stays — it still catches a missing `git`, which is a genuinely fatal condition.

- [ ] **Step 4: Run the new test**

Run: `uv run pytest tests/test_version_updater.py::test_run_git_update_succeeds_when_uv_missing -v`

Expected: PASS.

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest tests/ -v`

Expected: all green (147+ tests now: 144 from before + 4 new).

- [ ] **Step 6: Lint**

Run: `uv run ruff check src/ tests/`

Expected: no errors. Most likely issue: import ordering of the new `import shutil` — fix manually if ruff complains.

- [ ] **Step 7: Commit**

```bash
git add src/files_to_agent/updater.py tests/test_version_updater.py
git commit -m "fix(updater): skip uv sync when uv is missing instead of failing update"
```

- [ ] **Step 8: Push**

Per project convention (always push after commit):

```bash
git push
```

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Root cause from Agent's `[Errno 2] No such file or directory: 'uv'` traced to `subprocess.run(["uv", ...])` raising `FileNotFoundError` caught by the outer except — Task 2 fixes this exact path. PATH fallback for supervised processes — Task 1.
- [x] **Placeholder scan:** No "TBD" or "add validation" — every code block is the actual change.
- [x] **Type consistency:** `_find_uv()` returns `str | None`; the call site checks `if uv_path is not None:` and uses `uv_path` (a `str`) as `argv[0]`.
- [x] **Behavior preserved:** When `uv` IS available, behavior is identical to before (still `subprocess.run([uv_path, "sync", "--frozen"], ..., check=False)`). When uv-sync itself fails (returncode != 0), still ignored — matches the original "best effort" intent.
- [x] **Outer except still useful:** A missing `git` still surfaces as `UpdateResult(False, ..., "[Errno 2] No such file or directory: 'git'")` — that's a genuinely fatal config issue and should stay loud.
- [x] **No regression in existing tests:** Tests in `test_version_updater.py` for `detect_mode`, `has_supervisor`, `write_docker_flag` don't touch `run_git_update`, so they're unaffected.
- [x] **Test for the negative path:** `test_run_git_update_succeeds_when_uv_missing` is the canary that catches any future regression where someone re-introduces unconditional `["uv", ...]` invocation.
