## ADDED Requirements

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
