## 1. The guard

- [x] 1.1 Add `hooks/prepare-commit-msg`, acting only when a replay is in progress (`CHERRY_PICK_HEAD`, `REVERT_HEAD` or `REBASE_HEAD`)
          and the original is reachable from `refs/remotes/template/*`
- [x] 1.2 Read the template's `<org>/<repo>` from the `template` remote's URL, and refuse rather than guess when it cannot be read
- [x] 1.3 Rewrite `#<n>` and `GH-<n>` to `<org>/<repo>#<n>`, leaving qualified references, URLs, comment lines
          and anything past a scissors line alone
- [x] 1.4 Refuse a reference under a closing keyword, writing nothing, and name the offending lines
- [x] 1.5 Honour `REPO_SYNC_TEMPLATE_REFS=block` by refusing every reference
- [x] 1.6 Refuse with a diagnostic when `perl` is missing, rather than letting the commit through unchecked

## 2. Installation

- [x] 2.1 Add `hooks_path` and `configure_hooks_path` to `scripts/lib.sh`, skipping the template as `configure_template_remote` does
- [x] 2.2 Call it from `clone.sh`'s `--checkout` path, after the `template` remote is configured
- [x] 2.3 Call it from `sync.sh`'s per-mirror work, before the fetches, recording a failure without stopping the rest
- [x] 2.4 Record the failure as `config hooksPath <slug>`, as the sibling steps do

## 3. Verification

Against a fixture: three inventory repos served from local bare repositories, reached through `url.<path>.insteadOf git@github.com:`
so the scripts run unmodified.
The template carries one commit in each shape GitHub leaves — a `(#13)` suffix with `GH-11` and an issue URL in the body,
and a `(#12)` suffix with `Fixes #7`.

- [x] 3.1 A fresh `clone` leaves `core.hooksPath` set to `../../../hooks` in both non-template mirrors and unset in the template's checkout
- [x] 3.2 Cherry-picking the suffix-only commit rewrites `(#13)` and `GH-11` to the qualified form, reports both on stderr,
          and leaves the issue URL alone
- [x] 3.3 Cherry-picking the commit carrying `Fixes #7` is refused, HEAD does not move, the applied changes stay staged,
          and a `git commit -m` with the reference dropped completes the pick
- [x] 3.4 A commit written in a mirror, carrying `(#5)` and `Fixes #5`, is untouched
- [x] 3.5 A `sync` that rebases that commit onto its upstream leaves it unchanged, and does not re-qualify an already-qualified reference
- [x] 3.6 `REPO_SYNC_TEMPLATE_REFS=block` refuses the suffix-only commit, naming both references
- [x] 3.7 A mirror with `core.hooksPath` unset has it written by `sync` alone
- [x] 3.8 A second `clone` and a second `sync` change nothing and exit zero
- [x] 3.9 A commit made in the template's own checkout keeps its `(#14)`
- [x] 3.10 With `perl` off the path, the hook refuses and names `--no-verify` as the way past it
- [x] 3.11 `bash -n` on the hook and on all three scripts

## 4. Documentation

- [x] 4.1 Record under §2.2 of the roadmap that the mirrors carry a hook
          that keeps the template's issue numbers out of the commits copied from it
- [x] 4.2 Note perl among the prerequisites in `mise.toml`
