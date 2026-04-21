## Context

`krlmlr/actions-sync` is a public GitHub repository whose branch names encode the set of foreign repositories this tool manages. Each branch name is `<org>/<repo>` (confirmed by inspection). Infra branches without a `/` (`base`, `gh-pages`, `main`, `main-old-bidi`) are excluded.

`repos.yml` has been committed at the repository root with the current inventory (59 repos across 15 orgs), produced manually from `git ls-remote --heads`. What remains is to automate the refresh pipeline so the file stays current as `actions-sync` branches change.

## Goals / Non-Goals

**Goals:**
- Implement a Python script that fetches, parses, and writes `repos.yml` reproducibly.
- Add a scheduled GitHub Actions workflow that runs the script and commits any diff.

**Non-Goals:**
- Filtering archived or private repos (no metadata available from `git ls-remote`; deferred).
- Cloning, reconciling, or pushing to listed repos (separate roadmap sections).
- Supporting inventory sources other than `krlmlr/actions-sync`.

## Decisions

### Language: Python over shell

**Decision**: Implement in Python.

**Rationale**: Clean YAML serialisation via PyYAML, testable branch-name parsing, and structured error handling. The project will need Python for later phases anyway.

**Alternative considered**: Bash with `git ls-remote | awk`. Works but edge-case handling and testability are worse.

### Branch listing: `git ls-remote --heads` over GitHub API

**Decision**: Use `subprocess.run(["git", "ls-remote", "--heads", ...])`.

**Rationale**: `krlmlr/actions-sync` is public — no token needed. No pagination, no rate limits, always available in CI.

**Alternative considered**: GitHub REST API. Adds pagination and an HTTP client dependency; the only gain (archived-repo filtering) is deferred.

### Branch-name encoding: `<org>/<repo>` with single slash

**Decision**: Split on the first `/`; skip names with no `/`.

**Rationale**: Confirmed by inspecting live branches. Branches without a slash are infra branches and are not repositories.

### Inventory format: YAML list of mappings

**Decision**: `repos.yml` as a YAML sequence under `repos:`, sorted by org then repo, block style.

**Rationale**: Extensible (future fields like `skip: true` or `archived: true` require no format change), human-readable, stable diffs. Format is already in production.

## Risks / Trade-offs

- **`actions-sync` goes private** → `git ls-remote` without a token fails. Mitigation: pass `GITHUB_TOKEN` as an env var in the workflow; the script falls back to it when set.
- **Commit churn** → Workflow only commits when `repos.yml` content changes (diff check before commit).
- **Case-sensitive sorting** → Current repos.yml sorts case-sensitively (`DBI` before `adbi`). If this causes downstream friction, switch to case-insensitive sort. Deferred.

## Open Questions

1. **Commit identity**: What name/email should the refresh workflow use when committing `repos.yml`? (GitHub Actions default bot vs. a dedicated account.)
2. **Manual overrides**: Should `repos.yml` support a `skip: true` field that survives automated refreshes, to let operators exclude specific repos?
