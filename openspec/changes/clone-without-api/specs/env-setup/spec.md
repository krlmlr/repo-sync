## ADDED Requirements

### Requirement: GitHub-facing git commands carry `gh`'s credential helper

Every git command the tooling runs against a GitHub remote SHALL be invoked with
`credential.helper` first cleared and then set to `!gh auth git-credential`, so
the credential comes from `gh`'s own store and no helper configured elsewhere
answers ahead of it. Commands that reach only local paths SHALL be invoked as
plain `git`. No credential SHALL be written into a remote URL, a git config, or
a command line.

#### Scenario: Clone and `origin` traffic authenticated

- **WHEN** the tooling clones a mirror, or fetches from or pulls from its
  `origin`
- **THEN** the invocation carries `credential.helper` cleared and then set to
  `gh`'s helper

#### Scenario: Local-path operations left unauthenticated

- **WHEN** the tooling fetches the `template` remote, resets a branch, or reads
  or writes remote configuration
- **THEN** the invocation is plain `git`, there being no remote end to
  authenticate to

#### Scenario: Stale global helper does not answer first

- **WHEN** the user's global git config names a credential helper holding an
  expired or revoked GitHub token
- **THEN** that helper is not consulted, and the credential comes from `gh`

#### Scenario: No token left behind

- **WHEN** a mirror has been cloned
- **THEN** its `origin` URL carries no credential and none has been written into
  any git config

## MODIFIED Requirements

### Requirement: gh authentication documented as prerequisite

`mise.toml` SHALL document that `gh` must be authenticated before running the
`clone` task, so contributors know what to set up. `gh` is required as the
source of the GitHub credential, not as the tool that clones.

#### Scenario: gh authenticated

- **WHEN** `gh` is authenticated (any method — token, device flow, etc.)
- **THEN** `mise run clone` proceeds without additional configuration

#### Scenario: gh not authenticated

- **WHEN** `gh` is not authenticated and a private repository is reached
- **THEN** the credential helper yields nothing, `git` fails for that repository
  with its own descriptive error, the failure is recorded, and the task exits
  non-zero once the rest of the inventory has been processed

#### Scenario: gh not authenticated, public repository

- **WHEN** `gh` is not authenticated and the repository is public
- **THEN** the clone succeeds, no credential having been asked for
