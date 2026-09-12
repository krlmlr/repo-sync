## ADDED Requirements

### Requirement: Refresh the template's bare mirror first

The system SHALL fetch the template's bare mirror at `mirrors/<template-org>/<template-repo>.git` before any mirror fetches from it,
so the template refs the mirrors receive are the ones the upstream has.
The bare mirror carries no `.git` entry,
and so is not reachable by a sweep that discovers repositories by their working tree;
refreshing it is this capability's responsibility and no other's.

#### Scenario: Bare mirror refreshed before the template fetches

- **WHEN** sync runs against a populated `mirrors/` tree
- **THEN** the bare mirror is fetched before any mirror fetches its `template` remote,
  and every mirror ends the run with the template refs the upstream has

#### Scenario: Bare mirror missing

- **WHEN** `mirrors/<template-org>/<template-repo>.git` does not exist
- **THEN** the run records a failure naming `mise run clone` as the repair,
  skips the per-mirror `template` fetches rather than failing each one against a path that does not resolve,
  and still rebases the mirrors

#### Scenario: Bare path occupied by a non-bare repository

- **WHEN** a directory exists at the bare mirror's path but is not a bare repository
- **THEN** the run records a failure and does not fetch into it

#### Scenario: Stale bare mirror still usable

- **WHEN** the fetch of the bare mirror fails
- **THEN** the run records the failure and continues to fetch `template` in the mirrors,
  since the refs the bare mirror already holds remain readable

### Requirement: Rebase every mirror onto its upstream

The system SHALL run `git pull --rebase` in every mirror checkout listed in `repos.yml` that exists on disk,
keeping local commits that have not been pushed.
Mirrors that are not cloned SHALL be skipped without failing the run, since cloning is the `clone` capability's responsibility.

#### Scenario: Mirror fast-forwarded

- **WHEN** a mirror has no local commits and its upstream has moved
- **THEN** the mirror is updated to the upstream tip

#### Scenario: Local commits preserved

- **WHEN** a mirror carries a local commit that is not on its upstream, and the upstream has moved
- **THEN** the local commit is rebased on top of the new upstream tip rather than discarded

#### Scenario: Mirror not cloned

- **WHEN** an inventory entry has no directory under `mirrors/`
- **THEN** the entry is reported as skipped and the run does not count it as a failure

#### Scenario: Rebase stops on a conflict

- **WHEN** a mirror's rebase stops on a conflict
- **THEN** the failure is recorded, the mirror is left for a human to resolve, and the run continues with the remaining mirrors

### Requirement: Fetch the `template` remote in every mirror

The system SHALL fetch the `template` remote in every non-template mirror that exists on disk,
so each mirror holds the template refs it will be reconciled against.
The template's own mirror SHALL be skipped, as it carries no `template` remote.

#### Scenario: Template refs updated

- **WHEN** a non-template mirror has a `template` remote and the bare mirror has moved
- **THEN** the mirror's `template/*` refs are updated to match the bare mirror

#### Scenario: Mirror without a `template` remote

- **WHEN** a mirror exists but has no `template` remote
- **THEN** the run records a failure naming `mise run clone` as the repair

#### Scenario: Template mirror itself

- **WHEN** the mirror being processed is the template repo's own checkout
- **THEN** no `template` fetch is attempted for it

#### Scenario: Rebase failure does not stop the template fetch

- **WHEN** a mirror's `git pull --rebase` fails
- **THEN** its `template` remote is still fetched

### Requirement: Failures are isolated

The system SHALL continue processing the remaining mirrors when one step fails, report every failure at the end, and exit non-zero.

#### Scenario: One mirror unreachable

- **WHEN** one mirror's pull or fetch fails
- **THEN** the run logs the failure, continues with the rest, and exits non-zero
  after all mirrors are processed with a summary listing every failure

#### Scenario: Clean run

- **WHEN** every mirror pulls and fetches successfully
- **THEN** the run exits zero

#### Scenario: Idempotent run

- **WHEN** sync is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero

### Requirement: Invalid template designation is fatal

The system SHALL exit non-zero before touching any mirror if `repos.yml` does not contain exactly one entry with `template: true`,
matching the `clone` capability so both tools reject the same malformed inventory.

#### Scenario: No template flagged

- **WHEN** `repos.yml` has no entry with `template: true`
- **THEN** sync exits non-zero with a message naming the missing flag, before fetching or rebasing anything

#### Scenario: Multiple templates flagged

- **WHEN** `repos.yml` has more than one entry with `template: true`
- **THEN** sync exits non-zero with a message listing the conflicting entries
