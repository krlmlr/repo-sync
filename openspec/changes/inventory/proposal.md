## Why

The set of foreign repositories this tool must manage is encoded in the branch names of `krlmlr/actions-sync`, but there is currently no mechanism to fetch, parse, or persist that list. Without a machine-readable inventory, none of the downstream tooling (clone, reconcile, push) has anything to operate on.

## What Changes

- Add a script that fetches all branch names from `krlmlr/actions-sync` via `git ls-remote --heads` or the GitHub API and parses each name into an `<org>/<repo>` tuple.
- Persist the resulting list as a machine-readable file (`repos.yml`) committed into this repository so downstream tooling can consume it without network access.
- Add a GitHub Actions workflow that refreshes the inventory on a schedule (cron) and commits updated `repos.yml` automatically.

## Capabilities

### New Capabilities

- `fetch-inventory`: Fetch branch names from `krlmlr/actions-sync` and parse them into `<org>/<repo>` tuples.
- `persist-inventory`: Write the parsed tuple list to `repos.yml` in a stable, machine-readable format.
- `refresh-inventory`: GitHub Actions workflow that runs the fetch-and-persist pipeline on a schedule and commits any changes.

### Modified Capabilities

## Impact

- New script(s) under `scripts/` (language TBD in design; shell or Python are candidates).
- New `repos.yml` at the repository root consumed by all downstream tooling.
- New `.github/workflows/refresh-inventory.yml` workflow.
- Dependency on either `git` CLI or the GitHub REST API (via `gh` or direct HTTP) for branch listing.
