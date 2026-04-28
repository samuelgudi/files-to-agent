# files-to-agent

[![CI](https://github.com/samuelgudi/files-to-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/samuelgudi/files-to-agent/actions/workflows/ci.yml)
[![Release](https://github.com/samuelgudi/files-to-agent/actions/workflows/release.yml/badge.svg)](https://github.com/samuelgudi/files-to-agent/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Telegram-side staging bot that holds files for AI agents until they're explicitly consumed.

## Why this exists

AI agents that talk to you over Telegram (Hermes, custom Claude wrappers, your own scripts) treat every uploaded file as an immediate input — the model processes it, costs tokens, and may surface it later in unrelated turns. There's no clean way to say *"hold these three files for the email I'm about to compose."*

`files-to-agent` is a separate Telegram bot that acts as your file-staging surface. You upload files into named, ID-tracked sessions. The bot stores them on disk and assigns each session a short ID. You hand the ID to your agent (`"draft this email; ID: k7m2p9x4"`) and the agent fetches the files via a small HTTP resolver, attaches them, and the bot logs every use.

The agent never sees uploaded file contents until you reference them by ID. The bot can't be tricked into attaching the wrong file because the ID-bound session is the only thing it knows about.

## How it works

```
┌──────────┐  files     ┌────────────────────┐
│ Telegram │ ─────────► │ files-to-agent bot │
│  client  │            │  (Python + PTB)    │
└──────────┘            └─────────┬──────────┘
                                  │ writes
                                  ▼
                        ┌────────────────────┐
                        │  /data/staging     │  +  SQLite metadata
                        │  (one dir per ID)  │
                        └─────────┬──────────┘
                                  │ reads
                                  ▼
                        ┌────────────────────┐  HTTP   ┌──────────┐
                        │  HTTP resolver     │ ◄────── │ AI agent │
                        │  (FastAPI :8080)   │         │ (Hermes) │
                        └────────────────────┘         └──────────┘
```

Two processes share the same SQLite + filesystem layer: a Telegram bot you talk to, and an HTTP resolver your agents call. The resolver is the only path agents have to the files; the bot is the only path you have to upload them.

## Quick start

The fastest path — no source clone needed:

```bash
mkdir files-to-agent && cd files-to-agent
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/samuelgudi/files-to-agent/main/.env.example
mv .env.example .env
$EDITOR .env  # set BOT_TOKEN and BOT_ALLOWED_USER_IDS
docker network create agent-net
docker compose up -d
```

The image is pulled from `ghcr.io/samuelgudi/files-to-agent:latest`. To pin a release:

```yaml
image: ghcr.io/samuelgudi/files-to-agent:v0.1.1
```

Tags published: `latest`, `vX.Y.Z`, `vX.Y`, `vX`, `sha-<short>`. Multi-arch (`linux/amd64`, `linux/arm64`).

Updates: `docker compose pull && docker compose up -d`. For automatic updates, run [Watchtower](https://containrrr.dev/watchtower/) on the host.

For non-Docker deploys (process-compose, standalone Python) and full configuration, see [`docs/deployment.md`](docs/deployment.md).

## Telegram commands

All commands work in English and Italian (`/new` ≡ `/nuova`). The slash menu in the Telegram client picks the locale automatically.

| Command | Italian alias | Effect |
|---|---|---|
| `/start` | `/start` | Welcome + main inline keyboard |
| `/help` | `/help` | Detailed reference |
| `/new` | `/nuova` | Start a new draft session |
| `/confirm` | `/conferma` | Finalize the active draft → returns ID |
| `/cancel` | `/annulla` | Discard the active draft (or cancel a pending input) |
| `/rename <name>` | `/rinomina <nome>` | Rename the active draft |
| `/rename <ref> <new>` | `/rinomina <ref> <nuovo>` | Rename any upload (blocked after first use) |
| `/context <text>` | `/contesto <testo>` | Attach context to the active draft |
| `/context <ref> [text]` | `/contesto <ref> [testo]` | Set/clear context on any upload |
| `/list` | `/lista` | List uploads for this chat |
| `/info <ref>` | `/info <ref>` | Show details + context + usage history |
| `/cleanup` | `/pulizia` | Top-10 oldest + biggest, with delete buttons |
| `/cleanup <N>g` | `/pulizia <N>g` | Delete uploads older than N days |
| `/cleanup <ref>` | `/pulizia <ref>` | Delete one upload |
| `/language` | `/lingua` | Switch the per-chat language (English ↔ Italian) |
| `/version` | `/version` | Current version + commit (owner only) |
| `/restart` | `/riavvia` | Bounce the bot under its supervisor (owner only) |

`BOT_LANG` sets the default for new chats. Each chat can override via `/language`; the choice persists in SQLite.

After every reply the bot shows the inline keyboard appropriate to the current state — no command memorization required.

## Resolver HTTP API

| Method | Path | Description |
|---|---|---|
| `GET`  | `/healthz` | Liveness probe (no auth) |
| `GET`  | `/resolve?ref=<id\|name>` | Look up an upload — read-only, no audit entry |
| `POST` | `/use` | Mark used, append to audit log, return path + files + context |

Response shape (both endpoints):

```json
{
  "id": "k7m2p9x4",
  "name": "AprilInvoices",
  "context": "Attachments for email to Marco — April invoices",
  "status": "confirmed",
  "path": "/data/staging/k7m2p9x4",
  "files": ["invoice_001.pdf", "invoice_002.pdf"],
  "size_bytes": 245760,
  "file_count": 2,
  "created_at": "2026-04-28T12:00:00+00:00",
  "confirmed_at": "2026-04-28T12:01:33+00:00",
  "last_used_at": null
}
```

`POST /use` body:

```json
{ "ref": "k7m2p9x4", "action": "email_send", "details": { "to": "marco@example.com" } }
```

Both endpoints use bearer auth when `RESOLVER_AUTH=apikey`. `/healthz` is always open.

## Hermes Agent skill

The repo ships a [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill in [`skills/files-to-agent/SKILL.md`](skills/files-to-agent/SKILL.md). Drop it into your Hermes skills directory and the agent learns to look up staged batches and attach files when you reference an ID.

```bash
cp -r skills/files-to-agent ~/.hermes/skills/
export FILESTOAGENT_RESOLVER_URL=http://127.0.0.1:8080
```

The skill is provider-generic — works with any Hermes deployment that can reach the resolver URL.

## Configuration

All settings via environment variables. See [`.env.example`](.env.example) for the full list with defaults. The required ones:

| Variable | Purpose |
|---|---|
| `BOT_TOKEN` | Telegram bot token from `@BotFather` |
| `BOT_ALLOWED_USER_IDS` | Comma-separated Telegram numeric user IDs allowed to use the bot. The first ID is the owner (can run `/restart`). |

## Development

```bash
git clone https://github.com/samuelgudi/files-to-agent
cd files-to-agent
uv sync --extra dev
uv run pytest
uv run ruff check src tests
```

For a local Docker dev loop:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Status

Pre-1.0. Stable enough for production use, but minor breaking changes may land before v1.0 if a better design surfaces. All breaking changes are documented in [`CHANGELOG.md`](CHANGELOG.md) and gated through minor-version bumps until 1.0, then through major-version bumps after.

## Contributing

PRs welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow and [`SECURITY.md`](SECURITY.md) for vulnerability disclosure.

## License

[MIT](LICENSE) © Samuel Gudi
