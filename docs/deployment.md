# Deployment Guide

FilesToAgent supports three deploy modes. Pick one — they all run the same Python process.

## 1. Docker Compose (recommended for production)

Prerequisites: Docker, a Telegram bot token, your Telegram numeric user ID.

```bash
git clone <repo> files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env  # set BOT_TOKEN and BOT_ALLOWED_USER_IDS

docker network create agent-net  # one-time
docker compose up -d --build
```

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

## Self-update

`/version` reports current version and pending upstream commits. `/update` (or the inline button) actually performs the update. Behaviour depends on deploy mode.

### process-compose / standalone with restart-on-exit

The bot runs `git fetch && git reset --hard origin/main`, then `uv sync --frozen`, then exits. process-compose restarts it (`availability.restart: always` is already set).

Flag the process as supervised so the bot does not refuse to update:

- `process-compose.yaml` — already sets `FILES_TO_AGENT_SUPERVISED=1`.
- systemd — set `Environment=FILES_TO_AGENT_SUPERVISED=1` in the unit, or rely on systemd's `INVOCATION_ID` (auto-detected).
- bare `python -m` with no supervisor — `/update` refuses, since exiting would simply kill the bot.

### Docker

The bot can't `git pull` inside an immutable image. Instead, it drops a flag file at `/var/lib/files-to-agent/update.requested`, which `docker-compose.yml` mounts to `./update-flag/` on the host. A small host watcher script polls that file and runs `docker compose pull && docker compose up -d`.

Install the host watcher (one-time):

```bash
sudo cp scripts/update-host.sh /usr/local/bin/files-to-agent-update-host
sudo chmod +x /usr/local/bin/files-to-agent-update-host

# Edit the COMPOSE_DIR / FLAG_DIR in the unit to your install location.
sudo cp scripts/files-to-agent-update-host.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now files-to-agent-update-host
```

Without the host watcher, `/update` returns the manual `docker compose pull && docker compose up -d` command for you to run on the host.

### Daily upstream check

By default the bot polls `origin/main` once a day at 09:00 UTC. If new commits are available, the owner (the **first** id in `BOT_ALLOWED_USER_IDS`) gets a Telegram DM. Disable with:

```ini
UPDATE_CHECK_DAILY=false
```
