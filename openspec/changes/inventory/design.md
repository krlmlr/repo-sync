## Context

`krlmlr/actions-sync` is a public GitHub repository whose branch names encode the set of foreign repositories this tool manages. Each branch name represents one `<org>/<repo>` pair. Currently no tooling exists to turn those branches into a consumable list; the inventory must be fetched, parsed, and written to disk so that downstream clone/reconcile/push scripts can work without requiring live network access at run time.

The project is in its earliest stage — no scripts, workflows, or persistent data files exist yet.

## Goals / Non-Goals

**Goals:**
- Fetch all branch names from `krlmlr/actions-sync` using `git ls-remote --heads` (no auth required for public repos).
- Parse each branch name into an `(org, repo)` tuple using the branch-name encoding convention.
- Write the tuple list to `repos.yml` at the repository root in a stable, sorted format.
- Add a scheduled GitHub Actions workflow that re-runs the pipeline and commits any diff to `repos.yml`.

**Non-Goals:**
- Filtering out archived, disabled, or private repos at this stage (deferred until we confirm the encoding and have examples).
- Cloning, reconciling, or pushing to the listed repos (those are separate roadmap sections).
- Supporting inventory sources other than `krlmlr/actions-sync` branches.

## Decisions

### Language: Python over shell

**Decision**: Implement the fetch-and-persist script in Python.

**Rationale**: The pipeline is simple enough for shell, but Python gives us proper unit-testable parsing of branch names, clean YAML serialisation via `PyYAML`, and error handling without subshell complexity. The project will grow to need Python for later phases anyway.

**Alternative considered**: Bash with `git ls-remote | awk`. Works but parsing edge cases (branches with unexpected `/` counts, empty output) are harder to test and maintain.

### Branch listing: `git ls-remote --heads` over GitHub API

**Decision**: Use `subprocess.run(["git", "ls-remote", "--heads", ...])` to list branches.

**Rationale**: `krlmlr/actions-sync` is public, so no token is needed. `git ls-remote` is always available in CI and returns exactly `refs/heads/<branch>` lines — no pagination, no rate limits. Simple and dependency-free.

**Alternative considered**: GitHub REST API (`/repos/{owner}/{repo}/branches`). Adds an HTTP client dependency and pagination; gains the ability to filter archived repos, but that filtering is deferred.

### Branch-name encoding: `<org>/<repo>` with single slash

**Decision**: Parse branch names by splitting on the first `/`: everything before is `org`, everything after is `repo`.

**Rationale**: The ROADMAP states branches encode `<org>/<repo>` pairs, and `git ls-remote` returns `refs/heads/<org>/<repo>` for such branches. Splitting `refs/heads/<branch>` on `/` at index 2 and 3 is unambiguous.

**Risk**: The actual encoding in `actions-sync` may differ (e.g. `<org>-<repo>`). This must be verified by inspecting live branch names before the script is merged. See Open Questions.

### Inventory format: YAML list of mappings

**Decision**: Write `repos.yml` as a YAML sequence of `{org, repo}` mappings, sorted by `org` then `repo`.

```yaml
repos:
  - org: acme
    repo: infra
  - org: acme
    repo: web
```

**Rationale**: Structured and extensible (future fields like `skip: true` can be added without format changes). Sorted output means diffs are stable. PyYAML handles serialisation.

**Alternative considered**: Plain `repos.txt` one `org/repo` per line. Simpler but harder to extend and requires a custom parser in consumers.

## Risks / Trade-offs

- **Wrong branch encoding** → Script silently produces an empty or malformed inventory. Mitigation: add an assertion that at least one repo was parsed; fail loudly if output is empty. Verify encoding against live branches before merge.
- **Commit churn from scheduled refresh** → If `actions-sync` branches change frequently, each run creates a commit. Mitigation: workflow compares the new `repos.yml` against the committed version and only commits when there is a diff.
- **`actions-sync` goes private** → `git ls-remote` without a token will fail. Mitigation: fall back to the GitHub API with a `GITHUB_TOKEN` secret; document this in the workflow.

## Open Questions

1. **Branch encoding**: Are branches named `<org>/<repo>` (slash-separated) or `<org>-<repo>` (hyphen-separated), or another convention? Must be confirmed by running `git ls-remote --heads https://github.com/krlmlr/actions-sync` and inspecting real branch names.
2. **Filter criteria**: Should branches matching certain patterns (e.g. default branch `main`, or branches prefixed with `_`) be excluded from the inventory?
3. **Commit identity**: What name/email should the refresh workflow use when committing updated `repos.yml`? (GitHub Actions bot vs. a dedicated service account.)
