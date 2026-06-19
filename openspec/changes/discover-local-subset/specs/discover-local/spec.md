## ADDED Requirements

### Requirement: Discover repos checked out locally

The system SHALL scan a base directory and report which `repos.yml` entries are
checked out locally, supporting both the `mirrors/<org>/<repo>/` layout and a
flat layout where repos are direct children of the base directory (siblings of
`repo-sync`, with no intervening `<org>/` directory).

#### Scenario: Flat-sibling discovery

- **WHEN** the base directory contains flat sibling checkouts such as `dm/`,
  `cynkratemplate/`, and `repo-sync/` (no `<org>/` directory)
- **THEN** each directory matching an inventory entry is reported as discovered
  with its `<org>/<repo>` identity and absolute local path

#### Scenario: Mirrors-layout discovery

- **WHEN** the base directory uses the `mirrors/<org>/<repo>/` layout
- **THEN** each `mirrors/<org>/<repo>/` directory matching an inventory entry is
  reported as discovered with its `<org>/<repo>` identity and absolute local
  path

#### Scenario: Both layouts yield the same identity

- **WHEN** the same inventory repo is present under either layout
- **THEN** the reported `<org>/<repo>` identity is identical regardless of
  layout

### Requirement: Match by repo name verified via origin remote

The system SHALL treat a candidate directory as matching an inventory entry only
when the directory basename equals the entry's `repo` field AND the directory's
git `origin` remote resolves to that entry's `<org>/<repo>`. Candidates that
fail either condition SHALL NOT be matched.

#### Scenario: Basename and origin both match

- **WHEN** a directory named `dm` has an `origin` remote resolving to
  `cynkra/dm` and `repos.yml` contains `cynkra/dm`
- **THEN** the directory is matched to the `cynkra/dm` inventory entry

#### Scenario: Basename matches but origin mismatches

- **WHEN** a directory named `dm` has an `origin` remote resolving to a
  different `<org>/<repo>` than the inventory entry
- **THEN** the directory is not matched, and the mismatch is reported

#### Scenario: Same repo name across orgs disambiguated by origin

- **WHEN** two inventory entries share the same `repo` name under different
  orgs and a local directory carries that name
- **THEN** the directory matches only the entry whose `<org>/<repo>` equals the
  resolved `origin` remote

#### Scenario: Directory without an origin remote

- **WHEN** a candidate directory has no `origin` remote
- **THEN** the directory is not matched, and it is reported as unrecognized

### Requirement: Identify the template within the discovered subset

The system SHALL identify the entry flagged `template: true` in `repos.yml` when
it is present in the discovered subset, and SHALL mark it as the template in the
emitted output so reconcile can use it as the canonical source.

#### Scenario: Template present locally

- **WHEN** the discovered subset includes the `template: true` repo
- **THEN** that repo is marked as the template in the output

#### Scenario: Template absent locally

- **WHEN** the discovered subset does not include the `template: true` repo
- **THEN** the system warns that the template is not checked out locally and
  continues, marking no entry as template

### Requirement: Report-and-continue robustness

The system SHALL continue and exit zero whenever a valid subset is discovered,
reporting anomalies rather than aborting. Directories that do not correspond to
any inventory entry SHALL be reported as extras, and a missing template SHALL be
reported as a warning.

#### Scenario: Extra sibling not in inventory

- **WHEN** a sibling directory does not correspond to any `repos.yml` entry
- **THEN** it is reported as an unrecognized extra and discovery continues with
  the remaining valid matches

#### Scenario: Valid subset exits zero

- **WHEN** at least one inventory repo is discovered and matched
- **THEN** the system exits zero after emitting the subset, regardless of extras
  or a missing template

#### Scenario: Misconfigured template flag

- **WHEN** `repos.yml` does not contain exactly one entry with `template: true`
- **THEN** the system exits non-zero with a clear error before emitting a subset

### Requirement: Emit the discovered subset for reconcile

The system SHALL emit the discovered subset as machine-readable output where
each entry carries its `org`, `repo`, absolute local path, and a boolean
indicating whether it is the template.

#### Scenario: Subset emitted with required fields

- **WHEN** discovery completes with one or more matches
- **THEN** each emitted entry includes `org`, `repo`, local path, and template
  flag

#### Scenario: Deterministic ordering

- **WHEN** discovery is run twice against an unchanged layout
- **THEN** the emitted subset is identical across runs

### Requirement: Discovery exposed as a mise task

The system SHALL expose discovery as a named `mise` task so contributors run
`mise run <task>` without knowing the underlying script path or interpreter,
consistent with the existing `fetch-inventory` and `clone` tasks.

#### Scenario: Discovery task runs

- **WHEN** a contributor runs the discovery task via `mise run`
- **THEN** `mise` executes the discovery script and prints the discovered subset

#### Scenario: Base directory selectable

- **WHEN** the discovery task is run with a base directory other than the
  default
- **THEN** discovery scans that directory for matching checkouts
