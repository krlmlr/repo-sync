## MODIFIED Requirements

### Requirement: Rebase every mirror onto its upstream

The system SHALL run `git pull --rebase` in every mirror checkout listed in
`repos.yml` that exists on disk, keeping local commits that have not been
pushed. The pull SHALL carry `gh`'s credential helper, as the clone that created
the mirror did, so a private mirror is not cloneable but unpullable. Mirrors
that are not cloned SHALL be skipped without failing the run, since cloning is
the `clone` capability's responsibility.

#### Scenario: Mirror fast-forwarded

- **WHEN** a mirror has no local commits and its upstream has moved
- **THEN** the mirror is updated to the upstream tip

#### Scenario: Local commits preserved

- **WHEN** a mirror carries a local commit that is not on its upstream, and the
  upstream has moved
- **THEN** the local commit is rebased on top of the new upstream tip rather
  than discarded

#### Scenario: Private mirror rebased without global git configuration

- **WHEN** a mirror is of a private repository and the user's global git config
  names no credential helper
- **THEN** the pull succeeds on `gh`'s credential

#### Scenario: Mirror not cloned

- **WHEN** an inventory entry has no directory under `mirrors/`
- **THEN** the entry is reported as skipped and the run does not count it as a
  failure

#### Scenario: Rebase stops on a conflict

- **WHEN** a mirror's rebase stops on a conflict
- **THEN** the failure is recorded, the mirror is left for a human to resolve,
  and the run continues with the remaining mirrors
