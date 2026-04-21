## ADDED Requirements

### Requirement: Fetch branch list from actions-sync
The system SHALL fetch all remote branch names from `krlmlr/actions-sync` using `git ls-remote --heads` without requiring authentication.

#### Scenario: Successful branch fetch
- **WHEN** `krlmlr/actions-sync` is accessible and has one or more branches
- **THEN** the system returns a list of all branch names (strings after stripping the `refs/heads/` prefix)

#### Scenario: Empty branch list
- **WHEN** the remote repository has no branches (or only branches that fail parsing)
- **THEN** the system raises an error and exits non-zero rather than producing an empty inventory

#### Scenario: Network failure
- **WHEN** the remote repository is unreachable
- **THEN** the system exits non-zero with a descriptive error message and writes nothing to disk

### Requirement: Parse branch names into org/repo tuples
The system SHALL parse each branch name into an `(org, repo)` tuple by splitting on the first `/` character.

#### Scenario: Valid branch name
- **WHEN** a branch name is `acme/my-repo`
- **THEN** the parsed tuple is `org=acme`, `repo=my-repo`

#### Scenario: Branch name without slash
- **WHEN** a branch name contains no `/` (e.g. `main`)
- **THEN** that branch is silently skipped and not included in the output

#### Scenario: Branch name with multiple slashes
- **WHEN** a branch name is `acme/my/deep-repo`
- **THEN** the parsed tuple is `org=acme`, `repo=my/deep-repo` (split on first `/` only)
