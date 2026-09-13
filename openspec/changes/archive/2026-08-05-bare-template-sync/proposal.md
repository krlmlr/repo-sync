## Why

Every non-template mirror carries a `template` remote,
and today that remote points at the template's *checkout* — a repository with a branch checked out.
That is the wrong thing to have on the other end of the remote.
Git refuses a push to the checked-out branch of a non-bare repository (`receive.denyCurrentBranch`),
so the reconcile step of the roadmap (§2.3), which wants to publish curated changes back through the template,
would run into a wall the moment it pushes.
A working tree on the far end is also a moving target for a fetch:
whatever is staged, stashed, or half-rebased there is beside the point,
but it is still what the remote is made of.

There is a second, quieter gap.
The mirrors are kept in step by hand, with `s` (from `scriptlets`) sweeping a git command across them.
`s` is a wrapper around `h`, which finds repositories by their `.git` entry —
so a bare repository, whose `HEAD`, `config`, `objects` and `refs` sit at the top of the directory with no `.git` anywhere,
is invisible to that sweep.
A bare mirror added to `mirrors/` would be the one repository no sweep ever refreshes, going stale without saying so.

## What Changes

- **Mirror the template twice.**
  `scripts/clone.sh` clones the `template: true` entry both as a checkout at `mirrors/<org>/<repo>/`, as before,
  and as a bare `--mirror` clone at `mirrors/<org>/<repo>.git/` beside it.
- **Point the `template` remote at the bare mirror.**
  The URL every non-template mirror carries becomes `../../<template-org>/<template-repo>.git`.
  The checkout stays where it is, as the copy to read and reconcile against.
- **Add a `sync` task** that keeps the whole tree in step:
  fetch the bare mirror first, `git pull --rebase` in every mirror, then fetch `template` everywhere.
  The bare mirror goes first so the template refs the mirrors then fetch are the ones GitHub has, not the ones it had at the last clone;
  and it is in this task at all because `s` is structurally unable to reach it.
- **Extract `scripts/lib.sh`** so `clone` and `sync` read the inventory and resolve the template through the same code,
  rather than keeping two copies of the rule that exactly one entry may be flagged `template: true`.

## Capabilities

### New Capabilities

- `sync`: Bring every mirror back in step —
  refresh the template's bare mirror, rebase each mirror onto its own upstream,
  and fetch the `template` remote everywhere — isolating failures rather than ending the batch.

### Modified Capabilities

- `clone`: The template entry is mirrored twice, checkout and bare clone, and the `template` remote it wires up points at the bare one.
- `template-remote`: The `template` remote URL gains the `.git` suffix that names the bare mirror.
- `task-runner`: One more named task, `sync`.

## Impact

- **`scripts/clone.sh`** — clones and updates the template's bare mirror, and writes the new `template` remote URL.
- **`scripts/sync.sh`** — new.
- **`scripts/lib.sh`** — new; the inventory reader both scripts source.
- **`mise.toml`** — one new task, `sync`.
- **`ROADMAP.md`** — §2.2 and §2.4 record the bare mirror and the sync task.
- **Existing mirrors**: a `mise run clone` rewrites every `template` remote URL and creates the bare mirror; no manual migration.
- No new dependencies. `gh` clones the bare mirror as it clones the rest, so authentication is unchanged.

## Out of Scope

- Pushing anything to the bare mirror, or through it to GitHub (§2.3).
  This change makes the push possible; it does not make it.
- Bare mirrors for the non-template repos.
  Only the template is fetched *from* locally, so only it needs one.
- Teaching `s`/`h` to find bare repositories.
  A sweep over working trees is the right shape for what it does; the bare mirror is deliberately outside it, and `sync` covers it instead.
- Reconciling, diffing or classifying anything (§2.2 beyond the remote wiring).
