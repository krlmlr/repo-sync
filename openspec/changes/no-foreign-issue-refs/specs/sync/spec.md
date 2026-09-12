## ADDED Requirements

### Requirement: Keep the shared hooks configured on every sync

The system SHALL set `core.hooksPath` in every non-template mirror it visits, as `clone` does and with the same value.

`clone` is the tool reached for when a mirror needs re-baselining;
`sync` is the one that runs every day.
A guard installed only by the command nobody ran today is not installed.

The step SHALL run before the mirror's fetches,
SHALL be recorded as a failure like the others,
and SHALL NOT prevent the remaining steps from running.

#### Scenario: Mirror missing the setting

- **WHEN** a mirror has no `core.hooksPath` and `sync` runs
- **THEN** the setting is written,
  before the template's commits are fetched into that mirror

#### Scenario: Mirror not cloned

- **WHEN** no mirror exists at `mirrors/<org>/<repo>/`
- **THEN** the repository is skipped,
  as it is for the other steps

#### Scenario: Template mirror itself

- **WHEN** the mirror is the template repo
- **THEN** nothing is configured

#### Scenario: Second run with no drift

- **WHEN** the setting is already correct
- **THEN** writing it again changes nothing
  and the run exits zero
