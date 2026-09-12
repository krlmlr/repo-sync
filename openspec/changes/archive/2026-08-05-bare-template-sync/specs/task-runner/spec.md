## MODIFIED Requirements

### Requirement: Named tasks for each script entry point
`mise.toml` SHALL define a task for each script so contributors run `mise run <task>` without knowing the underlying path or interpreter.

#### Scenario: fetch-inventory task
- **WHEN** a contributor runs `mise run fetch-inventory`
- **THEN** `mise` executes `scripts/fetch_inventory.py` with the project Python interpreter

#### Scenario: clone task
- **WHEN** a contributor runs `mise run clone`
- **THEN** `mise` executes `scripts/clone.sh`

#### Scenario: sync task
- **WHEN** a contributor runs `mise run sync`
- **THEN** `mise` executes `scripts/sync.sh`, which refreshes the template's bare mirror, rebases every mirror onto its upstream,
  and fetches the `template` remote everywhere

#### Scenario: Unknown task
- **WHEN** a contributor runs `mise run nonexistent`
- **THEN** `mise` exits non-zero with a list of available tasks
