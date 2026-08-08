## ADDED Requirements

### Requirement: Mirrors are processed several at a time

The system SHALL work on more than one repository at once, since each mirror's
clone or update is independent of every other's and spends most of its duration
waiting on the network. The number worked on at once SHALL default to 8 and
SHALL be settable with the `REPO_SYNC_JOBS` environment variable, where `1`
reduces the run to one repository at a time.

The output of each repository SHALL be kept together rather than interleaved
with the other repositories', so a failure can be read without being
reassembled from lines scattered across the run.

#### Scenario: Inventory mirrored concurrently

- **WHEN** `clone` runs over an inventory of more than one non-template entry
- **THEN** several of them are cloned or updated at the same time, and the run
  takes materially less wall clock than mirroring them one after another

#### Scenario: Degree of concurrency chosen by the operator

- **WHEN** `REPO_SYNC_JOBS` is set to a number
- **THEN** that many repositories are worked on at once

#### Scenario: Reduced to one at a time

- **WHEN** `REPO_SYNC_JOBS=1`
- **THEN** the run performs the same work on the same mirrors, one repository at
  a time, and reaches the same result

#### Scenario: One repository's output stays together

- **WHEN** several repositories are being mirrored at once and one of them fails
- **THEN** that repository's output is printed as one block, not split across
  the output of the repositories running beside it

#### Scenario: Repository worked on by itself

- **WHEN** the operator names a single mirror to create or update
- **THEN** exactly that mirror is processed, by the same steps the batch would
  have applied to it, so a failure seen in a batch can be reproduced on its own

### Requirement: GNU parallel is required and checked for

The system SHALL verify before any mirror is touched that GNU parallel is
available, and SHALL exit non-zero naming what to install if it is absent or if
the `parallel` on `PATH` is a different program of the same name.

#### Scenario: GNU parallel absent

- **WHEN** no `parallel` is on `PATH`
- **THEN** the run exits non-zero with a message naming the package to install,
  before any mirror is cloned or updated

#### Scenario: A different `parallel` on PATH

- **WHEN** the `parallel` on `PATH` is not GNU parallel
- **THEN** the run exits non-zero saying so, rather than letting every job in
  the batch fail with the same usage error

## MODIFIED Requirements

### Requirement: Process the template mirror first

The system SHALL finish cloning or updating the entry flagged `template: true`
— both its checkout and its bare mirror — before it begins processing any
non-template entry, so the local path used by `template` remotes always
resolves on disk after a successful run. This SHALL hold as a barrier rather
than as an ordering within a single pass: no non-template entry SHALL be
started while either of the template's mirrors is still being made.

The template's two mirrors are independent clones of one upstream, so they MAY
be made at the same time as each other, and a failure in one SHALL NOT prevent
the other from being attempted.

#### Scenario: Template processed first on fresh run

- **WHEN** `clone.sh` runs against an empty `mirrors/` directory
- **THEN** the template's checkout and its bare mirror are created before any
  non-template entry, so each subsequent `git remote add template
  ../../<template-org>/<template-repo>.git` resolves to an existing repository

#### Scenario: No mirror overlaps the template's

- **WHEN** the inventory is mirrored several repositories at a time
- **THEN** no non-template mirror is begun until both of the template's mirrors
  have finished, successfully or otherwise

#### Scenario: Both mirrors of the template at once

- **WHEN** the template's checkout and bare mirror are made
- **THEN** they may be made concurrently, and each reports its own outcome

### Requirement: Failures are isolated

The system SHALL continue processing remaining repos if a single clone or fetch
fails, and report all failures at the end with a non-zero exit code. Failures
SHALL be collected across every repository worked on, including those processed
concurrently in separate processes, so the final report accounts for the whole
run. The report SHALL list them in a stable order, independent of the order the
repositories happened to finish in.

#### Scenario: One repo unreachable

- **WHEN** one repo returns a network or auth error
- **THEN** the script logs the failure, continues with the rest, and exits
  non-zero after all repos are processed

#### Scenario: Failure raised while other repositories are in flight

- **WHEN** a repository fails while others are still being mirrored
- **THEN** the others run to completion, and the failure is named in the report
  at the end of the run

#### Scenario: Report is stable

- **WHEN** the same set of repositories fails on two runs
- **THEN** both runs print the same report, in the same order
