# AGENTS.md

Orientation for agents working **in** the `repo-sync` repository.

> This file documents `repo-sync` itself. It is **not** a templated file that
> gets spread to the mirrored repos.

## What this repo is for

`repo-sync` maintains a local mirror of a set of "foreign" GitHub repositories,
reconciles their divergences against a single template repository, and pushes
curated changes back to them. The high-level plan lives in `ROADMAP.md`;
concrete changes are specified and implemented through OpenSpec under
`openspec/`.

## The inventory and template model

- The set of foreign repos is defined by the branch names in
  [`krlmlr/actions-sync`](https://github.com/krlmlr/actions-sync) — each branch
  encodes one `<org>/<repo>` pair.
- That set is persisted as **`repos.yml`** (one `org`/`repo` entry per repo).
  Refreshes are manual: regenerate, review the diff, commit.
- Exactly **one** entry is flagged `template: true` (currently
  `cynkra/cynkratemplate`). It is the canonical source the others are
  reconciled against; the tooling treats "not exactly one template" as a hard
  error.

## Layouts

The same repo can be present locally in either layout, and the tooling supports
both:

- **Mirrors** — `mirrors/<org>/<repo>/`, as produced by the `clone` task. Each
  non-template mirror also gets a `template` git remote pointing at the template
  mirror.
- **Flat siblings** — `<repo>/` directories sitting next to `repo-sync` with no
  `<org>/` directory (e.g. an active Claude Code session:
  `/home/user/dm`, `/home/user/cynkratemplate`, `/home/user/repo-sync`, …).

### Discovering the local subset

Work often happens against a *subset* of the inventory that is already checked
out. The `discover` task scans a base directory and reports which `repos.yml`
entries are present, in either layout. A directory matches an inventory entry
only when its basename equals the entry's `repo` **and** its git `origin` remote
resolves to `<org>/<repo>` (so repos that share a name across orgs are
disambiguated by their origin). It is read-only and report-and-continue:
unrecognized directories and a template that is not checked out locally are
reported, but a valid subset is still emitted (as JSON: `org`, `repo`, absolute
`path`, `template` flag) for the downstream reconcile engine.

## Tasks (`mise run <task>`)

| Task | What it does |
|------|--------------|
| `install` | Install Python dependencies (`requirements.txt`). |
| `fetch-inventory` | Fetch the branch list from `krlmlr/actions-sync` and write `repos.yml`. |
| `clone` | Clone/update every `repos.yml` repo into `mirrors/<org>/<repo>/` and wire the `template` remote. Requires `gh` to be authenticated. |
| `discover` | Discover which `repos.yml` repos are checked out locally (flat siblings or mirrors). Override the scan root with `mise run discover -- --base <dir>` (default: `repo-sync`'s parent). |

`mise.toml` pins Python 3.11; the scripts live under `scripts/`.

## OpenSpec workflow

Changes are planned and tracked with OpenSpec (`openspec/`):

- **explore** — think through the problem and clarify requirements.
- **propose** — create a change under `openspec/changes/<name>/` with
  `proposal.md`, `design.md`, `specs/<capability>/spec.md`, and `tasks.md`.
- **apply** — implement the tasks, checking them off as you go.
- **archive** — once implemented, fold the deltas into `openspec/specs/` and
  move the change into `openspec/changes/archive/`.

Spec files use `SHALL`/`MUST` requirements with `#### Scenario:` blocks
(`WHEN`/`THEN`). Run `openspec validate "<change>"` before considering a change
done.
