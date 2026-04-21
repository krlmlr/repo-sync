## ADDED Requirements

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

### Requirement: Inventory is sorted and stable
The system SHALL write the `repos` list sorted ascending by `org` then by `repo` so that repeated runs on the same branch list produce identical file content.

#### Scenario: Deterministic output
- **WHEN** the same set of branches is fetched in any order
- **THEN** `repos.yml` is byte-for-byte identical across runs

#### Scenario: Lexicographic sort
- **WHEN** branches `zorg/a`, `acme/b`, and `acme/a` are in the inventory
- **THEN** `repos.yml` lists them as `acme/a`, `acme/b`, `zorg/a`

### Requirement: repos.yml format is human-readable YAML
The system SHALL produce valid YAML that a human can read and edit. Each entry SHALL use block-style mapping with `org:` and `repo:` keys on separate lines.

#### Scenario: Valid YAML output
- **WHEN** `repos.yml` is written
- **THEN** it can be parsed by a standard YAML parser without errors

#### Scenario: Block style enforced
- **WHEN** `repos.yml` is written
- **THEN** entries are not collapsed to flow style (e.g. `{org: x, repo: y}`)
