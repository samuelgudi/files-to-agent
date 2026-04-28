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
