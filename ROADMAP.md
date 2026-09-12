# Roadmap

This repository's purpose is to maintain a local mirror of a set of
"foreign" GitHub repositories, reconcile divergences against upstream,
and push curated changes back to them.

The roadmap is tracked at a high level here. Concrete changes are
specified and implemented through OpenSpec (`openspec/changes/`).

## 1. Foreign repository inventory

The set of foreign repositories is defined by the branch names in
[`krlmlr/actions-sync`](https://github.com/krlmlr/actions-sync).
Each branch in that repository encodes one `<org>/<repo>` pair.

Tasks:

- [x] Fetch the branch list from `krlmlr/actions-sync` via
      `git ls-remote --heads`.
- [x] Parse each branch name into an `<org>/<repo>` tuple.
- [x] Persist the resulting inventory as `repos.yml` (59 repos across
      15 orgs). Refreshes are manual: run `scripts/fetch_inventory.py`,
      review the diff, commit.

## 2. Tooling

A small toolkit that operates on the inventory from section 1.

### 2.0 Development environment

- [x] `mise.toml` at the repository root, pinning Python 3.11.
- [x] Named `mise` tasks: `fetch-inventory`, `clone`, `sync`.
- [x] SSH access to GitHub documented as prerequisite for the `clone` task.
- [x] GNU parallel documented as prerequisite for `clone` and `sync`, which
      mirror several repositories at a time. `REPO_SYNC_JOBS` chooses how many
      (default 8); `REPO_SYNC_JOBS=1` reduces a run to one at a time.

### 2.1 Clone

- [x] Clone every listed repository into a local `mirrors/<org>/<repo>/`
      directory layout via `git clone` over SSH.
- [x] Support incremental updates: if a clone already exists, fetch
      and fast-forward rather than re-cloning (`scripts/clone.sh`).
- [x] Auth handled by SSH — no token management needed, and no `gh`. The
      GitHub API is not touched, so a run cannot be stopped by a spent rate
      limit.
- [x] Mirror several repositories at a time. Each clone is an independent
      conversation with GitHub that spends its time waiting, so running them
      one after another costs the sum of the waits for no reason. The
      template's two mirrors are made first, as a barrier, so every
      `template` remote written afterwards names a path that resolves.

### 2.2 Reconcile

- [x] One repository is picked as a template and defined as such in `repos.yml`.
      It is mirrored twice: as a checkout, to read and reconcile against, and
      as a bare clone at `mirrors/<org>/<repo>.git`. The bare one is added as a
      `template` remote in all the others, so that remote can be pushed to
      (§2.3) and not only fetched from.
- [x] That remote carries branches and not tags. Tags are the one ref namespace
      git does not partition by remote, so the template's would land among each
      mirror's own, be indistinguishable from them, and eventually be pushed
      back to the wrong repository (§2.3).
- [x] The mirrors carry a `prepare-commit-msg` hook, shared from `hooks/` and
      installed by both `clone` and `sync`, that keeps the template's issue
      numbers out of the commits copied from it. GitHub writes the number of
      the pull request into the subject of every squash merge, and `#12` in a
      foreign repository is a live reference to *that* repository's issue 12.
      The hook qualifies it — `<org>/<repo>#12` — and refuses the copy outright
      where a closing keyword would have a dependent repository close an issue
      in the template.
- [ ] For each foreign repo, diff the working tree against a
      canonical template / set of patches maintained in this repo.
- [ ] Classify divergences: clean (can auto-apply), conflicting
      (needs human review), or intentional (skip).
- [ ] Emit a report per repo and an aggregate summary across the
      inventory.

### 2.3 Commit & push

- [ ] Apply reconciled changes as commits directly on a dedicated
      branch in each foreign repo (e.g. `repo-sync/<topic>`).
- [ ] Push via HTTPS with a bot token; optionally open a PR instead
      of pushing straight to the default branch.
- [ ] Make pushes idempotent — re-running on an already-synced repo
      should be a no-op.
- [ ] Dry-run mode that prints the diff without writing anywhere.

### 2.4 Orchestration

- [x] `mise run sync` keeps the whole tree in step: fetch the template's
      bare mirror, `git pull --rebase` every mirror, fetch `template`
      everywhere. The bare mirror has no `.git` entry, so no sweep over
      working trees (`s`, `h`) ever reaches it; this task is what does.
      The bare fetch is a barrier and the mirrors follow it several at a
      time, since each one reads only its own upstream and that mirror.
- [ ] Wire clone → reconcile → push into a single entry point
      (CLI or `mise` task — the toolkit is `mise`, not `make`).
- [ ] Run the whole pipeline from GitHub Actions on a schedule,
      surfacing failures per repo without aborting the batch.

## Out of scope (for now)

- Managing repository settings (branch protection, labels, etc.) —
  only file contents are reconciled.
- Hosting a public web UI for the reconciliation reports.
