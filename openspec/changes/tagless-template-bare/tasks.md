## 1. Shared helpers in `lib.sh`

- [ ] 1.1 Add `template_bare_tagless`, a predicate answering from disk whether the bare mirror holds no refs under `refs/tags/`;
          verify it returns false against a bare mirror built by `git clone --mirror` of a tagged upstream
          and true after that mirror is normalised.
- [ ] 1.2 Add `template_bare_normalise`, writing `remote.origin.fetch` with `--replace-all`, setting `remote.origin.tagOpt`,
          unsetting `remote.origin.mirror`, and deleting every `refs/tags/*` via `update-ref --stdin`;
          verify that running it twice against the same bare mirror leaves the second run with nothing to change and exit zero.
- [ ] 1.3 Add `template_bare_set_head`, reading the upstream's default branch with `ls-remote --symref origin HEAD`
          and writing it with `symbolic-ref HEAD`;
          verify `git -C <bare> symbolic-ref HEAD` names the upstream's default branch
          and that a consumer's `git remote set-head template -a` then succeeds.
- [ ] 1.4 Add `template_bare_refresh`, composing normalise, `git fetch --prune origin` and set-head into the one call both commands make;
          verify it leaves a `--mirror`-built bare mirror with branches only, no push-mirror setting, and a resolvable `HEAD`,
          without re-cloning.

## 2. `clone.sh`

- [ ] 2.1 Rewrite `clone_or_update_bare` to create an absent bare mirror with `git init --bare` plus `remote add origin`,
          then delegate to `template_bare_refresh`;
          verify a fresh run against an empty `mirrors/` produces a bare mirror whose `for-each-ref` lists `refs/heads/*` only.
- [ ] 2.2 Verify the non-bare-path guard still reports a directory that exists but is not a bare repository,
          and that no fetch is attempted into it.
- [ ] 2.3 Change the barrier so the bare mirror alone precedes the fan-out,
          and move the template's checkout into the wave with every other checkout;
          verify the template's checkout is cloned by the same code path as the rest and that its `template` remote resolves afterwards.
- [ ] 2.4 Drop the `[[ "$slug" == "$template_slug" ]]` early return from `configure_template_remote`;
          verify `git -C mirrors/<template-org>/<template-repo> remote get-url template` resolves to the bare mirror beside it.
- [ ] 2.5 Replace the `git config remote.template.tagOpt --no-tags` write with a removal gated on `template_bare_tagless`;
          verify the setting is gone from a mirror after a full run,
          and that `clone.sh --checkout <slug>` run by hand against a tree whose bare mirror still carries tags leaves the setting in place.
- [ ] 2.6 Rewrite the header comment and the `--prune-tags` comment
          so `--prune-tags` is justified as re-baselining rather than as template cleanup;
          verify no comment still claims the guarantee lives on the `template` remote.

## 3. `sync.sh`

- [ ] 3.1 Replace the barrier's bare `git fetch --prune` with `template_bare_refresh`,
          keeping the existing missing and non-bare failure paths;
          verify a sync against a tree whose bare mirror still carries tags leaves it tagless before any checkout is processed.
- [ ] 3.2 Delete `fetch_template` and replace it in `run_one` with `git fetch --all --prune`,
          removing the `template_bare_usable` re-check, the `template`-remote presence check and the `--no-tags` option;
          verify a checkout's `refs/remotes/template/*` still matches the bare mirror after a run.
- [ ] 3.3 Verify the template's own checkout is processed by `run_one` with no special case,
          and that a checkout carrying no `template` remote is rebased and fetched without being recorded as a failure.
- [ ] 3.4 Verify a rebase that fails still leaves the checkout's remotes fetched, preserving the existing per-checkout ordering guarantee.
- [ ] 3.5 Rewrite the header comment to say the bare mirror's refresh is the one step generic tooling cannot perform,
          and that the per-checkout step is deliberately the generic one.

## 4. End-to-end verification

- [ ] 4.1 Build a local fixture — a tagged upstream, a bare mirror created by `git clone --mirror`, two checkouts wired the old way —
          and run the new `clone`;
          verify the bare mirror ends with branches only, no push-mirror setting, a resolvable `HEAD`,
          and every checkout carries a `template` remote with no `tagOpt`.
- [ ] 4.2 From that fixture, run `git fetch --tags template` in a checkout;
          verify its `refs/tags/` is unchanged, which is the guarantee the per-mirror configuration used to provide.
- [ ] 4.3 Run `git pull --rebase && git fetch --all --prune` in every checkout by hand, then run `mise run sync`;
          verify both leave the checkouts in the same state, which is the claim that the per-checkout step is generic.
- [ ] 4.4 Push a branch from a checkout to its `template` remote and then from the bare mirror to its upstream;
          verify the upstream's tags are still present, covering the push-mirror risk.
- [ ] 4.5 Run `clone` and `sync` twice each against a settled tree; verify the second run of each changes nothing and exits zero.

## 5. Documentation

- [ ] 5.1 Update ROADMAP §2.2 so the tag bullet states the guarantee as a property of the bare mirror rather than of the `template` remote;
          verify no bullet still describes per-mirror tag configuration.
- [ ] 5.2 Update ROADMAP §2.4 so the `sync` bullet names the bare mirror's refresh as the one non-generic step;
          verify it matches what `sync.sh` now does.
- [ ] 5.3 Add a ROADMAP §2.2 bullet recording that the bare mirror is never a push mirror, so the constraint survives into §2.3;
          verify it names the consequence rather than only the setting.

## 6. Spec bookkeeping

- [ ] 6.1 Archive the `no-template-tags` change before this one,
          so this change's deltas apply to a spec tree that already carries its requirements;
          verify `openspec/specs/template-remote/spec.md` contains "The `template` remote imports no tags" before this change is archived.
- [ ] 6.2 Run `openspec validate tagless-template-bare --strict` after any spec edit; verify it reports the change valid.
