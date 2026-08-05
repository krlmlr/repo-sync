## ADDED Requirements

### Requirement: SSH access to GitHub documented as prerequisite

`mise.toml` SHALL document that the operator needs SSH access to GitHub before
running the `clone` task: a key their account knows, reachable by the agent, and
`github.com` present in `known_hosts` so the first connection has nothing to ask
about. No API token and no `gh` login SHALL be required by any task.

#### Scenario: SSH configured

- **WHEN** the operator's key is on their GitHub account and loaded in the agent
- **THEN** `mise run clone` proceeds without additional configuration, for
  public and private repositories alike

#### Scenario: No usable key

- **WHEN** no key the account accepts is available
- **THEN** `git` fails for that repository with its own descriptive error, the
  failure is recorded, and the task exits non-zero once the rest of the
  inventory has been processed

#### Scenario: Host key not yet known

- **WHEN** `github.com` is absent from `known_hosts` and the run is
  non-interactive
- **THEN** the connection is refused rather than trusted silently; adding the
  host key is a documented one-time setup step, not something the tooling
  bypasses

## REMOVED Requirements

### Requirement: gh authentication documented as prerequisite

**Reason**: No script in the project calls `gh` any more. Cloning and updating
mirrors is `git` over SSH throughout, so an authenticated `gh` is no longer a
prerequisite for anything — and documenting it as one would send contributors to
set up a credential that nothing reads.

**Migration**: Set up SSH access to GitHub instead, per the requirement above.
Nothing needs to be undone: an existing `gh` login is simply unused, and
`mise run clone` rewrites each mirror's `origin` from HTTPS to SSH on its next
pass.
