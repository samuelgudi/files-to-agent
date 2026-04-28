# FilesToAgent

A Telegram-side staging bot that holds files for AI agents until they're explicitly consumed.

**Problem.** AI agents that talk to you over Telegram (Hermes, OpenClaw, custom Claude wrappers) treat every uploaded file as a turn — the LLM processes it, costs tokens, and may misuse it later. There's no clean way to say "hold these three files for the email I'm about to compose."

**FilesToAgent.** A separate Telegram bot is your file-staging surface. You upload files into named, ID-tracked sessions (`/nuova` → drop files → `/conferma`). The bot stores them on disk and assigns each session a short ID. You hand the ID to your AI agent ("draft this email; ID: `k7m2p9x4`"). The agent fetches the files via a small HTTP resolver, attaches them, and the bot logs every use.

The agent never sees uploaded file contents until you tell it to. The bot can't be talked into attaching the wrong file because the ID-bound session is the only thing it knows about.

## Features

- Per-chat upload sessions tracked in SQLite (no in-memory state)
- Short 8-character IDs, plus optional human names (`/rinomina`)
- Free-text context per upload (`/contesto`) — agent reads it to understand intent without seeing files
- Rename blocked after first use → no in-flight reference drift; context is *not* blocked (post-hoc notes welcome)
- Activity log: every agent use is recorded with action + JSON details
- Bilingual UI (Italian default, English optional via `BOT_LANG=en`)
- Three deploy modes: Docker (primary), process-compose (light), standalone Python
- Optional bearer-token auth on the resolver — off by default, since on-host deploys are network-isolated

## Quick start

See [docs/deployment.md](docs/deployment.md) for full instructions. TL;DR with Docker:

```bash
git clone <repo> files-to-agent
cd files-to-agent
cp .env.example .env
$EDITOR .env  # set BOT_TOKEN, BOT_ALLOWED_USER_IDS
docker network create agent-net
docker compose up -d --build
```

Mount `./data/staging` into your agent container so it can read the files.

## Telegram commands (Italian UI)

| Command | Effect |
|---|---|
| `/start` | Welcome + command list |
| `/nuova` | Start new draft session |
| `/conferma` | Finalize active draft → returns ID |
| `/annulla` | Discard active draft |
| `/rinomina <nome>` | Rename active draft |
| `/rinomina <id\|nome> <nuovo>` | Rename arbitrary upload (blocked after use) |
| `/contesto <testo>` | Set context on the active draft |
| `/contesto <id\|nome> [testo]` | Set/clear context on any upload (allowed even after use) |
| `/lista` | List uploads for this chat |
| `/info <id\|nome>` | Detailed info + context + usage history |
| `/pulizia` | Show top-10 oldest + biggest |
| `/pulizia <N>g` | Delete uploads older than N days |
| `/pulizia <id\|nome>` | Delete one upload |

The bot UI is bilingual: set `BOT_LANG=it` (default) or `BOT_LANG=en`. Command names stay Italian regardless.

## Resolver HTTP API

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness probe (no auth) |
| GET | `/resolve?ref=<id\|nome>` | Look up an upload, return path + files + context (read-only) |
| POST | `/use` | Mark used, append to audit log, return path + files + context |

Response shape (both endpoints):
```json
{
  "id": "k7m2p9x4",
  "name": "FattureAprile",
  "context": "Allegati per email a Marco — fatture aprile",
  "status": "confirmed",
  "path": "/data/staging/k7m2p9x4",
  "files": ["fattura_001.pdf", "fattura_002.pdf"],
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

## Configuration

All settings via env vars. See `.env.example` for the full list with defaults.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
```

## License

MIT — see [LICENSE](LICENSE).
