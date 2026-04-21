## Context

`krlmlr/actions-sync` is a public GitHub repository whose branch names encode the set of foreign repositories this tool manages. Each branch name is `<org>/<repo>` (confirmed by inspection). Infra branches without a `/` (`base`, `gh-pages`, `main`, `main-old-bidi`) are excluded.

`repos.yml` has been committed at the repository root with the current inventory (59 repos across 15 orgs). This is treated as a one-time import; updates are manual (run the script, review the diff, commit). No automated refresh workflow is planned.

## Goals / Non-Goals

**Goals:**
- Implement a Python script that reproducibly fetches, parses, and writes `repos.yml` so future manual refreshes are trivial.
- Sort output case-insensitively so mixed-case repo names (e.g. `DBI`, `RSQLite`) file alphabetically with lowercase names.

**Non-Goals:**
- Automated scheduling / GitHub Actions refresh workflow (manual process is sufficient).
- Filtering archived or private repos (no metadata from `git ls-remote`; deferred).
- Cloning, reconciling, or pushing to listed repos (separate roadmap sections).
- Supporting inventory sources other than `krlmlr/actions-sync`.

## Decisions

### Language: Python over shell

**Decision**: Implement in Python.

**Rationale**: Clean YAML serialisation via PyYAML, testable branch-name parsing, structured error handling. The project will need Python for later phases anyway.

**Alternative considered**: Bash with `git ls-remote | awk`. Works but edge-case handling and testability are worse.

### Branch listing: `git ls-remote --heads`

**Decision**: Use `subprocess.run(["git", "ls-remote", "--heads", ...])`.

**Rationale**: `krlmlr/actions-sync` is public — no token needed. No pagination, no rate limits.

### Branch-name encoding: `<org>/<repo>` with single slash

**Decision**: Split on the first `/`; skip names with no `/`.

**Rationale**: Confirmed by inspecting live branches. Branches without a slash are infra branches.

### Sort order: case-insensitive

**Decision**: Sort by `org.lower()` then `repo.lower()`.

**Rationale**: Mixed-case repo names in `r-dbi` (`DBI`, `RSQLite`) sorted case-sensitively by ASCII value, placing all uppercase names before lowercase. Case-insensitive sort produces natural alphabetical order.

### Inventory format: YAML list of mappings

**Decision**: `repos.yml` as a YAML sequence under `repos:`, block style.

**Rationale**: Extensible (future fields require no format change), human-readable, stable diffs.

## Risks / Trade-offs

- **`actions-sync` goes private** → `git ls-remote` without a token fails. Mitigation: pass `GITHUB_TOKEN` as an env var; script uses it when set.
- **Manual refresh lag** → Inventory can drift if `actions-sync` branches change and no one runs the script. Accepted trade-off; downstream tooling will fail on unknown repos, making staleness visible.
