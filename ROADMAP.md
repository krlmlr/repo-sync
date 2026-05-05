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
- [x] Named `mise` tasks: `fetch-inventory`, `clone`.
- [x] `gh` authentication documented as prerequisite for the `clone` task.

### 2.1 Clone

- [x] Clone every listed repository into a local `mirrors/<org>/<repo>/`
      directory layout via `gh repo clone`.
- [x] Support incremental updates: if a clone already exists, fetch
      and fast-forward rather than re-cloning (`scripts/clone.sh`).
- [x] Auth handled by `gh` — no token management needed.

### 2.2 Reconcile

- [x] One repository is picked as a template and defined as such in `repos.yml`.
      This repo is added as a `template` remote in all the others.
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

## Design Principles

### YAML Operations

**Prefer `yq` for YAML file operations over inline Python or PyYAML.**

Use Python only when the YAML is loaded into a structure that participates in non-trivial program logic. For reading, modifying, or writing YAML files at script boundaries, delegate to `yq`.

**Rationale:**
- `yq` is a specialized tool that makes YAML operations explicit and testable independently.
- Inline Python YAML parsing is harder to debug and less portable.
- This follows the Unix philosophy of composable tools.

**Example:**

Instead of:
```python
import yaml
with open('repos.yml') as f:
    data = yaml.safe_load(f)
    flagged = [e for e in data['repos'] if e.get('template') is True]
```

Use:
```bash
yq '.repos[] | select(.template == true) | [.org, .repo]' repos.yml
```

See `openspec/specs/yaml-operations/spec.md` for full requirements.

## Out of scope (for now)

- Managing repository settings (branch protection, labels, etc.) —
  only file contents are reconciled.
- Hosting a public web UI for the reconciliation reports.
