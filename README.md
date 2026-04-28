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
- Inline-keyboard UX — every state has the right buttons (no command memorization)
- Bilingual commands and UI — every command works in both languages (`/nuova` ≡ `/new`); per-chat language preference persisted to SQLite, switchable via `/lingua` button
- Self-update — `/version` checks origin, `/update` pulls and restarts (git checkouts) or signals the host helper script (Docker)
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

## Telegram commands

Every command works in both Italian and English.

| Italian | English | Effect |
|---|---|---|
| `/start` | `/start` | Welcome + main inline keyboard |
| `/help` | `/help` | Detailed reference with examples |
| `/nuova` | `/new` | Start new draft session |
| `/conferma` | `/confirm` | Finalize active draft → returns ID (monospace, tap to copy) |
| `/annulla` | `/cancel` | Discard active draft (or cancel a pending input prompt) |
| `/rinomina <nome>` | `/rename <name>` | Rename active draft |
| `/rinomina <ref> <nuovo>` | `/rename <ref> <new>` | Rename arbitrary upload (blocked after use) |
| `/contesto <testo>` | `/context <text>` | Set context on the active draft |
| `/contesto <ref> [testo]` | `/context <ref> [text]` | Set/clear context on any upload |
| `/lista` | `/list` | List uploads for this chat |
| `/info <ref>` | `/info <ref>` | Detailed info + context + usage history |
| `/pulizia` | `/cleanup` | Show top-10 oldest + biggest |
| `/pulizia <N>g` | `/cleanup <N>g` | Delete uploads older than N days |
| `/pulizia <ref>` | `/cleanup <ref>` | Delete one upload |
| `/lingua` | `/language` | Switch between Italian and English (per-chat) |
| `/version` | `/version` | Show current version + check upstream (owner-only) |
| `/update` | `/update` | Pull and restart the bot (owner-only) |

`BOT_LANG` sets the default for new chats. Each chat can then switch independently via `/lingua` — the choice is persisted in SQLite and survives restarts.

### Inline keyboards

After every reply the bot shows the buttons appropriate to the current state — there's no need to remember commands. The slash menu (the `/` icon next to the input box) is also auto-populated, in Italian or English depending on the user's Telegram client locale.

## Updates

`/version` reports the current commit, deploy mode, and how many commits behind `origin/main` you are. If there are new commits, the reply includes an **Update now** button.

`/update` (or the button) handles the update according to deploy mode:

- **process-compose / systemd / any supervised git checkout** — runs `git fetch && git reset --hard origin/main && uv sync`, then exits. The supervisor restarts the bot. DB schema migrations run on startup.
- **Bare `python -m`** (no supervisor) — refuses with a clear message: the bot would die without auto-restart. Update manually.
- **Docker** — drops a flag file in a mounted volume; a small host-side watcher script (`scripts/update-host.sh`) sees the flag and runs `docker compose pull && docker compose up -d`. See [docs/deployment.md](docs/deployment.md) for setup.

A daily check at 09:00 UTC fetches `origin/main` and DMs the owner if new commits are available. Disable with `UPDATE_CHECK_DAILY=false`.

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

## Hermes Agent skill

The repo ships a [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill in `skills/files-to-agent/SKILL.md`. Drop it into your Hermes skills directory and the agent will know how to look up staged batches and attach files when you reference an ID.

Install:

```bash
# For a docker-compose Hermes deploy with ~/.hermes:/opt/data mounted:
cp -r skills/files-to-agent ~/.hermes/skills/

# For a local Hermes install (e.g. WSL):
cp -r skills/files-to-agent ~/.hermes/skills/
```

Set the resolver URL via env var on the Hermes side (defaults to `http://127.0.0.1:8080`):

```bash
export FILESTOAGENT_RESOLVER_URL=http://127.0.0.1:18080  # or https://filestoagent.localhost
```

The skill is generic — works with any Hermes deployment that can reach the resolver.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
```

## License

MIT — see [LICENSE](LICENSE).
