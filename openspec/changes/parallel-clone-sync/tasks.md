## 1. Fan-out machinery in `lib.sh`

- [x] 1.1 Add `JOBS`, defaulting to 8 and overridable with `REPO_SYNC_JOBS`
- [x] 1.2 Add `require_parallel`, rejecting both a missing `parallel` and moreutils' program of the same name
- [x] 1.3 Add `run_parallel`: one child per line of stdin, `--will-cite --halt never --jobs "$JOBS"`, blank lines dropped
- [x] 1.4 Add `SCRIPTS_DIR` so each script can name itself as the fan-out target
- [x] 1.5 Record why this is GNU parallel and not `xargs -P`

## 2. Failures across processes

- [x] 2.1 Create the failure log with `mktemp` at source time, export its path, and remove it on exit in the process that created it
- [x] 2.2 Rewrite `fail` to append one line to that file instead of to a shell array
- [x] 2.3 Rewrite `report_failures` to read the file, sort it, and keep the existing `FAILED (n): ...` output and non-zero exit
- [x] 2.4 Record why an array cannot work once the work is in child processes

## 3. Inventory as template plus the rest

- [x] 3.1 Have the `python3` snippet print the template slug once, then every non-template slug
- [x] 3.2 Replace `ordered_slugs` with `other_slugs`, and export `REPO_SYNC_TEMPLATE_SLUG` for the children
- [x] 3.3 Add `load_template_slug`, inheriting the designation and falling back to parsing the inventory
- [x] 3.4 Add `template_bare_usable`, derived from disk, replacing `sync`'s `bare_present` flag

## 4. Parallel `clone`

- [x] 4.1 Add `run_one` with the `--checkout` and `--bare` modes, and dispatch to it when the script is called with arguments
- [x] 4.2 Reject a wrong argument count and an unknown mode with a usage message and exit 2
- [x] 4.3 Run the template's checkout and bare mirror as one batch, side by side
- [x] 4.4 Run the rest of the inventory as a second batch, after the first has finished
- [x] 4.5 Leave `clone_or_update`, `clone_or_update_bare` and `configure_template_remote` unchanged

## 5. Parallel `sync`

- [x] 5.1 Add `run_one` taking one slug: skip if not cloned, then `pull_rebase` and `fetch_template`, both attempted
- [x] 5.2 Dispatch to it when the script is called with an argument, rejecting a wrong count
- [x] 5.3 Fetch the bare mirror in the parent, before the fan-out, reporting missing and non-bare separately
- [x] 5.4 Have `fetch_template` consult `template_bare_usable` rather than an inherited flag, and stay quiet about what the parent already reported
- [x] 5.5 Fan out over the template's checkout and every other mirror

## 6. Documentation

- [x] 6.1 Name GNU parallel as a prerequisite in `mise.toml`, beside the SSH one, and document `REPO_SYNC_JOBS`
- [x] 6.2 Update `ROADMAP.md` §2.0, §2.1 and §2.4 to record the concurrency and the new prerequisite

## 7. Verification

- [x] 7.1 `bash -n` and `shellcheck -x` clean on all three scripts
- [x] 7.2 A fresh `clone` produces the same `mirrors/` layout, the same `origin` and `template` remotes, and exits zero
- [x] 7.3 A second `clone` run changes nothing and exits zero
- [x] 7.4 `sync` fast-forwards, rebases unpushed local work rather than discarding it, and updates `template/*`
- [x] 7.5 Every mirror ends a `sync` run holding the template refs the upstream has, proving the bare fetch really is a barrier
- [x] 7.6 A failure raised in a child reaches the parent's report and makes the run exit non-zero
- [x] 7.7 Several failures in one run are all reported, in sorted order
- [x] 7.8 A missing bare mirror is reported once, the `template` fetches are skipped, and the mirrors are still rebased
- [x] 7.9 A non-bare directory at the bare path is reported by both tools and fetched into by neither
- [x] 7.10 An invalid template designation still exits before any mirror is touched
- [x] 7.11 `REPO_SYNC_JOBS=1` runs the same work in single file
- [x] 7.12 The child entry points work when run by hand, and reject bad arguments
- [x] 7.13 The failure log is removed when the run ends
- [x] 7.14 Measure the improvement over a real subset of the inventory
