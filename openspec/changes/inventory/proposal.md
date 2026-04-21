## Why

The set of foreign repositories this tool must manage is encoded in the branch names of `krlmlr/actions-sync`. Without a machine-readable inventory, none of the downstream tooling (clone, reconcile, push) has anything to operate on.

## What Changes

- `repos.yml` committed at the repository root with the full current inventory (59 repos across 15 orgs), parsed from `krlmlr/actions-sync` branch names via `git ls-remote --heads`. Branches without a `/` (`base`, `gh-pages`, `main`, `main-old-bidi`) are excluded. Sorted case-insensitively by org then repo.
- A script to validate all repos in `repos.yml` are accessible on GitHub.
- A clone script that reads `repos.yml` and clones every repo into a local `<org>/<repo>/` layout, fetching and fast-forwarding on subsequent runs. Uses a GitHub token for auth.

## Capabilities

### New Capabilities

- `fetch-inventory`: Fetch branch names from `krlmlr/actions-sync` and parse them into `<org>/<repo>` tuples.
- `persist-inventory`: Write the parsed tuple list to `repos.yml` in a stable, case-insensitively sorted, machine-readable format.
- `clone`: Clone or incrementally update every repo listed in `repos.yml` into a local `<org>/<repo>/` directory layout.

### Modified Capabilities

## Impact

- `repos.yml` at the repository root — already committed; consumed by all downstream tooling.
- New `scripts/` with clone and validate scripts.
- Dependency on `git` CLI and a `GITHUB_TOKEN` for authenticated cloning.
