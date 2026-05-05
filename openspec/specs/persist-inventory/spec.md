## Purpose

Persist the foreign-repo inventory parsed from `krlmlr/actions-sync` branch names as a stable, machine-readable `repos.yml` so all downstream tooling has a single source of truth.

> **Note:** `repos.yml` is a one-time import. The script is run manually, the diff reviewed, and the result committed. There is no automated refresh; updates follow the same manual process.
## Requirements
### Requirement: Write inventory to repos.yml
The system SHALL write the parsed `(org, repo)` tuple list to `repos.yml` at the repository root as a YAML document under the top-level key `repos`.

#### Scenario: Non-empty inventory written
- **WHEN** one or more `(org, repo)` tuples are parsed
- **THEN** `repos.yml` is written with a `repos:` sequence where each entry has `org` and `repo` string fields

#### Scenario: File is created if absent
- **WHEN** `repos.yml` does not exist
- **THEN** the system creates it with the full inventory content

#### Scenario: File is overwritten if present
- **WHEN** `repos.yml` already exists with stale content
- **THEN** the system overwrites it atomically with the new inventory

### Requirement: Inventory is sorted case-insensitively and stable
The system SHALL write the `repos` list sorted ascending by `org` (case-insensitive) then by `repo` (case-insensitive) so that mixed-case names sort alphabetically and repeated runs produce identical output.

#### Scenario: Deterministic output
- **WHEN** the same set of branches is fetched in any order
- **THEN** `repos.yml` is byte-for-byte identical across runs

#### Scenario: Case-insensitive lexicographic sort
- **WHEN** branches `zorg/a`, `acme/b`, and `acme/a` are in the inventory
- **THEN** `repos.yml` lists them as `acme/a`, `acme/b`, `zorg/a`

#### Scenario: Mixed-case repo names sort alphabetically
- **WHEN** repos `DBI`, `adbi`, and `RSQLite` exist under the same org
- **THEN** they appear as `adbi`, `DBI`, `RSQLite` (case-insensitive alpha order)

### Requirement: repos.yml format is human-readable YAML
The system SHALL produce valid YAML that a human can read and edit. Each entry SHALL use block-style mapping with `org:` and `repo:` keys on separate lines.

#### Scenario: Valid YAML output
- **WHEN** `repos.yml` is written
- **THEN** it can be parsed by a standard YAML parser without errors

#### Scenario: Block style enforced
- **WHEN** `repos.yml` is written
- **THEN** entries are not collapsed to flow style (e.g. `{org: x, repo: y}`)

### Requirement: Preserve `template: true` flag across refreshes
The system SHALL preserve the `template: true` flag on the matching `(org, repo)` entry when refreshing `repos.yml` from upstream branches. The flag is human-curated metadata not derivable from `actions-sync`.

#### Scenario: Flag retained when repo still in inventory
- **WHEN** `repos.yml` exists with `template: true` on `<org>/<repo>` and a refresh sees the same `<org>/<repo>` in the new branch list
- **THEN** the rewritten `repos.yml` carries `template: true` on the same entry

#### Scenario: Flagged repo no longer in inventory
- **WHEN** the previously-flagged `<org>/<repo>` is absent from the new branch list
- **THEN** the writer exits non-zero without overwriting `repos.yml`, so the operator can choose a new template explicitly

#### Scenario: No prior flag
- **WHEN** no existing `repos.yml` carries `template: true` (e.g. first run)
- **THEN** the writer produces the inventory unchanged in shape; no entry is auto-flagged

### Requirement: At most one template flag
The system SHALL write `repos.yml` with at most one entry carrying `template: true`.

#### Scenario: Multiple flags rejected
- **WHEN** the existing `repos.yml` is malformed and carries `template: true` on more than one entry
- **THEN** the writer exits non-zero and refuses to write

