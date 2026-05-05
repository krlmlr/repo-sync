## Why

Inline Python code for YAML manipulation is harder to test, debug, and maintain than using a dedicated YAML tool. Using `yq` (a purpose-built command-line YAML processor) makes YAML operations more transparent, portable, and follows the Unix philosophy of composable tools.

## What Changes

- Add `yq` as a required tool in `mise.toml`
- Establish a design principle: prefer `yq` CLI for YAML operations over inline Python
- Refactor existing Python code that manipulates YAML files to use `yq` instead
- Update documentation to reflect this preference

## Capabilities

### New Capabilities
- `yaml-operations`: Standardized approach to reading/writing/modifying YAML files using `yq`

### Modified Capabilities
- `env-setup`: May use `yq` for YAML configuration processing instead of inline Python
- `task-runner`: May use `yq` for YAML task definition processing

## Impact

- Affects any Python code currently parsing or modifying YAML files
- Requires `yq` binary to be available (added to mise.toml)
- Simplifies YAML manipulation logic and improves code clarity
- Makes configuration file operations more portable across environments
