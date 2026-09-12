## MODIFIED Requirements

### Requirement: Incremental update

The system SHALL skip re-cloning if a directory already exists and instead fetch and fast-forward to match the remote default branch,
bringing the mirror's tags in line with the upstream's in the same step.
`clone` is the re-baselining tool — it resets the working tree onto `origin/HEAD` —
so a tag the upstream does not have is local state it discards like any other.

#### Scenario: Existing clone updated

- **WHEN** `mirrors/<org>/<repo>/` already exists
- **THEN** the script runs `git fetch --prune --prune-tags` and resets the default branch to `origin/HEAD`

#### Scenario: Tags left behind by an earlier run

- **WHEN** a mirror carries tags its upstream does not have,
  including any imported from the template before the `template` remote stopped offering them
- **THEN** the update removes them, leaving the mirror's tags equal to the upstream's

#### Scenario: Idempotent run

- **WHEN** the script is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero
