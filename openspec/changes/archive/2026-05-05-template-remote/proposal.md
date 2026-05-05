## Why

Reconciliation (roadmap §2.2) compares each foreign repo against a canonical template. Without a designated template repo and a uniform way to access it from every mirror, downstream tooling has nothing to diff against. Marking the template in `repos.yml` and wiring a `template` git remote into every other mirror gives reconcile a single, predictable source of truth.

## What Changes

- Pick `cynkra/cynkratemplate` as the canonical template (name signals intent; already in inventory).
- Extend `repos.yml` schema: the template repo's entry gains `template: true`. Exactly one entry must carry this flag.
- `scripts/clone.sh` (after a successful clone or fetch) configures a `template` remote on every non-template mirror, pointing at the **local mirror path** of the template repo (`../../<template-org>/<template-repo>` relative to each mirror's git dir). On the template mirror itself no `template` remote is added.
- The `template` remote URL is normalised on every run so a change of template entry gets corrected idempotently.
- `scripts/fetch_inventory.py` preserves the `template: true` flag across refreshes (the flag is metadata maintained by humans, not derived from `actions-sync` branches).

## Capabilities

### New Capabilities

- `template-remote`: Designate one inventory entry as the template and ensure every other mirror has a `template` git remote pointing at it.

### Modified Capabilities

- `persist-inventory`: `repos.yml` may carry a `template: true` boolean on exactly one entry; the writer must preserve it when refreshing inventory from upstream branches.
- `clone`: After clone/update, the script configures the `template` remote on non-template mirrors.

## Impact

- `repos.yml` — one entry gains `template: true`.
- `scripts/clone.sh` — adds the template-remote configuration step.
- `scripts/fetch_inventory.py` — must merge the flag from the existing file rather than overwriting.
- `ROADMAP.md` — first bullet under §2.2 marked done.
- No new dependencies; uses `git remote` and existing `gh` auth.
