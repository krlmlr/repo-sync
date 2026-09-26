## Context

`repos.yml` carries one piece of curated metadata today: `template: true`, on exactly one entry.
`scripts/fetch_inventory.py` rebuilds the inventory from `actions-sync`'s branch names
and re-applies that flag from the file it is about to overwrite.
This change adds a second flag, `maintained: true`, which any number of entries may carry.

## Goals / Non-Goals

**Goals:**

- Each entry says whether its package is maintained here.
- A refresh keeps the flag on every entry that is still in the branch list.
- An inventory that carries no `maintained` flag is written exactly as before.

**Non-Goals:**

- Deriving the flag from CRAN or GitHub.
- Changing what `clone` or `sync` do with any entry.

## Decisions

### A flag on the entry, not a separate list

A top-level `maintained:` list of slugs would work as well for reading.
It would also be a second list of names to keep in step with the first,
where a typo or a removed repository goes unnoticed.
A flag sits on the entry it describes and goes with it, which is how `template` already works.

### A missing flagged repository is dropped, not refused

The writer refuses to drop the template, because `clone` and `sync` cannot run without one
and the operator has to pick a replacement.
Nothing depends on any one entry being maintained.
The writer notes the dropped entries on stderr and writes the file,
and the diff the operator reviews before committing shows the entry going.

### Keys in a fixed order

`yaml.dump` sorts keys by default, which puts `maintained` ahead of `org`.
The writer lays each entry out as `org`, `repo`, `maintained`, `template` from one tuple, and dumps with `sort_keys=False`.
Without a `maintained` key the order is the one the sort already produced, so the output does not change.
The template flag is applied first so that its refusal is reported before any note about `maintained`.

## Risks / Trade-offs

- **The flag goes stale when maintainership changes** → it is curated by hand like the rest of `repos.yml`,
  and a change of maintainer is a one-line edit.
