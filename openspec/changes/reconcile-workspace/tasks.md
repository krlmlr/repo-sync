## 1. Shared helpers in `lib.sh`

- [ ] 1.1 Add `WORKSPACE_DIR` beside `MIRRORS_DIR`, resolving to `reconcile/` at the repository root;
          verify a child process spawned by the fan-out resolves the same path as its parent.
- [ ] 1.2 Add `workspace_remote_name` and `workspace_remote_url`, returning `<org>/<repo>` and `../mirrors/<org>/<repo>`;
          verify the URL resolves from the workspace root, from a subdirectory of it, and with an unrelated current directory.
- [ ] 1.3 Extend `load_inventory` usage so the workspace script reads the same `template_slug` and `other_slugs` as `clone` and `sync`,
          rejecting the same malformed inventory;
          verify an inventory with zero and with two `template: true` entries each exit non-zero before the workspace is touched.

## 2. `scripts/reconcile_workspace.sh`

- [ ] 2.1 Clone the template into `reconcile/` with `origin` on its GitHub upstream when the directory is absent,
          and do nothing to it when it is present;
          verify a second run neither re-clones nor modifies the existing clone.
- [ ] 2.2 Configure one remote per non-template entry,
          named for the slug with the relative URL, writing both the URL and `tagOpt` on every run;
          verify `git -C reconcile config --get-regexp 'remote\..*\.(url|tagOpt)'` lists every entry with the expected values
          after a run against a drifted workspace.
- [ ] 2.3 Skip the template entry; verify no remote named for the template's slug exists and that `origin` is the template's GitHub URL.
- [ ] 2.4 Remove remotes whose inventory entry is gone;
          verify the remote and its `refs/remotes/<org>/<repo>/*` are both gone after an entry is dropped from `repos.yml`.
- [ ] 2.5 Add an explicit opt-in that fetches every configured remote with pruning, off by default;
          verify a default run transfers no objects and that the opt-in run populates `refs/remotes/<org>/<repo>/*`.
- [ ] 2.6 Reuse `fail` and `report_failures` so one bad remote does not end the run;
          verify a run with one unconfigurable remote configures the rest and exits non-zero with a summary.
- [ ] 2.7 Verify the script never runs a command that writes the working tree, index or `HEAD` —
          no `checkout`, `switch`, `reset`, `pull`, `rebase` or `merge` appears in it.

## 3. The issue-reference guard

Depends on `no-foreign-issue-refs` having landed, which is what adds `hooks/prepare-commit-msg`.

- [ ] 3.1 Replace the hook's `refs/remotes/template/` provenance test with one that scans `refs/remotes/`
          and selects the remotes other than `origin` whose namespace contains the replayed commit;
          verify a commit reachable only from `origin` and a commit written locally
          both leave the hook exiting zero without touching the message.
- [ ] 3.2 Take the qualification slug from the selected remote's URL rather than from `template`;
          verify a mirror commit ending in `(#42)` becomes `(cynkra/dm#42)` in the workspace,
          and that a mirror's cherry-pick from the template still yields the template's slug.
- [ ] 3.3 Refuse when more than one non-`origin` remote contains the replayed commit;
          verify the diagnostic names the ambiguity and that the message file is left unmodified.
- [ ] 3.4 Reword the hook's diagnostics so they name the source repository rather than saying "copied from the template";
          verify the workspace's output reads correctly for a commit copied from a mirror.
- [ ] 3.5 Verify the outward direction is unchanged end to end:
          re-run the `no-foreign-issue-refs` fixture checks against the generalised hook and confirm all of them still pass.
- [ ] 3.6 Set `core.hooksPath` to `../hooks` in the workspace on every run, beside the remotes;
          verify the hook executes for a commit made at the workspace root and for one made from a subdirectory.

## 4. Wiring

- [ ] 4.1 Add the `reconcile-workspace` task to `mise.toml` with the prerequisites documented as the other tasks' are;
          verify `mise run reconcile-workspace` executes the script and `mise tasks` lists it.
- [ ] 4.2 Add `/reconcile/` to `.gitignore`; verify `git status` is clean after a run.

## 5. End-to-end verification

- [ ] 5.1 Build a local fixture — a template upstream, two mirrors each carrying their own upstream's tags — and run the task;
          verify the workspace's `refs/tags/` holds only the template's tags after fetching every remote.
- [ ] 5.2 Verify the template's mirror is unaffected: same remotes, same tags, no `refs/remotes/<org>/<repo>/*` in it.
- [ ] 5.3 Browse and cherry-pick a mirror's commit onto a branch started from the template's default branch, then push it to `origin`;
          verify it applies, the workspace's tags are unchanged, and the branch reaches the template's upstream in one hop.
- [ ] 5.4 Start a cherry-pick, stop it on a conflict, and re-run the task;
          verify the conflicted state, the uncommitted changes and the checked-out branch all survive.
- [ ] 5.5 Run `mise run clone` against the fixture; verify the workspace is untouched while the mirrors are re-baselined.
- [ ] 5.6 Run the task twice against an unchanged inventory; verify the second run changes nothing and exits zero.
- [ ] 5.7 Verify two inventory entries sharing a repository name across orgs get distinct remotes
          and distinct `refs/remotes/<org>/<repo>/*` namespaces.
- [ ] 5.8 Cherry-pick from a mirror a commit carrying `(#42)`, `GH-11` and a URL fragment;
          verify the two references are qualified against that mirror's slug, the URL is untouched, and the rewrites are reported.
- [ ] 5.9 Cherry-pick from a mirror a commit carrying `Fixes #7`;
          verify it is refused, `HEAD` does not move, the applied changes stay staged, and a corrected `git commit -m` completes the pick.
- [ ] 5.10 Verify `REPO_SYNC_TEMPLATE_REFS=block` refuses the suffix-only commit in the workspace.

## 6. Documentation

- [ ] 6.1 Add the inward direction to ROADMAP §2.2, naming the workspace and why it is neither a mirror nor a worktree;
          verify the section describes both directions.
- [ ] 6.2 Document the task's prerequisites in `mise.toml` alongside the existing ones,
          noting that it needs the mirrors on disk to fetch but not to configure;
          verify the comment matches what the script does.
- [ ] 6.3 Update the hook's header comment so it describes the direction-neutral rule rather than only the template's direction;
          verify it no longer reads as though the mirrors were the only destination.
- [ ] 6.4 Record under ROADMAP §2.2 that the guard runs in both directions; verify the section does not describe it as outward-only.
