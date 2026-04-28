# Release Process

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

## Cutting a release

1. **Decide the version bump:**
   - `PATCH` (`0.1.0` → `0.1.1`): bug fixes, doc updates, no API changes
   - `MINOR` (`0.1.0` → `0.2.0`): new features, backward-compatible
   - `MAJOR` (`0.1.0` → `1.0.0`): breaking changes (config keys removed, command renamed, etc.)

2. **Bump the version in `pyproject.toml`:**

   ```toml
   [project]
   version = "0.1.1"
   ```

3. **Generate the changelog entry:**

   ```bash
   uvx git-cliff --tag v0.1.1 -o CHANGELOG.md
   ```

   Review `CHANGELOG.md` for accuracy. Edit if a commit's message doesn't read well.

4. **Commit:**

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore(release): v0.1.1"
   ```

5. **Tag:**

   ```bash
   git tag -a v0.1.1 -m "Release v0.1.1"
   ```

6. **Push (commits + tags):**

   ```bash
   git push
   git push --tags
   ```

7. **Verify the release:**
   - GitHub Actions should run the `Release` workflow and publish:
     - `ghcr.io/samuelgudi/files-to-agent:v0.1.1`
     - `ghcr.io/samuelgudi/files-to-agent:0.1` (floating minor)
     - `ghcr.io/samuelgudi/files-to-agent:0` (floating major)
     - `ghcr.io/samuelgudi/files-to-agent:sha-<short>` (commit-pinned)
     - `ghcr.io/samuelgudi/files-to-agent:latest` (only on `main` push, not on tag push)
   - A GitHub Release should appear at `https://github.com/samuelgudi/files-to-agent/releases/tag/v0.1.1`

## Conventional Commits

Commits should follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat(scope): description` — new feature
- `fix(scope): description` — bug fix
- `docs(scope): description` — documentation
- `refactor(scope): description` — code refactor without behavior change
- `chore(scope): description` — chores (release, dependency bumps, etc.)
- `ci(scope): description` — CI changes
- `test(scope): description` — test changes

Append `!` for breaking changes: `feat(api)!: rename /old to /new`.

These are what `git-cliff` parses to build the changelog.

## Hotfix process

1. Branch from the tag of the affected release: `git checkout -b hotfix/v0.1.2 v0.1.1`
2. Apply the fix, commit (conventional message)
3. Bump `pyproject.toml` to `0.1.2`, regenerate changelog, commit
4. Tag `v0.1.2`, push the branch + tag
5. Cherry-pick / merge the fix back to `main` if applicable
