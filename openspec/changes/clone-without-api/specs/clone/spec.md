## ADDED Requirements

### Requirement: A clone run consumes no GitHub API quota

The system SHALL create and update every mirror over git transport alone.
No step of a `clone` run SHALL issue a GitHub REST or GraphQL request, so a
spent API rate limit SHALL NOT stand between the inventory and its mirrors.

#### Scenario: API rate limit already exhausted

- **WHEN** the authenticated user's GitHub API rate limit is already spent when
  the run starts
- **THEN** every reachable repository is still mirrored and the run exits zero

#### Scenario: Quota untouched by a full run

- **WHEN** a full `clone` run over the whole inventory completes
- **THEN** the user's remaining API rate limit is what it was before the run

## MODIFIED Requirements

### Requirement: Clone repos from inventory

The system SHALL read `repos.yml` and clone every listed repository into a local
`mirrors/<org>/<repo>/` directory using `git clone` against
`https://github.com/<org>/<repo>.git`, with `gh` supplying the credential. The
repository name SHALL be taken from the inventory rather than resolved through
the GitHub API.

#### Scenario: Fresh clone

- **WHEN** `mirrors/<org>/<repo>/` does not exist
- **THEN** the script runs `git clone https://github.com/<org>/<repo>.git
  mirrors/<org>/<repo>`, carrying `gh`'s credential helper

#### Scenario: Auth handled by gh

- **WHEN** `gh` is authenticated (any method)
- **THEN** the script clones without any additional token configuration; private
  repos succeed

#### Scenario: Public repo needs no credential

- **WHEN** the repository is public
- **THEN** GitHub serves the clone without asking for a credential, and `gh` is
  never invoked

### Requirement: Incremental update

The system SHALL skip re-cloning if a directory already exists and instead fetch
and fast-forward to match the remote default branch. The fetch SHALL carry the
same `gh` credential helper as the clone that created the mirror, so a mirror
that could be cloned can also be updated.

#### Scenario: Existing clone updated

- **WHEN** `mirrors/<org>/<repo>/` already exists
- **THEN** the script runs `git fetch --prune` and resets the default branch to
  `origin/HEAD`

#### Scenario: Idempotent run

- **WHEN** the script is run twice with no upstream changes
- **THEN** the second run makes no changes and exits zero

#### Scenario: Private mirror updated without global git configuration

- **WHEN** an existing mirror is of a private repository and the user's global
  git config names no credential helper
- **THEN** the fetch succeeds on `gh`'s credential, as the clone did
