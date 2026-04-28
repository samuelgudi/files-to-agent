# Deployment Guide

FilesToAgent supports three deploy modes. Pick one — they all run the same Python process.

## 1. Docker Compose (recommended for production)

Prerequisites: Docker, a Telegram bot token, your Telegram numeric user ID.

### Pull the image (recommended)

```bash
mkdir files-to-agent && cd files-to-agent
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/.env.example
mv .env.example .env
$EDITOR .env  # set BOT_TOKEN and BOT_ALLOWED_USER_IDS
docker network create agent-net  # one-time
docker compose up -d
```

The image comes from `ghcr.io/samuelgudi/files-to-agent:latest`. Pin a specific version by editing `docker-compose.yml`:

```yaml
image: ghcr.io/samuelgudi/files-to-agent:v0.1.0
```

Available tags:
- `latest` — current `main` branch (rolling, may break)
- `vX.Y.Z` — specific release (recommended for production)
- `vX.Y`, `vX` — major/minor floating tags
- `sha-<short>` — specific commit (for debugging)

### First-time setup (repo owner only)

The first time the release workflow publishes an image to GHCR, the package is created as **private** by default. To make `docker pull` work for everyone (including the quickstart in this doc):

1. Go to `https://github.com/samuelgudi?tab=packages`
2. Click `files-to-agent`
3. Package settings → "Change visibility" → Public

Also verify the workflow has push permission: repo Settings → Actions → General → Workflow permissions → "Read and write permissions". The workflow YAML already declares `permissions: packages: write`, but org-level policy can override.

These are one-time steps. Skip if your fork is intended to stay private.

### Build from source (development)

```bash
git clone https://github.com/samuelgudi/files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env
docker network create agent-net
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### Updating

Manual:
```bash
docker compose pull
docker compose up -d
```

Automatic: install [Watchtower](https://containrrr.dev/watchtower/) on the host. It watches your container for newer image tags and applies them automatically. The bot itself is stateless — Watchtower restarts are safe.

### Networking

The agent (Hermes / Agent) container should join the same `agent-net` network. From the agent it reaches the resolver at `http://files-to-agent:8080`. The staging files appear in `./data/staging/` on the host — mount the same path into the agent container so it can read them.

Example agent-side compose snippet:
```yaml
services:
  hermes:
    networks:
      - agent-net
    volumes:
      - /path/to/files-to-agent/data/staging:/staging:ro
networks:
  agent-net:
    external: true
```

The agent then receives upload paths like `/staging/<id>/<file>`.

## 2. process-compose (lightweight, e.g. WSL-host WSL)

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), [process-compose](https://github.com/F1bonacc1/process-compose).

```bash
git clone <repo> files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env
uv sync

process-compose up
```

The resolver listens on `127.0.0.1:8080`. The host-local agent (e.g. Agent in WSL) calls it directly. `data/staging/` is on the host filesystem.

## 3. Standalone Python

Prerequisites: Python 3.12+, uv.

```bash
git clone <repo> files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env
uv sync
uv run python -m files_to_agent
```

Useful for development. For production prefer Docker or process-compose.

## Configuration

All configuration is via environment variables — see `.env.example` for the full list.

## Authentication

By default the resolver runs without auth (`RESOLVER_AUTH=none`), assuming the agent and bot share a trusted network boundary. To require an API key, set:
```ini
RESOLVER_AUTH=apikey
RESOLVER_API_KEY=<long-random-string>
```
The agent must then send `Authorization: Bearer <key>` on every `/resolve` and `/use` call.

## Updating

The bot is a stateless container. Updates happen at the orchestrator layer.

### Manual

```bash
docker compose pull
docker compose up -d
```

### Automatic

Run [Watchtower](https://containrrr.dev/watchtower/) on the host. It polls
the registry for new image tags and restarts the container automatically.

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  files-to-agent
```

If you're running with `image: ghcr.io/samuelgudi/files-to-agent:latest`,
Watchtower picks up new pushes within the polling interval. If you're
pinned to `:vX.Y.Z`, Watchtower won't update across versions — you bump
the tag yourself.

For non-Docker deploys (process-compose, standalone Python), update by
re-running `git pull && uv sync` and bouncing the process. The `/restart`
command does the bounce part for you on supervised runs.
