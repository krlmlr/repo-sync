## Context

The inventory change (`openspec/changes/inventory`) introduces `scripts/fetch_inventory.py` and `scripts/clone.sh`. These are the first two concrete entry points. `mise` wraps them so the task surface stays stable as scripts are added or renamed.

`mise` (https://mise.jdx.dev/) is a polyglot tool-version manager and task runner backed by a single `mise.toml` file. It is a drop-in replacement for `asdf` + `make`/`just` combined.

## Goals / Non-Goals

**Goals:**
- Pin the Python version so all contributors and CI use the same interpreter.
- Define tasks that map 1:1 to the scripts from the inventory change.
- Declare `GITHUB_TOKEN` as a required env var for the `clone` task.

**Non-Goals:**
- Managing Node, Ruby, or other runtimes (not needed yet).
- Replacing the scripts themselves — `mise` is a thin wrapper.
- Installing `mise` for contributors (documented in README; out of scope here).

## Decisions

### Task runner: mise over Makefile or just

**Decision**: Use `mise` tasks in `mise.toml`.

**Rationale**: `mise` already handles tool-version pinning; adding task running in the same file avoids a second tool. `Makefile` semantics (file targets, tab indentation) are a poor fit for script-running tasks with no build artifacts. `just` is another good option but adds a dependency that `mise` already subsumes.

**Alternative considered**: `Makefile`. Widely available but poorly suited to pure task running; no tool-version management.

### Tool pinning: Python only

**Decision**: Pin only Python in `mise.toml [tools]`; no other runtimes for now.

**Rationale**: All current scripts are Python or shell. Shell requires no pinning. Python version must match the project's `pyproject.toml` constraint.

### Env vars: `mise.toml [env]` with `GITHUB_TOKEN` as required

**Decision**: Declare `GITHUB_TOKEN` with an empty default and a description; let `mise` error if absent when the `clone` task runs.

**Rationale**: Makes the requirement explicit at the tool level rather than buried in script error messages. Contributors see the missing variable before any git operation starts.

## Risks / Trade-offs

- **`mise` not installed** → `mise run` fails. Mitigation: document installation in `CONTRIBUTING.md`; scripts remain directly executable as a fallback.
- **Version drift** → If the pinned Python version falls behind, it must be updated manually. Accepted; same trade-off as any lockfile.
