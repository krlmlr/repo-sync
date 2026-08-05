# Where the sync logic lives, and what drives it

An investigation, not a proposal.
It answers two questions that turn out to be one:

1. Should the machinery in this repository move into
   `cynkra/cynkratemplate`, the repository it treats as the template?
2. Should `s` — `h git` from
   [`krlmlr/scriptlets`](https://github.com/krlmlr/scriptlets),
   which runs a Git command in every repository below the current
   directory — be what synchronizes the mirrors?

Every claim below marked *verified* was run against a throw-away fixture
of five repositories shaped like `mirrors/`,
not reasoned about from the source.

## What is here today

```
  krlmlr/actions-sync ──(branch names)──▶ repos.yml     47 repos, 11 orgs
                                              │
  krlmlr/repo-sync                            │  scripts/clone.sh
  ├── repos.yml  scripts/  mise.toml          ▼
  └── mirrors/                          ┌─────────────────────────┐
      ├── cynkra/cynkratemplate ◀───────┤ the one `template: true`│
      ├── cynkra/dm ───────────┐        └─────────────────────────┘
      ├── r-lib/pillar ────────┼── remote `template`
      └── … 44 more ───────────┘        = ../../cynkra/cynkratemplate
```

The inventory and the clone step are done
([`ROADMAP.md`](../ROADMAP.md) §2.1, §2.2 first item).
Reconcile, push and orchestration (§2.2–2.4) are not,
and this is the fork in the road before them.

There is already a contradiction to settle.
§2.2 says the tooling will diff each repo against
"a canonical template / set of patches maintained in this repo",
while `template: true` says the canonical content lives in
`cynkra/cynkratemplate`.
Both cannot be true.
Question 1 is really: which one do we make true?

(An aside while counting: `ROADMAP.md` §1 still says 59 repos across 15
orgs. `repos.yml` has held 47 across 11 since "Remove Poisson's repos".)

## Finding: the `template` remote is not a merge base

The `template` remote reads like an invitation to
`git merge template/main`.
It is not one.
`cynkratemplate` and each consumer have no commit in common,
so the merge is refused in every mirror (*verified*):

```
cynkra/dm:      fatal: refusing to merge unrelated histories
r-dbi/DBI:      fatal: refusing to merge unrelated histories
r-lib/pillar:   fatal: refusing to merge unrelated histories
```

`--allow-unrelated-histories` would not rescue it —
it would drag `cynkratemplate`'s own `DESCRIPTION`, `R/`, `man/` and
`NAMESPACE` into a consumer that is a different package.
The remote is an **object channel**, and the usable primitives are
path-scoped:

```sh
git diff     template/main -- .github/workflows/    # what drifted
git checkout template/main -- .github/workflows/    # take the template's
```

This is worth writing down before the reconcile engine is designed
around a merge that cannot happen,
and it is why the `template-remote` spec's "canonical source" wording
deserves a sentence saying *how* it is canonical.

## Question 1 — move the machinery into `cynkratemplate`?

### What moving buys

**One home for the content and the machinery that spreads it.**
It settles the §2.2 contradiction in the direction the facts already
point: the canonical workflows are in `cynkratemplate`, not here.

**A shorter loop** (*verified*).
The `template` remote becomes `../../..` — the tool repository itself —
`mirrors/cynkra/cynkratemplate` disappears (46 mirrors, not 47),
and a template change that is committed locally and pushed nowhere
is spreadable immediately.
Today the same change has to go out to GitHub and come back through
`clone.sh` before any consumer can see it.

**Review in one place.**
The pull request that changes `.github/workflows/R-CMD-check.yaml`
becomes the pull request that rolls it out.

**It is where the work already happens.**
`cynkratemplate` carries commits like
"Centralize R-CMD-check / install / roxygenize improvements from
consumers" (#87) and "Unify `fledge.yaml` across cynkratemplate and
fledge" (#86).
That is this pipeline, run by hand, in that repository.

### What moving costs

**The fleet is not cynkra's.**
`cynkra` owns 8 of the 47 repos; the rest are `krlmlr`, `r-dbi`,
`moodymudskipper`, `r-lib`, `tidyverse`, `r-prof`, `igraph`, `duckdb`,
`mlfit` and `renkun-ken`.
Moving makes a cynkra repository — whose stated purpose is
"a pkgdown template for cynkra packages" — the control plane for
pushes into ten other orgs.

**It is a released R package on a daily schedule.**
`fledge.yaml` runs nightly and turns commits into a version bump and
`NEWS.md` entries.
Every commit to the sync machinery would land in the changelog of a
package whose version is a release artifact,
and every tooling path (`mirrors/`, `repos.yml`, `scripts/`,
`requirements.txt`, `mise.toml`) would need an `.Rbuildignore` entry
to stay out of `R CMD check`.

**One CI, two audiences.**
The package's check matrix, revdep run and pkgdown deploy would fire on
sync-tooling commits, and the sync runs would sit in the package's
Actions history.

**Blast radius.**
§2.3 ends in a token that can push to 47 repositories across 11 orgs.
Today that would live in a 78 KB personal repository whose devcontainer
deliberately reaches exactly one host
([`.devcontainer/ROADMAP.md`](../.devcontainer/ROADMAP.md)).
Moving puts it in a public org repository with forks and open issues,
whose contributors signed up to maintain a pkgdown theme.

**The special case moves, it does not go away.**
The self-mirror disappears, and "the tool repository *is* the template"
arrives to replace it.
Every tool still needs to know which repository is not like the others.

**Easy in, awkward out.**
`repo-sync` is four months old, 78 KB, with no external consumer.
Merging it into a six-year-old package is a morning's work;
extracting it again once its history is entangled is not.

### Reading

The case for moving is about *content*: the template is the thing being
spread, so the spreader should sit beside it.
The case against is about *scope and lifecycle*: a released package for
one org is the wrong container for a push-capable fleet tool covering
eleven.

There is a version of "move" that takes the first without paying the
second: **move the declaration, not the machinery.**
What genuinely belongs next to the canonical files is the statement of
*which paths are canonical* — a small manifest listing the templated
paths and the per-repo exceptions — because that is content, it is
reviewable by the people who maintain those files, and it costs
`cynkratemplate` one file and one `.Rbuildignore` line.
`repo-sync` would read it from `template/main` and keep the clone,
diff, classify and push machinery, the credentials and the locked-down
devcontainer on this side of the boundary.

*(Nothing was written to `cynkratemplate` for this investigation.)*

## Question 2 — is `s` what synchronizes the mirrors?

`s` is `h git`: it finds every Git repository below the current
directory and runs the command in each, in parallel, prefixing each
line with the repository it came from.
Run from `mirrors/`, that is one command per fleet-wide operation.

First, a correction that had to come before any of this could be
measured: **`h` and `s` did not run at all.**
The loop that emits the per-repository commands advanced its colour
counter with `((i++))`, which reports the value from before the
increment — so on the first repository, where the counter is still 0,
it returned 1 and the script's `set -e` ended the run.
`h` printed its header and stopped.
That one is fixed in `krlmlr/scriptlets` (#48), independently and while
this was being written; a second abort behind it, in the interactive
path, is fixed on top.
Both went unnoticed because nothing there exercised either script —
`tests/checks/75-h.sh` now does.

### What `s` covers

Against the ROADMAP items that are still open:

| ROADMAP                     | `s`                                                        |
| --------------------------- | ---------------------------------------------------------- |
| §2.2 diff against template  | `s diff --stat template/main -- .github/workflows/`         |
| §2.2 classify               | partly — a verdict per repo, but the policy is not there    |
| §2.2 report per repo        | free; every output line is named by its repository          |
| §2.3 apply                  | `s checkout template/main -- <paths>` then `s commit`       |
| §2.3 push                   | `s push …` — but see the exit status below                  |
| §2.3 dry run                | `-n` shows the generated shell, not the Git effect          |
| §2.4 scheduled CI           | no                                                          |

The drift report is real, and it is one line (*verified*):

```
$ cd mirrors && s fetch template && s diff --stat template/main -- .github/workflows/
cynkra/dm:      .github/workflows/R-CMD-check.yaml | 4 +---
cynkra/dm:      .github/workflows/pkgdown.yaml     | 4 ----
r-dbi/DBI:      .github/workflows/R-CMD-check.yaml | 2 ++
r-lib/pillar:   .github/workflows/pkgdown.yaml     | 4 ----
```

A classification table is one more, through `h` rather than `s`,
because the verdict needs a shell and `s` only prepends `git`
(*verified*):

```sh
h sh -c 'git diff --quiet template/main -- .github/workflows/ \
           && echo IN-SYNC || echo DRIFT'
```

### What `s` does not cover

**No failure signal** (*verified*).
Each generated command ends in the `sed` that names its output, so the
parallel run exits 0 even when a repository failed outright — a fetch
that could not reach its remote scrolls past and `$?` stays 0.
`clone.sh` already satisfies "report every failure and exit non-zero";
`s` does not, and anything built on it has to re-derive failure by
reading the output.
`-i` does propagate the status (128 on that same fetch), but it is
serial, it needs a TTY, and it stops at the first failure instead of
reporting all of them.

**It clobbers intentional divergence, silently** (*verified*).
`git checkout` overwrites; it does not merge.
In the fixture, a consumer carrying a deliberate extra CI job lost it
to `s checkout template/main -- .github/workflows/` with no warning and
no conflict.
§2.2's third class — *intentional, skip* — is exactly the part `s`
cannot have an opinion about.
`s` is fan-out; the policy has to live somewhere else.

**It is Git only.** Cloning still needs `clone.sh` and `gh`.

**Its prerequisites are personal dotfiles.**
`h` needs `fd`, `gsed`, `gsort` and GNU `parallel`, under Homebrew's
`g` names, installed through krlmlr's rcm setup.
That is fine at a prompt and disqualifying for §2.4's scheduled run:
a GitHub runner has none of them, and neither does a colleague.

### Reading

`s` is an excellent **interactive** reconcile loop and a poor
**unattended** one.
It removes most of the reason to write a reconcile engine — diff,
per-repo report and apply are already there — while leaving exactly the
two things worth writing: the policy that says which drift is
intentional, and a portable runner for CI.

## Recommendation

1. **Keep the machinery here.** The costs of moving it into
   `cynkratemplate` are structural (a released package, one org's
   repository, a fleet-wide token) and the benefits are mostly
   reachable without moving.
2. **Settle §2.2 the other way:** the canonical content is
   `cynkratemplate`'s, not this repository's. Reword §2.2 to match what
   `template: true` already asserts, and say in the `template-remote`
   spec that the remote is an object channel, diffed and checked out
   per path — not merged.
3. **Adopt `s` for the human loop** and write the recipes down here
   instead of building a reconcile engine. What remains to be built is
   the templated-paths manifest with its per-repo exceptions, and a
   portable runner for §2.4 that does not depend on `s`.
4. **Consider moving the manifest — only the manifest — into
   `cynkratemplate`** once its shape is known. It is content, it is one
   file, and it is the piece whose reviewers are that repository's
   maintainers.
5. **Revisit the whole question** if the inventory ever narrows to
   cynkra, which is the condition under which the objection in §"What
   moving costs" disappears.

## Follow-ups worth their own change

- Give the template mirror a `template` remote pointing at itself
  (`../../<template-org>/<template-repo>` resolves there from its own
  directory), so every mirror answers the same question and `s` needs
  no exception. *Verified*: it turns the one guaranteed error per run
  into a plain `IN-SYNC` row. This contradicts the `clone` spec's
  "Template mirror skipped" scenario, so it belongs in an OpenSpec
  delta rather than a patch.
- Refresh `ROADMAP.md` §1's "59 repos across 15 orgs" to the 47 across
  11 that `repos.yml` holds.
