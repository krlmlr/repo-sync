## 1. Shared inventory reader

- [x] 1.1 Add `scripts/lib.sh`, sourced and not executable, holding `REPO_ROOT`, `REPOS_YML` and `MIRRORS_DIR`
- [x] 1.2 Move the `repos.yml` reader and the exactly-one-`template: true` rule into `load_inventory`, setting `template_slug` and `ordered_slugs` with the template first
- [x] 1.3 Add `template_checkout_dir`, `template_bare_dir` and `template_remote_url` so both scripts spell the paths the same way
- [x] 1.4 Move the failure list, `fail` and `report_failures` there, keeping `clone`'s reporting behaviour unchanged
- [x] 1.5 Rewrite `scripts/clone.sh` to source it, with no change to what it does for non-template mirrors

## 2. Bare mirror of the template

- [x] 2.1 In `scripts/clone.sh`, clone the `template: true` entry a second time as `mirrors/<org>/<repo>.git` with `gh repo clone ... -- --mirror`
- [x] 2.2 Update an existing bare mirror with `git fetch --prune` rather than re-cloning
- [x] 2.3 Fail, rather than fetch, when the bare path holds something that is not a bare repository
- [x] 2.4 Create or update both mirrors of the template before any non-template entry, attempting each independently

## 3. `template` remote points at the bare mirror

- [x] 3.1 Change the `template` remote URL to `../../<template-org>/<template-repo>.git`
- [x] 3.2 Confirm the existing normalisation rewrites mirrors that still carry the old checkout URL
- [x] 3.3 Verify a relative remote URL resolves from the top of the working tree, including when git is run from a subdirectory

## 4. Sync task

- [x] 4.1 Add `scripts/sync.sh`: fetch the bare mirror, `git pull --rebase` every mirror, fetch `template` in every non-template mirror
- [x] 4.2 Fetch the bare mirror first, so the `template` refs the mirrors receive are the upstream's
- [x] 4.3 Skip mirrors that are not cloned without failing the run
- [x] 4.4 Record a failure, naming `mise run clone`, for a mirror that exists without a `template` remote, and for a missing or non-bare template mirror
- [x] 4.5 Fetch `template` even when a mirror's rebase failed
- [x] 4.6 Collect failures and report them at the end with a non-zero exit, as `clone` does
- [x] 4.7 Add the `sync` task to `mise.toml`, depending on `install` as `fetch-inventory` does

## 5. Verification

- [x] 5.1 Fresh clone against a fixture: both mirrors of the template exist, one bare and one not, and every `template` remote points at the bare one
- [x] 5.2 A second `clone` run changes nothing and exits zero
- [x] 5.3 A sweep that discovers repositories by their `.git` entry finds the checkouts and not the bare mirror
- [x] 5.4 After an upstream commit on the template, `sync` advances the bare mirror and every mirror's `template/*` refs
- [x] 5.5 A mirror carrying an unpushed local commit keeps it across `sync`, rebased onto the new upstream tip
- [x] 5.6 A push to the `template` remote is accepted, and the same push against the checkout is refused by `receive.denyCurrentBranch`
- [x] 5.7 `sync` skips a mirror that is not cloned, and exits non-zero for a missing `template` remote, a missing bare mirror, and an inventory with no `template: true`

## 6. Roadmap

- [x] 6.1 Record the bare mirror under §2.2 and the sync task under §2.4 of `ROADMAP.md`
