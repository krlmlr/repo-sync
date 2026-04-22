### Requirement: Clone repos from inventory
The system SHALL read `repos.yml` and clone every listed repository into a local `mirrors/<org>/<repo>/` directory using `gh repo clone`.

#### Scenario: Fresh clone
- **WHEN** `mirrors/<org>/<repo>/` does not exist
- **THEN** the script runs `gh repo clone <org>/<repo> mirrors/<org>/<repo>`

#### Scenario: Auth handled by gh
- **WHEN** `gh` is authenticated (any method)
- **THEN** the script clones without any additional token configuration; private repos succeed

### Requirement: Incremental update
The system SHALL skip re-cloning if a directory already exists and instead fetch and fast-forward to match the remote default branch.

#### Scenario: Existing clone updated
- **WHEN** `mirrors/<org>/<repo>/` already exists
- **THEN** the script runs `git fetch --prune` and resets the default branch to `origin/HEAD`

#### Scenario: Idempotent run
- **WHEN** the script is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero

### Requirement: Failures are isolated
The system SHALL continue processing remaining repos if a single clone or fetch fails, and report all failures at the end with a non-zero exit code.

#### Scenario: One repo unreachable
- **WHEN** one repo returns a network or auth error
- **THEN** the script logs the failure, continues with the rest, and exits non-zero after all repos are processed
