# The portfolio dashboard

One reading of every package in `repos.yml` a day, as a document a program can read and a page a person can scan.

Three tasks and one file between them:

- `mise run metrics` collects a snapshot into `reports/metrics.json`,
  from GitHub, from CRAN, and from `mirrors/` when they are on this machine.
- `mise run dashboard` renders `reports/index.html` from that snapshot.
  It collects nothing, needs no network, and inlines the reading, so the file opens from disk on a double-click.
- `mise run publish-dashboard` pushes the page and the snapshot to the deploy branch,
  having first removed the group that describes this machine rather than the packages.

The snapshot is the seam. The renderer is a pure function of it, which is what lets the page be worked on offline against a fixture;
a failed collection leaves the previous page standing; and the history is made of snapshots, so keeping one costs nothing extra.

## The credential

A credential is required, and a stored secret is not.

GitHub's GraphQL API refuses anonymous requests outright, and batching is the thing that makes reading forty-six repositories cost five
queries rather than two hundred, so there is no anonymous mode to fall back to. Unauthenticated REST would be sixty requests an hour
against an inventory that needs more than that in one run.

Where the credential comes from:

- **In Actions**, the `GITHUB_TOKEN` that `.github/workflows/dashboard.yaml` is given. Its *write* scope stops at this repository,
  which is what publishing to the deploy branch needs; its reads reach public issues, pull requests, releases, commits and workflow runs
  anywhere, which is what collecting needs.
- **Locally**, `GITHUB_TOKEN` or `GH_TOKEN` from the environment if either is set, and otherwise an existing `gh` login, read at run time
  with `gh auth token`.
- **With neither**, the run says so and stops, naming both ways of providing one. It does not report forty-six unreadable packages.

Neither is a secret this project keeps, rotates, or can leak. What declining a stored fine-grained token costs:

- **Draft releases**, which GitHub returns only to a caller with push access. Most of the inventory is not ours to push to, so this is
  lost for most of it whatever token is used; the field is recorded as `unavailable` rather than as `none` where we cannot see.
- **Maintainer identification by permission**, which needs push access. It degrades rather than disappears: `author_association` is public
  on every comment, so an owner's reply is still distinguishable from a stranger's.
- **Private entries**, if the inventory ever holds one. A fine-grained token reaches only repositories its owner administers.
- **Headroom** — a thousand requests an hour rather than five thousand, against a budget in the low hundreds.

## What the snapshot contains

`metrics.json` carries a schema version, the time collection ran, and one entry per inventory entry keyed by `<org>/<repo>`.
Every number the page displays is a field here: nothing is computed during display that a consumer would have to reimplement.

**The contract**: field names are stable across publications. A metric whose definition changes such that an existing field would mean
something new is published as a *new* field, and the old one is marked deprecated — a field is added or deprecated, never repurposed.

### Top level

- `schema_version` — integer. Bumped when an entry's shape changes incompatibly; a reader that does not recognise it should stop.
- `collected_at` — UTC timestamp, seconds, `Z`. When this run started.
- `template_slug` — the inventory's template entry.
- `groups` — the names of the metric families, in the order the page presents them. Publication removes `workspace` from this list.
- `groups_collected` — which mirror-derived groups this run could collect:
  `template` and `workspace`, both false where `mirrors/` is absent.
- `requests` — requests made, by kind (`graphql`, `rest`, `cran`) and `total`.
- `failures` — the slugs that could not be read, sorted.
- `packages` — the entries, keyed by slug, in inventory order.
- `portfolio` — the reading as a whole: `packages`, `stale`, `ci_failing`, `cran_not_ok`, `unreleased_commits`, `open_issues`,
  `open_pull_requests`, `issues_no_maintainer_reply`, `dormant`, `attention_total`. One of these objects per publication is what the
  history series is made of.

### An entry

- `slug`, `org`, `repo`, `is_template` — who this is, from the inventory.
- `observed_at` — when these values were actually measured, which is *not* `collected_at` for a carried-forward entry.
- `stale` — true when the values were carried forward because the package could not be read this run.
- `never_observed` — true when it could not be read and there was no previous reading to carry forward. Its groups are `null`, which is
  distinguishable from a measured zero.
- `error` — why it could not be read, when it could not.

Then one group per metric family. A group is `null` when it was not collected at all.

### `identity`

- `default_branch`, `description`, `url`, `visibility` (`public` or `private`), `archived`.
- `is_r_package` — whether a `DESCRIPTION` exists at the repository root. `package` and `version` come from that file, and are `null`
  without one: the package name is never guessed from the repository name, because `duckdb-r` ships `duckdb` and `rigraph` ships `igraph`.
- `viewer_can_push` — whether the credential in use has push access, which is what makes draft releases visible.
- `links` — `repository`, `actions`, `actions_sync`. Links are fields so that a consumer that is not the page reaches the same places.

### `release`

- `latest_tag`, `latest_url`, `latest_published_at`, `latest_age_days` — the most recent *published* release; a draft is not one.
- `commits_since` — commits on the default branch newer than that release, from the recent history the batch already carries.
  `commits_since_truncated` is true when every commit fetched was newer than the release, so the true count may be higher.
- `commits_by_type` — those commits by Conventional Commits type, with unrecognised subjects under `unclassified`. The buckets sum to
  `commits_since`.
- `oldest_unreleased_at` — when the oldest of them was committed, which is what the score scales by.
- `draft_release` — `present`, `none`, or `unavailable` where the credential cannot see drafts. Three states, because a draft we cannot
  see is not a draft that is not there.
- `cran_version`, `cran_published_at`, `cran_age_days`, `ahead_of_cran` — where CRAN stands against the development version.

### `ci`

- `latest_conclusion`, `latest_run_at`, `latest_run_url` — the most recent run on the default branch.
- `runs` — the series, oldest first, each with `workflow`, `conclusion`, `status`, `created_at`, `duration_seconds` and `url`.
- `window_days` — the window asked for.
  `window_from` and `window_to` are the window actually covered, which is shorter for a quiet package.
- `success_rate` — passes over runs that concluded either way; a cancelled run counts towards neither.
- `median_duration_seconds`, `consecutive_failures`, `red_since` — the last two are zero and `null` whenever the latest run passed,
  so a flaky package is not recorded as a broken one.

### `cran`

- `state` — `available` (a reading), `absent` (the package is not on CRAN), or `unavailable` (CRAN could not be read this run).
- `package`, `version`, `published_at` — from the `DESCRIPTION` CRAN serves.
- `flavours` — one entry per check flavour, each with `flavour`, `version` and `status`.
- `status_counts`, `worst_status` — the statuses across flavours, keyed by status and ranked worst first:
  `ERROR`, `FAIL`, `WARN`, `NOTE`, `OK`.
- `deadline` — the date CRAN has set, when it has set one.
- `checked_at` — when CRAN last updated that page.
- `package_url`, `checks_url` — where a reader goes to see the same thing.

### `tickets`

- `open_issues`, `open_pull_requests` — the totals GitHub reports.
- `issues_sampled`, `pull_requests_sampled` — how many were actually examined for the cuts below. The cuts describe the sample, and the
  sample is the newest N; a repository with more open issues than that has cuts that are a floor rather than a count.
- `issues_no_maintainer_reply` — open issues with no comment from an owner, member or collaborator. A thread longer than the comments
  fetched is not counted, because an unknown is not a finding.
- `issues_stale`, `issues_stale_after_days` — open issues untouched beyond the configured age.
- `pull_requests_outside`, `pull_requests_bot`, `pull_requests_draft` — who opened what.
- `pull_requests_awaiting_review`, `pull_requests_review_after_days` — not draft, no review, no decision, older than the configured wait.
  The cuts overlap on purpose: a bot's pull request nobody has looked at in a month is waiting on us as much as a stranger's.
- `oldest_issue_age_days`, `oldest_pull_request_age_days` — absent rather than zero when there are none.

### `activity`

- `last_commit_at`, `last_commit_age_days`.
- `commits_recent`, `commits_recent_window_days` — commits on the default branch inside the recent window.
- `authors_recent`, `authors_window_days`, `authors_truncated` — distinct authors over the longer window, by login where GitHub knows one.
- `dormant`, `dormancy_days` — no commit within the configured period.

### `template`, collected only where the mirrors are

- `collected` — false, with a `reason`, for a mirror that is not on this machine and for the template itself.
- `template_ref` — the ref in the mirror that holds the template's default branch.
- `outstanding` — template commits with no equivalent in the mirror, by **patch identity**: the two histories are unrelated, so a commit
  that was cherry-picked and then amended counts as present.
- `outstanding_commits` — the first twenty of them, each with `sha`, `authored_at` and `subject`.
- `oldest_outstanding_at` — `null` for a mirror that is in step.
- `bounded_from` — the date the mirror side of the comparison was bounded at. A mirror commit older than the oldest template commit
  cannot be a copy of one, and computing patch identity over two full histories forty-six times is work for no answer.

### `workspace`, collected locally and never published

- `dirty`, `staged`, `unstaged`, `untracked`, `unpushed`, `upstream`, `operation_in_progress`.

Publication removes this group **by name**, for every entry, so a field added to it later is excluded by having been added to a group that
is already stripped. It describes unfinished work on a laptop rather than anything about a package.

### `score`

- `value` — the sum of the contributions below, and nothing else.
- `stale` — true when it was computed from carried-forward values.
- `reasons` — one per thing that is actually true about the package, each with `code`, `label`, `detail` and `contribution`.
  The contributions sum to `value`, so a ranking can be checked rather than trusted.
- A reason's `detail` names the numbers behind it: `days` and `consecutive_failures` for a red build,
  `deadline` and `days_remaining` for a CRAN deadline, `feat`, `fix` and `oldest_age_days` for unreleased work,
  `issues` for unanswered issues, `pull_requests` for reviews owed, and `commits` with `oldest` for template commits outstanding.

The reasons are `ci_red`, `cran_deadline`, `unreleased`, `issues_no_reply`, `prs_awaiting_review` and `template_outstanding`.
The weights and windows that produce them are in [`dashboard.yml`](../dashboard.yml), not in the code:
change one and re-run `python3 scripts/collect_metrics.py --rescore reports/metrics.json`, which rescores an existing snapshot and
collects nothing. The score ranks and does nothing else — nothing is filed, closed, released or opened on its strength.

## Publication and history

`mise run publish-dashboard` pushes to `gh-pages`, creating the branch on first run if it is not there, and commits only when the output
differs from what is published — the publication history records changes rather than runs.

What lands on the branch:

- `index.html`, the page. It carries no data: it fetches `metrics.json` at view time, so a new collection is visible on reload without
  the page being rebuilt.
- `metrics.json`, the published snapshot, with the workspace group stripped.
- `history/<collected_at>.json`, that snapshot retained under its collection time.
- `history.jsonl`, one line of portfolio-level counters per reading, which is what the page's trend is drawn from.

The pass/fail strip comes from GitHub's own ninety-day retention rather than from ours: keeping run records to extend it would be
storing data daily to answer a question ninety days already answers. The stored snapshots answer a different question — how the
*portfolio* moved — which no API holds, because nobody but us ever computed it.

Publication is reversible: disable the workflow and local collection and rendering are unaffected; delete the branch and nothing but
the page is gone.

## Tests

`mise run test` runs the suite, and every test runs offline:

- GitHub and CRAN are replaced by recorded answers through the transport the collector talks to, so the batching, the derivations and
  the failure isolation are exercised without a network.
- CRAN parsing runs against pages recorded from the live service — one package with NOTEs and one clean. The deadline fixture is derived
  from that shape rather than recorded, because no package with a live deadline was reachable when the fixtures were made.
- The mirror groups run against real git repositories built in a temporary directory, and the publication against a throwaway remote.
- The page's JavaScript runs in node against the fixture snapshots, which is where the ranking, the sorting, the filter and the
  absent-versus-stale distinction are checked.

`python3 tests/make_fixtures.py` regenerates the committed fixture snapshots after a schema change; `tests/test_fixtures.py` fails while
they are out of date.
