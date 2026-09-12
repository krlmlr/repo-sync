# template-remote Specification

## Purpose
TBD - created by archiving change template-remote.
Update Purpose after archive.
## Requirements
### Requirement: Designate exactly one template repo
The system SHALL recognise exactly one entry in `repos.yml` carrying `template: true` as the canonical template repo.
Zero or multiple flagged entries SHALL be treated as a configuration error.

#### Scenario: One entry flagged
- **WHEN** `repos.yml` has a single entry with `template: true`
- **THEN** that entry's `<org>/<repo>` is treated as the template

#### Scenario: No entry flagged
- **WHEN** no entry in `repos.yml` has `template: true`
- **THEN** any consumer of the template (e.g. `clone.sh`) exits non-zero with a clear error

#### Scenario: Multiple entries flagged
- **WHEN** more than one entry in `repos.yml` has `template: true`
- **THEN** any consumer of the template exits non-zero with a clear error

### Requirement: Configure `template` remote on non-template mirrors
The system SHALL ensure every non-template mirror has a git remote named `template`
pointing at the local path of the template repo's **bare** mirror,
expressed relative to the mirror's working tree as `../../<template-org>/<template-repo>.git`.
The remote SHALL NOT point at the template's checkout:
git refuses a push to the branch a non-bare repository has checked out,
and a working tree is state a fetch has no business seeing.

#### Scenario: Fresh non-template mirror
- **WHEN** a non-template mirror is freshly cloned and has no `template` remote
- **THEN** the system runs `git remote add template ../../<template-org>/<template-repo>.git` inside that mirror

#### Scenario: Existing `template` remote with stale URL
- **WHEN** a non-template mirror already has a `template` remote pointing at a different URL,
  including one pointing at the template's checkout
- **THEN** the system runs `git remote set-url template ../../<template-org>/<template-repo>.git` to normalise it

#### Scenario: Template repo itself
- **WHEN** the mirror is the template repo
- **THEN** the system does not add a `template` remote on it

#### Scenario: Remote accepts a push
- **WHEN** a mirror pushes a branch to its `template` remote
- **THEN** the push is accepted, because the far end is a bare repository with no checked-out branch to refuse it

### Requirement: Idempotent template-remote configuration
The system SHALL configure the `template` remote without error on repeated runs,
producing no changes when the configuration is already correct.

#### Scenario: Second run with no drift
- **WHEN** `clone.sh` is run twice with no inventory or template-URL changes
- **THEN** the second run reports the `template` remote already configured and exits zero

