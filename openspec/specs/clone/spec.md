## Purpose

Mirror every repository listed in `repos.yml` into a predictable local directory layout (`mirrors/<org>/<repo>/`), keeping the local copy fast-forwardable to its GitHub default branch on subsequent runs.
## Requirements
### Requirement: Clone repos from inventory
The system SHALL read `repos.yml` and clone every listed repository into a local `mirrors/<org>/<repo>/` directory using `gh repo clone`.

#### Scenario: Fresh clone
- **WHEN** `mirrors/<org>/<repo>/` does not exist
- **THEN** the script runs `gh repo clone <org>/<repo> mirrors/<org>/<repo>`

#### Scenario: Auth handled by gh
- **WHEN** `gh` is authenticated (any method)
- **THEN** the script clones without any additional token configuration; private repos succeed

### Requirement: Incremental update
The system SHALL skip re-cloning if a directory already exists and instead fetch and fast-forward to match the remote default branch.

#### Scenario: Existing clone updated
- **WHEN** `mirrors/<org>/<repo>/` already exists
- **THEN** the script runs `git fetch --prune` and resets the default branch to `origin/HEAD`

#### Scenario: Idempotent run
- **WHEN** the script is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero

### Requirement: Failures are isolated
The system SHALL continue processing remaining repos if a single clone or fetch fails, and report all failures at the end with a non-zero exit code.

#### Scenario: One repo unreachable
- **WHEN** one repo returns a network or auth error
- **THEN** the script logs the failure, continues with the rest, and exits non-zero after all repos are processed

### Requirement: Configure `template` remote during clone
The system SHALL configure a git remote named `template` on every non-template mirror after a successful clone or update, pointing at the local relative path `../../<template-org>/<template-repo>` (resolving to the template's mirror directory under `mirrors/`).

#### Scenario: Template URL added to non-template mirror
- **WHEN** a non-template mirror is cloned or updated successfully
- **THEN** the script ensures a `template` remote exists in that mirror with URL `../../<template-org>/<template-repo>`

#### Scenario: Template mirror skipped
- **WHEN** the mirror being processed is the template repo itself
- **THEN** the script does not add a `template` remote on it

#### Scenario: Drift normalised
- **WHEN** the template entry in `repos.yml` changes between runs
- **THEN** the next `clone` run rewrites every non-template mirror's `template` remote URL to match the new template path

### Requirement: Process the template mirror first
The system SHALL clone or update the entry flagged `template: true` before processing any non-template entry, so the local path used by `template` remotes always resolves on disk after a successful run.

#### Scenario: Template processed first on fresh run
- **WHEN** `clone.sh` runs against an empty `mirrors/` directory
- **THEN** the template entry is cloned before any non-template entry, so each subsequent `git remote add template ../../<template-org>/<template-repo>` resolves to an existing directory

### Requirement: Fail when template designation is invalid
The system SHALL exit non-zero before processing any mirror if `repos.yml` does not contain exactly one entry with `template: true`.

#### Scenario: No template flagged
- **WHEN** `repos.yml` has no entry with `template: true`
- **THEN** the script exits non-zero with a message naming the missing flag, before cloning or updating any mirror

#### Scenario: Multiple templates flagged
- **WHEN** `repos.yml` has more than one entry with `template: true`
- **THEN** the script exits non-zero with a message listing the conflicting entries

