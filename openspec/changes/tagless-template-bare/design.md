## Context

See `proposal.md` — Why.

The mechanics below were verified against git 2.55 on a local fixture
(an upstream carrying one branch and two tags, a bare mirror, and a consumer fetching from it)
rather than reasoned about from the documentation.
Each decision records what the fixture showed,
because several of them turn on behaviour that is easy to assume wrongly.

Two constraints shape the approach.
`scripts/lib.sh` already exists as the single home for what `clone` and `sync` both do,
which is where the bare mirror's handling belongs now that both commands must establish the same invariant.
And both commands fan out by re-invoking themselves once per repository,
so anything a child needs must either be inherited through the environment or re-derived from disk.

## Goals / Non-Goals

**Goals:**

- One enforcement point for the no-tags guarantee, established before any mirror can fetch.
- A per-checkout step that is a plain pair of git commands, so `s`, `h`, or a shell loop reach the same result as `mise run sync`.
- In-place migration of an existing `mirrors/` tree: no re-clone, no extra network.
- No path by which this repository can delete refs on a GitHub upstream.

**Non-Goals:**

- Removing the bare mirror's own exception. It still has no `.git` entry and no sweep over working trees reaches it;
  this change reduces the exceptions from two to one, it does not reach zero.
- Making `sync.sh` unnecessary. It keeps the barrier, the fan-out and the failure report.
  What changes is that its per-checkout half stops being special.

## Decisions

### Build the bare with `git init --bare`, not `git clone --mirror`

`git clone --mirror` sets `remote.origin.fetch = +refs/*:refs/*` and `remote.origin.mirror = true`.
The first copies `refs/tags/*` and is the reason the bare mirror has tags to leak;
the second is worse, and is covered below.
There is no option to `clone --mirror` that excludes tags,
so the bare mirror is built explicitly instead:

```
git init --bare <dest>
git -C <dest> remote add origin <ssh-url>
git -C <dest> config remote.origin.fetch '+refs/heads/*:refs/heads/*'
git -C <dest> config remote.origin.tagOpt --no-tags
git -C <dest> fetch --prune origin
```

Both settings are needed and neither implies the other.
The refspec stops tags being copied by the refspec;
`tagOpt` stops them arriving by auto-following, which happens independently of the refspec
whenever a fetch downloads an object a tag points at.

`--prune` works normally with the explicit refspec:
the fixture confirmed a branch deleted upstream disappears from the bare mirror on the next fetch.

*Alternative considered:* clone with `--mirror` and delete the tags afterwards.
Rejected — it leaves the refspec and the push-mirror setting in place,
so the next fetch re-imports every tag and the guarantee lasts exactly one command.

### Unset `remote.origin.mirror`, and treat it as a safety property

A bare repository with `remote.origin.mirror = true` treats a plain `git push origin` as a mirror push:
it makes the upstream match the local repository exactly, **deleting** refs the local repository does not have.
A tagless bare mirror carrying that setting therefore deletes every tag on the GitHub repository on the first push.
The fixture reproduced this — the upstream's `v1.0.0` was gone after one `git push origin`.

This is not hypothetical for long: ROADMAP §2.3 pushes curated changes back.
So the setting is not merely "not set" on a fresh bare mirror but actively unset on every run,
and the spec states it as a property of the bare mirror rather than as a step of its construction.

### Set `HEAD` with `ls-remote --symref`, not `remote set-head`

`git init --bare` points `HEAD` at whatever `init.defaultBranch` says — `master` unless configured otherwise —
regardless of the upstream's default branch.
`git clone --mirror` inherits the upstream's `HEAD` for free; the explicit construction does not.

The obvious repair, `git remote set-head origin -a`, does not work here.
It writes `refs/remotes/origin/HEAD`, and a bare mirror whose refspec maps branches into `refs/heads/*`
has no `refs/remotes/origin/` at all: the fixture returned `error: Not a valid ref: refs/remotes/origin/main`.

The mechanism that does work reads the upstream's symbolic ref and writes the local one:

```
git -C <dest> ls-remote --symref origin HEAD    # -> ref: refs/heads/<default>
git -C <dest> symbolic-ref HEAD refs/heads/<default>
```

This matters beyond tidiness.
A consumer's `git remote set-head template -a` fails against a bare mirror with a dangling `HEAD`,
so `template/HEAD` — the natural way for reconcile to mean "the template's default branch" — cannot be resolved.
With `HEAD` set, the fixture resolved `template/HEAD` to `template/main`.

### Normalise an existing bare mirror in place

An existing `mirrors/<org>/<repo>.git` was built by `git clone --mirror`.
Re-cloning it would re-download the whole repository for a configuration change, so it is repaired instead:

```
git -C <dest> config --replace-all remote.origin.fetch '+refs/heads/*:refs/heads/*'
git -C <dest> config remote.origin.tagOpt --no-tags
git -C <dest> config --unset-all remote.origin.mirror
git -C <dest> for-each-ref --format='delete %(refname)' refs/tags/ | git -C <dest> update-ref --stdin
```

`--replace-all` rather than plain `config`, because a repository that has accumulated more than one
`remote.origin.fetch` value must end with exactly one, not with the old value still present.
`update-ref --stdin` rather than a loop over `git tag -d`,
because it takes the whole deletion as one batch and accepts empty input without complaint,
which is what makes the step idempotent on an already-normalised repository.

The fixture confirmed the sequence converts a `--mirror` clone in place,
that a second run is a no-op, and that the upstream's tags are untouched throughout.

Deleted tag refs leave their objects unreachable rather than gone; ordinary `git gc` collects them. No action is taken.

### Put normalise-and-fetch in `lib.sh` and call it from both commands

The lesson recorded in the comment at `scripts/sync.sh:56-61` is that configuration written by `clone`
and relied on by `sync` leaves a window: `sync` runs every day, `clone` runs when someone remembers.
Moving the tag guarantee into the bare mirror does not by itself close that window —
it relocates it, since a `sync` run against a tree whose bare mirror is still in the old shape
would now have *no* per-mirror protection to fall back on.

So the bare mirror's normalisation is not a step of `clone` that `sync` trusts.
It lives in `lib.sh` and runs as the first thing both commands do, at the existing barrier, before any fan-out.
`clone` additionally creates the bare mirror when it is absent; `sync` reports its absence as it does today.
That makes "the invariant is re-established before any mirror fetches" true per command rather than per tree.

*Alternative considered:* have `sync` verify and fail loudly instead of repairing.
Rejected — it turns a routine migration into an error the operator must act on,
for a repair that is four config writes and a ref deletion.

### Remove `remote.template.tagOpt`, but only against a verifiably tagless bare mirror

Leaving the setting behind would be harmless, since it guards against tags that no longer exist.
It is removed anyway, because these specs already normalise drift of this kind
and because leaving it contradicts the claim that the guarantee has one home.

The removal is gated. `clone.sh` has a child entry point — `clone.sh --checkout <slug>` —
that an operator can run by hand against a tree whose bare mirror has not been normalised.
Unsetting `tagOpt` there would strip the only protection a mirror has.
So the unset is conditional on the bare mirror on disk carrying no tags,
checked by a small `lib.sh` predicate alongside the existing `template_bare_usable`
and following the same rule: each process answers from disk rather than being told,
so a child reaches the same verdict as the parent and a child run by hand reaches it too.

In the batch path the condition is always satisfied, because the barrier normalises the bare mirror first.

### The per-checkout step becomes `pull --rebase` plus a fetch of every remote

`fetch_template` disappears. Each checkout gets:

```
git -C <dest> pull --rebase
git -C <dest> fetch --all --prune
```

The second command is what makes the template's refs current, as one of the remotes it happens to fetch.
It also re-fetches `origin`, which `pull --rebase` just did;
that redundancy is the price of the step being the generic one, and it costs a no-op fetch.

Three behaviours fall out and are specified deliberately:
the template's own checkout is no longer skipped, because it now carries the remote and there is nothing to skip;
a checkout with no `template` remote is no longer a failure, because fetching every remote fetches the ones that are there;
and the checkout's own upstream tags still arrive, because only the template's were ever the problem.

The `template` remote is still fetched into `refs/remotes/template/*` exactly as before,
so what a checkout ends a run holding is unchanged.

### The template's checkout keeps `origin` on GitHub and gains a `template` remote

The checkout is not repointed at the bare mirror.
Doing so would make the bare mirror the single point of contact with GitHub for the template
and close the window in which the checkout and the bare mirror sit at different commits,
but it would also turn a push of a hand-made template edit into two hops.

Adding the `template` remote alongside `origin` gets the property this change is actually after:
every checkout, without exception, has `origin` on GitHub and `template` on the bare mirror,
so the sweep over checkouts needs no list of which one is special.
The drift window between the checkout and the bare mirror remains, and is noted as a known limitation below.

### Tags are dropped rather than namespaced

Fetching `+refs/tags/*:refs/template-tags/*` into the bare mirror was verified to work:
the bare mirror advertises nothing under `refs/tags/`, so there is nothing to auto-follow,
and a consumer fetching with tags explicitly requested received `refs/template-tags/*`
while its own `refs/tags/` stayed empty.
It preserves the option of anchoring reconcile on a template release.

It is not adopted. Nothing in ROADMAP §2.2 anchors on a template tag today,
and the simpler contract — the bare mirror holds branches, and that is all —
is easier to state and to check. The refspec can be added later without disturbing anything else.

## Risks / Trade-offs

- **A tagless bare mirror that still carries `remote.origin.mirror` deletes every upstream tag on the first push.**
  → The setting is unset on every run, not only at creation, and stated in the spec as a property rather than a construction step.
  Nothing in this repository pushes from the bare mirror yet, so the window before §2.3 is where this must be got right.

- **A `sync` run against a tree in the old shape would have no per-mirror fallback.**
  → Normalisation runs at `sync`'s barrier too, from the shared implementation, before any checkout fetches.

- **An operator running `clone.sh --checkout <slug>` by hand could strip `tagOpt` before the bare mirror is normalised.**
  → The unset is gated on the bare mirror on disk being tagless, checked per process from disk.

- **Tags already imported into mirrors by earlier runs are not removed by this change.**
  → `clone`'s `--prune-tags` on the re-baselining fetch removes them, as it does today.
  That requirement is retained unchanged, now justified solely as re-baselining rather than as template cleanup.

- **The template's checkout and its bare mirror are still fetched from GitHub independently,**
  so they can sit at different commits mid-run, and a human reading the checkout may see commits
  the mirrors' `template/*` refs do not yet have.
  → Accepted for this change; the alternative costs a two-hop push for template edits.
  Revisit if reconcile turns out to be sensitive to it.

- **The bare mirror remains invisible to `s` and `h`.**
  → Unchanged and inherent: it has no working tree to discover. This change makes it the only such exception.

## Migration Plan

No operator action. The first `mise run clone` or `mise run sync` after this change:

1. Normalises `mirrors/<template-org>/<template-repo>.git` in place — refspec, `tagOpt`, push-mirror setting, stray tag refs, `HEAD`.
2. Adds the `template` remote to the template's own checkout.
3. Removes `remote.template.tagOpt` from every mirror, now that the bare mirror is verifiably tagless.

Steps 2 and 3 happen in the fan-out, after step 1's barrier, so the ordering the gate depends on holds.

Rollback is `git revert` of the scripts.
A `mirrors/` tree normalised by this change keeps working with the previous scripts:
the old `sync` passes `--no-tags` explicitly and the old `clone` rewrites `tagOpt`,
so a bare mirror holding no tags is simply a remote with nothing to suppress.
The one asymmetry is that the reverted `clone` would not restore `remote.origin.mirror`,
which is a setting worth not restoring.

## Open Questions

None. The two forks that would have changed the specs — whether to namespace the template's tags,
and whether to repoint the template checkout's `origin` at the bare mirror — were settled before this document.
