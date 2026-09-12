## MODIFIED Requirements

### Requirement: Fetch the `template` remote in every mirror

The system SHALL fetch the `template` remote in every non-template mirror that
exists on disk, so each mirror holds the template refs it will be reconciled
against, and SHALL do so without importing tags. The template's own mirror
SHALL be skipped, as it carries no `template` remote.

The fetch SHALL suppress tags itself rather than relying on the remote's
configuration: `clone` writes that configuration, `sync` is the command that
runs every day, and a mirror wired up before the configuration existed must not
keep importing tags until someone happens to run the other command.

#### Scenario: Template refs updated

- **WHEN** a non-template mirror has a `template` remote and the bare mirror has
  moved
- **THEN** the mirror's `template/*` refs are updated to match the bare mirror

#### Scenario: Template tags stay out

- **WHEN** a mirror fetches its `template` remote and the template carries tags
- **THEN** the mirror's tag list is unchanged

#### Scenario: Mirror wired up before the remote suppressed tags

- **WHEN** a mirror's `template` remote carries no `tagOpt` setting
- **THEN** the fetch still imports no tags

#### Scenario: Mirror without a `template` remote

- **WHEN** a mirror exists but has no `template` remote
- **THEN** the run records a failure naming `mise run clone` as the repair

#### Scenario: Template mirror itself

- **WHEN** the mirror being processed is the template repo's own checkout
- **THEN** no `template` fetch is attempted for it

#### Scenario: Rebase failure does not stop the template fetch

- **WHEN** a mirror's `git pull --rebase` fails
- **THEN** its `template` remote is still fetched

#### Scenario: Tags already imported are left alone

- **WHEN** a mirror carries tags imported from the template by an earlier run
- **THEN** `sync` removes none of them, since it keeps local state that has not
  been pushed; `mise run clone` is what brings the mirror's tags back in line
