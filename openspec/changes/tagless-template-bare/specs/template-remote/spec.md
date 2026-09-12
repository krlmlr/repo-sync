## ADDED Requirements

### Requirement: The bare mirror is the single place the no-tags guarantee lives

The system SHALL keep the template's bare mirror free of tags,
and SHALL treat that as the whole of the guarantee that no mirror imports the template's tags.
No mirror SHALL be required to carry configuration for it, and no command SHALL be required to pass an option for it.

A fetch auto-follows tags the far end advertises under `refs/tags/*`.
A far end that advertises none offers nothing to follow, so the guarantee holds for any command a mirror runs against that remote --
including one that asks for tags explicitly, and including one run by tooling that knows nothing about this repository.

The guarantee SHALL be re-established at the start of every command that fetches the `template` remote,
before any mirror fetches from the bare mirror, so that a tree left in an older shape is corrected rather than relied upon.

#### Scenario: Mirror fetches the template remote

- **WHEN** a mirror fetches its `template` remote
- **THEN** its `refs/tags/*` is unchanged, and its `refs/remotes/template/*` branch refs are updated to match the bare mirror

#### Scenario: Tags requested explicitly

- **WHEN** a mirror fetches its `template` remote with tags explicitly requested
- **THEN** its `refs/tags/*` is still unchanged, because the bare mirror advertises no tags to import

#### Scenario: Mirror carrying no tag configuration

- **WHEN** a mirror's `template` remote carries no tag-related configuration at all
- **THEN** a fetch of it still imports no tags

#### Scenario: Generic tooling sweeps the checkouts

- **WHEN** a tool with no knowledge of this repository fetches every remote in every checkout
- **THEN** no mirror's `refs/tags/*` gains a ref from the template

#### Scenario: Tree left in an older shape

- **WHEN** a command that fetches the `template` remote runs against a tree whose
  bare mirror still carries tags
- **THEN** the bare mirror is brought back to its tagless shape before any mirror
  fetches from it

### Requirement: Every mirror carries the `template` remote

The system SHALL ensure every mirror has a git remote named `template`
pointing at the local path of the template repo's **bare** mirror,
expressed relative to the mirror's working tree as `../../<template-org>/<template-repo>.git`.
The template repo's own checkout SHALL carry it too.

The remote SHALL NOT point at the template's checkout:
git refuses a push to the branch a non-bare repository has checked out,
and a working tree is state a fetch has no business seeing.

The remote SHALL carry no tag-related configuration of its own.
The far end holds no tags, so there is nothing for such a setting to prevent,
and a setting written per mirror is a guarantee
that has to be repeated once per mirror and remembered by every tool.

On the template's own checkout the remote is redundant --
it offers what that checkout's own `origin` offers --
and exists so that no checkout is an exception:
a sweep that fetches every remote in every checkout needs no list of which checkouts to skip.

#### Scenario: Fresh non-template mirror

- **WHEN** a non-template mirror is freshly cloned and has no `template` remote
- **THEN** the system runs `git remote add template ../../<template-org>/<template-repo>.git` inside that mirror

#### Scenario: Template repo's own checkout

- **WHEN** the mirror is the template repo's own checkout
- **THEN** it is given the same `template` remote, pointing at its own bare
  mirror beside it

#### Scenario: Existing `template` remote with stale URL

- **WHEN** a mirror already has a `template` remote pointing at a different URL,
  including one pointing at the template's checkout
- **THEN** the system runs `git remote set-url template ../../<template-org>/<template-repo>.git` to normalise it

#### Scenario: Remote accepts a push

- **WHEN** a mirror pushes a branch to its `template` remote
- **THEN** the push is accepted, because the far end is a bare repository with no
  checked-out branch to refuse it

#### Scenario: No tag configuration on the remote

- **WHEN** a mirror's `template` remote has been configured by a current run and
  the bare mirror carries no tags
- **THEN** the remote carries no tag-related setting, and a fetch of it still
  imports no tags

#### Scenario: Sweep needs no exception list

- **WHEN** every checkout is swept by the same command
- **THEN** the template's checkout is handled by that command like any other, and
  the command needs no knowledge of which entry is the template

## REMOVED Requirements

### Requirement: Configure `template` remote on non-template mirrors

**Reason**: The contract changed from "every non-template mirror" to "every mirror".
The exception it carried -- the template repo itself gets no `template` remote --
is what made the template's checkout the last per-repository special case in a sweep over checkouts.
Replaced by "Every mirror carries the `template` remote".

**Migration**: No action.
A current `clone` run adds the remote to the template's own checkout;
every other mirror's remote is unchanged.

### Requirement: The `template` remote imports no tags

**Reason**: The guarantee moved from each mirror's `remote.template.tagOpt` to the bare mirror itself,
which carries no tags for a fetch to follow.
Enforcing it per mirror made it behavioural: it held only for mirrors a `clone` run had reached,
and only for commands that knew to pass the option,
which is exactly what stopped generic tooling from sweeping the checkouts.
Replaced by "The bare mirror is the single place the no-tags guarantee lives".

**Migration**: No action.
A current `clone` or `sync` run normalises the bare mirror to its tagless shape
and then removes `remote.template.tagOpt` from each mirror.
The setting is removed only once the bare mirror on disk is verifiably tagless,
so a partially migrated tree is never left with neither protection.
