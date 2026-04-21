## Why

The set of foreign repositories this tool must manage is encoded in the branch names of `krlmlr/actions-sync`. Without a machine-readable inventory, none of the downstream tooling (clone, reconcile, push) has anything to operate on.

## What Changes

- `repos.yml` committed at the repository root with the current inventory (59 repos across 15 orgs), parsed from `krlmlr/actions-sync` branch names via `git ls-remote --heads`. Branches without a `/` (`base`, `gh-pages`, `main`, `main-old-bidi`) are excluded.
- A Python script (`scripts/fetch_inventory.py`) that automates the fetch-parse-write pipeline so the inventory can be refreshed without manual steps.
- A GitHub Actions workflow that runs the script on a schedule and commits any diff to `repos.yml`.

## Capabilities

### New Capabilities

- `fetch-inventory`: Fetch branch names from `krlmlr/actions-sync` and parse them into `<org>/<repo>` tuples.
- `persist-inventory`: Write the parsed tuple list to `repos.yml` in a stable, sorted, machine-readable format.
- `refresh-inventory`: GitHub Actions workflow that runs the fetch-and-persist pipeline on a schedule and commits any changes.

### Modified Capabilities

## Impact

- `repos.yml` at the repository root — already committed; consumed by all downstream tooling.
- New `scripts/fetch_inventory.py` and associated `pyproject.toml`.
- New `.github/workflows/refresh-inventory.yml` workflow.
- Dependency on `git` CLI (for `git ls-remote`) and `PyYAML`.
