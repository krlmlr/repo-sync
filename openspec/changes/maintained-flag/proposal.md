## Why

`repos.yml` mixes two kinds of entry.
Most are packages maintained by this repository's owner.
The rest are mirrored to contribute to or to follow, and are maintained by someone else.
Nothing in the inventory tells them apart,
so a tool that should act only on the maintained packages has no way to ask.

The distinction cannot be derived.
An `actions-sync` branch says only that a repository is synced.
CRAN's `Maintainer` field says nothing about a package that is not on CRAN, and several maintained packages never have been.
Like the template designation, it is curated by hand, and belongs next to it.

## What Changes

- **A `maintained: true` flag on inventory entries.**
  Any number of entries may carry it.
  An entry without it is not maintained here: the flag is absent rather than `false`, as `template` is.
- **Flag the maintained entries.**
  35 of the 45 entries carry it.
- **`scripts/fetch_inventory.py` preserves the flag across refreshes,** as it already preserves `template: true`.
  A flagged repository that has left the branch list is dropped with a note on stderr rather than refused.
- **Entry keys are written in a fixed order:** `org`, `repo`, then the flags.
  YAML's default alphabetical order would put `maintained` ahead of the name it qualifies.

## Capabilities

### Modified Capabilities

- `persist-inventory`: An entry may carry `maintained: true`.
  The writer preserves it across refreshes and writes each entry's keys in a fixed order.

## Impact

- **`repos.yml`**: 35 entries gain `maintained: true`.
- **`scripts/fetch_inventory.py`**: reads the existing inventory once, re-applies both flags, and writes keys in a fixed order.
  For an inventory without `maintained`, the output is byte-identical to before.
- **`scripts/lib.sh`, `clone.sh`, `sync.sh`**: nothing.
  They read `org`, `repo` and `template` and ignore any other key.
- **`ROADMAP.md`**: §1 records the flag.

## Out of Scope

- Any tool that acts on the flag.
  This change records it and nothing more.
- Keeping hand-removed entries out of a refresh.
  `actions-sync` still has branches for repositories removed from `repos.yml` by hand, and a refresh adds them back.
  That holds with or without this change.
