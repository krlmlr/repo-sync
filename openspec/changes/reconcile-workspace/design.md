## Context

See `proposal.md` — Why.

As in `tagless-template-bare`, the mechanics below were verified against git 2.55 on a local fixture
rather than reasoned about from the documentation.
Two of them ruled options out rather than confirming them, and are recorded for that reason.

The relevant existing shape: `scripts/lib.sh` already holds the inventory parsing, the template designation,
the relative-URL convention and the failure collection that both `clone` and `sync` use,
and `clone` re-baselines every mirror with `git reset --hard origin/HEAD` and `git fetch --prune --prune-tags`.

## Goals / Non-Goals

**Goals:**

- A place where a commit from any mirror can be cherry-picked into the template using ordinary git.
- No tag from any mirror in that place, and no change to any mirror.
- Work in progress that survives `mise run clone`.
- Remotes reconciled with the inventory on every run, like every other configuration this project writes.

**Non-Goals:**

- Choosing what to promote, or applying anything automatically. The workspace is where a human or a later engine works.
- Sharing object storage with the mirrors.
- Any change to the outward direction. `tagless-template-bare` owns that, and the two do not touch.

## Decisions

### A separate clone, not a worktree

A git worktree was the obvious candidate and is wrong.
Remotes are per-repository, not per-worktree:
`git config` is shared across every worktree of a repository, as are its refs and its object database.
On the fixture, adding a remote inside a worktree of the template's checkout made that remote appear in the checkout itself,
and a single fetch put `dm-v1.0.0` and `dm-v2.0.0` into the checkout's `refs/tags/`.
That is the outward guarantee broken from the other side, in the one repository every mirror reads.

`extensions.worktreeConfig` does not rescue it: it scopes a small fixed set of settings, not remotes.

A second reason stands on its own.
`clone.sh` resets every mirror with `git reset --hard origin/HEAD`.
A cherry-pick stopped on a conflict, or a half-built promotion branch, would not survive a routine `mise run clone`.
Anything under `mirrors/` is re-baselinable by definition, so the workspace lives beside it.

*Alternative considered:* put the per-entry remotes on the template's mirror directly and skip the workspace.
Rejected for both reasons above — it is the worktree case without the worktree.

### Remotes named `<org>/<repo>`

A remote name may contain a slash.
The fixture confirmed `git remote add cynkra/dm ...` works, that its branches land at `refs/remotes/cynkra/dm/main`,
and that `git rev-parse cynkra/dm/main` resolves.

Naming remotes for the repository alone would be shorter and is unsafe:
repository names are not unique across orgs,
and the failure mode is a cherry-pick from a repository that merely shares a name with the intended one.
The slug is what `repos.yml` already keys on,
and `refs/remotes/<org>/<repo>/*` keeps two same-named entries apart with no further rule.

### Relative URLs, `../mirrors/<org>/<repo>`

Git resolves a relative remote URL from the top of the working tree,
which is the convention `lib.sh` already documents for the `template` remote.
From `reconcile/`, `../mirrors/<org>/<repo>` reaches the mirror,
and the fixture confirmed it resolves from a subdirectory of the workspace and from any current directory.

So the tree can be moved or copied without rewriting forty-seven URLs.

### Per-remote `tagOpt`, and why that is not a regression

`tagless-template-bare` removes per-mirror tag configuration on the grounds that it is unenforceable.
This change adds per-remote tag configuration. The difference is where it lives, and it is the whole difference.

What made the old arrangement fail was replication across forty-seven *repositories*:
`clone` wrote the setting, `sync` ran daily, and a repository the former had not reached kept importing tags —
with no single command that could check them all.
Here every remote is in one repository, so the configuration is one file:
`git -C reconcile config --get-regexp 'remote\..*\.tagOpt'` reports all of them,
and one pass repairs all of them.

There is also no alternative.
The outward direction could be made structural because nothing wanted the template's tags,
so the far end could be emptied.
Here every mirror must keep its own upstream's tags, so there is no far end to empty.
Suppression on the remote is the only mechanism, and this is the shape in which it is sound.

The setting is written on every run rather than at creation, for the same reason the URL is.

### Wire by default, fetch on request

Configuring a remote writes two config lines and transfers nothing.
Fetching all forty-seven copies every repository's history into a second place on disk
before anyone has said which one they are promoting from.
Since a promotion reads one repository at a time,
the default run wires and does not fetch, and fetching is asked for explicitly.

This also keeps the default run fast enough to be re-run freely,
which is what makes "reconcile the remotes with the inventory on every run" a reasonable rule.

*Alternative considered:* a partial clone (`--filter=blob:none`) to make eager fetching cheap.
Not pursued — the local transport makes filtering unreliable, and lazy fetching already solves it without a new concept.

### Object storage is not shared

`git clone --reference` or an `objects/info/alternates` entry per mirror would avoid duplicating history.
Both make the workspace depend on objects it does not own,
and a `git gc` in a mirror can prune an object the workspace still needs —
the classic alternates hazard, made likelier here because `clone` re-baselines the mirrors routinely.

For forty-eight R packages the duplication is not worth that failure mode,
and lazy fetching means only the repositories actually promoted from are ever duplicated.

### The working tree is never touched, and that is a requirement

Every other tool in this project is free to re-baseline what it manages.
This one is not, and the distinction is easy to erode later —
a plausible-looking `git checkout` added to "make the run deterministic" would quietly eat a conflicted cherry-pick.
So it is stated as a requirement with its own scenarios rather than left as an implementation habit.

### `origin` is the template's GitHub upstream

The workspace clones the template from GitHub, as the template's own mirror does.
A promotion is then pushed with an ordinary `git push origin <branch>`, verified on the fixture to reach the upstream in one hop.

Pointing `origin` at the template's bare mirror instead would make the push two hops,
which is the same trade `tagless-template-bare` already settled the same way for the template's checkout.
Adding the bare mirror as a second remote here would be harmless and buys nothing this change needs; it is not done.

### The issue-reference guard has to run here too, and the rule generalises

`no-foreign-issue-refs` guards the outward copy: a commit collected by the template ends in `(#12)`,
which addresses a stranger's issue once cherry-picked into a mirror.
This change creates the copy that runs the other way, and the hazard is the same one reflected.
A commit collected by `cynkra/dm` ends in `(#42)` and may carry `Fixes #7`;
the workspace is a clone of the template, so here those address the *template's* issues,
and the closing keyword closes one on push.

That hook does not already cover it, which was checked rather than assumed.
Its provenance test is `git for-each-ref --contains <original> refs/remotes/template/`,
and a commit coming from a mirror is reachable from `refs/remotes/<org>/<repo>/*` instead.
Run unmodified in a workspace on the fixture,
it let a commit through carrying both `(#42)` and `Fixes #7` untouched.

The fix is not a second hook.
The rule the existing one implements is a special case of a direction-neutral one:

> qualify against the slug of the remote-tracking namespace the replayed commit came from,
> for any remote other than `origin`.

`origin` is excluded in both directions for the same reason:
in a mirror it is that mirror's own upstream, in the workspace it is the template,
and a commit reachable from it already refers to the repository it is in.
Every other remote is a foreign repository whose numbers do not mean here what they meant there.
With the rule stated that way, the mirrors' behaviour is unchanged --
`template` is a non-`origin` remote, so it is selected exactly as before --
and the workspace is covered by the same code.

This is why the workspace's remotes are named `<org>/<repo>` and carry a relative URL ending in that slug.
The naming was chosen to disambiguate repositories sharing a name;
it also makes the source repository recoverable from the ref that contains the commit,
which is what lets the qualification name the right repository without `repos.yml` or an environment variable.

Verified on the fixture: a suffix-only commit from `cynkra/dm` became `(cynkra/dm#42)`
with `GH-11` becoming `cynkra/dm#11` and a URL fragment left alone;
a commit carrying `Fixes #7` was refused;
and commits reachable only from `origin`, or written in the workspace, were untouched.

### Ambiguous provenance is refused, not guessed

A replayed commit reachable from more than one mirror's namespace cannot be qualified correctly --
the two candidates name different repositories, and picking one would be a guess.
The hook refuses, matching what `no-foreign-issue-refs` already does
when the slug cannot be read at all.

It should be rare: the mirrors are unrelated upstreams.
It is reachable when one has already taken the other's commit,
which is exactly when qualifying against the wrong one would be most misleading.

### `core.hooksPath` is `../hooks` from the workspace

The same mechanism the mirrors use, at a different depth:
`mirrors/<org>/<repo>/` is three levels below the repository root and uses `../../../hooks`,
`reconcile/` is one and uses `../hooks`.

Git runs a hook with the top of the working tree as the current directory,
so the relative path resolves wherever the tree sits.
Checked on the fixture rather than inferred from the mirrors' case,
including from a subdirectory of the workspace.

Written on every run, like the remotes, and for the reason `no-foreign-issue-refs` gives:
a guard installed only by a command nobody ran today is not installed.

### Ordering against `no-foreign-issue-refs`

`hooks/prepare-commit-msg` is added by that change, so it lands first and this one edits it.
Until then the workspace has no guard to point at,
which is a reason to sequence the two and not a reason to duplicate the hook here.

## Risks / Trade-offs

- **The workspace's tag cleanliness rests on configuration, not on structure.**
  → One repository, one config file, one command to verify and one to repair.
  There is no tagless far end available in this direction, so this is the sound form rather than a weaker form of something better.

- **A second copy of the history of every repository promoted from.**
  → Bounded by lazy fetching: only repositories actually fetched are duplicated. Sharing objects was considered and rejected above.

- **Someone later "tidies" the workspace into a worktree of the template's mirror.**
  → The spec states the prohibition and its reason, with a scenario asserting the mirror is unaffected.

- **Someone later adds a checkout or reset to the task.**
  → Stated as a requirement with scenarios covering a run during a cherry-pick, with uncommitted changes, and on a promotion branch.

- **The generalised provenance rule widens what the shared hook acts on in a mirror:**
  any non-`origin` remote, not only `template`.
  → No mirror this project configures has another remote,
  and a foreign remote added by hand carries the same hazard the rule exists for,
  so the wider rule is the more correct one.
  It is called out because it is a behaviour change to a hook this change does not own.

- **A stale remote left behind after an inventory entry is dropped**
  would offer commits from a repository no longer in scope.
  → Remotes are reconciled with the inventory on every run; removing a remote removes its refs with it, which the fixture confirmed.

## Migration Plan

Nothing to migrate. The workspace does not exist yet, and no existing tree, mirror or script changes.
The first `mise run reconcile-workspace` clones the template into `reconcile/` and wires the remotes.

Rollback is deleting `reconcile/` and reverting the script, the task and the `.gitignore` line.
No other part of the project reads the workspace.

## Open Questions

None that affect the specs or the task breakdown.
What a later reconcile engine will want *on top of* this — a report of which mirrors carry candidate commits,
a convention for promotion branch names — is left to the change that builds it,
and none of it constrains the workspace's shape.
