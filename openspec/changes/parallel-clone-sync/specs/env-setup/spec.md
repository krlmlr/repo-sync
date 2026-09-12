## ADDED Requirements

### Requirement: GNU parallel documented as prerequisite

`mise.toml` SHALL document that GNU parallel must be installed before running the `clone` and `sync` tasks,
and SHALL name `REPO_SYNC_JOBS` as the way to choose how many repositories are worked on at once.
The requirement is GNU parallel specifically:
moreutils ships an unrelated program under the same name, which understands none of the options the tasks use.

#### Scenario: GNU parallel installed

- **WHEN** GNU parallel is on `PATH`
- **THEN** `mise run clone` and `mise run sync` proceed without additional configuration

#### Scenario: GNU parallel missing

- **WHEN** no `parallel` is on `PATH`, or the one on `PATH` is moreutils'
- **THEN** the task exits non-zero naming the package to install, before any mirror is touched

#### Scenario: Concurrency chosen by the operator

- **WHEN** the operator wants a different number of repositories in flight,
  or wants the run reduced to one at a time to read a failure
- **THEN** `REPO_SYNC_JOBS` is documented as the way to say so, and needs no edit to any script
