## ADDED Requirements

### Requirement: Configure `template` remote during clone
The system SHALL configure a git remote named `template` on every non-template mirror after a successful clone or update, pointing at the HTTPS URL of the entry flagged `template: true` in `repos.yml`.

#### Scenario: Template URL added to non-template mirror
- **WHEN** a non-template mirror is cloned or updated successfully
- **THEN** the script ensures a `template` remote exists in that mirror with URL `https://github.com/<template-org>/<template-repo>.git`

#### Scenario: Template mirror skipped
- **WHEN** the mirror being processed is the template repo itself
- **THEN** the script does not add a `template` remote on it

#### Scenario: Drift normalised
- **WHEN** the template entry in `repos.yml` changes between runs
- **THEN** the next `clone` run rewrites every non-template mirror's `template` remote URL to match the new template

### Requirement: Fail when template designation is invalid
The system SHALL exit non-zero before processing any mirror if `repos.yml` does not contain exactly one entry with `template: true`.

#### Scenario: No template flagged
- **WHEN** `repos.yml` has no entry with `template: true`
- **THEN** the script exits non-zero with a message naming the missing flag, before cloning or updating any mirror

#### Scenario: Multiple templates flagged
- **WHEN** `repos.yml` has more than one entry with `template: true`
- **THEN** the script exits non-zero with a message listing the conflicting entries
