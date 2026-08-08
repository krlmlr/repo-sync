## ADDED Requirements

### Requirement: Mirrors are synced several at a time

The system SHALL rebase and fetch more than one mirror at once, since each
mirror talks only to its own upstream and to the template's bare mirror, and
never to another mirror. The number worked on at once SHALL default to 8 and
SHALL be settable with the `REPO_SYNC_JOBS` environment variable, where `1`
reduces the run to one mirror at a time.

Each mirror's `git pull --rebase` and its `template` fetch SHALL stay together,
so that the rule that the second is attempted even when the first fails holds
per mirror rather than per run.

The output of each mirror SHALL be kept together rather than interleaved with
the other mirrors', so a rebase that stopped on a conflict can be read without
being reassembled from lines scattered across the run.

#### Scenario: Mirrors synced concurrently

- **WHEN** `sync` runs over a populated `mirrors/` tree with more than one
  mirror
- **THEN** several mirrors are rebased and fetched at the same time, and the run
  takes materially less wall clock than syncing them one after another

#### Scenario: Reduced to one at a time

- **WHEN** `REPO_SYNC_JOBS=1`
- **THEN** the run performs the same work on the same mirrors, one at a time,
  and reaches the same result

#### Scenario: Rebase failure does not stop that mirror's template fetch

- **WHEN** a mirror's rebase fails while other mirrors are being synced beside it
- **THEN** that mirror's `template` remote is still fetched, and the other
  mirrors are unaffected

#### Scenario: One mirror's output stays together

- **WHEN** several mirrors are being synced at once and one of them fails
- **THEN** that mirror's output is printed as one block, not split across the
  output of the mirrors running beside it

#### Scenario: Mirror synced by itself

- **WHEN** the operator names a single mirror to sync
- **THEN** exactly that mirror is rebased and its `template` remote fetched, by
  the same steps the batch would have applied to it, so a failure seen in a
  batch can be reproduced on its own

### Requirement: GNU parallel is required and checked for

The system SHALL verify before any mirror is touched that GNU parallel is
available, and SHALL exit non-zero naming what to install if it is absent or if
the `parallel` on `PATH` is a different program of the same name, matching the
`clone` capability so both tools reject the same incomplete environment.

#### Scenario: GNU parallel absent

- **WHEN** no `parallel` is on `PATH`
- **THEN** the run exits non-zero with a message naming the package to install,
  before any mirror is fetched or rebased

#### Scenario: A different `parallel` on PATH

- **WHEN** the `parallel` on `PATH` is not GNU parallel
- **THEN** the run exits non-zero saying so, rather than letting every job in
  the batch fail with the same usage error

## MODIFIED Requirements

### Requirement: Refresh the template's bare mirror first

The system SHALL fetch the template's bare mirror at
`mirrors/<template-org>/<template-repo>.git` before any mirror fetches from it,
so the template refs the mirrors receive are the ones the upstream has. That
fetch SHALL be a barrier: no mirror SHALL be started until it has finished,
whatever its outcome. The bare mirror carries no `.git` entry, and so is not
reachable by a sweep that discovers repositories by their working tree;
refreshing it is this capability's responsibility and no other's.

Whether the bare mirror can be fetched from SHALL be determined from the
repository on disk rather than carried as state through the run, so every
process that asks reaches the same answer.

#### Scenario: Bare mirror refreshed before the template fetches

- **WHEN** sync runs against a populated `mirrors/` tree
- **THEN** the bare mirror is fetched before any mirror fetches its `template`
  remote, and every mirror ends the run with the template refs the upstream has

#### Scenario: No mirror overlaps the bare fetch

- **WHEN** the mirrors are synced several at a time
- **THEN** none of them is started until the bare mirror's fetch has finished,
  so no mirror can fetch template refs that the bare mirror was about to replace

#### Scenario: Bare mirror missing

- **WHEN** `mirrors/<template-org>/<template-repo>.git` does not exist
- **THEN** the run records a failure naming `mise run clone` as the repair,
  skips the per-mirror `template` fetches rather than failing each one against
  a path that does not resolve, and still rebases the mirrors

#### Scenario: Bare path occupied by a non-bare repository

- **WHEN** a directory exists at the bare mirror's path but is not a bare
  repository
- **THEN** the run records a failure and does not fetch into it

#### Scenario: Missing bare mirror reported once

- **WHEN** the bare mirror is missing or is not a bare repository
- **THEN** the run says so once, rather than once per mirror that would have
  fetched from it

#### Scenario: Stale bare mirror still usable

- **WHEN** the fetch of the bare mirror fails
- **THEN** the run records the failure and continues to fetch `template` in the
  mirrors, since the refs the bare mirror already holds remain readable

### Requirement: Failures are isolated

The system SHALL continue processing the remaining mirrors when one step fails,
report every failure at the end, and exit non-zero. Failures SHALL be collected
across every mirror worked on, including those processed concurrently in
separate processes, so the final report accounts for the whole run. The report
SHALL list them in a stable order, independent of the order the mirrors
happened to finish in.

#### Scenario: One mirror unreachable

- **WHEN** one mirror's pull or fetch fails
- **THEN** the run logs the failure, continues with the rest, and exits non-zero
  after all mirrors are processed with a summary listing every failure

#### Scenario: Failure raised while other mirrors are in flight

- **WHEN** a mirror fails while others are still being synced
- **THEN** the others run to completion, and the failure is named in the report
  at the end of the run

#### Scenario: Report is stable

- **WHEN** the same set of mirrors fails on two runs
- **THEN** both runs print the same report, in the same order

#### Scenario: Clean run

- **WHEN** every mirror pulls and fetches successfully
- **THEN** the run exits zero

#### Scenario: Idempotent run

- **WHEN** sync is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero
