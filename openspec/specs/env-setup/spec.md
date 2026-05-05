## Purpose

Document the ambient environment a contributor must have ready (notably an authenticated `gh`) before running any tooling task.

## Requirements

### Requirement: gh authentication documented as prerequisite
`mise.toml` SHALL document that `gh` must be authenticated before running the `clone` task, so contributors know what to set up.

#### Scenario: gh authenticated
- **WHEN** `gh` is authenticated (any method — token, device flow, etc.)
- **THEN** `mise run clone` proceeds without additional configuration

#### Scenario: gh not authenticated
- **WHEN** `gh` is not authenticated
- **THEN** `gh repo clone` fails with its own descriptive error; the task exits non-zero
