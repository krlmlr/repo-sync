## Why

`repos.yml` knows forty-seven packages by name and nothing else about them.

Every question a maintainer actually asks is answered somewhere else, one repository at a time:
whether CI is red, how long it has been red, what has accumulated since the last CRAN release,
which issue has been waiting longest, whether a package has gone dormant.
The answers exist — GitHub and CRAN both publish them — but they exist forty-seven times over,
and the cost of the portfolio is that nobody visits forty-seven pages to find the two that need work.

[`actions-sync`](https://github.com/krlmlr/actions-sync) already showed the shape of the fix.
Its [status page](https://krlmlr.github.io/actions-sync/) is one table, one row per repository, rebuilt daily,
and it answers exactly one question: is the workflow green.
That question is the one that has aged best, because agents now fix most red builds before a human sees them.
What is left over is everything the page never covered.

This change is the same page for the rest of it.
The inventory is already here, the orchestration is already here,
and the one thing missing is the measurement.

## What Changes

- Add a **collector** that reads `repos.yml`, asks GitHub and CRAN about every entry,
  and writes one machine-readable snapshot of the whole portfolio.
- Measure per package, in seven groups:
  - **Identity** — default branch, description, archived, and whether the repository is an R package at all,
    taken from a root `DESCRIPTION` rather than from a hand-kept map,
    since `duckdb-r` ships `duckdb` and `rigraph` ships `igraph`.
  - **Release position** — latest release and its age, the commits on the default branch since it,
    classified by Conventional Commits prefix so that three `feat:` reads differently from twelve `chore:`,
    the CRAN version and its age, and whether a release-drafter draft is already open.
  - **CI, with history** — the latest conclusion per workflow on the default branch,
    the last ninety days of runs as a pass/fail strip, the success rate and median duration over that window,
    and, when red, how many runs in a row and since when.
  - **CRAN health** — the check result across flavours, and the deadline date when CRAN has set one.
  - **Issues and pull requests** — open counts, and the cuts that carry an action:
    issues with no maintainer reply, issues older than ninety days, pull requests from outside contributors,
    pull requests awaiting review, and the age of the oldest of each.
  - **Activity and lifecycle** — last commit, commits in the last ninety days, distinct authors in the last year,
    and a dormancy flag for a package that has had none.
  - **Template position** — the template commits not yet present in each mirror, by patch-id rather than by count,
    since the mirrors and the template have unrelated histories and cherry-pick equivalence is the only measure that means anything.
- Rank the portfolio by an **attention score** whose reasons are shown next to it,
  so the top of the page is a worklist and not a number nobody can check.
- Publish that snapshot as the deliverable it is, at a stable URL beside the page,
  so the portfolio is readable by a script, a `jq` one-liner or an agent and not only by an eye.
  It carries a schema version, its field names are stable, and every number the page shows is a field in it —
  nothing is computed in the browser that a consumer would have to reimplement.
- Add a **page** that is a client over that document: it fetches the JSON and formats it, sortable and filterable,
  with no build step, no framework and no CDN. The HTML holds no data, so a new reading needs no new page.
- Keep a **history** of snapshots on the deploy branch, so the page can show a trend and not only a reading.
- Publish both on a schedule, the way `actions-sync` publishes its own.

### The API is the point here, and was the problem there

`clone-without-api` took the GitHub API out of `clone` on purpose:
`gh repo clone` spent a GraphQL query per repository to resolve a name `repos.yml` already knew,
out of a budget shared with everything else, and a spent budget did not slow the run down, it ended it.

This change adds the API back, and the difference is not a reversal:

- **The data exists nowhere else.** Clone needed a URL it could have built. Nobody can derive an issue count from a slug.
- **It is off the critical path.** `clone` and `sync` gain nothing and lose nothing.
  A dashboard run that fails leaves a stale page, not an unmirrored portfolio.
- **It degrades instead of collapsing.** A package that cannot be read keeps its last known values, marked stale.
  The other forty-six still render.
- **It is one run.** Batched by GraphQL, the whole inventory costs a low three-figure request count against an hourly five thousand.

## Capabilities

### New Capabilities
- `package-metrics`: Collect per-package facts from GitHub, CRAN and the local mirrors into one versioned snapshot,
  isolating per-package failure so a portfolio-wide reading survives a repository that cannot be read.
- `status-dashboard`: Publish a snapshot as a machine-readable document and present it as a page that ranks the portfolio
  by what needs attention, retaining snapshots as history and publishing on a schedule.

### Modified Capabilities
- `task-runner`: the named-task requirement enumerates one scenario per script entry point, so it gains one for each new task.
  `reconcile-workspace` is open and modifies the same requirement, and a `MODIFIED` block replaces the whole of it:
  whichever of the two is archived second must carry the other's scenario forward, or it is silently dropped.

## Impact

- **New scripts** `scripts/collect_metrics.py` and `scripts/render_dashboard.py`, and a `mise` task for each.
- **A published contract**: `metrics.json` at a stable URL, versioned and consumable by anything that is not this page.
- **`scripts/lib.sh`**: nothing. The collector reads `repos.yml` through the same rules but does not clone, fetch or fan out over SSH.
- **`requirements.txt`**: an HTTP client beside `PyYAML`.
  No R and no rmarkdown, though `actions-sync` uses both: it was already an R package, and this repository is not.
- **`.gitignore`**: `/reports/`, beside `/mirrors/`.
- **`mise.toml`**: three named tasks.
- **New workflow** `.github/workflows/dashboard.yaml`, and a fine-grained read-only token as a secret, as `actions-sync` already keeps one.
- **`ROADMAP.md`**: §2.2's report bullet is partly delivered here, and the "public web UI" non-goal is retired — see below.
- **No changes** to `clone.sh`, `sync.sh`, `repos.yml`, the hook, or any mirror.

### The ROADMAP says this is out of scope

It does: *"Hosting a public web UI for the reconciliation reports"*, under **Out of scope (for now)**.
The parenthesis is doing real work there — it is a deferral, and this change is the decision to stop deferring.
The entry is removed rather than quietly contradicted, and §2.2's
*"Emit a report per repo and an aggregate summary across the inventory"*
is marked as delivered for the observable half.

What stays out is the other half: classification.
The page reports what is measurably true and never says a divergence is fine.

## Out of Scope

- **Classifying divergence** as clean, conflicting or intentional.
  That is ROADMAP §2.2 proper, and it needs a judgement this change does not have.
- **Acting on anything.** No issue is triaged, no release is cut, no pull request is opened.
  The page ranks work; a human or an agent does it.
- **Re-deriving CI status per workflow file.** `actions-sync` owns the workflow inventory and links a badge per workflow.
  This page reports the default branch's outcome and links there rather than duplicating it.
- **Publishing local workspace state.** A dirty tree or an unpushed commit is a fact about the laptop rather than about the package,
  and it names work in progress. It is collected, shown locally, and dropped on publish.
- **A hand-kept map from repository to CRAN package.** The name comes from `DESCRIPTION` or the package columns stay empty.
- **Longer retention than the deploy branch gives.** History is snapshots on `gh-pages`; no database, no external service.
