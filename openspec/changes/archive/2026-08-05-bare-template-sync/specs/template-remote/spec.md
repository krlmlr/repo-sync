## MODIFIED Requirements

### Requirement: Configure `template` remote on non-template mirrors
The system SHALL ensure every non-template mirror has a git remote named `template`
pointing at the local path of the template repo's **bare** mirror,
expressed relative to the mirror's working tree as `../../<template-org>/<template-repo>.git`.
The remote SHALL NOT point at the template's checkout: git refuses a push to the branch a non-bare repository has checked out,
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
