## Context

See `proposal.md` — Why.

Three constraints shape everything below.

**The data is not here.** `clone` and `sync` work on `mirrors/`, which is gitignored and exists on one laptop.
Almost every metric this change wants — issues, releases, CI runs, CRAN results — lives behind an API instead,
and is therefore reachable from anywhere, including from Actions, including from a machine with no mirrors at all.
Only one group, the template position, is the other way round.

**The repository has a position on the API.** `clone-without-api` removed it from the clone path because a shared
hourly budget turned one exhausted counter into forty-eight failed clones. The reasoning was about the *critical
path*, not about the API, and this change stays on the right side of it: nothing here runs during `clone` or `sync`.

**The audience is public.** `krlmlr/repo-sync` is public and so is every entry in `repos.yml`,
so anything published has an audience of everyone. Most of what is collected is already public at its source
and loses nothing by being aggregated. The local group is not, and is handled separately.

## Goals / Non-Goals

**Goals:**

- One snapshot that is the sole input to the page, so what is rendered can be diffed, replayed and tested without the network.
- A page that ranks, rather than a page that merely lists — the top of it should be a worklist.
- Per-package failure isolation, matching the discipline `fail` and `report_failures` already set for the shell tools.
- A collection run that works with no mirrors, and says more when they are there.

**Non-Goals:**

- Real-time. The page is a daily reading with a timestamp on it, not a monitor.
- A query interface. Sorting and filtering one table is the whole interaction model.
- Retaining anything the source does not. When GitHub drops a run at ninety days, the strip gets shorter.

## Decisions

### The snapshot is the seam, and it is published too

Collection and rendering are two entry points over one versioned JSON document, not one script that fetches and writes HTML.

The alternative — render straight from the API — is shorter by a file and worse in every other way.
A snapshot makes the renderer a pure function, so the page can be iterated on offline against a fixture
instead of against forty-seven live repositories; it makes a failed collection leave the *previous* page standing;
and it is what the history is made of, so building it costs nothing extra.

That document is a deliverable and not an intermediate. It is published beside the page at a stable relative URL,
so the portfolio is readable by something other than an eye: a script, a `jq` one-liner, an agent deciding what to
work on next, or `r-pkg-maintain` if its portfolio-view track ever wants this as input rather than as a rival.
A page is a rendering of a fact; publishing only the rendering throws the fact away.

Being consumed by strangers is what makes it a contract, so it carries a `schema_version`, its field names are
stable, and a field is added or deprecated rather than repurposed. Every number the page displays is a field in
the document — nothing is computed in the browser that a consumer would then have to reimplement, the attention
score and its reasons included.

### Batched GraphQL for the repository facts, REST for the runs

One GraphQL query carries many repositories as aliased fields, and each one carries its issues, pull requests,
releases, default branch and last commit in the same round trip. Ten repositories per query keeps the response
readable and the node budget low, so the whole inventory is five queries rather than forty-seven times five REST calls.

Workflow runs stay on REST: the run history is paginated differently, is filtered by branch and event,
and is the one place a per-repository call is genuinely per-repository.

The resulting budget is low three figures against five thousand an hour, and a request count is a thing the collector
reports at the end, the way `clone` and `sync` report failures.

### Any token reads the public portfolio; the secret is only for what is private

Every entry in `repos.yml` today is a public repository, and public issues, releases and workflow runs are readable
with any valid credential — including the `GITHUB_TOKEN` that Actions mints for `repo-sync` itself, whose *write*
scope stops at this repository but whose reads do not.

That matters because most of the inventory is not the user's to grant: a fine-grained PAT can only be given access
to repositories its owner administers, and `r-lib`, `tidyverse`, `igraph` and `r-dbi` are not that.
So the design does not depend on one. A PAT is supported and documented — `actions-sync` already keeps a
`TOKEN_KEYS` secret and the same pattern applies — and it buys exactly one thing: entries that are private.
Where no credential can see a repository, the collector records it as unreadable and moves on.

### A failure is a stale cell, never a missing run

The collector loads the previous snapshot before it starts. A package it cannot read keeps its last known values,
each marked with the time it was actually observed; the page renders them greyed with that timestamp.
A run whose every package failed still writes a snapshot, and it is the old one with new timestamps on nothing.

This is the API-shaped version of what `fail` and `report_failures` do in the shell tools: record, continue, summarise,
exit non-zero. The exit status is for the scheduler; the page is for the human, and the human is better served by
forty-six fresh rows and one grey one than by yesterday's page or none.

### CI history comes from GitHub's retention, not from ours

The pass/fail strip is the last ninety days of runs on the default branch, read per run from the API.
Ninety days is what GitHub keeps, and keeping our own copy to extend it would mean storing run records daily
to answer a question about flakiness that ninety days already answers well.

Stored snapshots therefore exist for a different purpose: portfolio-level trend — how many packages were red,
how many were due a release, how many issues were open — which is a fact about the *reading*, not about any run,
and is unavailable from any API because nobody but us ever computed it.

### History lives on the deploy branch

Each published run writes its snapshot to `history/<timestamp>.json` on `gh-pages` and appends one line of
portfolio-level counters to a `history.jsonl` beside it.

`main` stays free of generated data. A branch that already exists to hold generated output is the natural place
for more of it, the page can fetch its own history as a relative URL with no API and no token,
and pruning is a delete on a branch nobody bisects.

### The attention score shows its work

Each package gets a score from weighted reasons — days red, a CRAN deadline, user-facing commits since the last
release scaled by their age, issues with no reply, pull requests awaiting review, template commits outstanding —
and the row displays *the reasons*, not just the number.

A composite that cannot be interrogated gets ignored the second time it is wrong, so the weights live in a
configuration file rather than in the code, and every contribution is visible next to the total.
Ranking is the only thing the score does: nothing is filed, closed, released or opened on its strength.

### Template position is measured by patch-id, and only locally

The mirrors and the template have unrelated histories — template changes arrive by cherry-pick — so "behind by N"
has no meaning and `git cherry` does: it compares patch-ids and reports which template commits have no equivalent
in the mirror.

Patch-id over two full histories is real work at forty-seven repositories, so the mirror side is bounded by date:
a commit authored before a template commit existed cannot be a copy of it.

This group is the one thing CI cannot compute — it would need every repository's history, which is what `mirrors/`
already is — so it is present when collection runs on a machine that has the mirrors and absent otherwise.
The page renders the section only when the snapshot carries it.

### Publishing drops the workspace group

Whether a mirror's tree is dirty, how many commits sit unpushed, whether a rebase is half-finished:
useful locally, and a description of unfinished work rather than of a package. Publication strips the group by name,
so a field added to it later is not published by having been forgotten.

The template lag itself is published — which public commit has reached which public repository is public either way.

### The page is a client over the snapshot

The published site is two files: `metrics.json`, and an `index.html` that fetches it at view time and formats it.
The HTML carries no data — reloading the page after a collection run shows the new reading without the page
having been rebuilt, and the file that is the machine-readable version is the same file the page is reading,
so the two can never disagree about what was measured.

`fetch` of a relative URL is same-origin on `gh-pages` and blocked under `file://`, which is exactly how the local
copy would be opened. So the page reads an inlined `<script type="application/json">` block when one is present and
fetches `metrics.json` when it is not: the local task inlines and produces one file that works on a double-click,
publication does not and produces two. One code path in the page, one fallback, and neither mode is the degraded one.

No framework and no CDN either way: sorting, filtering and the detail rows are a hundred lines of vanilla
JavaScript, and a dependency fetched at view time is a page that breaks when someone else's CDN does.

Not R and not rmarkdown, though `actions-sync` uses both. It uses them because it already *was* an R package
with R in CI; this repository is `mise`, Python and bash, and adding an R toolchain to run one template would be
copying the accident rather than the idea.

### What is deliberately not measured

- **Per-workflow CI status.** `actions-sync` renders a badge per workflow per repository and owns that view.
  This page reports the default branch's outcome and links to it.
- **Anything needing admin scope** — branch protection, secrets, settings. Most of the inventory is not ours to administer,
  so a column that is empty for two thirds of the rows is worse than no column.
- **File-level template divergence.** `cynkratemplate` is a whole R package; `DESCRIPTION` and `R/` are meant to differ.
  Without a manifest of which paths are shared, every package reports as wildly divergent. Commit provenance needs no such manifest.

## Risks / Trade-offs

- **Secondary rate limits, which are not the documented hourly one** → requests are serialised with backoff rather than fanned out;
  the collector is the one tool here that does not use `parallel`. A run that takes two minutes daily is not worth the risk of a 403.
- **CRAN has no stable machine-readable check API** → the exact source is confirmed during implementation against the live service,
  and the CRAN group degrades to empty rather than failing the run. No metric outside that group depends on it.
- **The score is wrong for somebody's package** → the weights are configuration and the reasons are visible, so being wrong is a tuning
  step and not a reason to distrust the page.
- **`DESCRIPTION` parsing is a partial R implementation** → only `Package` and `Version` are read, from a root file, with no dependency
  on R being installed. A repository without one simply has no package columns.
- **Forty-eight rows with detail is a large page** → detail rows render collapsed and the history is fetched only when a trend is opened.
- **A published page is a standing summary of somebody else's repository** → everything published is already public at its source,
  and the one group that is not is stripped by name at publication.

## Migration Plan

Additive throughout: no existing script, task, spec or mirror changes behaviour, so there is nothing to roll back into.

1. Collector and renderer land with local tasks only. The page is a file on disk; nothing is published.
2. `gh-pages` is created by the workflow on first run if absent, as `actions-sync`'s status job already does.
3. The scheduled workflow is enabled last, once a snapshot collected in CI has been compared against one collected locally.

Rollback is disabling the workflow. The branch can be deleted; nothing reads it but the page.

## Open Questions

- **Which CRAN endpoint.** Several expose check results and none is contractually stable. Decided at implementation
  against the live service; the requirement is stated in terms of the facts, not the source.
- **How long history is kept.** Starts unbounded because a JSON file a day is small, with pruning added if the branch
  becomes unwieldy. It affects nothing but the branch.
- **Whether `r-pkg-maintain` should own this instead.** Its charter names a *Portfolio view* track —
  "every package's CRAN status, CI status, unreleased changes, open issues, and last release" — which is this page.
  That initiative sequences the release track first and builds no other track until it is feature-complete,
  while the inventory and the orchestration are already here, so this is the cheaper place to build it today.
  Whether the track later consumes this page, replaces it, or narrows to the packages that repository manages
  is a cross-repository decision, and it changes nothing in these specs.
