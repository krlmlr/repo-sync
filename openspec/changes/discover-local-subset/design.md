## Context

repo-sync maintains an inventory (`repos.yml`) of foreign repos, one flagged
`template: true`. The existing `clone.sh` mirrors the *entire* inventory into
`mirrors/<org>/<repo>/` and wires a `template` remote on each non-template
mirror. Reconcile (ROADMAP §2.2) is the next step, but it needs to know which
repos are actually available to operate on.

In practice the available set is often a *subset*, and the layout is not always
`mirrors/`. In an active Claude Code session the relevant repos are checked out
as flat siblings of `repo-sync` (e.g. `/home/user/dm`, `/home/user/repo-sync`)
with no `<org>/` directory. Discovery must bridge both worlds and produce a
single, trustworthy subset for the reconcile engine to consume.

A second, smaller gap: repo-sync has no `AGENTS.md`, so an agent landing in the
repo has no map of its model (inventory/template), its layouts, its `mise`
tasks, or its OpenSpec workflow.

## Goals / Non-Goals

**Goals:**
- Discover the subset of `repos.yml` entries present locally under either the
  `mirrors/<org>/<repo>/` or flat-sibling layout.
- Confirm identity by resolving the `origin` remote, not by name alone.
- Identify the template within the subset.
- Be resilient: report extras and a missing template, still emit a valid subset.
- Emit a machine-readable subset (`org`, `repo`, path, template flag) for
  reconcile, exposed via a `mise` task.
- Add a repo-oriented `AGENTS.md`.

**Non-Goals:**
- Diffing, classifying, or pushing changes (the reconcile engine proper).
- Cloning or fetching — discovery is read-only over what already exists.
- A canonical, spreadable `AGENTS.md` for consumer repos.
- Mutating `repos.yml` or any discovered repo.

## Decisions

### Identity by basename + origin remote

A directory matches an inventory entry only when its basename equals `repo` AND
its git `origin` remote resolves to `<org>/<repo>`. Origin resolution normalizes
both SSH (`git@github.com:org/repo.git`) and HTTPS
(`https://github.com/org/repo(.git)`) forms to `<org>/<repo>`.

- *Why not basename only?* Repo names collide across orgs (e.g. `mlfit/mlfit`,
  several `igraph`/`r-dbi` names); basename alone is ambiguous and risks
  reconciling against the wrong upstream.
- *Why not path structure (`<org>/<repo>`) only?* The flat-sibling session
  layout has no `<org>/` directory, so a path rule would miss the primary case
  this change exists for.
- The `origin` check makes both layouts converge on the same identity.

### Read-only, report-and-continue

Discovery never aborts on a valid subset. Unmatched directories are reported as
extras; an absent template is a warning. Only a structurally invalid inventory
(not exactly one `template: true`) is a hard error, mirroring the existing
`clone`/`template-remote` specs so behavior is consistent across tools.

### Reuse the existing tooling shape

Discovery follows the established pattern: a script under `scripts/` plus a named
`mise` task alongside `fetch-inventory` and `clone`. Python is the natural fit
(reads `repos.yml`, already used by `fetch_inventory.py`), invoking `git` for
remote resolution. The base directory defaults to repo-sync's parent (so flat
siblings are found in a session) and is overridable for the `mirrors/` case.

### Output contract

Emit machine-readable records — `org`, `repo`, absolute `path`, `template`
(bool) — in deterministic order (sorted by `org` then `repo`, case-insensitive,
matching `persist-inventory`). This is the input the reconcile engine will read.

### AGENTS.md as documentation, not a spec

`AGENTS.md` has no testable runtime behavior, so it is a documentation task with
no spec delta. It will reference the discovery task and the inventory/template
model so it stays accurate to this change.

## Risks / Trade-offs

- **Origin URL formats vary** (SSH, HTTPS, trailing `.git`, casing) → normalize
  to lowercase `<org>/<repo>` before comparison; cover formats in tests.
- **Default base directory guess is wrong** in non-session contexts → make the
  base directory an explicit, overridable argument; document the default.
- **A repo with a detached/renamed origin** silently won't match → it is
  reported as an extra/unrecognized, surfacing the situation rather than hiding
  it.
- **Scope creep toward reconcile** → this change deliberately stops at emitting
  the subset; no diffing or writing.

## Migration Plan

Additive only. New script + new `mise` task + new `AGENTS.md`. No existing
script, spec, or `repos.yml` changes; nothing to roll back beyond removing the
new files.

## Open Questions

- Output format for the subset (JSON vs. YAML) — leaning JSON for easy
  downstream parsing; to confirm when the reconcile consumer is designed.
- Whether the default base directory should be repo-sync's parent or an explicit
  `--base`/env value with no default; current lean is "parent, overridable".
