## ADDED Requirements

### Requirement: yq tool availability
The project SHALL make `yq` available as a required tool via `mise.toml`, ensuring all developers and CI/CD environments have it installed.

#### Scenario: yq is installed
- **WHEN** a developer runs `mise install`
- **THEN** `yq` binary is available in PATH with the version specified in `mise.toml`

#### Scenario: yq not found
- **WHEN** `yq` is not installed (or PATH is misconfigured)
- **THEN** scripts that depend on `yq` fail with a clear error message

### Requirement: YAML read operations use yq
Scripts and tools SHALL use `yq` CLI for reading and extracting data from YAML files instead of inline Python YAML parsing.

#### Scenario: Extract nested YAML value
- **WHEN** a script needs to extract a value from a YAML file (e.g., `.metadata.version`)
- **THEN** the script uses `yq eval '.metadata.version' file.yaml` or equivalent

#### Scenario: Filter YAML list
- **WHEN** a script needs to filter items from a YAML list based on a condition
- **THEN** the script uses `yq` with a filter expression instead of Python list comprehension

### Requirement: YAML write/modify operations use yq
Scripts SHALL use `yq` CLI for modifying YAML files instead of inline Python YAML manipulation.

#### Scenario: Update YAML value
- **WHEN** a script needs to modify a value in a YAML file
- **THEN** the script uses `yq eval -i '.<path> = <value>' file.yaml` instead of Python dict manipulation

#### Scenario: Add YAML entry
- **WHEN** a script needs to add a new key-value pair to a YAML file
- **THEN** the script uses `yq eval -i '.<path> += {<key>: <value>}' file.yaml`

### Requirement: Design principle documented
The project SHALL document the preference for `yq` over inline Python for YAML operations as a design principle.

#### Scenario: Developer review
- **WHEN** a developer reviews code with inline YAML manipulation
- **THEN** they can reference the documented principle to suggest refactoring to `yq`

#### Scenario: Code review guideline
- **WHEN** new code includes YAML parsing/modification
- **THEN** reviewers check if `yq` could be used instead, following the established principle
