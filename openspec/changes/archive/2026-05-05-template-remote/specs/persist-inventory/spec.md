## ADDED Requirements

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
