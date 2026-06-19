## Why

The reconcile tooling (ROADMAP §2.2) needs to know which inventory repos it can
actually operate on. Today the tooling assumes a full `mirrors/<org>/<repo>/`
clone of the whole inventory, but real work often happens against a *subset*
that is already checked out — most notably an active session where a handful of
repos sit as flat siblings (e.g. `/home/user/dm`, `/home/user/cynkratemplate`)
with no `<org>/` directory. There is no way to discover that subset or to
identify the template among it. Separately, repo-sync has `openspec/`,
`.claude/`, `scripts/`, and `mise.toml` but no `AGENTS.md`, so an agent working
in the repo has no orientation to its model and workflow.

## What Changes

- Add a **local-subset discovery** capability: scan a base directory for repos
  that match `repos.yml`, supporting both the `mirrors/<org>/<repo>/` layout and
  a flat-sibling layout (siblings of `repo-sync`, no org directory).
- Match a candidate directory to an inventory entry only when its basename
  equals the `repo` field **and** its git `origin` remote resolves to
  `<org>/<repo>`, disambiguating repos that share a name across orgs.
- Identify the `template: true` repo within the discovered subset so reconcile
  can use it as the canonical source.
- Be resilient: report sibling directories not present in `repos.yml` and warn
  when the template sibling is absent, but still emit the valid subset and exit
  zero.
- Emit the discovered subset (org/repo, local path, template flag) for
  downstream reconcile consumption.
- Expose discovery as a `mise` task, consistent with the existing
  `fetch-inventory` and `clone` tasks.
- Add **repo-sync's own `AGENTS.md`** (a documentation deliverable, not a
  templated/spread file) orienting agents to the repo: its purpose, the
  inventory/template model, the mirror-vs-sibling layouts and this discovery
  capability, the `mise run` tasks, and the OpenSpec workflow.

## Capabilities

### New Capabilities
- `discover-local`: Discover the subset of `repos.yml` entries that are checked
  out locally (mirrors or flat siblings), verify identity via the `origin`
  remote, identify the template, and emit the subset for reconcile while
  reporting unrecognized or missing entries.

### Modified Capabilities
<!-- None: existing clone/template-remote/task-runner specs are unchanged; discovery is additive. -->

## Impact

- **New script**: a discovery entry point under `scripts/` (e.g.
  `discover_local.py` / `.sh`) and a corresponding `mise` task.
- **`mise.toml`**: one new named task (per the `task-runner` spec convention).
- **New file `AGENTS.md`** at the repo root. Documentation only; no behavior
  change and no separate spec.
- **No changes** to `repos.yml`, `clone.sh`, or the existing specs.
- Downstream: provides the input contract the future reconcile engine will
  consume; this change stops at discovery and does not diff, classify, or push.

## Out of Scope

- Centralizing a canonical `AGENTS.md` into `cynkratemplate` and spreading it to
  consumer repos (the broader unification goal).
- The reconcile/diff/classify/push engine itself (ROADMAP §2.2–2.4 beyond
  discovery).
- Reconciling the existing divergent `AGENTS.md` lineages across consumers
  (cynkra-style in `dm`/`rigraph` vs. copilot-style in `duckdb-r`).
