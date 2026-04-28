# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.1] - 2026-04-28

### Refactor

- Delete dead _read_pyproject_version helper and stale test



## [0.1.1] - 2026-04-28

### Bug Fixes

- Add pull_policy: always so :latest moves on up -d
- Explicitly register slash menu after bot.initialize()
- Skip uv sync when uv is missing instead of failing update

### Documentation

- Add RELEASE.md and git-cliff config for changelog automation
- Note Compose v2.22+ requirement in dev override
- Document GHCR first-time public-visibility step
- Rewrite Docker deployment for registry-pull + Watchtower auto-update
- Rewrite README quickstart for registry-pull deployment
- Add 4-phase architecture overhaul plans
- Add plan for slash-menu registration fix
- Add plan for uv-PATH fix in run_git_update
- Add plan for /restart command
- Add plan for bot rebrand + cleanup delete buttons
- Public-ready README with quick start and command tables
- Document BOT_LANG in .env.example

### Features

- Switch docker-compose to GHCR registry image; add dev override
- Add _find_uv helper with PATH fallback for supervised deploys
- Register /restart and /riavvia commands
- Add handle_restart owner-only handler
- Add restart_starting message key + help-text entry
- Handle del:<id> callback to delete uploads from cleanup view
- Attach per-item delete buttons to cleanup view
- Add kb_cleanup_items keyboard factory for delete buttons
- Rebrand welcome to 'File To Agent Bot' in both locales
- Full bot UX overhaul — inline keyboards, bilingual UI, self-update
- Add Hermes Agent skill for using staged batches
- Docker, docker-compose, process-compose deploy artifacts + guide
- Concurrent runner (bot polling + uvicorn) + python -m entrypoint
- HTTP resolver (/healthz, /resolve, /use) with context + optional bearer auth
- /pulizia (interactive list, by-ref, by-age)
- /lista and /info handlers
- /contesto handler (active draft, by-ref, clear)
- /rinomina handler (active-draft and explicit forms)
- /conferma and /annulla handlers
- Media intake handler (document/photo/video/audio/voice)
- Bot scaffold with /start, /nuova, auth gate
- Bilingual (it/en) message catalog with t(key, lang) helper
- Add bot_lang config field (it|en, default it)
- Add Core.set_context (allowed after use, unlike rename)
- Context field on Upload model + row mapper
- Add context column to uploads schema
- List/oldest/biggest/older-than queries + delete_upload
- Usage tracking with audit log + status guard
- Rename + by-ref resolution with use-state guard
- Core upload lifecycle (create/add/confirm/cancel)
- StagingStorage with folder lifecycle + filename dedup
- Pydantic data models for Upload + UsageLogEntry
- Sqlite schema, WAL mode, FK enforcement
- Env-driven Settings module with auth validation

### Refactor

- Read version from importlib.metadata; bake commit SHA via env
- Rename _post_init to register_slash_menu, drop dead PTB hook

