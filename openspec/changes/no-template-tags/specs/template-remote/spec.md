## ADDED Requirements

### Requirement: The `template` remote imports no tags

The system SHALL configure every non-template mirror's `template` remote
so that no fetch of it writes into that mirror's `refs/tags/*`,
by setting `remote.template.tagOpt` to `--no-tags`.
Branch refs SHALL continue to be fetched into `refs/remotes/template/*` unchanged.

The setting SHALL be written on every run,
as the remote's URL already is,
so a mirror configured before this requirement existed is repaired without being re-cloned.

A fetch auto-follows every tag pointing at an object it downloads,
and a fetch of the template downloads the template's whole history.
`refs/remotes/*` gives each remote a namespace of its own;
`refs/tags/*` is flat and shared,
so an auto-followed tag arrives indistinguishable from the mirror's own
and is not removed by `--prune`.

#### Scenario: Remote configured

- **WHEN** the `template` remote is added to a mirror
- **THEN** `remote.template.tagOpt` is set to `--no-tags` in that mirror

#### Scenario: Mirror configured before this rule

- **WHEN** a mirror already carries a `template` remote without the setting
- **THEN** the next run writes it, in the same pass that normalises the URL

#### Scenario: Template fetched

- **WHEN** a mirror fetches its `template` remote
  and the template carries tags
- **THEN** the mirror's tag list is unchanged,
  and its `refs/remotes/template/*` branch refs are updated to match the bare mirror

#### Scenario: Template repo itself

- **WHEN** the mirror is the template repo
- **THEN** nothing is configured,
  since it carries no `template` remote

#### Scenario: Second run with no drift

- **WHEN** the configuration already names `--no-tags`
- **THEN** writing it again changes nothing
  and the run exits zero
