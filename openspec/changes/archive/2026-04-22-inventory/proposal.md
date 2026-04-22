## Why

The set of foreign repositories this tool must manage is encoded in the branch names of `krlmlr/actions-sync`. Without a machine-readable inventory, none of the downstream tooling (clone, reconcile, push) has anything to operate on.

## What Changes

- `repos.yml` committed at the repository root with the full current inventory (59 repos across 15 orgs), parsed from `krlmlr/actions-sync` branch names via `git ls-remote --heads`. Branches without a `/` (`base`, `gh-pages`, `main`, `main-old-bidi`) are excluded. Sorted case-insensitively by org then repo.
- A clone script that reads `repos.yml` and clones every repo into a local `<org>/<repo>/` layout, fetching and fast-forwarding on subsequent runs. Uses `gh repo clone` with pre-authenticated `gh` credentials.

## Capabilities

### New Capabilities

- `persist-inventory`: Write the parsed tuple list to `repos.yml` in a stable, case-insensitively sorted, machine-readable format.
- `clone`: Clone or incrementally update every repo listed in `repos.yml` into a local `<org>/<repo>/` directory layout using `gh repo clone`.

### Modified Capabilities

## Impact

- `repos.yml` at the repository root — already committed; consumed by all downstream tooling.
- New `scripts/clone.sh`.
- Dependency on `git` CLI (for `git ls-remote`) and `gh` CLI (authenticated; for cloning).
