## ADDED Requirements

### Requirement: Scheduled refresh workflow
The system SHALL provide a GitHub Actions workflow that runs the fetch-and-persist pipeline on a daily schedule (cron) and on manual trigger (`workflow_dispatch`).

#### Scenario: Scheduled run
- **WHEN** the cron schedule fires
- **THEN** the workflow runs the inventory script and proceeds to commit-or-skip logic

#### Scenario: Manual trigger
- **WHEN** a user triggers the workflow via `workflow_dispatch`
- **THEN** the workflow runs the inventory script identically to the scheduled path

### Requirement: Commit only when inventory changes
The system SHALL commit the updated `repos.yml` only when its content differs from the version currently committed in the repository, so that no-op runs produce no commit.

#### Scenario: Inventory changed
- **WHEN** the newly generated `repos.yml` differs from the committed version
- **THEN** the workflow commits and pushes the updated file to the default branch with a descriptive commit message

#### Scenario: Inventory unchanged
- **WHEN** the newly generated `repos.yml` is byte-for-byte identical to the committed version
- **THEN** the workflow exits successfully without creating a commit or push

### Requirement: Workflow failure is visible
The system SHALL cause the workflow run to fail (non-zero exit) if the inventory script exits non-zero, so that fetch errors are surfaced in GitHub Actions UI.

#### Scenario: Script failure propagates
- **WHEN** the inventory script exits non-zero (e.g. network error, empty result)
- **THEN** the workflow step fails and no commit is attempted

#### Scenario: Successful run is green
- **WHEN** the inventory script exits zero and the commit-or-skip step completes
- **THEN** the workflow run is marked as successful
