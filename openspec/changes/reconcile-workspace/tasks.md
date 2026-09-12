## 1. Shared helpers in `lib.sh`

- [ ] 1.1 Add `WORKSPACE_DIR` beside `MIRRORS_DIR`, resolving to `reconcile/` at the repository root; verify a child process spawned by the fan-out resolves the same path as its parent.
- [ ] 1.2 Add `workspace_remote_name` and `workspace_remote_url`, returning `<org>/<repo>` and `../mirrors/<org>/<repo>`; verify the URL resolves from the workspace root, from a subdirectory of it, and with an unrelated current directory.
- [ ] 1.3 Extend `load_inventory` usage so the workspace script reads the same `template_slug` and `other_slugs` as `clone` and `sync`, rejecting the same malformed inventory; verify an inventory with zero and with two `template: true` entries each exit non-zero before the workspace is touched.

## 2. `scripts/reconcile_workspace.sh`

- [ ] 2.1 Clone the template into `reconcile/` with `origin` on its GitHub upstream when the directory is absent, and do nothing to it when it is present; verify a second run neither re-clones nor modifies the existing clone.
- [ ] 2.2 Configure one remote per non-template entry, named for the slug with the relative URL, writing both the URL and `tagOpt` on every run; verify `git -C reconcile config --get-regexp 'remote\..*\.(url|tagOpt)'` lists every entry with the expected values after a run against a drifted workspace.
- [ ] 2.3 Skip the template entry; verify no remote named for the template's slug exists and that `origin` is the template's GitHub URL.
- [ ] 2.4 Remove remotes whose inventory entry is gone; verify the remote and its `refs/remotes/<org>/<repo>/*` are both gone after an entry is dropped from `repos.yml`.
- [ ] 2.5 Add an explicit opt-in that fetches every configured remote with pruning, off by default; verify a default run transfers no objects and that the opt-in run populates `refs/remotes/<org>/<repo>/*`.
- [ ] 2.6 Reuse `fail` and `report_failures` so one bad remote does not end the run; verify a run with one unconfigurable remote configures the rest and exits non-zero with a summary.
- [ ] 2.7 Verify the script never runs a command that writes the working tree, index or `HEAD` — no `checkout`, `switch`, `reset`, `pull`, `rebase` or `merge` appears in it.

## 3. Wiring

- [ ] 3.1 Add the `reconcile-workspace` task to `mise.toml` with the prerequisites documented as the other tasks' are; verify `mise run reconcile-workspace` executes the script and `mise tasks` lists it.
- [ ] 3.2 Add `/reconcile/` to `.gitignore`; verify `git status` is clean after a run.

## 4. End-to-end verification

- [ ] 4.1 Build a local fixture — a template upstream, two mirrors each carrying their own upstream's tags — and run the task; verify the workspace's `refs/tags/` holds only the template's tags after fetching every remote.
- [ ] 4.2 Verify the template's mirror is unaffected: same remotes, same tags, no `refs/remotes/<org>/<repo>/*` in it.
- [ ] 4.3 Browse and cherry-pick a mirror's commit onto a branch started from the template's default branch, then push it to `origin`; verify it applies, the workspace's tags are unchanged, and the branch reaches the template's upstream in one hop.
- [ ] 4.4 Start a cherry-pick, stop it on a conflict, and re-run the task; verify the conflicted state, the uncommitted changes and the checked-out branch all survive.
- [ ] 4.5 Run `mise run clone` against the fixture; verify the workspace is untouched while the mirrors are re-baselined.
- [ ] 4.6 Run the task twice against an unchanged inventory; verify the second run changes nothing and exits zero.
- [ ] 4.7 Verify two inventory entries sharing a repository name across orgs get distinct remotes and distinct `refs/remotes/<org>/<repo>/*` namespaces.

## 5. Documentation

- [ ] 5.1 Add the inward direction to ROADMAP §2.2, naming the workspace and why it is neither a mirror nor a worktree; verify the section describes both directions.
- [ ] 5.2 Document the task's prerequisites in `mise.toml` alongside the existing ones, noting that it needs the mirrors on disk to fetch but not to configure; verify the comment matches what the script does.
