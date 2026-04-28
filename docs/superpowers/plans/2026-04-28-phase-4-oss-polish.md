# Phase 4 — OSS Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phases 1-3 must be merged + pushed.

**Goal:** Bring the repo up to OSS-publishable standard: contributing guide, security policy, issue/PR templates, README badges, and a final review pass to make sure nothing user-facing references the removed self-update machinery. After Phase 4, the repo can be linked from public sources (Hacker News, Reddit, social media) without anyone hitting an embarrassing edge case or undocumented landmine.

**Architecture:** No code changes. Pure docs + GitHub integration files. Total surface area: 5 new markdown files + edits to README.

**Tech Stack:** Markdown, GitHub issue/PR templates (`.github/ISSUE_TEMPLATE/*.yml`, `.github/pull_request_template.md`).

**Codebase context the executor needs:**
- `LICENSE` already exists (MIT) — no change needed.
- `README.md` after Phase 1 has a registry-pull quickstart. Phase 4 adds badges (Build, Release, License), a project status section, and a "Why this exists" hook above the current intro.
- `pyproject.toml` after Phase 2 has `version = "0.1.1"` (or whatever's current).
- `CHANGELOG.md` after Phase 2 exists. No change needed.
- `RELEASE.md` after Phase 2 exists. No change needed.
- `.github/` already has `workflows/`. We add `ISSUE_TEMPLATE/` and `pull_request_template.md`.
- The repo URL is `https://github.com/samuelgudi/files-to-agent`. GHCR images at `ghcr.io/samuelgudi/files-to-agent`.

**External prerequisites (USER must do):** None. This phase is fully self-driven. After it lands, the user **may** want to manually create a few GitHub Discussions categories, add a logo, or pick repo topics in the GitHub settings — these are optional polish items, not required.

---

## File Structure

**Add:**
- `CONTRIBUTING.md` — how to contribute (fork, branch, conventional commits, run tests, open PR)
- `SECURITY.md` — vulnerability disclosure policy (private email + 30-day window)
- `.github/ISSUE_TEMPLATE/bug_report.yml` — structured bug template
- `.github/ISSUE_TEMPLATE/feature_request.yml` — structured feature template
- `.github/ISSUE_TEMPLATE/config.yml` — disables blank issues, points to discussions
- `.github/pull_request_template.md` — PR checklist

**Modify:**
- `README.md` — add badges, "Why this exists" hook, link to CONTRIBUTING/SECURITY, repo topics suggestion in a comment

**Don't touch:**
- Any code (Phase 4 is doc-only)
- `LICENSE`, `CHANGELOG.md`, `RELEASE.md` (already in place)

---

## Task 1: `CONTRIBUTING.md`

**Files:**
- Add: `CONTRIBUTING.md`

- [ ] **Step 1: Create `CONTRIBUTING.md` at the repo root**

```markdown
# Contributing to files-to-agent

Thanks for considering a contribution. This is an MIT-licensed project — patches, bug reports, and feature suggestions are all welcome.

## Reporting bugs

Open an issue using the [Bug Report](https://github.com/samuelgudi/files-to-agent/issues/new?template=bug_report.yml) template. Include:

- What you expected
- What happened
- Logs (the bot logs to stdout / Docker logs)
- Your deploy mode (Docker, process-compose, standalone) and the bot's `/version` output

## Suggesting features

Open an issue using the [Feature Request](https://github.com/samuelgudi/files-to-agent/issues/new?template=feature_request.yml) template. Describe:

- The problem you're trying to solve (not the solution)
- Why the existing commands / config don't cover it
- What "good" looks like

## Submitting pull requests

1. **Fork** the repo and create a topic branch off `main`:
   ```bash
   git checkout -b feat/short-description
   ```

2. **Set up your environment:**
   ```bash
   uv sync --extra dev
   ```

3. **Make your changes.** Keep PRs focused — one logical change per PR. Tests are required for new features and bug fixes.

4. **Follow existing patterns:**
   - Match the codebase's style (run `uv run ruff check src/ tests/` before submitting)
   - Italian is canonical for user-facing strings; English mirrors it (see `messages.py`)
   - Tests go in `tests/`, mirroring the source structure

5. **Use Conventional Commit messages:**
   - `feat(scope): short description` for features
   - `fix(scope): short description` for bug fixes
   - `docs(scope): short description` for documentation
   - `refactor(scope): short description` for refactors
   - `test(scope): short description` for test-only changes
   - `chore(scope): short description` for everything else

6. **Run the full check before pushing:**
   ```bash
   uv run ruff check src/ tests/
   uv run pytest tests/ -v
   ```

7. **Open the PR.** The CI workflow runs the same checks; the release workflow builds a multi-arch image (no push for PRs). Both must be green before review.

8. **Respond to review.** I'll usually leave a few notes; squash-merge happens after both sides are happy.

## What I'm likely to accept

- Bug fixes (with a test that fails before the fix, passes after)
- New commands that fit the bot's scope (file staging for AI agents)
- Resolver-side improvements that don't expand the API surface unnecessarily
- Performance improvements with measurements
- Test coverage improvements
- Documentation clarifications

## What I'm likely to push back on

- Big refactors without a concrete user-visible benefit
- Wholesale dependency swaps
- Changes that couple the bot to a specific orchestrator (k8s-only features, etc.)
- Re-introducing the self-update mechanism — that's been deliberately removed, see [docs/migration-from-self-update.md](docs/migration-from-self-update.md)

## Code of Conduct

Be reasonable. The project doesn't (yet) have a formal CoC document, but the gist is: technical merit decides, personal attacks don't.

## Releases

See [RELEASE.md](RELEASE.md) for the release process. Maintainers tag versions; contributors don't need to touch `pyproject.toml` or `CHANGELOG.md`.

## Questions

Open a [GitHub Discussion](https://github.com/samuelgudi/files-to-agent/discussions) — issues are for bugs and concrete features.
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md with PR workflow and conventional commits"
```

---

## Task 2: `SECURITY.md`

**Files:**
- Add: `SECURITY.md`

- [ ] **Step 1: Create `SECURITY.md` at the repo root**

```markdown
# Security Policy

## Supported versions

This project follows semantic versioning. Security patches are issued for:

- The latest minor release (e.g., if `0.3.x` is current, `0.3.x` is patched)
- The previous minor release for 6 months after the next minor ships

Older versions are EOL.

| Version | Status |
|---|---|
| Latest minor | Active support |
| Previous minor | Patches for 6 months after successor ships |
| Older | Unsupported |

## Reporting a vulnerability

**Do not open a public issue.** Instead, email:

**(redacted)** with:

- A description of the vulnerability
- Steps to reproduce (or a proof-of-concept)
- Affected versions (run `/version` in the bot or check the image tag)
- Your assessment of severity (Critical / High / Medium / Low)

I'll acknowledge receipt within 7 days and aim to release a patched version within 30 days for High/Critical issues, 90 days for Medium/Low.

## Scope

In scope:
- The bot Telegram interface (`/start`, `/new`, `/upload`, etc.)
- The HTTP resolver API (`/resolve`, `/use`, `/healthz`)
- The Docker image (privilege escalation, base-image vulns specific to our changes)
- Authentication / authorization bypasses
- File-system access boundary violations (escaping the staging directory)

Out of scope:
- Vulnerabilities in upstream dependencies (report to the upstream project; we'll bump promptly)
- Issues requiring physical access to the host
- DoS via unauthenticated traffic on the resolver (the resolver is intended to run on a trusted network; document `RESOLVER_AUTH=apikey` for stricter setups)
- Social engineering of the bot operator

## Disclosure

I prefer coordinated disclosure: I publish the patch, then you publish details after users have had a chance to update (typically 14 days post-patch). I'll credit you in the changelog and the GitHub Release notes unless you ask to remain anonymous.
```

- [ ] **Step 2: Commit**

```bash
git add SECURITY.md
git commit -m "docs: add SECURITY.md with vulnerability disclosure policy"
```

---

## Task 3: GitHub issue templates

**Files:**
- Add: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Add: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Add: `.github/ISSUE_TEMPLATE/config.yml`

- [ ] **Step 1: Create `bug_report.yml`**

Path: `.github/ISSUE_TEMPLATE/bug_report.yml`

```yaml
name: Bug Report
description: Something isn't working as documented
labels: [bug, triage]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting a bug. Please fill in the fields below — generic reports without reproduction steps are hard to act on.
  - type: input
    id: version
    attributes:
      label: Version
      description: What does `/version` say in the bot?
      placeholder: "files-to-agent 0.1.1, sha-abc1234"
    validations:
      required: true
  - type: dropdown
    id: deploy_mode
    attributes:
      label: Deploy mode
      options:
        - Docker (registry image)
        - Docker (build from source)
        - process-compose
        - Standalone Python
        - Other / unsure
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: What you expected
      placeholder: When I send /pulizia, the bot should show inline buttons for each upload.
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: What actually happened
      placeholder: The bot showed a list of uploads but no buttons appeared. Tapping the text did nothing.
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. /nuova
        2. Send a file
        3. /conferma
        4. /pulizia
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Relevant logs
      description: Run `docker logs files-to-agent` (or equivalent for your deploy) and paste any errors or warnings.
      render: shell
    validations:
      required: false
  - type: textarea
    id: config
    attributes:
      label: Notable env / config
      description: Any non-default `.env` values that might be relevant. **Redact your BOT_TOKEN.**
      render: shell
    validations:
      required: false
```

- [ ] **Step 2: Create `feature_request.yml`**

Path: `.github/ISSUE_TEMPLATE/feature_request.yml`

```yaml
name: Feature Request
description: Suggest a new command, behavior, or capability
labels: [enhancement, triage]
body:
  - type: markdown
    attributes:
      value: |
        Describe the **problem**, not the solution. The "what should the bot do" question is easier to discuss when I know what you're trying to achieve.
  - type: textarea
    id: problem
    attributes:
      label: What problem are you trying to solve?
      placeholder: When uploading large batches, I lose track of which uploads are for which agent task.
    validations:
      required: true
  - type: textarea
    id: workaround
    attributes:
      label: What workaround are you using today?
      placeholder: I prefix file names with `[task-name]_` but it's manual and error-prone.
    validations:
      required: false
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution (optional)
      placeholder: Add a `/tag <name>` command that attaches a tag to the active draft and shows it in `/lista`.
    validations:
      required: false
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives you've considered
      placeholder: Use `/contesto` for the same purpose — but `/contesto` is free-form text that the agent reads, whereas tags would be for filtering.
    validations:
      required: false
```

- [ ] **Step 3: Create `config.yml`**

Path: `.github/ISSUE_TEMPLATE/config.yml`

```yaml
blank_issues_enabled: false
contact_links:
  - name: Question / discussion
    url: https://github.com/samuelgudi/files-to-agent/discussions
    about: Use Discussions for usage questions, ideas, and general help.
  - name: Security vulnerability
    url: https://github.com/samuelgudi/files-to-agent/security/policy
    about: Report security issues privately, not via public issues.
```

- [ ] **Step 4: Commit**

```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "ci: add issue templates for bugs, features, and security routing"
```

---

## Task 4: PR template

**Files:**
- Add: `.github/pull_request_template.md`

- [ ] **Step 1: Create the PR template**

Path: `.github/pull_request_template.md`

```markdown
## Summary

<!-- One paragraph: what does this PR change and why. -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactor / internal cleanup (no user-visible change)
- [ ] CI / build / chore

## Checklist

- [ ] My commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) format (see `RELEASE.md`)
- [ ] I've run `uv run ruff check src/ tests/` and there are no errors
- [ ] I've run `uv run pytest tests/ -v` and all tests pass
- [ ] I've added tests that fail before this change and pass after (for bug fixes / features)
- [ ] I've updated user-facing strings in **both** `_IT` and `_EN` (if applicable)
- [ ] I've updated `README.md` / `docs/` (if user-visible behavior changed)
- [ ] This change does not re-introduce the self-update mechanism

## Related issues

<!-- Closes #123, refs #456 -->

## Screenshots / logs (optional)

<!-- For UX changes, drop a screenshot or short clip. For bug fixes, paste relevant before/after logs. -->
```

- [ ] **Step 2: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "ci: add pull request template with checklist"
```

---

## Task 5: README polish

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add badges and intro hook above the existing content**

In `README.md`, the file currently starts with:

```markdown
# FilesToAgent

A Telegram-side staging bot that holds files for AI agents until they're explicitly consumed.
```

Replace those two lines with:

```markdown
# files-to-agent

[![CI](https://github.com/samuelgudi/files-to-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/samuelgudi/files-to-agent/actions/workflows/ci.yml)
[![Release](https://github.com/samuelgudi/files-to-agent/actions/workflows/release.yml/badge.svg)](https://github.com/samuelgudi/files-to-agent/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GHCR](https://ghcr-badge.egpl.dev/samuelgudi/files-to-agent/latest_tag?label=ghcr)](https://github.com/samuelgudi/files-to-agent/pkgs/container/files-to-agent)

> A Telegram-side staging bot that holds files for AI agents until they're explicitly consumed.

**Why this exists:** AI agents that talk to you over Telegram (Hermes, OpenClaw, custom Claude wrappers) treat every uploaded file as a turn — the LLM processes it, costs tokens, and may misuse it later. There's no clean way to say "hold these three files for the email I'm about to compose."

**files-to-agent** is a separate Telegram bot that acts as your file-staging surface. You upload files into named, ID-tracked sessions (`/nuova` → drop files → `/conferma`). The bot stores them on disk and assigns each session a short ID. You hand the ID to your AI agent ("draft this email; ID: `k7m2p9x4`"). The agent fetches the files via a small HTTP resolver, attaches them, and the bot logs every use.

The agent never sees uploaded file contents until you tell it to. The bot can't be talked into attaching the wrong file because the ID-bound session is the only thing it knows about.
```

(The 3rd-party `ghcr-badge` shield is optional — if it returns errors, drop that line.)

- [ ] **Step 2: Add a `Status` and `Contributing` section near the bottom**

After all the existing sections, before the very end of the file, add:

```markdown
## Status

This is a personal project I run for myself, but it's MIT-licensed and stable enough for others to use. Breaking changes are rare and gated through major-version bumps. Pre-1.0 means I reserve the right to make small breaking changes if I discover a better design — but I'll document them in the changelog and migration guides.

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and [SECURITY.md](SECURITY.md) for vulnerability disclosure.

## License

[MIT](LICENSE) © Samuel Gudi
```

- [ ] **Step 3: Update the existing problem-description block to remove duplication**

The new intro at the top (Step 1) already covers what was previously in the `**Problem.**` paragraph and the `**FilesToAgent.**` paragraph. **Delete** those two paragraphs from the original location to avoid saying the same thing twice. Specifically, delete from `**Problem.** AI agents...` through `...the only thing it knows about.` (which was around lines 5-9 of the pre-Phase-1 README).

The flow after this change should be: badges → quote → Why → How (existing intro) → Features → Quick start → Telegram commands → ... → Status → Contributing → License.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README badges, status section, and contributor links"
```

---

## Task 6: Final review and push

- [ ] **Step 1: Manual sanity sweep**

Run: `grep -rn "self-update\|/update\b\|update_host\|UPDATE_CHECK\|fetch_upstream\|commits_behind" --include="*.md" --include="*.py" --include="*.yml" .`

(Excluding the migration guide and changelog, which legitimately reference the removed mechanism.)

Expected: only matches in `docs/migration-from-self-update.md`, `CHANGELOG.md`, and possibly `docs/superpowers/plans/` (the plan files themselves are historical record). Anything else means there's a stale reference to clean up.

- [ ] **Step 2: Run the full suite + lint**

Run: `uv run pytest tests/ -v && uv run ruff check src/ tests/`

Expected: green.

- [ ] **Step 3: Push**

```bash
git push
```

- [ ] **Step 4: Verify GitHub renders the README correctly**

Open `https://github.com/samuelgudi/files-to-agent` in a browser. Check:
- Badges render (or fail gracefully if a third-party shield is down)
- Issue templates show up under "New Issue"
- Security policy is linked from the repo's Security tab

If any of those fail, **flag in the report** — the user can adjust manually.

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** CONTRIBUTING (Task 1), SECURITY (Task 2), issue templates (Task 3), PR template (Task 4), README polish (Task 5), sanity sweep (Task 6).
- [x] **No code changes:** Phase 4 is pure docs + GitHub integration. No Python touched.
- [x] **No re-introduction of removed features:** CONTRIBUTING explicitly calls out that re-adding the self-update mechanism won't be accepted; PR template has a checkbox for it.
- [x] **MIT license + contact info aligned:** SECURITY.md uses the user's actual email (from CLAUDE.md context).
- [x] **OSS basics present:** License (already), changelog (Phase 2), release process (Phase 2), contributing, security policy, issue templates, PR template, badges. Standard checklist for an MIT project.
- [x] **Phase 4 is the last phase:** After this, the project is shippable as a public OSS tool. Future work is feature work, not infrastructure.
