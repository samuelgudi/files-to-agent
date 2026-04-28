---
name: files-to-agent
description: Use when the user references a FilesToAgent staging ID or name (e.g. "ID&#58; k7m2p9x4", "uso il fascicolo FattureAprile") and asks for an outbound action that needs file attachments — email, forward, CRM upload, anything where files should be attached. Skip if no ID/name is present in the user's message.
---

# FilesToAgent — using staged file batches

The user maintains a separate Telegram bot (FilesToAgent) where they upload files into ID-tracked sessions. Instead of sending you files directly, they send you the **ID** (or human-readable **name**) and expect you to fetch the staged files and attach them to your outbound action.

You never see the file contents until you explicitly fetch them. The user can verify *which* files you're about to send before you send.

## When this skill triggers

The user's message contains:
- An explicit ID like `ID: k7m2p9x4`, `id: k7m2p9x4`, `Id: k7m2p9x4`
- Or a name reference: `con il fascicolo "FattureAprile"`, `using batch X`, `the staged folder Y`

AND the user is asking for an outbound action that needs attachments (send email, forward to chat, upload to CRM, etc.).

If only an ID is present without an action verb ("what's in ID k7m2p9x4?"), use `/resolve` (read-only) — don't mark used.

## Resolver endpoint

The resolver runs on the same host as you. URL is configured at install:
- **Homelab-host (Host):** `http://127.0.0.1:8080`
- **Samuel/Agent (WSL-host):** `http://127.0.0.1:18080` (or `https://filestoagent.localhost`)

Set `FILESTOAGENT_RESOLVER_URL` env var to override. If unset, fall back to `http://127.0.0.1:8080`.

## Workflow

### 1. Resolve (read-only) to inspect

```bash
curl -s "$FILESTOAGENT_RESOLVER_URL/resolve?ref=<ID_OR_NAME>"
```

Returns JSON like:
```json
{
  "id": "k7m2p9x4",
  "name": "FattureAprile",
  "context": "Allegati per email a Marco - fatture aprile",
  "status": "confirmed",
  "path": "/staging/k7m2p9x4",
  "files": ["fattura_001.pdf", "fattura_002.pdf"],
  "size_bytes": 245760,
  "file_count": 2,
  "created_at": "2026-04-28T12:00:00+00:00",
  "confirmed_at": "2026-04-28T12:01:33+00:00",
  "last_used_at": null
}
```

Read carefully:
- `context` — user's free-text note about what this batch is for. Use it to inform tone, recipients, etc.
- `files` — exact filenames to attach. Don't fabricate; don't omit.
- `path` — where the files live in your filesystem. Combine with each filename: `/staging/k7m2p9x4/fattura_001.pdf`.

### 2. Confirm with the user before sending

Reply summarising:
- Action (send email / forward / upload)
- Recipient(s)
- Subject (if email)
- 1–2 line body summary
- **The exact list of files about to be attached** (names from `files` array)

Wait for explicit user confirmation. Do not skip this step — the audit log will record whatever you send.

### 3. Use (when actually sending)

When the user confirms and you proceed with the outbound action:

```bash
curl -s -X POST "$FILESTOAGENT_RESOLVER_URL/use" \
  -H "Content-Type: application/json" \
  -d '{"ref": "<ID_OR_NAME>", "action": "email_send", "details": {"to": "marco@example.com", "subject": "Fatture aprile"}}'
```

This:
- Marks the upload's `status` as `used` (rename will be blocked from now on)
- Inserts a row in the audit log (the user can review with `/info <id>` in the bot)
- Returns the same JSON shape as `/resolve` (re-use the path/files)

`action` short identifiers: `email_send`, `forward`, `crm_upload`, `whatsapp_send`, etc. — pick what fits.
`details` is freeform JSON for the audit log; record what you actually sent (to, subject, etc.).

Call `/use` **once** per outbound action. Multiple calls duplicate audit log entries.

### 4. Attach the files

Use the `path` and `files` from the response to build attachment paths. For Hermes' built-in `MEDIA:` syntax (Telegram replies, email attachments), emit one `MEDIA:` line per file:

```
MEDIA:/staging/k7m2p9x4/fattura_001.pdf
MEDIA:/staging/k7m2p9x4/fattura_002.pdf
```

The gateway picks them up and attaches them to whatever you're sending.

## Failure modes

- **404 from `/resolve` or `/use`**: the ID or name doesn't exist (or has been deleted via `/pulizia`). Tell the user the ID isn't found and suggest `/lista` in the staging bot to find the right one.
- **409 from `/use`**: status mismatch — typically the user forgot to `/conferma` the upload in the bot. Tell them.
- **Connection refused on the resolver**: the bot isn't running. Tell the user `files-to-agent` may be down; don't pretend it worked.

## Safety rules

1. Never hallucinate an ID. If the user didn't give one, ask which staged batch.
2. Always confirm before `/use` + outbound action — typo'd IDs happen.
3. One `/use` per send. Don't double-call.
4. Don't trust filenames you didn't get from `/resolve`. Don't add files that weren't in the staged batch.
5. If `files` is empty, the staged batch has no files — refuse to attach anything and tell the user.

## Quick reference

```
/resolve?ref=X       → JSON, no side effects
POST /use {ref,...}  → JSON + status=used + audit log row
```

Path the resolver returns is absolute and ready for `MEDIA:` attachments. Use it as-is.
