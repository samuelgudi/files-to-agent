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
