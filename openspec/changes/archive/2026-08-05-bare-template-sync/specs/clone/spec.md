## ADDED Requirements

### Requirement: Mirror the template as a bare clone as well

The system SHALL additionally clone the entry flagged `template: true` as a bare mirror at `mirrors/<template-org>/<template-repo>.git/`,
using `git clone --mirror` semantics so a later `git fetch --prune` brings every ref in line with the upstream.
The bare mirror is what the `template` remotes point at; the checkout beside it remains the copy to read and reconcile against.

#### Scenario: Fresh bare mirror

- **WHEN** `mirrors/<template-org>/<template-repo>.git/` does not exist
- **THEN** the script clones the template repo there as a bare mirror, through the same `gh` authentication as every other clone

#### Scenario: Existing bare mirror updated

- **WHEN** `mirrors/<template-org>/<template-repo>.git/` already exists and is a bare repository
- **THEN** the script runs `git fetch --prune` in it rather than re-cloning

#### Scenario: Bare path occupied by a non-bare repository

- **WHEN** a directory exists at the bare mirror's path but is not a bare repository
- **THEN** the script records a failure and does not fetch into it

#### Scenario: Both mirrors attempted independently

- **WHEN** either the template's checkout or its bare mirror fails to clone or update
- **THEN** the other is still attempted, and each failure is reported on its own

## MODIFIED Requirements

### Requirement: Configure `template` remote during clone
The system SHALL configure a git remote named `template` on every non-template mirror after a successful clone or update,
pointing at the local relative path `../../<template-org>/<template-repo>.git` (resolving to the template's bare mirror under `mirrors/`).

#### Scenario: Template URL added to non-template mirror
- **WHEN** a non-template mirror is cloned or updated successfully
- **THEN** the script ensures a `template` remote exists in that mirror with URL `../../<template-org>/<template-repo>.git`

#### Scenario: Template mirror skipped
- **WHEN** the mirror being processed is the template repo itself
- **THEN** the script does not add a `template` remote on it

#### Scenario: Drift normalised
- **WHEN** the template entry in `repos.yml` changes between runs,
  or a mirror still carries a `template` URL pointing at the template's checkout
- **THEN** the next `clone` run rewrites every non-template mirror's `template` remote URL to match the current template's bare mirror path

### Requirement: Process the template mirror first
The system SHALL clone or update the entry flagged `template: true`
— both its checkout and its bare mirror — before processing any non-template entry,
so the local path used by `template` remotes always resolves on disk after a successful run.

#### Scenario: Template processed first on fresh run
- **WHEN** `clone.sh` runs against an empty `mirrors/` directory
- **THEN** the template's checkout and its bare mirror are created before any non-template entry,
  so each subsequent `git remote add template ../../<template-org>/<template-repo>.git` resolves to an existing repository
