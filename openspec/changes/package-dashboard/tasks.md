## 1. The snapshot contract

- [x] 1.1 Define the snapshot document: top-level schema version and collection timestamp, one entry per inventory entry keyed by slug, and one named group per metric family; verify a written snapshot round-trips through a parser and carries both top-level fields.
- [x] 1.2 Record the group names as data rather than as prose, so publication can strip a group by name; verify adding a field to the workspace group leaves it excluded from publication with no further change.
- [x] 1.3 Commit a fixture snapshot covering every shape the renderer must handle — fresh, stale, never-observed, not-an-R-package, no-CI, no-releases, mirrors-absent; verify the renderer test suite runs against it with no network.
- [x] 1.4 Write the field reference documenting each field's meaning and unit, and the add-or-deprecate rule; verify every field present in the fixture appears in it.

## 2. Collector: inventory and identity

- [x] 2.1 Read `repos.yml` through the same template-designation rules the shell tools use, rejecting the same malformed inventory; verify an inventory with zero and with two `template: true` entries each exit non-zero before any request is made.
- [x] 2.2 Emit one entry per inventory entry in inventory order; verify the entry count equals the inventory count and two runs produce the same order.
- [x] 2.3 Record default branch, description, visibility and archived state per repository; verify an archived repository is marked as such.
- [x] 2.4 Detect an R package from a root `DESCRIPTION` and take `Package` and `Version` from it; verify `duckdb/duckdb-r` yields the package name `duckdb`, and that a repository without a `DESCRIPTION` carries no package fields rather than a guess.
      **Verified against a recorded payload for that slug**: GitHub's API is unreachable from the implementation environment, so the live repository was not read.

## 3. Collector: GitHub metrics

- [x] 3.1 Batch the repository facts into aliased queries covering several repositories per request; verify the whole inventory is collected in a number of requests an order of magnitude below one per metric per package, and that the count is reported.
      The real forty-six-entry inventory costs five queries, which a run against the live API confirmed before it was refused the data.
- [x] 3.2 Collect the latest release, its date, and the commits on the default branch since it; verify a package with no release records the fields as absent rather than as zero.
- [x] 3.3 Classify those commits by Conventional Commits type, counting unrecognised subjects as unclassified; verify a mixed set of subjects lands in the expected buckets and the buckets sum to the total.
- [x] 3.4 Record whether an unpublished draft release exists where the credential has push access, and record the field as unavailable where it does not; verify a repository we can push to distinguishes a draft from none, and that one we cannot reports unavailable rather than none.
      **Verified against recorded payloads** carrying each `viewerPermission`; no live repository was readable to confirm it end to end.
- [x] 3.5 Collect the latest workflow conclusion on the default branch and the run series over the retention window; verify the series is ordered oldest-first and records the window actually covered.
- [x] 3.6 Derive success rate, median duration, consecutive-failure count and red-since timestamp from the series; verify three failing runs yield a count of three and the first one's timestamp, and that an alternating series is not recorded as consecutively failing while the latest run succeeded.
- [x] 3.7 Collect open issue and pull-request counts with the actionable cuts — no maintainer reply, beyond a configured age, outside contributors, bots, drafts, awaiting review — and the oldest age of each, identifying a maintainer reply by the comment's public author association rather than by a permission lookup; verify an empty tracker records zeros with the age fields absent, and that an owner's reply is distinguished from a stranger's without push access.
      The cuts are computed over the newest fifty of each, and the entry records how many were examined beside the totals; see `design.md`.
- [x] 3.8 Collect last commit date, commits in the recent window, distinct authors in the longer window, and the dormancy flag; verify a repository with no commit inside the dormancy period is marked dormant.

## 4. Collector: CRAN

- [x] 4.1 Confirm against the live service which endpoint exposes per-package check results and deadlines, and record the choice in `design.md`; verify the chosen source returns the expected shape for a package known to have a NOTE and for one known to be clean.
      Confirmed live against `tibble` (five NOTE flavours, eight OK) and `here` (thirteen OK), both recorded as fixtures.
      **The deadline half is not confirmed live**: no package under a deadline was reachable, so the pattern is parsed defensively and `design.md` says so.
- [x] 4.2 Collect the CRAN version, its release date, and the check results across flavours; verify a package ahead of CRAN records both versions and that the development version is marked ahead.
- [x] 4.3 Collect a CRAN deadline when one is set; verify a package under deadline records the date.
      **Verified against a fixture derived from the live page's shape**, for the reason 4.1 records.
- [x] 4.4 Degrade the CRAN group to unavailable when the source cannot be reached or its shape is unrecognised; verify that with the source blocked every non-CRAN metric is still collected and the run exits zero.

## 5. Collector: the mirrors

- [x] 5.1 Detect whether `mirrors/` is present and omit both mirror-derived groups when it is not, recording that they were not collected; verify a run on a machine with no mirrors exits zero and produces a snapshot with no template group.
- [x] 5.2 Compute outstanding template commits per mirror by patch identity, bounding the mirror side by the date of the oldest candidate; verify a commit cherry-picked into a mirror with a rewritten subject is reported as present, and that bounding does not change the result against an unbounded run on a fixture.
- [x] 5.3 Record the date of the oldest outstanding template commit; verify a mirror fully in step records none and no date.
- [x] 5.4 Record the workspace group per mirror — dirty tree, unpushed commits, operation in progress; verify a mirror with staged and unstaged changes and an interrupted cherry-pick records all three.
- [x] 5.5 Record a per-entry template group as uncollected when `mirrors/` exists but that mirror does not; verify the other entries still carry theirs.
- [x] 5.6 Verify collection never writes to a mirror — no command that touches a working tree, index or `HEAD` appears on the mirror path.
      Enforced by an allowlist that refuses a write subcommand before it runs, and checked by comparing every file in three mirrors before and after a collection.

## 6. Collector: resilience

- [x] 6.1 Load the previous snapshot before collecting and carry values forward for any package that cannot be read, stamping each with when it was last actually observed; verify one unreadable repository yields a stale entry, fresh entries for the rest, and a non-zero exit with the failure named.
- [x] 6.2 Record a package as never observed when it fails with no previous snapshot to fall back on; verify its fields are distinguishable from measured zeros.
- [x] 6.3 Write a snapshot even when every package fails; verify the run writes the file, marks every entry stale, and exits non-zero.
      Also observed for real: a run against the live API, which refuses it, wrote all forty-six entries as never observed and exited non-zero.
- [x] 6.4 Back off and retry on a rate-limit signal within a bounded number of attempts before recording the affected packages unreadable; verify a stubbed limit response is retried and then recorded rather than raised.
- [x] 6.5 Report the request count and the failure list at the end of a run, in the shape `report_failures` already uses; verify both appear for a run with one failure.
- [x] 6.6 Verify `mise run clone` and `mise run sync` are unaffected by a failing collector — neither imports from it nor changes behaviour when it is broken.
      Verified structurally: neither script, nor `lib.sh`, names anything this change adds, and both still parse.
      **Neither was run**: cloning needs SSH access to forty-six repositories, which this environment does not have.

## 7. Attention score

- [x] 7.1 Add a configuration file carrying the weights and the age thresholds, with documented defaults; verify changing one weight and re-running against unchanged inputs changes the scores and the ranking and nothing else.
- [x] 7.2 Compute the score from weighted reasons and record each reason with its individual contribution; verify the contributions sum to the total for every entry in the fixture.
- [x] 7.3 Score a clean package at zero with an empty reason list; verify a green, released, quiet package scores zero.
- [x] 7.4 Mark a score stale when it was computed from carried-forward values; verify a stale entry's score carries the mark.

## 8. Renderer and page

- [x] 8.1 Render a page from a snapshot with no network access; verify the same snapshot produces byte-identical output on repeated runs.
- [x] 8.2 Have the page read a fetched `metrics.json` when one is reachable and an embedded snapshot when it is not; verify the published shape picks up a replaced `metrics.json` on reload, and that the local file renders identically when opened directly from disk.
      **Verified in node against a stubbed DOM**, which runs the page's own JavaScript: the two sources produce identical tables and the embedded one is used without fetching.
      No browser was available, so `file://` blocking a fetch was not exercised as such.
- [x] 8.3 Say so plainly when neither source is available; verify the page renders a message rather than an empty table.
- [x] 8.4 Order by attention score by default and show each score's reasons beside it; verify the fixture's highest-scoring package is first and its reasons are visible without interaction.
- [x] 8.5 State that the portfolio is clear when every score is zero, rather than presenting an arbitrary order; verify with an all-zero fixture.
- [x] 8.6 Implement column sorting with absent values sorted together rather than as zero, and a text filter over identity that restates the aggregate counts while applied; verify both against the fixture.
- [x] 8.7 Distinguish measured, not-applicable and stale values visually, showing the observation time for stale ones; verify a non-R-package row reads as not applicable where a zero would mislead.
- [x] 8.8 Omit a group the snapshot does not carry, with a note saying it was not collected; verify a mirrors-absent fixture renders no template section and does not imply every package is in step.
- [x] 8.9 Render CI history as a per-package pass/fail series; verify a package with a short history renders the runs that exist rather than padding.
- [ ] 8.10 Link each row to the repository, its actions, its CRAN page where it has one, and `actions-sync`'s per-workflow page; verify every link resolves for the fixture's entries.
      The links are built and rendered, and each is a field in the snapshot rather than something the page assembles.
      **Not ticked because resolution was not verified**: only the CRAN links could be fetched from here (they do resolve);
      `github.com` and `krlmlr.github.io` are both refused by this environment's proxy.
      The `actions-sync` link is that site's page rather than a per-repository anchor in it — see `design.md`.
- [x] 8.11 Verify the page carries no framework and no externally fetched asset — no request leaves the origin when it is opened.
- [x] 8.12 Verify the page is legible at a narrow width, with the table scrolling rather than the document.
      **Verified structurally**: a viewport meta, the table inside its own scrolling container, and nothing declaring a width wider than a phone.
      Nobody looked at it in a browser.

## 9. Publication and history

- [x] 9.1 Strip the workspace group by name when preparing a snapshot for publication; verify no workspace field survives for any entry, including one added after the fact.
- [x] 9.2 Publish the page and the snapshot to the deploy branch, creating the branch on first run when it is absent; verify a run against a repository without the branch establishes it.
      Verified against a throwaway repository and bare remote in a temporary directory.
- [x] 9.3 Commit nothing when the output is identical to what is published; verify a second run against an unchanged reading adds no commit.
- [x] 9.4 Retain each published snapshot under its collection time and append the portfolio-level counters to a series beside it; verify two publications leave two retained snapshots and two series entries.
- [x] 9.5 Render the trend from that series and omit it when the series cannot be read; verify the current reading still renders in full with the series removed.
- [ ] 9.6 Add the scheduled workflow, with a manual trigger, reading the `GITHUB_TOKEN` Actions mints and storing no secret of its own; verify a manual run publishes and collects every public entry.
      The workflow is written, and its shape is checked: a schedule and a manual trigger, `contents: write`, the Actions-minted token and no other secret,
      collection allowed to fail without stopping publication, and the run still ending non-zero when something could not be read.
      **Not ticked because it has never run**: that needs Actions, and this environment cannot reach GitHub at all.
- [x] 9.7 Verify disabling the workflow leaves local collection and rendering working unchanged.
      Verified structurally: no script refers to the workflow, and the three tasks are the same code paths whether or not it exists.

## 10. Wiring

- [x] 10.1 Add the `metrics`, `dashboard` and `publish-dashboard` tasks to `mise.toml`, documenting their prerequisites as the existing tasks document theirs; verify `mise tasks` lists all three and each runs its script.
      A fourth task, `test`, runs the suite; the task-runner spec gained a scenario for it.
      `mise tasks` lists all four here. **`mise run` could not execute them**: `mise` cannot install the pinned Python in this environment,
      so each script was run directly instead.
- [x] 10.2 Confirm no HTTP client is needed beside `PyYAML`: `urllib.request` makes the JSON requests with a bearer token that both APIs want; verify the collector runs with `PyYAML` alone, that nothing outside the standard library is imported, and that the proposal's Impact line says so rather than naming a dependency.
      **Rewritten from "Add the HTTP client to `requirements.txt`"** once it was clear the standard library covers it; `requirements.txt` is unchanged but for a comment saying why.
- [x] 10.3 Read the credential from the environment, falling back to an existing `gh` login, and fail with a message naming both when neither is available; verify a run with no credential says what to do rather than reporting every package unreadable.
- [x] 10.4 Add `/reports/` to `.gitignore` beside `/mirrors/`; verify `git status` is clean after a local collect and render.
      `__pycache__/` too, which a collect leaves behind for the same reason.

## 11. End-to-end verification

- [ ] 11.1 Collect against the real inventory on a machine with mirrors, then render; verify every entry appears, the request count is reported, and the page opens from disk.
      **Not possible here**: there are no mirrors in this environment and cloning forty-six repositories is out of scope for the implementation.
- [ ] 11.2 Collect against the real inventory on a machine without mirrors; verify the run exits zero, both mirror-derived groups are absent, and every other group is populated.
      Half of this was observed: a run against the real inventory produced forty-six entries, five batched queries, and both mirror groups absent.
      **It exited non-zero with every package unreadable**, because this environment's proxy refuses GitHub's GraphQL API outright.
- [ ] 11.3 Verify a snapshot collected in CI and one collected locally agree on every group they both carry, for the same moment.
      **Not possible here**: neither collection can be run against the live services.
- [ ] 11.4 Verify the published snapshot is retrievable and parseable on its own, and that a value read from it matches what the page displays for that package.
      Nothing has been published. The equivalent against a throwaway remote is covered by 9.2 and 9.4, and that the page shows only fields of the document by 8.x.
- [ ] 11.5 Verify a package known to be failing CI surfaces near the top of the ranking with the failure among its reasons.
      **Not possible here**; the same behaviour against a fixture with a red package is covered by 7.2 and 8.4.
- [ ] 11.6 Verify a package known to be overdue a release surfaces with its unreleased commit counts among its reasons.
      **Not possible here**; covered against a fixture by 7.2.
- [ ] 11.7 Verify the whole collection stays within a low three-figure request count against the real inventory.
      A full run over the real inventory with recorded answers stays under two hundred requests, and the live attempt made the expected five batched queries before being refused.
      **A complete live run was not possible**, so this stays open.
- [ ] 11.8 Verify a published snapshot contains no workspace group after a publication run started from a machine with dirty mirrors.
      Covered against a fixture carrying a dirty workspace group and a throwaway remote in 9.1; **not done from a machine with real mirrors**.

## 12. Documentation

- [x] 12.1 Tick ROADMAP §2.5's bullets as each lands, and mark §2.2's report bullet delivered for its observable half while leaving classification open; verify both sections describe what actually ships. The non-goal's retirement and §2.5 itself landed with the proposal, so nothing here re-does them.
      §2.5's third bullet stays unticked in the ROADMAP: publication has landed but has never published.
- [x] 12.2 Document the credential: that one is required because GraphQL refuses anonymous requests, that it is `GITHUB_TOKEN` in CI and an existing `gh` login locally, and what declining a stored token costs — draft releases, maintainer precision by permission, private entries, headroom; verify the note matches what the workflow actually does.
- [x] 12.3 Record in `design.md` which CRAN source was chosen and what it returns; verify the Open Question is answered rather than left standing.
