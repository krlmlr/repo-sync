## Context

The template is merged the way everything on GitHub is merged:
a pull request, squashed, and a subject ending in the number of that pull request.
`fix: keep the template's tags out of the mirrors (#10)` is the shape of every commit it has.
Bodies add the other shape, `Fixes #7`,
whenever the description that closed an issue is carried into the message.

Those numbers are addresses, and they are relative.
`#10` means *issue 10 of the repository this commit is in*,
resolved by GitHub at the moment it renders a message,
not by whoever wrote it.
A commit that moves to another repository takes the address with it
and it now points somewhere else —
at a stranger's issue 10, which GitHub will helpfully annotate
with a cross-reference to a commit in a repository nobody in that conversation has heard of.
Forty-seven mirrors, forty-seven annotations, one per copy.

Under a closing keyword the same mechanism closes the issue.

## Goals / Non-Goals

**Goals:**

- No commit copied from the template into a mirror
  carries a reference that resolves against the mirror.
- The common case — GitHub's `(#12)` suffix — costs the operator nothing.
- The uncommon case, where the reference is an instruction rather than a mention,
  is decided by a human.
- Commits a mirror makes about its own issues are untouched.

**Non-Goals:**

- Changing anything in the template. It cannot be fixed there (see below).
- Reference rewriting for commits already in a mirror's history.
  A copy made before this existed keeps what it was given;
  rewriting it would mean rewriting history that has been pushed.
- Guarding the push. The copy is the moment a reference changes meaning,
  and it is the moment this change guards.
  A second check at `pre-push` would have nothing left to repair —
  only history to refuse, and refusing it helps nobody.

## Decisions

### The fix belongs at the copy, not at the source

The obvious place is the template:
stop writing the number into the message and there is nothing to clean up later.
It is not available.
The `(#12)` suffix is written by GitHub when a squash merge is performed,
from the pull request's own number, and no repository setting suppresses it.
Whatever the template's contributors do —
however carefully a title or a description is worded —
the merge adds the reference afterwards.

So the guarantee has to be enforced where the commit crosses a repository boundary,
which is the cherry-pick into a mirror.

### `prepare-commit-msg`, because `commit-msg` does not run

A cherry-pick does not run `commit-msg` or `pre-commit`; it runs `prepare-commit-msg`.
That is the one hook on the path, on the clean path (`source=message`)
and on the `git cherry-pick --continue` after a conflict (`source=merge`) alike.
It also honours what the hook leaves in the message file,
which is what makes repairing possible and not only refusing.

`git am` is the one copy that bypasses it —
it runs `applypatch-msg` instead — and is not how the template is applied here.

### Repair the mention, refuse the instruction

A guard that fires on every cherry-pick and asks for the message to be retyped
is a toll, not a guard:
the `(#12)` suffix is on *every* squashed commit the template has,
so refusing it would mean rewriting every message by hand, in every mirror.

`<org>/<repo>#12` is the same reference made absolute.
It resolves to the template's issue from any repository,
renders as a link to it, and is what a human would have written
had they thought about where the commit was going.
Rewriting to it loses nothing and asks nothing.

A closing keyword is different in kind.
`Fixes #7` qualified reads `Fixes cynkra/cynkratemplate#7`,
and that is a dependent repository closing an issue in the template —
which GitHub will do, once per mirror, for anyone with write access to both.
Whether the reference should survive the copy at all is a judgement,
and the hook stops and asks for it.
The stop is recoverable: the cherry-pick leaves its state in place,
and a `git commit -m` with the reference dropped or qualified by hand carries on.

*Alternative considered*: refuse everything, which is the smaller rule.
It is available as `REPO_SYNC_TEMPLATE_REFS=block`
for anyone who would rather read every message than have one repaired quietly.
Not the default, for the reason above.

*Alternative considered*: strip the reference entirely.
It is the only rewrite with no cross-repository effect at all,
and it throws away the one thing the message knew
that the mirror's copy cannot reconstruct — where the change came from.

### Provenance from the refs, not from the operator

The hook acts only when two things hold:
a replay is in progress — `CHERRY_PICK_HEAD`, `REVERT_HEAD` or `REBASE_HEAD` names the original —
and that original is reachable from `refs/remotes/template/*`.

Both are read from the repository rather than passed in,
so a cherry-pick typed by hand is covered exactly as one made by a script,
and `sync`'s daily `pull --rebase`, which replays a mirror's *own* commits,
is not: those commits' references are the mirror's own and correct.

The template's slug comes from the remote that brought the commit in
(`../../cynkra/cynkratemplate.git` → `cynkra/cynkratemplate`),
so the hook needs neither `repos.yml` nor an environment variable to name it.
If it cannot be read, the hook refuses rather than guesses.

### `core.hooksPath`, and one hook for all mirrors

Hooks are not cloned, so every mirror would otherwise need its own copy —
forty-seven of them to update the day the hook changes,
with no way to tell which are current.
`core.hooksPath` points a mirror at this repository's tracked `hooks/`,
relative (`../../../hooks`) for the same reason the `template` remote's URL is:
git runs hooks from the top of the working tree,
so it resolves wherever the tree as a whole sits.

It is written by `clone` *and* by `sync`, deliberately, as `--no-tags` is:
`clone` is reached for when a mirror needs re-baselining,
`sync` is what runs every day,
and a guard installed only by the command nobody ran today is not installed.

The cost is that `core.hooksPath` takes over a mirror's hooks entirely:
anything in its `.git/hooks` stops running.
A fresh mirror has none — hooks are not cloned —
and a mirror is not where anyone's local tooling should live.

## Risks / Trade-offs

- **A message is edited without anyone asking.** That is what `prepare-commit-msg`
  is for, and the hook says on stderr what it changed, per reference.
  `REPO_SYNC_TEMPLATE_REFS=block` turns every repair into a stop.
- **`--no-verify` skips it**, as it skips every hook. This is a guard against
  a mechanism, not against a determined operator.
- **The qualified reference still annotates the template.** A cross-reference
  lands on the template's own pull request, forty-seven times over, rather than
  on forty-seven strangers'. That is provenance arriving where it belongs.
- **A mirror's own hooks stop running.** See above.
- **perl is needed.** It is on every machine that runs the rest of this toolkit,
  and a hook that cannot run refuses the commit rather than waving it through.
- **Commits copied before this existed keep their references.** Nothing rewrites
  history, deliberately: what is already in a mirror stays as it is, and the
  guard covers the copies made from here on.

## Migration Plan

`mise run sync`, or `mise run clone`, sets `core.hooksPath` on every mirror.
Either will do; both are idempotent, and `sync` is the one already run daily.

To roll back: `git config --unset core.hooksPath` in each mirror,
or delete `hooks/`, which leaves every mirror pointing at a directory
with no hooks in it — the same as having none.

## Open Questions

- Should `applypatch-msg` share the implementation, so `git am` is covered
  too? Nothing applies the template that way today.
