## ADDED Requirements

### Requirement: Point every non-template mirror at the shared hooks

The system SHALL set `core.hooksPath` in every non-template mirror to this repository's tracked `hooks/` directory,
expressed relative to the mirror's working tree as `../../../hooks`.
Git runs hooks from the top of the working tree, so the relative path resolves wherever the mirror tree as a whole sits.

The setting SHALL be written on every run, as the `template` remote's URL and its `tagOpt` are,
so a mirror made before the hooks existed is repaired without being re-cloned.

#### Scenario: Fresh non-template mirror

- **WHEN** a non-template mirror is cloned
- **THEN** `core.hooksPath` in that mirror names `../../../hooks`

#### Scenario: Mirror configured before this rule

- **WHEN** a mirror carries no `core.hooksPath`, or one pointing elsewhere
- **THEN** the next run writes it, in the same pass that normalises the `template` remote

#### Scenario: Template repo itself

- **WHEN** the mirror is the template repo
- **THEN** nothing is configured: it has no `template` remote, and its own commits refer to its own issues

#### Scenario: Second run with no drift

- **WHEN** the configuration already names `../../../hooks`
- **THEN** writing it again changes nothing and the run exits zero
