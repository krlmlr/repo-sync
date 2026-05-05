## 1. Inventory schema

- [x] 1.1 Add `template: true` to the `cynkra/cynkratemplate` entry in `repos.yml`

## 2. Inventory writer

- [x] 2.1 In `scripts/fetch_inventory.py`, read existing `repos.yml` (if present) and capture all `(org, repo)` tuples carrying `template: true`
- [x] 2.2 Re-apply the flag to matching entries in the freshly-built inventory before writing
- [x] 2.3 If a previously-flagged entry is missing from the new branch list, exit non-zero without overwriting `repos.yml`
- [x] 2.4 Reject existing `repos.yml` that carries `template: true` on more than one entry

## 3. Clone script

- [x] 3.1 In `scripts/clone.sh`, parse `repos.yml` for the unique `template: true` entry; fail fast on zero or multiple matches before processing any mirror
- [x] 3.2 Process the template entry first (clone or update), then iterate over the remaining entries
- [x] 3.3 After a successful clone or fetch on a non-template mirror, add or update a `template` remote pointing at the local relative path `../../<template-org>/<template-repo>` using `git remote add` / `git remote set-url`
- [x] 3.4 Skip the template-remote step on the template mirror itself
- [x] 3.5 Verify idempotency: a second consecutive run produces no change

## 4. Backfill and roadmap

- [ ] 4.1 Run `mise run clone` to backfill `template` remotes across already-cloned mirrors (deferred — `gh`/`mise` unavailable in sandbox; user to run locally)
- [x] 4.2 Mark the first bullet of `ROADMAP.md` §2.2 as done
