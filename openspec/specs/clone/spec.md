## Purpose

Mirror every repository listed in `repos.yml` into a predictable local directory layout (`mirrors/<org>/<repo>/`),
keeping the local copy fast-forwardable to its GitHub default branch on subsequent runs.

## Requirements

### Requirement: Incremental update

The system SHALL skip re-cloning if a directory already exists and instead fetch and fast-forward to match the remote default branch,
bringing the mirror's tags in line with the upstream's in the same step.
`clone` is the re-baselining tool — it resets the working tree onto `origin/HEAD` —
so a tag the upstream does not have is local state it discards like any other.

#### Scenario: Existing clone updated

- **WHEN** `mirrors/<org>/<repo>/` already exists
- **THEN** the script runs `git fetch --prune --prune-tags` and resets the default branch to `origin/HEAD`

#### Scenario: Tags left behind by an earlier run

- **WHEN** a mirror carries tags its upstream does not have,
  including any imported from the template before the `template` remote stopped offering them
- **THEN** the update removes them, leaving the mirror's tags equal to the upstream's

#### Scenario: Idempotent run

- **WHEN** the script is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero

### Requirement: Failures are isolated

The system SHALL continue processing remaining repos if a single clone or fetch fails,
and report all failures at the end with a non-zero exit code.
Failures SHALL be collected across every repository worked on, including those processed concurrently in separate processes,
so the final report accounts for the whole run.
The report SHALL list them in a stable order, independent of the order the repositories happened to finish in.

#### Scenario: One repo unreachable

- **WHEN** one repo returns a network or auth error
- **THEN** the script logs the failure, continues with the rest, and exits non-zero after all repos are processed

#### Scenario: Failure raised while other repositories are in flight

- **WHEN** a repository fails while others are still being mirrored
- **THEN** the others run to completion, and the failure is named in the report at the end of the run

#### Scenario: Report is stable

- **WHEN** the same set of repositories fails on two runs
- **THEN** both runs print the same report, in the same order

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

The system SHALL finish cloning or updating the entry flagged `template: true` — both its checkout and its bare mirror —
before it begins processing any non-template entry,
so the local path used by `template` remotes always resolves on disk after a successful run.
This SHALL hold as a barrier rather than as an ordering within a single pass: no non-template entry SHALL be started
while either of the template's mirrors is still being made.

The template's two mirrors are independent clones of one upstream, so they MAY be made at the same time as each other,
and a failure in one SHALL NOT prevent the other from being attempted.

#### Scenario: Template processed first on fresh run

- **WHEN** `clone.sh` runs against an empty `mirrors/` directory
- **THEN** the template's checkout and its bare mirror are created before any non-template entry,
  so each subsequent `git remote add template ../../<template-org>/<template-repo>.git` resolves to an existing repository

#### Scenario: No mirror overlaps the template's

- **WHEN** the inventory is mirrored several repositories at a time
- **THEN** no non-template mirror is begun until both of the template's mirrors have finished, successfully or otherwise

#### Scenario: Both mirrors of the template at once

- **WHEN** the template's checkout and bare mirror are made
- **THEN** they may be made concurrently, and each reports its own outcome

### Requirement: Fail when template designation is invalid
The system SHALL exit non-zero before processing any mirror if `repos.yml` does not contain exactly one entry with `template: true`.

#### Scenario: No template flagged
- **WHEN** `repos.yml` has no entry with `template: true`
- **THEN** the script exits non-zero with a message naming the missing flag, before cloning or updating any mirror

#### Scenario: Multiple templates flagged
- **WHEN** `repos.yml` has more than one entry with `template: true`
- **THEN** the script exits non-zero with a message listing the conflicting entries

### Requirement: Mirror the template as a bare clone as well

The system SHALL additionally clone the entry flagged `template: true` as a bare mirror at `mirrors/<template-org>/<template-repo>.git/`,
using `git clone --mirror` semantics so a later `git fetch --prune` brings every ref in line with the upstream.
The bare mirror is what the `template` remotes point at; the checkout beside it remains the copy to read and reconcile against.

#### Scenario: Fresh bare mirror

- **WHEN** `mirrors/<template-org>/<template-repo>.git/` does not exist
- **THEN** the script clones the template repo there as a bare mirror, over SSH like every other clone

#### Scenario: Existing bare mirror updated

- **WHEN** `mirrors/<template-org>/<template-repo>.git/` already exists and is a bare repository
- **THEN** the script runs `git fetch --prune` in it rather than re-cloning

#### Scenario: Bare path occupied by a non-bare repository

- **WHEN** a directory exists at the bare mirror's path but is not a bare repository
- **THEN** the script records a failure and does not fetch into it

#### Scenario: Both mirrors attempted independently

- **WHEN** either the template's checkout or its bare mirror fails to clone or update
- **THEN** the other is still attempted, and each failure is reported on its own

### Requirement: Mirrors are processed several at a time

The system SHALL work on more than one repository at once, since each mirror's clone or update is independent of every other's
and spends most of its duration waiting on the network.
The number worked on at once SHALL default to 8 and SHALL be settable with the `REPO_SYNC_JOBS` environment variable,
where `1` reduces the run to one repository at a time.

The output of each repository SHALL be kept together rather than interleaved with the other repositories',
so a failure can be read without being reassembled from lines scattered across the run.

#### Scenario: Inventory mirrored concurrently

- **WHEN** `clone` runs over an inventory of more than one non-template entry
- **THEN** several of them are cloned or updated at the same time,
  and the run takes materially less wall clock than mirroring them one after another

#### Scenario: Degree of concurrency chosen by the operator

- **WHEN** `REPO_SYNC_JOBS` is set to a number
- **THEN** that many repositories are worked on at once

#### Scenario: Reduced to one at a time

- **WHEN** `REPO_SYNC_JOBS=1`
- **THEN** the run performs the same work on the same mirrors, one repository at a time, and reaches the same result

#### Scenario: One repository's output stays together

- **WHEN** several repositories are being mirrored at once and one of them fails
- **THEN** that repository's output is printed as one block, not split across the output of the repositories running beside it

#### Scenario: Repository worked on by itself

- **WHEN** the operator names a single mirror to create or update
- **THEN** exactly that mirror is processed, by the same steps the batch would have applied to it,
  so a failure seen in a batch can be reproduced on its own

### Requirement: GNU parallel is required and checked for

The system SHALL verify before any mirror is touched that GNU parallel is available,
and SHALL exit non-zero naming what to install if it is absent or if the `parallel` on `PATH` is a different program of the same name.

#### Scenario: GNU parallel absent

- **WHEN** no `parallel` is on `PATH`
- **THEN** the run exits non-zero with a message naming the package to install, before any mirror is cloned or updated

#### Scenario: A different `parallel` on PATH

- **WHEN** the `parallel` on `PATH` is not GNU parallel
- **THEN** the run exits non-zero saying so, rather than letting every job in the batch fail with the same usage error

### Requirement: Point every non-template mirror at the shared hooks

The system SHALL set `core.hooksPath` in every non-template mirror to this repository's tracked `hooks/` directory,
expressed relative to the mirror's working tree as `../../../hooks`.
Git runs hooks from the top of the working tree, so the relative path resolves wherever the mirror tree as a whole sits.

The setting SHALL be written on every run, as the `template` remote's URL and its `tagOpt` are,
so a mirror made before the hooks existed is repaired without being re-cloned.

#### Scenario: Fresh non-template mirror

- **WHEN** a non-template mirror is cloned
- **THEN** `core.hooksPath` in that mirror names `../../../hooks`

#### Scenario: Mirror configured before this rule

- **WHEN** a mirror carries no `core.hooksPath`, or one pointing elsewhere
- **THEN** the next run writes it, in the same pass that normalises the `template` remote

#### Scenario: Template repo itself

- **WHEN** the mirror is the template repo
- **THEN** nothing is configured: it has no `template` remote, and its own commits refer to its own issues

#### Scenario: Second run with no drift

- **WHEN** the configuration already names `../../../hooks`
- **THEN** writing it again changes nothing and the run exits zero

### Requirement: A clone run consumes no GitHub API quota

The system SHALL create and update every mirror over git transport alone.
No step of a `clone` run SHALL issue a GitHub REST or GraphQL request, so a spent API rate limit SHALL NOT stand between the inventory
and its mirrors.

#### Scenario: API rate limit already exhausted

- **WHEN** the authenticated user's GitHub API rate limit is already spent when the run starts
- **THEN** every reachable repository is still mirrored and the run exits zero

#### Scenario: Quota untouched by a full run

- **WHEN** a full `clone` run over the whole inventory completes
- **THEN** the user's remaining API rate limit is what it was before the run

### Requirement: Normalise `origin` to the SSH URL

The system SHALL rewrite the `origin` remote of every existing mirror — checkout and bare mirror alike —
to `git@github.com:<org>/<repo>.git` before fetching it, so the transport a mirror uses follows from the inventory rather than from
when the mirror was created.

#### Scenario: Mirror cloned over HTTPS

- **WHEN** a mirror on disk has an `origin` URL of `https://github.com/<org>/<repo>.git`
- **THEN** the run rewrites it to `git@github.com:<org>/<repo>.git` and fetches over SSH, with no re-clone

#### Scenario: Already normalised

- **WHEN** a mirror's `origin` already names the SSH URL
- **THEN** the rewrite is a no-op and the run exits zero

#### Scenario: Bare mirror normalised too

- **WHEN** the template's bare mirror has an `origin` URL that is not the SSH URL
- **THEN** it is rewritten in the same way before the bare mirror is fetched

### Requirement: Clone repos from inventory over SSH

The system SHALL read `repos.yml`
and clone every listed repository into a local `mirrors/<org>/<repo>/` directory using `git clone` against `git@github.com:<org>/<repo>.git`.
The repository name SHALL be taken from the inventory rather than resolved through the GitHub API, and no credential SHALL be configured,
stored or passed by the tooling: SSH authenticates with the operator's key.

#### Scenario: Fresh clone

- **WHEN** `mirrors/<org>/<repo>/` does not exist
- **THEN** the script runs `git clone git@github.com:<org>/<repo>.git mirrors/<org>/<repo>`

#### Scenario: Auth handled by SSH

- **WHEN** the operator's SSH key is known to their GitHub account and reachable by the agent
- **THEN** the script clones without any token configuration; private repos succeed

#### Scenario: No credential left behind

- **WHEN** a mirror has been cloned
- **THEN** its `origin` URL carries no credential, and the run has written no credential into any git config

#### Scenario: No `upstream` remote

- **WHEN** the repository is a fork of one the operator owns
- **THEN** the mirror carries `origin`, and `template` if it is not the template, and no other remote
