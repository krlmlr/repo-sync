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
<!-- None — clone, persist-inventory, env-setup, task-runner keep the same requirements; only their implementations change. -->

## Impact

- `mise.toml`: adds `yq` under `[tools]`
- `scripts/clone.sh`: replaces the inline `python3 -c` YAML-parsing block (lines 8-30) with `yq` invocations
- `scripts/fetch_inventory.py`: moves YAML I/O boundaries to `yq`, keeps Python for in-memory transforms
- `requirements.txt`: PyYAML may become removable after refactor
- Documentation: a new "Design principles" section captures the yq preference for future contributors
