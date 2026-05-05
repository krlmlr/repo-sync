## ADDED Requirements

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
The system SHALL ensure every non-template mirror has a git remote named `template` pointing at the HTTPS URL of the template repo.

#### Scenario: Fresh non-template mirror
- **WHEN** a non-template mirror is freshly cloned and has no `template` remote
- **THEN** the system runs `git remote add template https://github.com/<template-org>/<template-repo>.git` inside that mirror

#### Scenario: Existing `template` remote with stale URL
- **WHEN** a non-template mirror already has a `template` remote pointing at a different URL
- **THEN** the system runs `git remote set-url template <current-url>` to normalise it

#### Scenario: Template repo itself
- **WHEN** the mirror is the template repo
- **THEN** the system does not add a `template` remote on it

### Requirement: Idempotent template-remote configuration
The system SHALL configure the `template` remote without error on repeated runs, producing no changes when the configuration is already correct.

#### Scenario: Second run with no drift
- **WHEN** `clone.sh` is run twice with no inventory or template-URL changes
- **THEN** the second run reports the `template` remote already configured and exits zero
