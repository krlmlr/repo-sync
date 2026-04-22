## Why

Scripts and tool versions are currently invoked ad-hoc. Without a task runner, contributors must know which script to call, where it lives, and how to pass arguments. Without pinned tool versions, the Python version is implicit and environment setup is undocumented. `mise` solves both: it pins tool versions declaratively and provides named tasks as a stable entry point.

## What Changes

- `mise.toml` at the repository root pinning the required Python version and defining named tasks for each script entry point.
- Environment prerequisites (e.g. `gh` authentication) documented in `mise.toml` so contributors know what must be in place before running a task.

## Capabilities

### New Capabilities

- `task-runner`: Run any script via `mise run <task>` without knowing the underlying path or interpreter.
- `env-setup`: Document environment prerequisites (e.g. `gh` must be authenticated) in `mise.toml` so contributors know what to set up before running tasks.

### Modified Capabilities

## Impact

- New `mise.toml` at the repository root.
- `gh` must be authenticated; documented as a prerequisite in `mise.toml`.
- No changes to existing scripts — `mise` wraps them.
