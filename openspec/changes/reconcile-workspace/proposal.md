## Why

Reconcile (ROADMAP §2.2) has to move changes in both directions.
The template's bare mirror already carries the template outward to every mirror,
but there is nowhere to carry an improvement made in one mirror back into the template.

Pushing a promotion from the mirror does not solve it.
A push requires the mirror to decide in advance what is worth promoting,
and cherry-picking is the opposite of that:
it is browsing one repository's history from inside another,
which needs the source commits present as objects where the pick happens.

So the template needs a working copy that can reach every other repository's history.
Neither existing checkout can be that.
The template's mirror is re-baselined by `clone`, which resets it onto `origin/HEAD` and prunes its tags,
so in-flight work there is not safe.
And a git worktree of it shares its parent's config, refs and objects,
so wiring the other repositories into a worktree wires them into the mirror --
where their tags land in the mirror's `refs/tags/` and generic tooling sweeps the result.

## What Changes

- Add a **reconcile workspace**: a separate clone of the template at `reconcile/`, beside `mirrors/` rather than inside it,
  whose `origin` is the template's GitHub upstream and which carries one remote per non-template inventory entry.
- Name each remote `<org>/<repo>` and point it at the mirror checkout by relative path `../mirrors/<org>/<repo>`,
  so its branches land in `refs/remotes/<org>/<repo>/*` and repositories sharing a name across orgs stay distinct.
- Configure `tagOpt` on every one of those remotes,
  so no mirror's own upstream tags reach the workspace's `refs/tags/*`.
- Wire remotes without fetching by default, and fetch only when asked.
  A promotion reads one repository at a time; fetching all forty-seven eagerly copies history nobody has asked for yet.
- Reconcile stale remotes with the inventory on every run:
  add entries that appeared, rewrite URLs and `tagOpt` that drifted, remove remotes whose entry is gone.
- Never touch the workspace's working tree, index or `HEAD`.
  The task manages remotes and nothing else, so it is safe to run while a cherry-pick is in progress.
- Expose it as `mise run reconcile-workspace`, and ignore `/reconcile/` as `/mirrors/` already is.

## Capabilities

### New Capabilities
- `reconcile-workspace`: Create and maintain a separate clone of the template that can reach every other repository's history, so a change made in one mirror can be browsed and cherry-picked into the template.

### Modified Capabilities
- `task-runner`: the named-task requirement enumerates one scenario per script entry point, so it gains one for the new task.

## Impact

- **New script** `scripts/reconcile_workspace.sh` and a `mise` task named after it.
- **`scripts/lib.sh`**: the workspace's path and the remote-naming rule, beside the template helpers that are already there.
- **`.gitignore`**: `/reconcile/` alongside `/mirrors/`.
- **`mise.toml`**: one new named task.
- **`ROADMAP.md`**: §2.2 gains the inward direction, which is currently unrepresented.
- **No changes** to `clone.sh`, `sync.sh`, `repos.yml`, or any mirror.
  The workspace is additive: it reads the mirrors and is read by nobody.

## Out of Scope

- Deciding *what* to promote. This change provides the workspace a promotion happens in; the reconcile engine that finds candidates is ROADMAP §2.2 proper.
- Pushing the template's result anywhere. The workspace's `origin` is the template's GitHub upstream, so an ordinary `git push` reaches it; no tooling is added for that.
- Any change to the outward direction. The template's bare mirror and the `template` remotes are untouched.
- Sharing objects with the mirrors through `--reference` or alternates. Considered and rejected in `design.md`.
