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

- [ ] Fetch the branch list from `krlmlr/actions-sync` (e.g. via
      `git ls-remote --heads` or the GitHub API).
- [ ] Parse each branch name into an `<org>/<repo>` tuple.
- [ ] Persist the resulting inventory in a machine-readable form
      (e.g. `repos.yml` or `repos.txt`) that downstream tooling can
      consume.
- [ ] Refresh the inventory on a schedule (cron / GitHub Actions) so
      new branches in `actions-sync` flow through automatically.

Open questions:

- Branch-name encoding: `<org>/<repo>` vs. `<org>-<repo>` vs. some
  other convention — confirm by inspecting `actions-sync` HEADs.
- Should archived or disabled repos be filtered out up front?

## 2. Tooling

A small toolkit that operates on the inventory from section 1.

### 2.0 Development environment

- [ ] Add `mise.toml` at the repository root, pinning the Python
      version required by the scripts.
- [ ] Define named `mise` tasks for each script entry point
      (`fetch-inventory`, `clone`, `validate`) so contributors run
      `mise run <task>` rather than invoking scripts directly.
- [ ] Document required environment variables (`GITHUB_TOKEN`) in
      `mise.toml` so `mise` surfaces missing config before a task runs.

### 2.1 Clone

- [ ] Clone every listed repository into a local `<org>/<repo>/`
      directory layout (mirroring GitHub's namespacing).
- [ ] Support incremental updates: if a clone already exists, fetch
      and fast-forward rather than re-cloning.
- [ ] Cache credentials / use a GitHub App token so the tool scales
      past the anonymous rate limit.

### 2.2 Reconcile

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

- [ ] Wire clone → reconcile → push into a single entry point
      (CLI or `Makefile` target).
- [ ] Run the whole pipeline from GitHub Actions on a schedule,
      surfacing failures per repo without aborting the batch.

## Out of scope (for now)

- Managing repository settings (branch protection, labels, etc.) —
  only file contents are reconciled.
- Hosting a public web UI for the reconciliation reports.
