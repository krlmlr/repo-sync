## Context

Every non-template mirror carries a `template` remote
pointing at the template's bare mirror,
and `sync` fetches it in every mirror on every run.

That fetch brings the template's tags with it.
The mechanism is `git fetch`'s tag auto-following,
which is on by default
and is not a refspec:
after the refspec has been applied,
git looks for tags pointing at objects it has just downloaded
and writes them into `refs/tags/*`.
The `template` refspec (`+refs/heads/*:refs/remotes/template/*`)
never mentions tags
and does not need to;
the auto-follow happens regardless.

The reason it matters, and the reason it is easy to miss,
is that `refs/tags/*` is the one ref namespace git does not partition by remote.
`refs/remotes/template/master` is obviously the template's.
`refs/tags/v0.1.0` is nobody's in particular.
And `git fetch --prune` prunes only what the refspec covers,
which does not include tags —
so nothing that runs today ever takes one back out.

## Goals / Non-Goals

**Goals:**

- No fetch of the `template` remote writes into a mirror's `refs/tags/*`.
- The guarantee holds for fetches this repository does not make:
  a `git fetch template` typed by hand, or by whatever reconcile becomes.
- The tags already imported are removed, without a manual sweep.
- `refs/remotes/template/*` keeps being updated exactly as before.

**Non-Goals:**

- Making the template's tags available to the mirrors under another name.
- Touching the tags a mirror gets from its own upstream.
- Changing anything about pushing.

## Decisions

### `remote.template.tagOpt`, not `--no-tags` on one fetch

`git fetch --no-tags` suppresses the auto-follow for that invocation.
`remote.<name>.tagOpt` suppresses it for every fetch of that remote,
including ones this repository does not make.
Since the property wanted is about the remote —
*this remote has no tags to offer a mirror* —
the configuration belongs on the remote and not on a call site.

It is written on every `clone` run,
next to the `set-url` that already normalises the URL,
so a mirror configured before this change is repaired by the same run
that repairs a stale URL.
Both are idempotent.

*Alternative considered*: `git remote add --no-tags template ...`,
which writes the same config key.
It only covers the branch that adds the remote,
and every mirror on disk today takes the other branch.
Writing the key unconditionally after both covers new and existing alike,
so the flag on `remote add` would be decoration.

### `--no-tags` at `sync`'s fetch as well

Two mechanisms for one guarantee, deliberately.

The config is the durable one,
and it is written by `clone`.
But `clone` is the re-baselining tool, run when a mirror needs re-baselining;
`sync` is the one that runs every day.
Leaving `sync` to depend on config that only `clone` writes
means the leak continues, daily, on every mirror
until someone happens to run the other command.
`--no-tags` on the fetch itself closes that window
without waiting for a migration.

They do not conflict: both say the same thing,
and the flag is what the config expands to.

### `--prune-tags` in `clone`, and not in `sync`

Setting `tagOpt` stops the import.
It removes nothing already imported,
and the mirrors have been accumulating these tags for as long as
the `template` remote has existed.

`git fetch --prune --prune-tags` makes the mirror's tags equal its upstream's.
It is a blunt instrument — it deletes any tag not on the upstream,
including one a human made locally
and has not pushed.
That is precisely why it goes in `clone` and not in `sync`.
`clone` already resets the working tree hard onto `origin/HEAD`:
it is the tool that discards local state,
and now discards local tags with it.
`sync` promises the opposite —
it rebases rather than resets,
keeping commits that have not been pushed —
and it keeps that promise for tags.

An operator with a local tag worth keeping uses `sync`, as before.
The one who wants the mirror to look like its upstream runs `clone`, as before.

*Alternative considered*: a targeted deletion —
tags the mirror shares with the bare template
that its upstream does not have.
It is precise,
and it preserves unrelated local tags,
so it could live in `sync`.
It also costs a `git ls-remote` per repository
to find out what the upstream's tags are, over the whole inventory,
to remove refs that `clone` removes for free.
The blunt version in the tool that is already blunt is a better trade.

### The template's tags are not kept anywhere

`+refs/tags/*:refs/remotes/template/tags/*` alongside `--no-tags`
would keep them, namespaced, out of `git tag` and out of `git describe`.
It works,
and it is one config line
if a use appears.
Nothing reads them today.
Left out.

## Risks / Trade-offs

- **`clone` now deletes local-only tags.**
  It already discarded local commits in the same function;
  a mirror is not where unpushed work should live,
  and `sync` remains the tool that respects it.
- **A mirror not re-cloned keeps its imported tags.**
  `sync` stops adding to them
  but removes none.
  The repair is `mise run clone`,
  as it was for the `template` URL rewrite.
- **A tag name shared by template and upstream.**
  If the upstream has its own `v0.1.0`,
  the imported one has already overwritten nothing —
  auto-follow does not clobber an existing tag —
  and `--prune-tags` keeps the upstream's.
  Nothing to reconcile.
- **`--prune-tags` needs git ≥ 2.17.**
  Long since the floor for everything else the scripts use.

## Migration Plan

Run `mise run clone`.
It sets `remote.template.tagOpt` in every mirror
and prunes the tags already imported, in the same pass.
`mise run sync` is then safe on its own,
and stops importing tags even where `clone` has not run yet.

To roll back: `git config --unset remote.template.tagOpt` in each mirror.
The tags come back on the next fetch,
which is the way to tell it worked.

## Open Questions

- Should the bare mirror of the template stop being a full `--mirror` clone?
  It holds the template's tags,
  which is right —
  it is the template.
  The question only arises
  if reconcile ever wants a tag-free view of it,
  and the namespaced refspec above answers it better than a narrower clone.
