## Why

Every mirror ends up carrying the template's tags.

`git fetch` auto-follows tags:
any tag pointing at an object the fetch downloaded
is written into the local `refs/tags/*`.
A fetch of the `template` remote downloads the template's whole history,
so every tag in the template is auto-followed into the mirror.

Branches survive this
because they land in `refs/remotes/template/*`,
a namespace that remote has to itself.
Tags have no such namespace.
`refs/tags/*` is flat and shared with the mirror's own tags,
so the template's arrive indistinguishable from them —
and `--prune` does not remove tags,
so once they land
they stay.

The damage is local for now.
It stops being local at §2.3:
a `git push --tags`, or a mirror carrying `push.followTags`,
would publish the template's version tags
into a foreign repository on GitHub,
which is a great deal harder to walk back than a local ref.

## What Changes

- **Configure the `template` remote to import no tags.**
  `scripts/clone.sh` sets `remote.template.tagOpt` to `--no-tags`
  on every non-template mirror,
  so every fetch of that remote inherits it —
  `sync`'s, and any run by hand or by the reconcile step later.
- **Pass `--no-tags` at `sync`'s fetch as well.**
  `sync` is the command that runs every day,
  and a mirror wired up before this change carries no such setting
  until the next `mise run clone`.
  Belt and braces, in the one place where the leak actually happens.
- **Prune tags when `clone` updates a mirror.**
  `git fetch --prune --prune-tags` in place of `git fetch --prune`,
  so the tags already imported are removed
  rather than left to sit there forever.
  This is the tool that resets the working tree onto `origin/HEAD`;
  bringing the tags in line with the upstream is the same promise.

## Capabilities

### Modified Capabilities

- `template-remote`: The `template` remote is configured to import no tags.
- `clone`: An incremental update brings the mirror's tags in line with its upstream's,
  removing any the upstream does not have.
- `sync`: The `template` fetch imports no tags,
  whether or not the remote carries the setting.

## Impact

- **`scripts/clone.sh`** — `--prune-tags` on the update fetch,
  and `remote.template.tagOpt` written beside the `template` URL.
- **`scripts/sync.sh`** — `--no-tags` on the `template` fetch.
- **`ROADMAP.md`** — §2.2 records that the `template` remote carries branches and not tags.
- **Existing mirrors**: one `mise run clone` configures every `template` remote
  and drops the tags already imported.
  No manual migration.
- No new dependencies, and no change to what is fetched otherwise:
  `refs/remotes/template/*` is updated exactly as before.

## Out of Scope

- Keeping the template's tags under a namespace of their own
  (`+refs/tags/*:refs/remotes/template/tags/*`).
  Nothing reads them today;
  the reconcile step can ask for them
  when it has a use for them.
- Tags on the mirrors' own upstreams.
  Those belong to the mirror
  and are fetched, pruned and pushed as they always were.
- Anything about pushing (§2.3).
  This closes the way the template's tags would get there;
  it does not change what a push does.
