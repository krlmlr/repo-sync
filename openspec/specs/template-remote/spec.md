# template-remote Specification

## Purpose
Carry the designated template repository outward to every mirror, by wiring a `template` remote on
each one that resolves to the template's bare mirror on disk. The remote brings branches and
nothing else: no tags, and no commit message whose issue reference would resolve against the
wrong repository once copied.

## Requirements

### Requirement: Designate exactly one template repo
The system SHALL recognise exactly one entry in `repos.yml` carrying `template: true` as the canonical template repo. Zero or multiple flagged entries SHALL be treated as a configuration error.

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
The system SHALL ensure every non-template mirror has a git remote named `template` pointing at the local path of the template repo's **bare** mirror, expressed relative to the mirror's working tree as `../../<template-org>/<template-repo>.git`. The remote SHALL NOT point at the template's checkout: git refuses a push to the branch a non-bare repository has checked out, and a working tree is state a fetch has no business seeing.

#### Scenario: Fresh non-template mirror
- **WHEN** a non-template mirror is freshly cloned and has no `template` remote
- **THEN** the system runs `git remote add template ../../<template-org>/<template-repo>.git` inside that mirror

#### Scenario: Existing `template` remote with stale URL
- **WHEN** a non-template mirror already has a `template` remote pointing at a different URL, including one pointing at the template's checkout
- **THEN** the system runs `git remote set-url template ../../<template-org>/<template-repo>.git` to normalise it

#### Scenario: Template repo itself
- **WHEN** the mirror is the template repo
- **THEN** the system does not add a `template` remote on it

#### Scenario: Remote accepts a push
- **WHEN** a mirror pushes a branch to its `template` remote
- **THEN** the push is accepted, because the far end is a bare repository with no checked-out branch to refuse it

### Requirement: Idempotent template-remote configuration
The system SHALL configure the `template` remote without error on repeated runs, producing no changes when the configuration is already correct.

#### Scenario: Second run with no drift
- **WHEN** `clone.sh` is run twice with no inventory or template-URL changes
- **THEN** the second run reports the `template` remote already configured and exits zero

### Requirement: The `template` remote imports no tags

The system SHALL configure every non-template mirror's `template` remote so
that no fetch of it writes into that mirror's `refs/tags/*`, by setting
`remote.template.tagOpt` to `--no-tags`. Branch refs SHALL continue to be
fetched into `refs/remotes/template/*` unchanged.

The setting SHALL be written on every run, as the remote's URL already is, so a
mirror configured before this requirement existed is repaired without being
re-cloned.

A fetch auto-follows every tag pointing at an object it downloads, and a fetch
of the template downloads the template's whole history. `refs/remotes/*` gives
each remote a namespace of its own; `refs/tags/*` is flat and shared, so an
auto-followed tag arrives indistinguishable from the mirror's own and is not
removed by `--prune`.

#### Scenario: Remote configured

- **WHEN** the `template` remote is added to a mirror
- **THEN** `remote.template.tagOpt` is set to `--no-tags` in that mirror

#### Scenario: Mirror configured before this rule

- **WHEN** a mirror already carries a `template` remote without the setting
- **THEN** the next run writes it, in the same pass that normalises the URL

#### Scenario: Template fetched

- **WHEN** a mirror fetches its `template` remote and the template carries tags
- **THEN** the mirror's tag list is unchanged, and its
  `refs/remotes/template/*` branch refs are updated to match the bare mirror

#### Scenario: Template repo itself

- **WHEN** the mirror is the template repo
- **THEN** nothing is configured, since it carries no `template` remote

#### Scenario: Second run with no drift

- **WHEN** the configuration already names `--no-tags`
- **THEN** writing it again changes nothing and the run exits zero

### Requirement: A commit copied from the template carries no relative issue reference

The system SHALL ensure that a commit created in a mirror by replaying a commit
reachable from that mirror's `refs/remotes/template/*` carries no issue reference
that resolves against the mirror it lands in.

A reference of the form `#<number>` or `GH-<number>` SHALL be rewritten to
`<template-org>/<template-repo>#<number>`, except where a closing keyword
(`close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`,
`resolved`) immediately precedes it, in which case the commit SHALL be refused
with a diagnostic naming the offending references. Where the template's
`<org>/<repo>` cannot be determined, the commit SHALL be refused rather than
rewritten.

When `REPO_SYNC_TEMPLATE_REFS` is set to `block`, every such reference SHALL be
refused rather than rewritten.

A reference already carrying an owner and repository, a URL, and text in a
comment line or past a scissors line SHALL be left unchanged.

#### Scenario: Squash-merge suffix

- **WHEN** a commit whose subject ends in `(#12)` is cherry-picked from the
  template into a mirror
- **THEN** the mirror's commit reads `(<template-org>/<template-repo>#12)`, and
  the rewrite is reported on stderr

#### Scenario: Reference under a closing keyword

- **WHEN** the copied message contains `Fixes #7`
- **THEN** the commit is refused, the message file is left unmodified, and the
  replay state remains in place so the operator can commit again with a
  corrected message

#### Scenario: The mirror's own commit

- **WHEN** a commit is written in a mirror rather than replayed from the
  template, and refers to `#5`
- **THEN** the message is unchanged: that number is the mirror's own issue

#### Scenario: A commit replayed from the mirror's own history

- **WHEN** `sync` rebases a mirror onto its upstream, replaying commits the
  mirror made itself
- **THEN** their messages are unchanged, whatever references they carry

#### Scenario: Already qualified

- **WHEN** a message already reads `<template-org>/<template-repo>#12`, because
  an earlier run rewrote it
- **THEN** it is left as it is

#### Scenario: Block mode

- **WHEN** `REPO_SYNC_TEMPLATE_REFS=block` is set
- **THEN** a copied commit carrying `(#12)` is refused rather than rewritten

#### Scenario: The guard cannot run

- **WHEN** the hook cannot determine the template's `<org>/<repo>`, or `perl` is
  not available
- **THEN** the commit is refused with a diagnostic, rather than allowed through
  unchecked
