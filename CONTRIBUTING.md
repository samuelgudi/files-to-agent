# Contributing to files-to-agent

Thanks for considering a contribution. This is an MIT-licensed project — patches, bug reports, and feature suggestions are all welcome.

## Reporting bugs

Open an issue using the [Bug Report](https://github.com/samuelgudi/files-to-agent/issues/new?template=bug_report.yml) template. Include:

- What you expected
- What happened
- Logs (the bot logs to stdout / Docker logs)
- Your deploy mode (Docker, process-compose, standalone) and the bot's `/version` output

## Suggesting features

Open an issue using the [Feature Request](https://github.com/samuelgudi/files-to-agent/issues/new?template=feature_request.yml) template. Describe:

- The problem you're trying to solve (not the solution)
- Why the existing commands / config don't cover it
- What "good" looks like

## Submitting pull requests

1. **Fork** the repo and create a topic branch off `main`:
   ```bash
   git checkout -b feat/short-description
   ```

2. **Set up your environment:**
   ```bash
   uv sync --extra dev
   ```

3. **Make your changes.** Keep PRs focused — one logical change per PR. Tests are required for new features and bug fixes.

4. **Follow existing patterns:**
   - Match the codebase's style (run `uv run ruff check src/ tests/` before submitting)
   - Italian is canonical for user-facing strings; English mirrors it (see `messages.py`)
   - Tests go in `tests/`, mirroring the source structure

5. **Use Conventional Commit messages:**
   - `feat(scope): short description` for features
   - `fix(scope): short description` for bug fixes
   - `docs(scope): short description` for documentation
   - `refactor(scope): short description` for refactors
   - `test(scope): short description` for test-only changes
   - `chore(scope): short description` for everything else

6. **Run the full check before pushing:**
   ```bash
   uv run ruff check src/ tests/
   uv run pytest tests/ -v
   ```

7. **Open the PR.** The CI workflow runs the same checks; the release workflow builds a multi-arch image (no push for PRs). Both must be green before review.

8. **Respond to review.** I'll usually leave a few notes; squash-merge happens after both sides are happy.

## What I'm likely to accept

- Bug fixes (with a test that fails before the fix, passes after)
- New commands that fit the bot's scope (file staging for AI agents)
- Resolver-side improvements that don't expand the API surface unnecessarily
- Performance improvements with measurements
- Test coverage improvements
- Documentation clarifications

## What I'm likely to push back on

- Big refactors without a concrete user-visible benefit
- Wholesale dependency swaps
- Changes that couple the bot to a specific orchestrator (k8s-only features, etc.)
- Re-introducing the self-update mechanism — that's been deliberately removed, see [docs/migration-from-self-update.md](docs/migration-from-self-update.md)

## Code of Conduct

Be reasonable. The project doesn't (yet) have a formal CoC document, but the gist is: technical merit decides, personal attacks don't.

## Releases

See [RELEASE.md](RELEASE.md) for the release process. Maintainers tag versions; contributors don't need to touch `pyproject.toml` or `CHANGELOG.md`.

## Questions

Open a [GitHub Discussion](https://github.com/samuelgudi/files-to-agent/discussions) — issues are for bugs and concrete features.
