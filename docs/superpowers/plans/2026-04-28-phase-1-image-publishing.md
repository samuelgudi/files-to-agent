# Phase 1 — Image Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop building images locally on every host. Publish multi-arch (`linux/amd64`, `linux/arm64`) container images to GitHub Container Registry (`ghcr.io/samuelgudi/files-to-agent`) on every push to `main` and on every `v*` git tag. Convert `docker-compose.yml` to a registry-pull deployment, add `docker-compose.dev.yml` for local-build development, and update the README quickstart so new users can `docker compose up -d` without ever cloning the repo.

**Architecture:** A new `.github/workflows/release.yml` uses `docker/setup-qemu-action` + `docker/setup-buildx-action` + `docker/login-action` (with the auto-provisioned `GITHUB_TOKEN`) + `docker/metadata-action` to compute the right tags + `docker/build-push-action` to build and push. The metadata action computes:
- `latest` on `refs/heads/main`
- `vX.Y.Z`, `vX.Y`, `vX` on `refs/tags/v*` semver tags
- `sha-<short>` on every commit (for traceability)
- `pr-<number>` on PRs (build-only, no push)

`docker-compose.yml` switches its `services.files-to-agent` from `build: .` to `image: ghcr.io/samuelgudi/files-to-agent:latest` (a sane default for "track the bleeding edge"; production users override via env or by editing the file). `docker-compose.dev.yml` keeps `build: .` for local development. Existing `Dockerfile` is **already production-grade** (multi-stage, non-root user, healthcheck) — Phase 1 audits it but doesn't rewrite it.

**Tech Stack:** GitHub Actions, Docker buildx, GHCR. No Python changes.

**Codebase context the executor needs:**
- `Dockerfile` (root) — multi-stage Python 3.12 build, non-root `app` user, exposes 8080, healthcheck at `/healthz`. **Don't modify** unless something blocks the build.
- `docker-compose.yml` (root) — current production compose. Has `build: .`, `image: files-to-agent:latest`, mounts `./data:/data` and `./update-flag:/var/lib/files-to-agent` (the `update-flag` mount is going away in Phase 3 but stays here for now).
- `.github/workflows/ci.yml` — existing test workflow. Don't touch it.
- `pyproject.toml` — `name = "files-to-agent"`, `version = "0.1.0"`. Don't bump in Phase 1 (Phase 2 owns versioning).
- `README.md` lines 24-37 — current Quick Start uses `git clone` + `docker compose up -d --build`. Will be rewritten in this phase.
- `docs/deployment.md` lines 1-65 — three deploy modes documented. Mode 1 (Docker) gets rewritten. Other modes are touched lightly (just removing the `git clone` requirement isn't possible for non-Docker modes).
- The repo's GitHub URL is `https://github.com/samuelgudi/files-to-agent`. GHCR images go to lowercase: `ghcr.io/samuelgudi/files-to-agent`.
- Run tests with `uv run pytest tests/ -v`. Lint with `uv run ruff check src/ tests/`. No tests change in this phase.

**External prerequisites (USER must do):** After the first successful push of an image to GHCR (which happens automatically on the next `main` push after this PR merges), the package is created in **private** mode by default. The user must **manually mark it public** in GitHub settings → Packages → files-to-agent → Settings → Change visibility → Public. This is a one-time step. Document this in the deployment guide so other users hitting the same workflow know.

---

## File Structure

**Add:**
- `.github/workflows/release.yml` — image build + push pipeline
- `docker-compose.dev.yml` — local-build compose for development
- `.dockerignore` — speeds up builds, prevents secrets leaking into the image (verify it exists; create if not)

**Modify:**
- `docker-compose.yml` — switch from `build: .` to `image: ghcr.io/...:latest`. Keep `update-flag` mount for now (Phase 3 removes it).
- `README.md` — replace Quick Start with a "no-clone" registry-pull flow as the primary path; keep "build from source" as an alternative.
- `docs/deployment.md` — rewrite Mode 1 (Docker Compose) for the registry-pull flow; add a "Updating" section that points to `docker compose pull && docker compose up -d` (and mentions Watchtower as the recommended auto-update tool); leave Modes 2 + 3 untouched.

**Don't touch:**
- `Dockerfile` (it's already correct)
- `.github/workflows/ci.yml`
- Any Python code
- `pyproject.toml` (Phase 2 owns this)
- The `/update`, `/restart`, `update-host.sh` machinery (Phase 3 removes it)

---

## Task 1: Verify the Dockerfile and `.dockerignore`

**Files:**
- Read: `Dockerfile`
- Verify or Create: `.dockerignore`

- [ ] **Step 1: Read the Dockerfile and confirm it's good**

Run: `cat Dockerfile`

Verify it contains all of:
- `FROM python:3.12-slim AS builder`
- `RUN pip install --no-cache-dir uv==0.5.14`
- `RUN uv sync --no-dev --frozen`
- A second stage `FROM python:3.12-slim`
- `RUN useradd --create-home --uid 1000 app`
- `USER app`
- `EXPOSE 8080`
- A `HEALTHCHECK` directive that hits `/healthz`
- `CMD ["python", "-m", "files_to_agent"]`

If anything's missing, **stop and report** — Phase 1 assumes the Dockerfile is production-ready.

- [ ] **Step 2: Check `.dockerignore`**

Run: `cat .dockerignore` (or `ls -la .dockerignore`).

If it doesn't exist, create it at the repo root with this content:

```gitignore
# Version control
.git
.github
.gitignore
.gitattributes

# Local virtualenvs / caches
.venv
__pycache__
*.pyc
*.pyo
.pytest_cache
.ruff_cache
.mypy_cache
.coverage
htmlcov/

# IDE / OS
.vscode
.idea
*.swp
.DS_Store
Thumbs.db

# Project
data/
update-flag/
.env
.env.*
!.env.example
docs/
tests/
```

If it exists, **read it and check** that it ignores at least: `.git`, `.venv`, `__pycache__`, `tests/`, `.env` (not `.env.example`), `data/`, `update-flag/`. If anything is missing, append it. If nothing is missing, leave the file alone.

- [ ] **Step 3: Commit (only if changes)**

If you created `.dockerignore` or modified it:

```bash
git add .dockerignore
git commit -m "chore(docker): add/update .dockerignore for clean image builds"
```

If no changes, skip this commit.

---

## Task 2: GHA workflow for image build + push to GHCR

**Files:**
- Add: `.github/workflows/release.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/release.yml` with this exact content:

```yaml
name: Release

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=sha,format=short,prefix=sha-
            type=raw,value=latest,enable=${{ github.ref == format('refs/heads/{0}', 'main') }}

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

Key design notes (don't change without reason):
- `permissions.packages: write` is required for GHCR push.
- `IMAGE_NAME: ${{ github.repository }}` resolves to `samuelgudi/files-to-agent` (lowercase preserved by GitHub).
- `pull_request` events build but **do not push** — provides PR validation without polluting the registry.
- `enable=${{ github.ref == ... }}` ensures `latest` is **only** applied to main-branch pushes, not to PRs or tags.
- `cache-from/to: type=gha` reuses GHA's cache layer between runs, keeping build time low.
- Multi-arch is mandatory for an OSS bot — Raspberry Pi / Apple Silicon users matter.

- [ ] **Step 2: Validate YAML syntax**

Run: `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" 2>&1 || echo "YAML PARSE FAILED"`

If pyyaml isn't installed, install it for this check or use a different validator: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`. If neither works, fall back to: `cat .github/workflows/release.yml` and visually inspect the indentation.

Expected: no parse error.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release workflow for multi-arch GHCR image builds"
```

---

## Task 3: Split compose into prod (registry) and dev (local-build)

**Files:**
- Add: `docker-compose.dev.yml`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.dev.yml`**

Create `docker-compose.dev.yml` at the repo root:

```yaml
# Development override — builds the image locally instead of pulling from GHCR.
# Use with: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

services:
  files-to-agent:
    build: .
    image: files-to-agent:dev
    pull_policy: build
```

Why an override and not a full compose: Compose merges files left-to-right, so `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` keeps all the volumes/networks/env from the prod file but replaces `image:` and adds `build:`.

- [ ] **Step 2: Modify `docker-compose.yml`**

Replace the current contents of `docker-compose.yml` with:

```yaml
services:
  files-to-agent:
    image: ghcr.io/samuelgudi/files-to-agent:latest
    container_name: files-to-agent
    restart: unless-stopped
    env_file: .env
    networks:
      - agent-net
    volumes:
      - ./data:/data
      # Update-flag volume — bot writes ./update-flag/update.requested
      # which the host script (scripts/update-host.sh) polls.
      # NOTE: This mount is removed in Phase 3 alongside the self-update stack.
      - ./update-flag:/var/lib/files-to-agent
    expose:
      - "8080"

networks:
  agent-net:
    name: agent-net
    external: true
```

Key changes from the previous file:
- `build: .` → removed
- `image: files-to-agent:latest` → `image: ghcr.io/samuelgudi/files-to-agent:latest`
- Everything else preserved

- [ ] **Step 3: Smoke-test compose syntax**

Run: `docker compose -f docker-compose.yml config > /dev/null && echo "PROD OK"`

Expected: `PROD OK` (no errors). If `docker` isn't on the agent's PATH, skip this step but **read the file back** and check syntax visually.

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml config > /dev/null && echo "DEV OK"` if Docker is available; otherwise skip.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml
git commit -m "feat(deploy): switch docker-compose to GHCR registry image; add dev override"
```

---

## Task 4: Update README quickstart

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current Quick Start section**

Run: `sed -n '24,40p' README.md` (or use Read tool with offset=24, limit=20).

Current content (around lines 24-37):

```markdown
## Quick start

See [docs/deployment.md](docs/deployment.md) for full instructions. TL;DR with Docker:

`​`​`​bash
git clone <repo> files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env  # set BOT_TOKEN, BOT_ALLOWED_USER_IDS
docker network create agent-net
docker compose up -d --build
`​`​`​

Mount `./data/staging` into your agent container so it can read the files.
```

- [ ] **Step 2: Replace with the registry-pull quickstart**

Replace the entire Quick Start section (the `## Quick start` heading through the "Mount `./data/staging`..." line) with:

```markdown
## Quick start

The fastest way to get a bot running — no source clone needed:

`​`​`​bash
mkdir files-to-agent && cd files-to-agent
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/.env.example
mv .env.example .env
$EDITOR .env  # set BOT_TOKEN and BOT_ALLOWED_USER_IDS
docker network create agent-net
docker compose up -d
`​`​`​

The image is pulled from `ghcr.io/samuelgudi/files-to-agent:latest`. Mount `./data/staging` into your agent container so it can read the files.

To pin a specific version, edit `docker-compose.yml`'s `image:` line:

`​`​`​yaml
image: ghcr.io/samuelgudi/files-to-agent:v0.1.0
`​`​`​

Updating is `docker compose pull && docker compose up -d`. For automatic updates, use [Watchtower](https://containrrr.dev/watchtower/).

For local development (build from source), see [docs/deployment.md](docs/deployment.md).
```

(The triple-backtick fences in the inserted block need to be unescaped — the `\`​\`​\`​bash` and similar sequences above use a zero-width-space to keep the markdown parser of *this plan* happy. When you write the README, use plain ` ``` `.)

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README quickstart for registry-pull deployment"
```

---

## Task 5: Update `docs/deployment.md` Mode 1

**Files:**
- Modify: `docs/deployment.md`

- [ ] **Step 1: Read the current Mode 1 section (lines 1-35)**

Run: `sed -n '1,35p' docs/deployment.md` (or Read tool).

- [ ] **Step 2: Replace Mode 1**

Replace the existing `## 1. Docker Compose (recommended for production)` section (everything from the `## 1.` heading down to but **not including** the `## 2. process-compose` heading) with:

```markdown
## 1. Docker Compose (recommended for production)

Prerequisites: Docker, a Telegram bot token, your Telegram numeric user ID.

### Pull the image (recommended)

`​`​`​bash
mkdir files-to-agent && cd files-to-agent
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/.env.example
mv .env.example .env
$EDITOR .env  # set BOT_TOKEN and BOT_ALLOWED_USER_IDS
docker network create agent-net  # one-time
docker compose up -d
`​`​`​

The image comes from `ghcr.io/samuelgudi/files-to-agent:latest`. Pin a specific version by editing `docker-compose.yml`:

`​`​`​yaml
image: ghcr.io/samuelgudi/files-to-agent:v0.1.0
`​`​`​

Available tags:
- `latest` — current `main` branch (rolling, may break)
- `vX.Y.Z` — specific release (recommended for production)
- `vX.Y`, `vX` — major/minor floating tags
- `sha-<short>` — specific commit (for debugging)

### Build from source (development)

`​`​`​bash
git clone https://github.com/samuelgudi/files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env
docker network create agent-net
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
`​`​`​

### Updating

Manual:
`​`​`​bash
docker compose pull
docker compose up -d
`​`​`​

Automatic: install [Watchtower](https://containrrr.dev/watchtower/) on the host. It watches your container for newer image tags and applies them automatically. The bot itself is stateless — Watchtower restarts are safe.

### Networking

The agent (Hermes / Agent) container should join the same `agent-net` network. From the agent it reaches the resolver at `http://files-to-agent:8080`. The staging files appear in `./data/staging/` on the host — mount the same path into the agent container so it can read them.

Example agent-side compose snippet:
`​`​`​yaml
services:
  hermes:
    networks:
      - agent-net
    volumes:
      - /path/to/files-to-agent/data/staging:/staging:ro
networks:
  agent-net:
    external: true
`​`​`​

The agent then receives upload paths like `/staging/<id>/<file>`.
```

(Same caveat as Task 4: unescape the triple-backtick fences when writing.)

Leave Mode 2 (process-compose) and Mode 3 (Standalone Python) and the rest of the file untouched.

- [ ] **Step 3: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: rewrite Docker deployment for registry-pull + Watchtower auto-update"
```

---

## Task 6: Push everything

- [ ] **Step 1: Push**

```bash
git push
```

- [ ] **Step 2: Confirm the push succeeded**

Run: `git log origin/main..HEAD` and confirm output is empty (i.e., local main matches remote main).

- [ ] **Step 3: Smoke-test the workflow trigger**

The workflow runs automatically on the push you just did. **You can't directly verify it from this agent** (no GitHub API access), but the user can check `https://github.com/samuelgudi/files-to-agent/actions` to confirm:
- A "Release" workflow run appears
- The run succeeds (~3-5 mins for first run, faster on subsequent runs due to GHA cache)
- After success, `https://github.com/samuelgudi/files-to-agent/pkgs/container/files-to-agent` shows the published image with `latest` and `sha-<x>` tags

If the workflow fails, the most likely causes:
1. **Permissions** — `packages: write` is set in the workflow but if the org-level setting blocks it, the user must enable it under Settings → Actions → General → Workflow permissions → "Read and write permissions".
2. **First-time visibility** — GHCR creates the package as private by default. The image still pushes, but `docker pull` from a fresh host won't work until the user marks it public (Settings → Packages → files-to-agent → Change visibility → Public). This is a one-time manual step.

Document both in your final report.

---

## Self-Review Checklist (already applied by the planner)

- [x] **Spec coverage:** Image publishing (Task 2), compose split (Task 3), README quickstart (Task 4), deployment doc update (Task 5), push (Task 6). All four phase-1 deliverables covered.
- [x] **Multi-arch:** `linux/amd64,linux/arm64` in the workflow — required for OSS bot.
- [x] **Tag strategy:** `latest`, `vX.Y.Z`, `vX.Y`, `vX`, `sha-<short>`, `pr-<n>` — covers stable / floating / debug / preview.
- [x] **No-clone quickstart:** README shows `curl -O` flow, not `git clone` — users can deploy without ever touching source.
- [x] **Build-from-source still works:** `docker-compose.dev.yml` overrides `image:` with `build: .` — local development unchanged.
- [x] **Phase boundary:** No changes to `pyproject.toml` (Phase 2), no removal of `/update` or watcher (Phase 3), no changelog/contributing docs (Phase 4). Phase 1 is self-contained and ships standalone value.
- [x] **External prereqs flagged:** GHCR private-by-default + workflow permissions — both called out in Task 6.
