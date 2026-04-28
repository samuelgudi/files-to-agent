# Phase 2 — Versioning Discipline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 1 must be merged + pushed first. The Phase 1 GHA workflow (`.github/workflows/release.yml`) is what handles the `vX.Y.Z` tag-triggered image build that Phase 2 cuts releases against.

**Goal:** Adopt semver discipline so users (and Watchtower / `image:` pinning) can rely on stable version tags. Concretely: `version.py` reads from `importlib.metadata` instead of running `git rev-parse` (works inside the container, where there's no `.git`); a `RELEASE.md` documents the tag-cutting process; the first proper tag (`v0.1.1` since `pyproject.toml` is currently `0.1.0`) is created and pushed, validating the full pipeline; an auto-changelog tool (`git-cliff`) is wired so changelog generation is deterministic and reproducible.

**Architecture:** `version.py` becomes a thin wrapper around `importlib.metadata.version("files-to-agent")` for the version string and `importlib.metadata.metadata("files-to-agent")` for any other metadata. The git-SHA path is **kept** as a separate function (`short_sha()`) for the development case (running from a checkout) but `get_version_info()` no longer falls back to git for the version string itself — the version always comes from packaging metadata, which is what `pip install`/`uv sync` populates from `pyproject.toml`. This means: in a container, `/version` reports `0.1.1` (from packaging metadata) + a baked-in commit SHA (passed in via Docker build arg, see Task 3). In a checkout, `/version` reports `0.1.1` (still from metadata) + the live `git rev-parse HEAD`. Both paths agree on the version string, which is the whole point.

`fetch_upstream()` and `commits_behind()` stay for now — Phase 3 deletes them along with the daily-update job.

**Tech Stack:** Python 3.12+ stdlib (`importlib.metadata`), `git-cliff` (Rust binary, pin a version, run via `uvx` or pre-built action), GitHub Releases via the Phase 1 workflow.

**Codebase context the executor needs:**
- `src/files_to_agent/version.py` — current implementation reads version from `pyproject.toml` directly via `tomllib`, queries git for SHA + upstream behind. The `_read_pyproject_version()` function works in checkouts but **silently returns "unknown"** in a container (no `pyproject.toml` at runtime — only `.venv/lib/.../files_to_agent/`). This is the latent bug Phase 2 fixes.
- `pyproject.toml` — `version = "0.1.0"`. Update to `0.1.1` in Task 4 of this phase as the first semver release.
- `Dockerfile` — multi-stage build, `COPY pyproject.toml uv.lock ./` happens in stage 1. Stage 2 doesn't have `pyproject.toml` available — confirms the latent bug.
- `.github/workflows/release.yml` (from Phase 1) — already triggers on `v*` tags. Phase 2 just adds a "create GitHub Release" step to it.
- The version string is shown to users via `/version` (`handle_version` in `bot/handlers.py:568`). Users see `📦 files-to-agent 0.1.0\nCommit: abc123\nMode: ...`.

**External prerequisites (USER must do):** None. Phase 2 is fully self-driven.

---

## File Structure

**Modify:**
- `src/files_to_agent/version.py` — switch to `importlib.metadata`. Keep `short_sha`, `is_git_checkout`, `fetch_upstream`, `commits_behind` for now (Phase 3 removes the upstream pair). Add a new function `commit_sha()` that returns the bot's known commit SHA — checked from env var `FILES_TO_AGENT_COMMIT_SHA` (set at Docker build time) first, then falls back to `short_sha()` for git checkouts.
- `Dockerfile` — accept `COMMIT_SHA` build arg; bake it into the image as `ENV FILES_TO_AGENT_COMMIT_SHA=...`.
- `.github/workflows/release.yml` — pass `--build-arg COMMIT_SHA=${{ github.sha }}` to the build step. Add a "Create GitHub Release" step that runs only on `v*` tags.
- `pyproject.toml` — bump version to `0.1.1`.
- `tests/test_version_updater.py` — update tests for the new `commit_sha()` function. The existing tests for `short_sha`, `is_git_checkout`, etc. should still pass.

**Add:**
- `RELEASE.md` (root) — documents the release process: bump version, update changelog, tag, push.
- `cliff.toml` (root) — `git-cliff` configuration.

**Don't touch:**
- `runner.py`, `bot/app.py`, `bot/handlers.py` — they import `version` symbols; the API stays compatible.
- The self-update stack (Phase 3 owns it).

---

## Task 1: Refactor `version.py` to use `importlib.metadata`

**Files:**
- Modify: `src/files_to_agent/version.py`
- Modify: `tests/test_version_updater.py`

- [ ] **Step 1: Read the current `version.py`**

Run: `cat src/files_to_agent/version.py` (or Read tool).

Confirm the current shape:
- `_read_pyproject_version()` reads version from `pyproject.toml`
- `short_sha()` runs `git rev-parse --short HEAD`
- `is_git_checkout()` checks for `.git` dir
- `fetch_upstream()` and `commits_behind()` exist
- `get_version_info()` returns a dataclass

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_version_updater.py`:

```python
def test_read_version_from_metadata() -> None:
    """version.py should resolve the version via importlib.metadata, not pyproject.toml."""
    from files_to_agent import version as v

    info = v.get_version_info(check_upstream=False)
    # In a checkout-with-uv-sync run, this should be the pyproject version.
    # The exact value isn't asserted (it changes per release), but it must
    # NOT be "unknown" — that would indicate a packaging-metadata miss.
    assert info.version != "unknown", "importlib.metadata resolution failed"
    # And it must be a sane semver-ish string.
    assert info.version[0].isdigit() or info.version.startswith("v")


def test_commit_sha_from_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """When FILES_TO_AGENT_COMMIT_SHA is set, commit_sha() returns it."""
    from files_to_agent import version as v

    monkeypatch.setenv("FILES_TO_AGENT_COMMIT_SHA", "abc1234")
    assert v.commit_sha() == "abc1234"


def test_commit_sha_falls_back_to_git(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """When the env var is unset, commit_sha() falls back to short_sha (git)."""
    from files_to_agent import version as v

    monkeypatch.delenv("FILES_TO_AGENT_COMMIT_SHA", raising=False)
    monkeypatch.setattr(v, "short_sha", lambda: "deadbee")
    assert v.commit_sha() == "deadbee"
```

- [ ] **Step 3: Run the tests to confirm they fail**

Run: `uv run pytest tests/test_version_updater.py -k "metadata or commit_sha" -v`

Expected: AttributeError on `commit_sha`, plus the metadata test may or may not pass depending on whether `_read_pyproject_version` already works in the dev environment (it does, since uv sync exists). Either way, after the refactor all three pass.

- [ ] **Step 4: Refactor `version.py`**

Replace the current `version.py` contents with:

```python
"""Version inspection — reads packaging metadata + commit SHA, queries upstream."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISTRIBUTION_NAME = "files-to-agent"


@dataclass(frozen=True)
class VersionInfo:
    version: str           # from packaging metadata (importlib.metadata)
    sha: str               # short commit SHA, or "unknown"
    behind: int | None     # commits behind origin/main, None if undetermined
    is_git: bool


def _read_distribution_version() -> str:
    """Read the version string from packaging metadata.

    Works in any environment where the package was installed (uv sync,
    pip install, container with the wheel installed). Returns "unknown"
    only if the package isn't installed in the current Python environment
    (which shouldn't happen in production).
    """
    try:
        return metadata.version(DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return "unknown"


def _git(*args: str, cwd: Path = PROJECT_ROOT, timeout: int = 10) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def is_git_checkout() -> bool:
    return (PROJECT_ROOT / ".git").exists()


def short_sha() -> str:
    """Live commit SHA from a git checkout. Returns 'unknown' if no .git or git fails."""
    if not is_git_checkout():
        return "unknown"
    code, out = _git("rev-parse", "--short", "HEAD")
    return out if code == 0 else "unknown"


def commit_sha() -> str:
    """Commit SHA the bot was built from.

    Resolution order:
      1. FILES_TO_AGENT_COMMIT_SHA env var (set at Docker build via build-arg)
      2. Live `git rev-parse --short HEAD` (for development checkouts)

    This lets containerised deployments report the actual commit they were
    built from (env var baked in at build time), while dev runs report HEAD.
    """
    baked = os.environ.get("FILES_TO_AGENT_COMMIT_SHA")
    if baked:
        return baked
    return short_sha()


def fetch_upstream() -> bool:
    """Run `git fetch origin`. Returns True on success.

    NOTE: scheduled for removal in Phase 3 along with the daily-update job.
    """
    if not is_git_checkout():
        return False
    code, _ = _git("fetch", "origin", "--quiet", timeout=30)
    return code == 0


def commits_behind() -> int | None:
    """Count of commits on origin/main not in HEAD. None if undetermined.

    NOTE: scheduled for removal in Phase 3 along with the daily-update job.
    """
    if not is_git_checkout():
        return None
    code, out = _git("rev-list", "--count", "HEAD..origin/main")
    if code != 0:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def get_version_info(check_upstream: bool = True) -> VersionInfo:
    version = _read_distribution_version()
    sha = commit_sha()
    is_git = is_git_checkout()
    behind: int | None = None
    if is_git and check_upstream and fetch_upstream():
        behind = commits_behind()
    return VersionInfo(version=version, sha=sha, behind=behind, is_git=is_git)
```

Key changes:
- Removed `tomllib` import and `_read_pyproject_version`. Added `importlib.metadata` import and `_read_distribution_version`.
- Added `commit_sha()` (env-or-git lookup).
- `get_version_info()` calls `commit_sha()` instead of `short_sha()` (so containers report the baked-in SHA).
- `fetch_upstream` / `commits_behind` annotated with the Phase 3 removal note (no behavior change).

- [ ] **Step 5: Run all version tests**

Run: `uv run pytest tests/test_version_updater.py -v`

Expected: all PASS, including the three new ones from Step 2 and the existing ones.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest tests/ -v`

Expected: 153 passed (150 from before + 3 new).

- [ ] **Step 7: Lint**

Run: `uv run ruff check src/ tests/`

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add src/files_to_agent/version.py tests/test_version_updater.py
git commit -m "refactor(version): read version from importlib.metadata; bake commit SHA via env"
```

---

## Task 2: Bake the commit SHA into the Docker image

**Files:**
- Modify: `Dockerfile`
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Add `ARG` and `ENV` to the Dockerfile**

In `Dockerfile`, the second stage currently looks like (at the top of the second `FROM`):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 1000 app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz', timeout=2)" || exit 1
CMD ["python", "-m", "files_to_agent"]
```

After the `ENV PYTHONPATH="/app/src"` line, add:

```dockerfile
ARG COMMIT_SHA=unknown
ENV FILES_TO_AGENT_COMMIT_SHA=${COMMIT_SHA}
```

Resulting second stage (only the changed region shown):

```dockerfile
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ARG COMMIT_SHA=unknown
ENV FILES_TO_AGENT_COMMIT_SHA=${COMMIT_SHA}
USER app
```

The default `unknown` is what local `docker build` produces when no `--build-arg` is passed; the workflow always passes a real SHA.

- [ ] **Step 2: Pass the build arg in the GHA workflow**

In `.github/workflows/release.yml`, the `Build and push` step currently looks like:

```yaml
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Add a `build-args` field:

```yaml
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          build-args: |
            COMMIT_SHA=${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

(`${{ github.sha }}` is the full 40-char SHA — that's fine; `commit_sha()` returns whatever's in the env var verbatim. If you want a short SHA in the image, use `${{ steps.short_sha.outputs.value }}` with a shell step that computes it. **Don't** bother with that complication unless the user requests a specific format.)

- [ ] **Step 3: Smoke-test the Dockerfile syntax (no full build needed)**

Run: `docker build --target builder -f Dockerfile . --no-cache --pull -t files-to-agent:plan-2-test 2>&1 | head -20` if Docker is available locally. If not, skip — the GHA run will validate.

If you don't have Docker, instead just inspect the file:

Run: `cat Dockerfile`

Visually verify the `ARG`/`ENV` lines are present and the rest of the file is unchanged.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .github/workflows/release.yml
git commit -m "ci: bake commit SHA into image via COMMIT_SHA build arg"
```

---

## Task 3: Add `git-cliff` configuration + RELEASE.md

**Files:**
- Add: `cliff.toml`
- Add: `RELEASE.md`

- [ ] **Step 1: Create `cliff.toml`**

Create `cliff.toml` at the repo root:

```toml
# git-cliff configuration — generates CHANGELOG.md from conventional commits.
# Run with: uvx git-cliff --tag v0.1.1 -o CHANGELOG.md

[changelog]
header = """
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""
body = """
{% if version %}\
## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else %}\
## [Unreleased]
{% endif %}\

{% for group, commits in commits | group_by(attribute="group") %}
### {{ group | upper_first }}
{% for commit in commits %}
- {{ commit.message | upper_first }}\
{% if commit.breaking %} **[BREAKING]**\
{% endif %}\
{% endfor %}
{% endfor %}\n
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
split_commits = false
commit_parsers = [
    { message = "^feat", group = "Features" },
    { message = "^fix", group = "Bug Fixes" },
    { message = "^docs", group = "Documentation" },
    { message = "^perf", group = "Performance" },
    { message = "^refactor", group = "Refactor" },
    { message = "^style", skip = true },
    { message = "^test", skip = true },
    { message = "^chore", skip = true },
    { message = "^ci", skip = true },
    { message = "^build", skip = true },
]
filter_commits = false
tag_pattern = "v[0-9]*"
sort_commits = "newest"
```

- [ ] **Step 2: Create `RELEASE.md`**

Create `RELEASE.md` at the repo root:

```markdown
# Release Process

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

## Cutting a release

1. **Decide the version bump:**
   - `PATCH` (`0.1.0` → `0.1.1`): bug fixes, doc updates, no API changes
   - `MINOR` (`0.1.0` → `0.2.0`): new features, backward-compatible
   - `MAJOR` (`0.1.0` → `1.0.0`): breaking changes (config keys removed, command renamed, etc.)

2. **Bump the version in `pyproject.toml`:**

   ```toml
   [project]
   version = "0.1.1"
   ```

3. **Generate the changelog entry:**

   ```bash
   uvx git-cliff --tag v0.1.1 -o CHANGELOG.md
   ```

   Review `CHANGELOG.md` for accuracy. Edit if a commit's message doesn't read well.

4. **Commit:**

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore(release): v0.1.1"
   ```

5. **Tag:**

   ```bash
   git tag -a v0.1.1 -m "Release v0.1.1"
   ```

6. **Push (commits + tags):**

   ```bash
   git push
   git push --tags
   ```

7. **Verify the release:**
   - GitHub Actions should run the `Release` workflow and publish:
     - `ghcr.io/samuelgudi/files-to-agent:v0.1.1`
     - `ghcr.io/samuelgudi/files-to-agent:0.1` (floating minor)
     - `ghcr.io/samuelgudi/files-to-agent:0` (floating major)
     - `ghcr.io/samuelgudi/files-to-agent:sha-<short>` (commit-pinned)
     - `ghcr.io/samuelgudi/files-to-agent:latest` (only on `main` push, not on tag push)
   - A GitHub Release should appear at `https://github.com/samuelgudi/files-to-agent/releases/tag/v0.1.1`

## Conventional Commits

Commits should follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat(scope): description` — new feature
- `fix(scope): description` — bug fix
- `docs(scope): description` — documentation
- `refactor(scope): description` — code refactor without behavior change
- `chore(scope): description` — chores (release, dependency bumps, etc.)
- `ci(scope): description` — CI changes
- `test(scope): description` — test changes

Append `!` for breaking changes: `feat(api)!: rename /old to /new`.

These are what `git-cliff` parses to build the changelog.

## Hotfix process

1. Branch from the tag of the affected release: `git checkout -b hotfix/v0.1.2 v0.1.1`
2. Apply the fix, commit (conventional message)
3. Bump `pyproject.toml` to `0.1.2`, regenerate changelog, commit
4. Tag `v0.1.2`, push the branch + tag
5. Cherry-pick / merge the fix back to `main` if applicable
```

- [ ] **Step 3: Commit**

```bash
git add cliff.toml RELEASE.md
git commit -m "docs: add RELEASE.md and git-cliff config for changelog automation"
```

---

## Task 4: Cut the first proper release (`v0.1.1`)

**Files:**
- Modify: `pyproject.toml`
- Add: `CHANGELOG.md`

- [ ] **Step 1: Bump the version**

In `pyproject.toml`, change:

```toml
version = "0.1.0"
```

to:

```toml
version = "0.1.1"
```

- [ ] **Step 2: Generate the changelog**

Run: `uvx git-cliff --tag v0.1.1 -o CHANGELOG.md 2>&1`

If `git-cliff` isn't available via `uvx`, install it: `uv tool install git-cliff` then re-run.

Verify `CHANGELOG.md` exists and contains a `## [0.1.1] - 2026-04-28` section. Review the content — every commit since the dawn of the repo will be in it (since there's no prior tag). Edit any commit messages that don't read well in the changelog.

- [ ] **Step 3: Commit the version bump + changelog**

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): v0.1.1"
```

- [ ] **Step 4: Add the `Create GitHub Release` step to the workflow**

Open `.github/workflows/release.yml`. After the `Build and push` step, append a new step:

```yaml
      - name: Create GitHub Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          name: ${{ github.ref_name }}
          generate_release_notes: true
          body: |
            Container image: `ghcr.io/${{ github.repository }}:${{ github.ref_name }}`

            See [CHANGELOG.md](https://github.com/${{ github.repository }}/blob/main/CHANGELOG.md) for full release notes.
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

The workflow already has `permissions.contents: read` — change it to `contents: write` since release creation needs write access:

```yaml
    permissions:
      contents: write
      packages: write
```

Commit the workflow change:

```bash
git add .github/workflows/release.yml
git commit -m "ci: create GitHub Release on v* tag pushes"
```

- [ ] **Step 5: Tag and push everything**

```bash
git tag -a v0.1.1 -m "Release v0.1.1"
git push
git push --tags
```

- [ ] **Step 6: Smoke-test**

Wait for the workflow to run (~5 mins). The user can verify via `https://github.com/samuelgudi/files-to-agent/actions`. After completion, expect:
1. A new package version at `https://github.com/samuelgudi/files-to-agent/pkgs/container/files-to-agent` with tags `v0.1.1`, `0.1`, `0`, `sha-<x>`.
2. A GitHub Release at `https://github.com/samuelgudi/files-to-agent/releases/tag/v0.1.1`.

If the workflow fails, the most likely cause is `permissions: contents: write` not being effective due to org-level GHA settings — flag this in the report.

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Distribution metadata switch (Task 1), Docker SHA bake (Task 2), changelog automation (Task 3), first proper release (Task 4).
- [x] **Backward compat:** `version.py`'s public API (`get_version_info`, `short_sha`, `is_git_checkout`, `fetch_upstream`, `commits_behind`) is preserved. `commit_sha()` is added but no caller is forced to use it (`get_version_info` does internally; `handle_version` continues to use `info.sha` which now reflects the baked SHA in containers).
- [x] **Phase boundary:** Doesn't touch the `/update` stack (Phase 3); doesn't add any READMEs/CONTRIBUTING (Phase 4 owns OSS polish).
- [x] **Conventional commit alignment:** `cliff.toml` filters by `feat`, `fix`, `docs`, `refactor` — matches the existing commit history style. The repo's commits already follow this convention.
- [x] **First-release sanity:** `v0.1.1` (not `v0.1.0`) because `pyproject.toml` is currently `0.1.0` and we want the tag to bump *something* — also gives us a clean before/after for validating the pipeline.
