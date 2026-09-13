## MODIFIED Requirements

### Requirement: Mirror the template as a bare clone as well

The system SHALL additionally mirror the entry flagged `template: true` as a bare repository at `mirrors/<template-org>/<template-repo>.git/`,
holding the upstream's branches and nothing else.
The bare mirror is what the `template` remotes point at; the checkout beside it remains the copy to read and reconcile against.

The bare mirror SHALL carry no tags, and SHALL be configured so that fetching its upstream imports none:
its fetch refspec SHALL map the upstream's branches into `refs/heads/*` and SHALL map nothing into `refs/tags/*`,
and tag auto-following SHALL be off.
This is where the guarantee that the mirrors import no template tags is established, rather than in each mirror's configuration.

The bare mirror SHALL NOT be configured as a push mirror.
A repository whose refs are a strict subset of its upstream's, pushed as a mirror,
deletes from the upstream everything it does not itself have -- for a tagless bare, every tag on the GitHub repository.

The bare mirror's `HEAD` SHALL name the upstream's default branch, so a consumer can resolve the template's default branch through it.
An empty repository initialised locally names whatever branch the local git is configured to default to, which need not be the upstream's.

A later `git fetch --prune` SHALL bring its branches in line with the upstream's, including removing branches the upstream no longer has.

#### Scenario: Fresh bare mirror

- **WHEN** `mirrors/<template-org>/<template-repo>.git/` does not exist
- **THEN** the script creates a bare mirror there over the same SSH transport as every other clone,
  holding the upstream's branches under `refs/heads/*`, with `refs/tags/*` empty and `HEAD` naming the upstream's default branch

#### Scenario: Upstream tags are not imported

- **WHEN** the template's GitHub repository carries tags
- **THEN** the bare mirror's `refs/tags/*` is empty after the run, and stays empty across further runs

#### Scenario: Existing full mirror normalised in place

- **WHEN** the bare mirror exists but was created as a full mirror of every ref, so it carries tags, a refspec that copies them,
  and a push-mirror setting
- **THEN** the run rewrites the refspec, deletes every ref under `refs/tags/`, clears the push-mirror setting,
  and corrects `HEAD` if it names a branch the bare mirror does not have, without re-cloning
  and without contacting the upstream for anything beyond the usual fetch

#### Scenario: A push from the bare mirror deletes nothing upstream

- **WHEN** a push is made from the bare mirror to its GitHub upstream
- **THEN** no ref on the upstream is deleted, and in particular the upstream's tags are untouched

#### Scenario: Existing bare mirror updated

- **WHEN** `mirrors/<template-org>/<template-repo>.git/` already exists and is a bare repository
- **THEN** the script fetches into it with pruning rather than re-cloning, and branches the upstream no longer has are removed

#### Scenario: Bare path occupied by a non-bare repository

- **WHEN** a directory exists at the bare mirror's path but is not a bare repository
- **THEN** the script records a failure and does not fetch into it

#### Scenario: Both mirrors attempted independently

- **WHEN** either the template's checkout or its bare mirror fails to clone, normalise or update
- **THEN** the other is still attempted, and each failure is reported on its own

#### Scenario: Idempotent run

- **WHEN** the bare mirror is already in the required shape and the upstream has not moved
- **THEN** a further run changes nothing and exits zero

## ADDED Requirements

### Requirement: Configure the `template` remote on every mirror during clone

The system SHALL configure a git remote named `template` on every mirror after a successful clone or update,
the template's own checkout included,
pointing at the local relative path `../../<template-org>/<template-repo>.git` (resolving to the template's bare mirror under `mirrors/`).

The system SHALL NOT write per-mirror tag configuration on that remote.
Where an earlier version wrote `remote.template.tagOpt`, the system SHALL remove it,
but only once the bare mirror on disk is verifiably free of tags:
a mirror whose bare mirror has not yet been normalised SHALL keep the setting rather than lose its only protection.

#### Scenario: Template URL added to a mirror

- **WHEN** a mirror is cloned or updated successfully
- **THEN** the script ensures a `template` remote exists in that mirror with URL `../../<template-org>/<template-repo>.git`

#### Scenario: Template's own checkout carries the remote

- **WHEN** the mirror being processed is the template repo's own checkout
- **THEN** it is given the same `template` remote as every other mirror, so no checkout is an exception to a sweep that fetches every remote

#### Scenario: Drift normalised

- **WHEN** the template entry in `repos.yml` changes between runs,
  or a mirror still carries a `template` URL pointing at the template's checkout
- **THEN** the next `clone` run rewrites every mirror's `template` remote URL to match the current template's bare mirror path

#### Scenario: Stale tag configuration removed

- **WHEN** a mirror carries `remote.template.tagOpt` from an earlier version and the bare mirror on disk carries no tags
- **THEN** the setting is removed, leaving the guarantee resting on the bare mirror alone

#### Scenario: Stale tag configuration kept while the bare mirror still has tags

- **WHEN** a mirror carries `remote.template.tagOpt` and the bare mirror on disk still carries tags
- **THEN** the setting is left in place

### Requirement: Process the template's bare mirror first

The system SHALL bring the entry flagged `template: true` into its bare form -- created if absent, normalised and fetched if present --
before processing any mirror checkout, the template's own checkout included,
so that the local path used by `template` remotes always resolves on disk after a successful run and so
that no checkout is wired up against a bare mirror that still carries tags.

This SHALL hold as a barrier rather than as an ordering within a single pass: no checkout SHALL be started
while the bare mirror is still being made.

The template's checkout SHALL be processed with the other checkouts and not ahead of them.
It is a mirror like any other once the bare mirror exists.

#### Scenario: Template processed first on fresh run

- **WHEN** `clone` runs against an empty `mirrors/` directory
- **THEN** the template's bare mirror is created before any checkout is cloned,
  so each subsequent `template` remote names an existing repository

#### Scenario: Bare mirror normalised before any checkout is wired up

- **WHEN** `clone` runs against a tree whose bare mirror still carries tags
- **THEN** the bare mirror is normalised before any checkout's `template` remote is configured

#### Scenario: No checkout overlaps the bare mirror's creation

- **WHEN** the inventory is mirrored several repositories at a time
- **THEN** no checkout is begun until the bare mirror has been created or normalised and fetched, successfully or otherwise

#### Scenario: Template checkout is not special

- **WHEN** the checkouts are processed
- **THEN** the template's own checkout is processed among them by the same steps as every other checkout

## REMOVED Requirements

### Requirement: Configure `template` remote during clone

**Reason**: The contract changed from "every non-template mirror" to "every mirror", and the exception it carried --
the template's own checkout is skipped -- is the thing being removed.
Replaced by "Configure the `template` remote on every mirror during clone".

**Migration**: No action.
A current `clone` run adds the `template` remote to the template's own checkout and leaves every other mirror's remote as it was.

### Requirement: Process the template mirror first

**Reason**: The requirement ordered both of the template's mirrors ahead of every other entry,
and its "Both mirrors of the template at once" scenario made the checkout's place in that head start part of the contract.
Under a tagless bare only the bare mirror has to go first, and the template's checkout is processed with the rest,
so the ordering is replaced by "Process the template's bare mirror first" -- which keeps the barrier, now scoped to the bare mirror alone.

**Migration**: No action.
The barrier still holds where it matters, and a run under the new ordering reaches the same tree: the template's checkout is cloned
or updated in the same pass as every other checkout.
