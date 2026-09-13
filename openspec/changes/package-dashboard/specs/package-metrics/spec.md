## Purpose

Collect what is true about every package in the inventory — from GitHub, from CRAN, and from the local mirrors when they are
present — into one versioned snapshot, so that the portfolio can be read in one place by a person or by a program, and so that
a repository which cannot be read costs one stale row rather than the whole reading.

## ADDED Requirements

### Requirement: One snapshot for the whole inventory

The system SHALL produce a single machine-readable document containing one entry per `repos.yml` entry, carrying a schema
version and the time collection ran. The document SHALL be the sole input to anything that presents these metrics, and every
value presented SHALL be a field in it rather than a computation performed by a consumer.

#### Scenario: Every inventory entry is represented

- **WHEN** collection completes against an inventory of N entries
- **THEN** the snapshot contains exactly N package entries, each identified by its `<org>/<repo>` slug

#### Scenario: Schema version accompanies the data

- **WHEN** a snapshot is written
- **THEN** it carries a schema version and a collection timestamp at the top level

#### Scenario: Deterministic ordering

- **WHEN** collection runs twice against an unchanged inventory
- **THEN** the entries appear in the same order, sorted as `repos.yml` is sorted

#### Scenario: A consumer needs no second source

- **WHEN** a consumer reads the snapshot
- **THEN** every metric described by this capability is present as a named field, including derived values such as ages, rates and scores

### Requirement: Repository identity and R-package detection

The system SHALL record each repository's default branch, description, visibility and archived state, and SHALL determine
whether the repository is an R package from a `DESCRIPTION` file at its root. The package name and version SHALL be taken
from that file. A repository without one SHALL carry no package-level fields rather than a guessed name.

#### Scenario: Package name differs from repository name

- **WHEN** the repository `duckdb/duckdb-r` has a root `DESCRIPTION` declaring `Package: duckdb`
- **THEN** the entry records the package name `duckdb` and uses it for every package-level lookup

#### Scenario: Repository is not an R package

- **WHEN** a repository has no root `DESCRIPTION`
- **THEN** the entry is marked as not an R package and the package, release-version and CRAN fields are absent

#### Scenario: Archived repository

- **WHEN** a repository is archived upstream
- **THEN** the entry records that, so presentation can separate it from active work

### Requirement: Release position

The system SHALL record, per package, the most recent release and its age, the number of commits on the default branch since
that release classified by Conventional Commits type, and the version and release date currently on CRAN. Where the credential
in use has push access to the repository, the system SHALL also record whether an unpublished draft release exists; where it
does not, that field SHALL be recorded as unavailable rather than as absent, since draft releases are not public.

#### Scenario: Unreleased commits are classified

- **WHEN** the default branch carries commits after the latest release tag
- **THEN** the entry records the total and a per-type breakdown, with commits whose subject has no recognised prefix counted as unclassified

#### Scenario: Development version ahead of CRAN

- **WHEN** the `DESCRIPTION` version is higher than the version CRAN serves
- **THEN** the entry records both versions and that the development version is ahead

#### Scenario: Draft release is not visible

- **WHEN** the credential in use has no push access to a repository
- **THEN** the draft-release field is recorded as unavailable, distinct from a recorded absence of a draft

#### Scenario: Package has never been released

- **WHEN** a repository has no releases and no CRAN entry
- **THEN** the release fields are recorded as absent and the entry is not treated as overdue for a release

### Requirement: Continuous-integration status and history

The system SHALL record, per package, the most recent workflow conclusion on the default branch, the runs from the retention
window the source offers as an ordered pass/fail series, the success rate and median duration across that window, and — when
the latest run failed — how many consecutive runs have failed and when the first of them ran.

#### Scenario: Currently failing

- **WHEN** the three most recent runs on the default branch all concluded as failures
- **THEN** the entry records the failing state, a consecutive-failure count of three, and the timestamp of the first of the three

#### Scenario: History shorter than the window

- **WHEN** the source retains fewer runs than the requested window
- **THEN** the series contains what the source retains, and the window actually covered is recorded alongside it

#### Scenario: No workflows

- **WHEN** a repository runs no workflows on its default branch
- **THEN** the CI fields are recorded as absent, and the entry is not counted as failing

#### Scenario: Flaky rather than broken

- **WHEN** runs in the window alternate between success and failure
- **THEN** the success rate reflects the mix, and the entry is not recorded as consecutively failing while the latest run succeeded

### Requirement: CRAN check health

The system SHALL record, per CRAN package, the check results across flavours and any deadline CRAN has set. Where the check
results cannot be obtained, the system SHALL record the group as unavailable and SHALL NOT fail the run or affect any other
metric.

#### Scenario: Deadline set

- **WHEN** CRAN publishes a deadline for a package
- **THEN** the entry records the deadline date

#### Scenario: Results unavailable

- **WHEN** the CRAN check source cannot be reached or its shape is not recognised
- **THEN** the CRAN group is recorded as unavailable, the run continues, and every non-CRAN metric for that package is still collected

### Requirement: Issues and pull requests

The system SHALL record, per repository, the number of open issues and open pull requests, and the subsets that carry an
action: issues with no maintainer reply, issues untouched beyond a configured age, pull requests from outside contributors,
pull requests opened by bots, draft pull requests, and pull requests awaiting review beyond a configured age. The age of the
oldest open issue and of the oldest open pull request SHALL be recorded.

#### Scenario: Unanswered issue

- **WHEN** an open issue has no comment from anyone with write access
- **THEN** it is counted among the issues with no maintainer reply

#### Scenario: Bot pull requests are separated

- **WHEN** open pull requests include ones opened by an automation account
- **THEN** those are counted separately from the ones opened by people

#### Scenario: Empty tracker

- **WHEN** a repository has no open issues and no open pull requests
- **THEN** the counts are recorded as zero and the oldest-age fields are absent

### Requirement: Activity and dormancy

The system SHALL record the date of the most recent commit on the default branch, the number of commits in a recent window,
and the number of distinct authors over a longer window, and SHALL mark a package dormant when it has had no commit within a
configured period.

#### Scenario: Dormant package

- **WHEN** a repository's default branch has had no commit within the configured dormancy period
- **THEN** the entry is marked dormant and records the date of its last commit

#### Scenario: Active package

- **WHEN** a repository has commits within the window
- **THEN** the entry records the count and the distinct author count, and is not marked dormant

### Requirement: Template position from the local mirrors

When the mirrors are present on the machine running collection, the system SHALL record, per package, which template commits
have no equivalent in the mirror and the date of the oldest such commit. Equivalence SHALL be determined by patch identity,
because the mirrors and the template have unrelated histories. When the mirrors are absent, the system SHALL omit the group
and complete successfully.

#### Scenario: Cherry-picked commit counts as present

- **WHEN** a template commit has been cherry-picked into a mirror and its subject or hash has since changed
- **THEN** it is recorded as present in that mirror and is not listed as outstanding

#### Scenario: No mirrors on this machine

- **WHEN** collection runs where `mirrors/` does not exist
- **THEN** the template group is omitted from every entry, the snapshot records that it was not collected, and the run exits zero

#### Scenario: Mirror missing for one entry

- **WHEN** `mirrors/` exists but one inventory entry has no mirror in it
- **THEN** that entry's template group is recorded as uncollected while the other entries carry theirs

### Requirement: Workspace state is collected locally and never published

The system SHALL record, per mirror, whether its working tree is dirty, how many commits are unpushed, and whether a rebase,
merge or cherry-pick is in progress, as a group distinguishable by name. Publication SHALL remove that group by name, so that
a field added to it later is excluded without further change.

#### Scenario: Local snapshot carries workspace state

- **WHEN** collection runs on a machine with mirrors and one mirror has uncommitted changes
- **THEN** that mirror's entry records the dirty state in the workspace group

#### Scenario: Published snapshot omits the group

- **WHEN** a snapshot is prepared for publication
- **THEN** no workspace group appears in it, for any entry, whatever fields that group contained

### Requirement: A failure is a stale value, not a missing run

The system SHALL isolate failure per package. When a package cannot be read, the system SHALL carry forward the values from
the previous snapshot, each marked with the time it was last actually observed, and SHALL continue with the remaining
packages. The run SHALL report which packages failed and exit non-zero, having written a snapshot regardless.

#### Scenario: One unreadable repository

- **WHEN** one repository cannot be read and the rest can
- **THEN** that entry carries its last observed values marked stale, the others are fresh, and the run exits non-zero naming the failure

#### Scenario: No previous snapshot to fall back on

- **WHEN** a package cannot be read and no previous snapshot exists
- **THEN** its entry records that it has never been observed, rather than carrying absent values that would read as zero

#### Scenario: Every package fails

- **WHEN** no package can be read
- **THEN** a snapshot is still written, every entry is marked stale, and the run exits non-zero

### Requirement: Bounded, off-path API usage

The system SHALL keep collection off the critical path of cloning and syncing, SHALL batch remote queries so that the whole
inventory costs an order of magnitude fewer requests than one per metric per package, SHALL report the number of requests
made, and SHALL back off and retry rather than fail when the remote signals that it is being asked too often.

#### Scenario: Request count reported

- **WHEN** collection completes
- **THEN** the number of requests made is reported, as failures already are

#### Scenario: Rate limited

- **WHEN** the remote signals a rate limit
- **THEN** the system waits and retries within a bounded number of attempts before recording the affected packages as unreadable

#### Scenario: Cloning is unaffected

- **WHEN** collection is failing for any reason
- **THEN** `mise run clone` and `mise run sync` behave exactly as they did before this capability existed

### Requirement: Attention score with visible reasons

The system SHALL compute, per package, a score expressing how much it needs attention, together with the individual reasons
contributing to it and each reason's contribution. Both the score and the reasons SHALL be fields in the snapshot. The
weights SHALL be read from configuration rather than fixed in code. The score SHALL rank only; no action SHALL be taken on
its strength.

#### Scenario: Reasons accompany the score

- **WHEN** a package scores above zero
- **THEN** its entry lists each contributing reason with its individual contribution, and the contributions account for the total

#### Scenario: Nothing needs attention

- **WHEN** a package is green, released, has no waiting issues or pull requests and no outstanding template commits
- **THEN** its score is zero and its reason list is empty

#### Scenario: Weights are configuration

- **WHEN** a weight is changed in configuration and collection is re-run against unchanged inputs
- **THEN** the scores and the ranking change accordingly, with no change to any other field

#### Scenario: Stale data does not inflate a score

- **WHEN** a package's values were carried forward because it could not be read
- **THEN** its score is recorded as stale alongside the values it was computed from
