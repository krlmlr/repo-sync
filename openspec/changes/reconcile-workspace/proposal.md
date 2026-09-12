## Why

Reconcile (ROADMAP §2.2) has to move changes in both directions.
The template's bare mirror already carries the template outward to every mirror,
but there is nowhere to carry an improvement made in one mirror back into the template.

Pushing a promotion from the mirror does not solve it.
A push requires the mirror to decide in advance what is worth promoting,
and cherry-picking is the opposite of that:
it is browsing one repository's history from inside another,
which needs the source commits present as objects
where the pick happens.

So the template needs a working copy that can reach every other repository's history.
Neither existing checkout can be that.
The template's mirror is re-baselined by `clone`,
which resets it onto `origin/HEAD` and prunes its tags,
so in-flight work there is not safe.
And a git worktree of it shares its parent's config, refs and objects,
so wiring the other repositories into a worktree wires them into the mirror --
where their tags land in the mirror's `refs/tags/` and generic tooling sweeps the result.

## What Changes

- Add a **reconcile workspace**:
  a separate clone of the template at `reconcile/`,
  beside `mirrors/` rather than inside it,
  whose `origin` is the template's GitHub upstream
  and which carries one remote per non-template inventory entry.
- Name each remote `<org>/<repo>` and point it at the mirror checkout by relative path `../mirrors/<org>/<repo>`,
  so its branches land in `refs/remotes/<org>/<repo>/*`
  and repositories sharing a name across orgs stay distinct.
- Configure `tagOpt` on every one of those remotes,
  so no mirror's own upstream tags reach the workspace's `refs/tags/*`.
- Wire remotes without fetching by default,
  and fetch only when asked.
  A promotion reads one repository at a time;
  fetching all forty-seven eagerly copies history nobody has asked for yet.
- Reconcile stale remotes with the inventory on every run:
  add entries that appeared,
  rewrite URLs and `tagOpt` that drifted,
  remove remotes whose entry is gone.
- Never touch the workspace's working tree, index or `HEAD`.
  The task manages remotes and nothing else,
  so it is safe to run while a cherry-pick is in progress.
- Expose it as `mise run reconcile-workspace`,
  and ignore `/reconcile/` as `/mirrors/` already is.
- **Guard the copy in the direction this workspace creates.**
  Point the workspace at the shared `hooks/` directory with `core.hooksPath`,
  and extend the hook `no-foreign-issue-refs` installs on the mirrors
  so it qualifies a reference against the mirror the commit came *from*
  rather than against the template it is going *to*.

## The guard runs in both directions or neither

`no-foreign-issue-refs` keeps the template's issue numbers out of the mirrors:
GitHub writes `(#12)` into the subject of every squash merge,
and cherry-picked into a mirror that number addresses a stranger's issue.

This change creates the copy that runs the other way,
and the hazard is symmetrical.
A commit collected by `cynkra/dm` ends in `(#42)` and may carry `Fixes #7`.
Cherry-picked into the workspace -- a clone of the template --
`#42` addresses the template's issue 42,
and `Fixes #7` closes the template's issue 7 on push.

That hook does not cover it.
It fires only on a commit reachable from `refs/remotes/template/*`,
which a commit coming from a mirror is not.
Run unmodified in a workspace,
it lets `(#42)` and `Fixes #7` through untouched.

The rule generalises rather than needing a second implementation:
qualify against the slug of the remote-tracking namespace the replayed commit came from,
whichever remote that is,
and leave `origin` alone --
in a mirror `origin` is its own upstream,
in the workspace it is the template,
and in both cases a commit from there already refers to the right repository.
Stated that way,
the existing behaviour is the case where that remote is `template`.

## Capabilities

### New Capabilities
- `reconcile-workspace`: Create and maintain a separate clone of the template that can reach every other repository's history,
  so a change made in one mirror can be browsed and cherry-picked into the template.

### Modified Capabilities
- `task-runner`: the named-task requirement enumerates one scenario per script entry point,
  so it gains one for the new task.

## Impact

- **New script** `scripts/reconcile_workspace.sh` and a `mise` task named after it.
- **`scripts/lib.sh`**: the workspace's path and the remote-naming rule,
  beside the template helpers that are already there.
- **`.gitignore`**: `/reconcile/` alongside `/mirrors/`.
- **`mise.toml`**: one new named task.
- **`ROADMAP.md`**: §2.2 gains the inward direction,
  which is currently unrepresented.
- **`hooks/prepare-commit-msg`**: its provenance test generalised from `refs/remotes/template/*`
  to any non-`origin` remote-tracking namespace,
  and its qualification slug taken from that remote.
  The file is added by `no-foreign-issue-refs`,
  so that change lands first
  and this one edits the hook rather than creating it.
- **No changes** to `clone.sh`, `sync.sh`, `repos.yml`, or any mirror.
  Apart from the shared hook,
  the workspace is additive:
  it reads the mirrors and is read by nobody.

## Out of Scope

- Deciding *what* to promote.
  This change provides the workspace a promotion happens in;
  the reconcile engine that finds candidates is ROADMAP §2.2 proper.
- Pushing the template's result anywhere.
  The workspace's `origin` is the template's GitHub upstream,
  so an ordinary `git push` reaches it;
  no tooling is added for that.
- Any change to the outward direction.
  The template's bare mirror and the `template` remotes are untouched,
  and the outward guard's observable behaviour on a mirror is unchanged:
  `template` is a non-`origin` remote,
  so the generalised rule selects it exactly as the current one does.
- Sharing objects with the mirrors through `--reference` or alternates.
  Considered and rejected in `design.md`.
