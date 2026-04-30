### Requirement: Named tasks for each script entry point
`mise.toml` SHALL define a task for each script so contributors run `mise run <task>` without knowing the underlying path or interpreter.

#### Scenario: fetch-inventory task
- **WHEN** a contributor runs `mise run fetch-inventory`
- **THEN** `mise` executes `scripts/fetch_inventory.py` with the project Python interpreter

#### Scenario: clone task
- **WHEN** a contributor runs `mise run clone`
- **THEN** `mise` executes `scripts/clone.sh`

#### Scenario: Unknown task
- **WHEN** a contributor runs `mise run nonexistent`
- **THEN** `mise` exits non-zero with a list of available tasks

### Requirement: Pinned Python version
`mise.toml` SHALL declare the Python version under `[tools]` so `mise install` resolves and installs the correct interpreter.

#### Scenario: Correct interpreter used
- **WHEN** `mise run fetch-inventory` is executed
- **THEN** the Python version matches the `[tools]` declaration in `mise.toml`
