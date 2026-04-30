## Context

The inventory change (`openspec/changes/inventory`) introduces `scripts/fetch_inventory.py` and `scripts/clone.sh`. These are the first two concrete entry points. `mise` wraps them so the task surface stays stable as scripts are added or renamed.

`mise` (https://mise.jdx.dev/) is a polyglot tool-version manager and task runner backed by a single `mise.toml` file. It is a drop-in replacement for `asdf` + `make`/`just` combined.

## Goals / Non-Goals

**Goals:**
- Pin the Python version so all contributors and CI use the same interpreter.
- Define tasks that map 1:1 to the scripts from the inventory change.
- Document that `gh` must be authenticated as a prerequisite for the `clone` task.

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

### Env prereqs: document `gh` auth in `mise.toml`

**Decision**: Add a comment or `[env]` description in `mise.toml` noting that `gh` must be authenticated before running the `clone` task. No runtime check needed — `gh repo clone` fails with a clear message if unauthenticated.

**Rationale**: `gh` handles auth transparently via its own credential store; no token plumbing needed in the script or task runner. Documentation at the task level is sufficient.

## Risks / Trade-offs

- **`mise` not installed** → `mise run` fails. Mitigation: document installation in `CONTRIBUTING.md`; scripts remain directly executable as a fallback.
- **Version drift** → If the pinned Python version falls behind, it must be updated manually. Accepted; same trade-off as any lockfile.
