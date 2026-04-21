## Why

Scripts and tool versions are currently invoked ad-hoc. Without a task runner, contributors must know which script to call, where it lives, and how to pass arguments. Without pinned tool versions, the Python version is implicit and environment setup is undocumented. `mise` solves both: it pins tool versions declaratively and provides named tasks as a stable entry point.

## What Changes

- `mise.toml` at the repository root pinning the required Python version and defining named tasks for each script entry point.
- Required environment variables (`GITHUB_TOKEN`) declared in `mise.toml` so `mise` surfaces missing config before a task runs.

## Capabilities

### New Capabilities

- `task-runner`: Run any script via `mise run <task>` without knowing the underlying path or interpreter.
- `env-setup`: Declare required env vars in `mise.toml`; `mise` fails fast with a clear message when they are absent.

### Modified Capabilities

## Impact

- New `mise.toml` at the repository root.
- `GITHUB_TOKEN` required for the `clone` task; documented in `mise.toml`.
- No changes to existing scripts — `mise` wraps them.
