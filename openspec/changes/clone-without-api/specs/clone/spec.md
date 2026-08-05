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

### Requirement: Normalise `origin` to the SSH URL

The system SHALL rewrite the `origin` remote of every existing mirror —
checkout and bare mirror alike — to `git@github.com:<org>/<repo>.git` before
fetching it, so the transport a mirror uses follows from the inventory rather
than from when the mirror was created.

#### Scenario: Mirror cloned over HTTPS

- **WHEN** a mirror on disk has an `origin` URL of
  `https://github.com/<org>/<repo>.git`
- **THEN** the run rewrites it to `git@github.com:<org>/<repo>.git` and fetches
  over SSH, with no re-clone

#### Scenario: Already normalised

- **WHEN** a mirror's `origin` already names the SSH URL
- **THEN** the rewrite is a no-op and the run exits zero

#### Scenario: Bare mirror normalised too

- **WHEN** the template's bare mirror has an `origin` URL that is not the SSH
  URL
- **THEN** it is rewritten in the same way before the bare mirror is fetched

## MODIFIED Requirements

### Requirement: Clone repos from inventory

The system SHALL read `repos.yml` and clone every listed repository into a local
`mirrors/<org>/<repo>/` directory using `git clone` against
`git@github.com:<org>/<repo>.git`. The repository name SHALL be taken from the
inventory rather than resolved through the GitHub API, and no credential SHALL
be configured, stored or passed by the tooling: SSH authenticates with the
operator's key.

#### Scenario: Fresh clone

- **WHEN** `mirrors/<org>/<repo>/` does not exist
- **THEN** the script runs `git clone git@github.com:<org>/<repo>.git
  mirrors/<org>/<repo>`

#### Scenario: Auth handled by SSH

- **WHEN** the operator's SSH key is known to their GitHub account and reachable
  by the agent
- **THEN** the script clones without any token configuration; private repos
  succeed

#### Scenario: No credential left behind

- **WHEN** a mirror has been cloned
- **THEN** its `origin` URL carries no credential, and the run has written no
  credential into any git config

#### Scenario: No `upstream` remote

- **WHEN** the repository is a fork of one the operator owns
- **THEN** the mirror carries `origin`, and `template` if it is not the
  template, and no other remote
