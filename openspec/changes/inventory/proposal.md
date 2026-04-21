## Why

The set of foreign repositories this tool must manage is encoded in the branch names of `krlmlr/actions-sync`. Without a machine-readable inventory, none of the downstream tooling (clone, reconcile, push) has anything to operate on.

## What Changes

- `repos.yml` committed at the repository root with the full current inventory (59 repos across 15 orgs), parsed from `krlmlr/actions-sync` branch names via `git ls-remote --heads`. Branches without a `/` (`base`, `gh-pages`, `main`, `main-old-bidi`) are excluded. Sorted case-insensitively by org then repo.
- A Python script (`scripts/fetch_inventory.py`) that automates the fetch-parse-write pipeline for future manual refreshes.

## Capabilities

### New Capabilities

- `fetch-inventory`: Fetch branch names from `krlmlr/actions-sync` and parse them into `<org>/<repo>` tuples.
- `persist-inventory`: Write the parsed tuple list to `repos.yml` in a stable, case-insensitively sorted, machine-readable format.

### Modified Capabilities

## Impact

- `repos.yml` at the repository root — already committed; consumed by all downstream tooling.
- New `scripts/fetch_inventory.py` and associated `pyproject.toml`.
- Dependency on `git` CLI (for `git ls-remote`) and `PyYAML`.
