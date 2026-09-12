## Why

Every commit the template collects names a pull request that only the template has.

GitHub writes the number when the merge button is pressed:
a squash merge takes the pull request's title as the subject
and appends `(#12)`,
and a body copied from the description brings `Fixes #7` with it.
In the template those references are right.
Cherry-picked into a mirror they are not inert —
`#12` in a commit pushed to a foreign repository
is a live reference to *that* repository's issue 12,
and GitHub posts a cross-reference on it,
once per mirror,
on forty-seven unrelated issues.
A closing keyword is worse: it closes them.

The template cannot fix this at its end.
No repository setting suppresses the `(#12)` suffix,
so the template's history carries these references
whatever anyone does upstream.
The moment to intervene is the one
where a commit is copied into a mirror.

## What Changes

- **Guard the copy with a `prepare-commit-msg` hook.**
  A new tracked `hooks/` directory holds one hook, shared by every mirror.
  It acts only on a commit that replays another one
  whose original is reachable from `refs/remotes/template/*`,
  so a commit written in a mirror keeps its own `#5`.
- **Repair what can be repaired, refuse what cannot.**
  `#12` and `GH-12` become `<template-org>/<template-repo>#12`,
  which points at the issue the message meant
  and links to it from anywhere.
  A reference under a closing keyword is refused instead:
  qualifying it would leave a dependent repository closing an issue in the template.
  `REPO_SYNC_TEMPLATE_REFS=block` refuses both.
- **Install it from both `clone` and `sync`.**
  Each sets `core.hooksPath` on every non-template mirror,
  next to the `template` remote's URL and its `tagOpt`,
  so a mirror made before the hook existed is repaired rather than re-cloned.

## Capabilities

### Added Capabilities

- `template-remote`: A commit copied from the template carries no reference that resolves against the mirror it lands in.

### Modified Capabilities

- `clone`: Every non-template mirror is pointed at this repository's `hooks/`.
- `sync`: The same, on the command that runs every day.
