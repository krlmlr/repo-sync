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
- **THEN** `mise` executes `scripts/sync.sh`, which refreshes the template's bare mirror, rebases every mirror onto its upstream, and fetches the `template` remote everywhere

#### Scenario: metrics task
- **WHEN** a contributor runs `mise run metrics`
- **THEN** `mise` executes `scripts/collect_metrics.py`, writing one snapshot of the inventory,
  its mirror-derived groups present only where the mirrors are

#### Scenario: dashboard task
- **WHEN** a contributor runs `mise run dashboard`
- **THEN** `mise` executes `scripts/render_dashboard.py` against the latest snapshot,
  writing a page that opens from disk, collecting nothing and needing no network

#### Scenario: publish-dashboard task
- **WHEN** a contributor runs `mise run publish-dashboard`
- **THEN** `mise` publishes the current snapshot and page, having first removed the workspace group that is local to the machine

#### Scenario: Unknown task
- **WHEN** a contributor runs `mise run nonexistent`
- **THEN** `mise` exits non-zero with a list of available tasks
