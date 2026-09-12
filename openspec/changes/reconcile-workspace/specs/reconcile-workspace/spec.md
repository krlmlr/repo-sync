## Purpose

Maintain a separate clone of the template that can reach every other repository's history,
so an improvement made in one mirror can be browsed and cherry-picked into the template
without exposing the mirrors' tags or putting in-flight work where `clone` will reset it.

## ADDED Requirements

### Requirement: A workspace separate from the mirrors

The system SHALL maintain a clone of the template repository at `reconcile/`,
beside `mirrors/` and not within it,
with `origin` pointing at the template's GitHub upstream.

It SHALL NOT be a git worktree of the template's mirror.
A worktree shares its parent's configuration, refs and object database,
so the remotes this capability adds would be added to the mirror,
and the mirrors' tags would arrive in the mirror's own `refs/tags/*`.

It SHALL NOT live under `mirrors/`.
The `clone` capability resets every mirror onto `origin/HEAD` and prunes its tags,
which would discard a cherry-pick in progress.

The workspace SHALL be excluded from version control, as `mirrors/` is.

#### Scenario: Fresh workspace

- **WHEN** `reconcile/` does not exist
- **THEN** the template repository is cloned there with `origin` pointing at its
  GitHub upstream

#### Scenario: Existing workspace

- **WHEN** `reconcile/` already exists
- **THEN** the run configures its remotes and does not re-clone it

#### Scenario: Mirror is unaffected

- **WHEN** the workspace is created and its remotes configured
- **THEN** the template's mirror under `mirrors/` has the same remotes and the
  same tags it had before, and no ref of any other repository has appeared in it

#### Scenario: Re-baselining does not reach the workspace

- **WHEN** the `clone` capability runs and resets the mirrors onto `origin/HEAD`
- **THEN** the workspace's working tree, index and `HEAD` are untouched

### Requirement: One remote per inventory entry, named for its slug

The system SHALL configure one remote in the workspace for every entry in `repos.yml` other than the template,
named `<org>/<repo>` and pointing at that entry's mirror checkout
by the relative path `../mirrors/<org>/<repo>`.

The slug rather than the repository name alone,
because repository names are not unique across orgs
and a remote named for one would silently resolve to the wrong upstream.
Branches therefore arrive under `refs/remotes/<org>/<repo>/*`,
which stays distinct for two entries sharing a name.

The path SHALL be relative, so the tree can be moved or cloned elsewhere without rewriting every remote.

#### Scenario: Remote configured for an entry

- **WHEN** the workspace is configured against an inventory containing
  `<org>/<repo>`
- **THEN** it carries a remote named `<org>/<repo>` whose URL is
  `../mirrors/<org>/<repo>`

#### Scenario: Branches land under the slug

- **WHEN** a remote named `<org>/<repo>` is fetched
- **THEN** that mirror's branches appear under `refs/remotes/<org>/<repo>/*`

#### Scenario: Names colliding across orgs stay distinct

- **WHEN** two inventory entries share a repository name under different orgs
- **THEN** each has its own remote and its own `refs/remotes/<org>/<repo>/*`
  namespace, and neither resolves to the other's mirror

#### Scenario: Template entry has no remote

- **WHEN** the inventory entry is the one flagged `template: true`
- **THEN** no remote is configured for it, since the workspace is a clone of that
  repository and reaches it through `origin`

### Requirement: The workspace imports no tags from the mirrors

The system SHALL configure every per-entry remote so that fetching it writes nothing into the workspace's `refs/tags/*`.

Each mirror legitimately carries its own upstream's tags and SHALL keep them,
so unlike the template's bare mirror there is no tagless far end to fetch from
and the suppression SHALL be configured on the remote.
Every such remote lives in this one repository,
so the configuration is written, verified and repaired in one place
rather than replicated across the inventory.

The setting SHALL be written on every run, as the URL is,
so a remote configured before this requirement existed is repaired without the workspace being re-created.

#### Scenario: Mirror with tags fetched

- **WHEN** a remote is fetched whose mirror carries tags from its own GitHub
  upstream
- **THEN** the workspace's `refs/tags/*` is unchanged, and the mirror's branches
  are updated under `refs/remotes/<org>/<repo>/*`

#### Scenario: Every remote fetched at once

- **WHEN** every remote in the workspace is fetched in one command
- **THEN** the workspace's `refs/tags/*` still holds only the template's own tags

#### Scenario: Remote configured before this rule

- **WHEN** a remote exists without the setting
- **THEN** the next run writes it, in the same pass that normalises the URL

### Requirement: Remotes are wired without fetching unless asked

The system SHALL configure the remotes without fetching from them by default,
and SHALL fetch from every configured remote when explicitly asked to.

A promotion reads one repository at a time.
Configuring a remote costs nothing, while fetching every entry eagerly
copies history into a second place on disk before anyone has asked for it.

#### Scenario: Default run

- **WHEN** the workspace is configured with no fetch requested
- **THEN** every remote is configured and no object is transferred

#### Scenario: Fetch requested

- **WHEN** a fetch is requested
- **THEN** every configured remote is fetched with pruning

#### Scenario: Fetching one repository by hand

- **WHEN** an operator fetches a single remote by name
- **THEN** that mirror's branches become available under
  `refs/remotes/<org>/<repo>/*` and no other remote is contacted

### Requirement: Remotes are reconciled with the inventory

The system SHALL bring the workspace's remotes into line with `repos.yml` on every run:
adding a remote for an entry that has appeared,
rewriting the URL and the tag setting of one that has drifted,
and removing a remote whose entry is gone.

Removing a remote removes its `refs/remotes/<org>/<repo>/*` with it,
so a repository dropped from the inventory leaves nothing behind for a later cherry-pick to find.

#### Scenario: Entry added to the inventory

- **WHEN** an entry is added to `repos.yml` and the workspace is configured again
- **THEN** a remote for it is added

#### Scenario: Entry removed from the inventory

- **WHEN** an entry is removed from `repos.yml` and the workspace is configured
  again
- **THEN** its remote is removed, together with its refs under
  `refs/remotes/<org>/<repo>/*`

#### Scenario: Drift normalised

- **WHEN** a remote's URL or tag setting no longer matches what this capability
  specifies
- **THEN** the next run rewrites it

#### Scenario: Idempotent run

- **WHEN** the workspace is configured twice against an unchanged inventory
- **THEN** the second run changes nothing and exits zero

### Requirement: The workspace's working state is never modified

The system SHALL NOT check out, reset, rebase, merge or otherwise modify the workspace's working tree, index or `HEAD`.
It manages remotes and, when asked, fetches.

This is what separates the workspace from a mirror.
A promotion is human work that spans runs --
a cherry-pick stopped on a conflict, a branch half built --
and a tool that re-baselines would destroy it.

#### Scenario: Run during a cherry-pick

- **WHEN** the workspace is configured while a cherry-pick is in progress
- **THEN** the cherry-pick's state is intact afterwards and the run exits zero

#### Scenario: Run with uncommitted changes

- **WHEN** the workspace is configured while its working tree has uncommitted
  changes
- **THEN** those changes are still present and unmodified afterwards

#### Scenario: Run on a branch other than the default

- **WHEN** the workspace has a promotion branch checked out
- **THEN** that branch is still checked out afterwards

### Requirement: A promotion can be browsed, picked and pushed

The system SHALL leave the workspace in a state where a commit from any configured mirror
can be found, applied to the template and sent to the template's upstream using ordinary git,
with no tooling of this project's own.

#### Scenario: Commits browsed across repositories

- **WHEN** an operator lists what a mirror has that the template does not
- **THEN** the mirror's commits are reachable in the workspace and can be
  inspected there

#### Scenario: Commit cherry-picked into the template

- **WHEN** an operator cherry-picks a mirror's commit onto a branch started from
  the template's default branch
- **THEN** the commit applies and the workspace's `refs/tags/*` is unchanged

#### Scenario: Promotion pushed to the template's upstream

- **WHEN** an operator pushes the resulting branch to `origin`
- **THEN** it reaches the template's GitHub repository in one hop

### Requirement: Failures are isolated

The system SHALL continue configuring the remaining remotes when one fails,
report every failure at the end, and exit non-zero,
matching the `clone` and `sync` capabilities.

#### Scenario: One mirror missing

- **WHEN** an inventory entry has no mirror checkout on disk
- **THEN** its remote is still configured, since the path is relative and may
  resolve later, and a fetch of it is what reports the absence

#### Scenario: One remote fails to be configured

- **WHEN** configuring one remote fails
- **THEN** the run records the failure, configures the rest, and exits non-zero
  with a summary listing every failure

#### Scenario: Clean run

- **WHEN** every remote is configured successfully
- **THEN** the run exits zero

### Requirement: Invalid template designation is fatal

The system SHALL exit non-zero before touching the workspace
if `repos.yml` does not contain exactly one entry with `template: true`,
matching the `clone` and `sync` capabilities so every tool rejects the same malformed inventory.

#### Scenario: No template flagged

- **WHEN** `repos.yml` has no entry with `template: true`
- **THEN** the run exits non-zero with a message naming the missing flag

#### Scenario: Multiple templates flagged

- **WHEN** `repos.yml` has more than one entry with `template: true`
- **THEN** the run exits non-zero with a message listing the conflicting entries
