## Why

The rule that the template's tags stay out of the mirrors is enforced today in three places across forty-seven repositories:
`remote.template.tagOpt` written per mirror by `clone`,
`--no-tags` passed again by `sync`,
and `--prune-tags` to sweep up what already leaked.
The guarantee is behavioural, so anything that does not know about it breaks it --
a `git fetch --all` typed by hand, or any generic sweep over checkouts.
`sync.sh` says as much in its own comment:
the configuration is the durable half, but `clone` writes it and `sync` runs every day,
so a mirror wired up before the configuration existed keeps importing tags until someone happens to run the other command.

Pulling the template's bare mirror from GitHub without tags in the first place makes the guarantee structural instead.
A mirror cannot import a tag the far end does not have,
so the remaining sync operations become plain git commands
that any tool iterating over the checkouts can run.

## What Changes

- Build the bare mirror with `git init --bare` and an explicit `+refs/heads/*:refs/heads/*` refspec
  plus `remote.origin.tagOpt = --no-tags`, rather than with `git clone --mirror`.
  Its `refs/tags/` is empty and stays empty.
- Normalise a bare left by `git clone --mirror` in place rather than re-cloning it:
  rewrite the refspec, delete every `refs/tags/*`, and unset `remote.origin.mirror`.
- Unset `remote.origin.mirror` specifically,
  because a tagless bare that still carries it would delete every tag on the GitHub upstream on a bare `git push origin`.
  This matters ahead of ROADMAP §2.3, which pushes curated changes back.
- Set the bare's `HEAD` from the upstream's,
  since `git init --bare` leaves it at `init.defaultBranch` regardless of what the upstream's default branch is.
- Configure the `template` remote on every mirror, the template's own checkout included,
  removing the last per-repository exception from the sweep over checkouts.
- Stop writing `remote.template.tagOpt`, and remove it where earlier runs wrote it,
  once the bare on disk is verifiably tagless.
- Reduce `sync`'s per-checkout step to `git pull --rebase` and a pruned fetch of every remote,
  carrying no template-specific options and no template-specific checks.
- Move the bare's normalisation and refresh into `lib.sh`,
  so `clone` and `sync` share one implementation
  and every command re-establishes the invariant before any mirror fetches from it.

## Capabilities

### New Capabilities
<!-- None: the bare mirror and the `template` remote are already owned by the
     `clone`, `template-remote` and `sync` capabilities. -->

### Modified Capabilities
- `clone`: how the template's bare mirror is built and normalised, and the `template` remote configured on every mirror rather than only the non-template ones.
- `template-remote`: the no-tags guarantee moves from per-mirror configuration to the bare repository itself, and the remote is carried by every mirror.
- `sync`: the barrier normalises the bare as well as refreshing it, and the per-checkout step becomes generic.

## Impact

- **`scripts/lib.sh`**: gains the bare's build, normalise and refresh helpers, and a check for whether the bare is tagless.
- **`scripts/clone.sh`**: `clone_or_update_bare` rewritten; `configure_template_remote` loses its template special case and its `tagOpt` write.
- **`scripts/sync.sh`**: `fetch_template` collapses into a generic fetch; the barrier calls the shared normalise-and-refresh.
- **`ROADMAP.md`**: §2.2 and §2.4 restate where the tag guarantee lives.
- **Existing `mirrors/` trees**: normalised in place on the next `clone` or `sync` run. No re-clone and no extra network beyond the usual fetch.
- **Pending `no-template-tags` change**: this supersedes its `template-remote` requirement and relaxes its `sync` requirement.
  Its `clone` requirement (`--prune-tags` on the re-baselining fetch) is retained unchanged.
  Archive `no-template-tags` before this change so the deltas apply to a spec tree that already carries it.

## Out of Scope

- Preserving the template's tags under a non-conflicting namespace such as `refs/template-tags/*`.
  Verified to work and to keep `refs/tags/` clean, but the template's tags are not something reconcile anchors on today;
  dropping them is the simpler contract and can be revisited if reconcile ever needs "the template as of `v1.2.0`".
- Repointing the template checkout's `origin` at the bare.
  `origin` stays on GitHub; the checkout gains the `template` remote alongside it.
- The flat-sibling layout, where the relative `template` URL does not resolve. That belongs to `discover-local-subset`.
- The reconcile engine itself (ROADMAP §2.2 beyond the remote wiring) and the push path (§2.3).
