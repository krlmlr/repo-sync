## ADDED Requirements

### Requirement: Preserve `maintained: true` flags across refreshes
The system SHALL preserve the `maintained: true` flag on every matching `(org, repo)` entry when refreshing `repos.yml` from upstream branches.
Any number of entries MAY carry the flag.
Like `template: true`, it is human-curated metadata not derivable from `actions-sync`.

#### Scenario: Flag retained when repo still in inventory
- **WHEN** `repos.yml` exists with `maintained: true` on `<org>/<repo>` and a refresh sees the same `<org>/<repo>` in the new branch list
- **THEN** the rewritten `repos.yml` carries `maintained: true` on the same entry

#### Scenario: Flagged repo no longer in inventory
- **WHEN** a previously-flagged `<org>/<repo>` is absent from the new branch list
- **THEN** the writer names it on stderr and writes `repos.yml` without it, exiting zero

#### Scenario: New repo in inventory
- **WHEN** a refresh sees an `<org>/<repo>` that `repos.yml` does not list
- **THEN** its entry is written without `maintained: true`

## MODIFIED Requirements

### Requirement: repos.yml format is human-readable YAML
The system SHALL produce valid YAML that a human can read and edit.
Each entry SHALL use block-style mapping with `org:` and `repo:` keys on separate lines.
Each entry's keys SHALL be written in the order `org`, `repo`, `maintained`, `template`, omitting any that are absent.

#### Scenario: Valid YAML output
- **WHEN** `repos.yml` is written
- **THEN** it can be parsed by a standard YAML parser without errors

#### Scenario: Block style enforced
- **WHEN** `repos.yml` is written
- **THEN** entries are not collapsed to flow style (e.g. `{org: x, repo: y}`)

#### Scenario: Flags follow the name
- **WHEN** an entry carries both `maintained: true` and `template: true`
- **THEN** it is written as `org`, `repo`, `maintained`, `template`, in that order
