## ADDED Requirements

### Requirement: Required env vars declared in mise.toml
`mise.toml` SHALL declare `GITHUB_TOKEN` as a required environment variable for the `clone` task so that `mise` surfaces missing config before any git operation runs.

#### Scenario: Token present
- **WHEN** `GITHUB_TOKEN` is set in the shell environment
- **THEN** `mise run clone` proceeds without prompting

#### Scenario: Token absent
- **WHEN** `GITHUB_TOKEN` is not set
- **THEN** `mise run clone` exits non-zero with a message identifying the missing variable before invoking `gh` or `git`
