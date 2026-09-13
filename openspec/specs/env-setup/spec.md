## Purpose

Document the ambient environment a contributor must have ready before running any tooling task:
SSH access to GitHub and GNU parallel, with no API token and no `gh` login required by anything.

## Requirements

### Requirement: GNU parallel documented as prerequisite

`mise.toml` SHALL document that GNU parallel must be installed before running
the `clone` and `sync` tasks, and SHALL name `REPO_SYNC_JOBS` as the way to
choose how many repositories are worked on at once. The requirement is GNU
parallel specifically: moreutils ships an unrelated program under the same
name, which understands none of the options the tasks use.

#### Scenario: GNU parallel installed

- **WHEN** GNU parallel is on `PATH`
- **THEN** `mise run clone` and `mise run sync` proceed without additional
  configuration

#### Scenario: GNU parallel missing

- **WHEN** no `parallel` is on `PATH`, or the one on `PATH` is moreutils'
- **THEN** the task exits non-zero naming the package to install, before any
  mirror is touched

#### Scenario: Concurrency chosen by the operator

- **WHEN** the operator wants a different number of repositories in flight, or
  wants the run reduced to one at a time to read a failure
- **THEN** `REPO_SYNC_JOBS` is documented as the way to say so, and needs no
  edit to any script

### Requirement: SSH access to GitHub documented as prerequisite

`mise.toml` SHALL document that the operator needs SSH access to GitHub before
running the `clone` task: a key their account knows, reachable by the agent, and
`github.com` present in `known_hosts` so the first connection has nothing to ask
about. No API token and no `gh` login SHALL be required by any task.

#### Scenario: SSH configured

- **WHEN** the operator's key is on their GitHub account and loaded in the agent
- **THEN** `mise run clone` proceeds without additional configuration, for
  public and private repositories alike

#### Scenario: No usable key

- **WHEN** no key the account accepts is available
- **THEN** `git` fails for that repository with its own descriptive error, the
  failure is recorded, and the task exits non-zero once the rest of the
  inventory has been processed

#### Scenario: Host key not yet known

- **WHEN** `github.com` is absent from `known_hosts` and the run is
  non-interactive
- **THEN** the connection is refused rather than trusted silently; adding the
  host key is a documented one-time setup step, not something the tooling
  bypasses
