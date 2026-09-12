## ADDED Requirements

### Requirement: The per-checkout step is generic

The system SHALL bring each checkout in step using git commands that carry no knowledge of this repository:
a rebasing pull of its upstream, and a pruned fetch of every remote it has.
No template-specific option SHALL be passed,
no checkout SHALL be skipped for being the template,
and no checkout's remotes SHALL be inspected to decide what to run against it.

This is the point of keeping the template's bare mirror free of tags.
Once the far end holds no tags, the correct command for a checkout is the obvious one,
so the per-checkout half of a sync is something any tool that iterates over checkouts can perform --
`s`, `h`, a shell loop, or this capability's own fan-out --
and all of them reach the same result.

A checkout that has no `template` remote SHALL NOT fail the run on that account.
A fetch of every remote fetches the remotes that are there;
wiring remotes up is the `clone` capability's responsibility.

#### Scenario: Checkout brought in step

- **WHEN** a checkout is processed
- **THEN** it is rebased onto its own upstream and every one of its remotes is
  fetched with pruning, leaving its `refs/remotes/template/*` matching the bare
  mirror

#### Scenario: No template-specific options

- **WHEN** the commands run against a checkout are inspected
- **THEN** none of them carries an option or an argument naming the template

#### Scenario: Template's own checkout included

- **WHEN** the checkouts are processed
- **THEN** the template's own checkout is processed among them by the same
  commands, and is not skipped

#### Scenario: Equivalent to a generic sweep

- **WHEN** a tool that iterates over checkouts runs the same rebasing pull and
  pruned fetch of every remote
- **THEN** the checkouts end in the state this capability would have left them
  in, and no mirror gains a tag from the template

#### Scenario: Checkout without a `template` remote

- **WHEN** a checkout exists but has no `template` remote
- **THEN** its own upstream is still fetched and rebased, and the run does not
  count it as a failure

#### Scenario: Upstream tags still arrive

- **WHEN** a checkout's own GitHub upstream carries tags
- **THEN** those tags are fetched into the checkout as before, since only the
  template's tags were ever the problem

## MODIFIED Requirements

### Requirement: Refresh the template's bare mirror first

The system SHALL bring the template's bare mirror at
`mirrors/<template-org>/<template-repo>.git` into its required shape and up to date
before any checkout fetches from it,
so that the template refs the checkouts receive are the ones the upstream has
and so that the bare mirror holds no tags for them to import.

Bringing it into shape SHALL cover the same properties the `clone` capability establishes --
a fetch refspec that imports branches and no tags, no push-mirror setting, no refs under `refs/tags/`,
and a `HEAD` naming a branch the bare mirror has --
so that a tree last touched by an older version is corrected by whichever command runs next
rather than only by `clone`.

The bare mirror carries no `.git` entry, and so is not reachable by a sweep that discovers repositories by their working tree;
refreshing it is this capability's responsibility and no other's.
It is the one step of a sync that generic tooling cannot perform.

#### Scenario: Bare mirror refreshed before the template fetches

- **WHEN** sync runs against a populated `mirrors/` tree
- **THEN** the bare mirror is fetched before any checkout fetches from it, and
  every checkout ends the run with the template refs the upstream has

#### Scenario: Bare mirror normalised before the checkouts fetch

- **WHEN** sync runs against a tree whose bare mirror still carries tags or a
  refspec that would import them
- **THEN** the bare mirror is brought into its tagless shape before any checkout
  fetches from it, so no checkout imports a tag during that run

#### Scenario: Bare mirror missing

- **WHEN** `mirrors/<template-org>/<template-repo>.git` does not exist
- **THEN** the run records a failure naming `mise run clone` as the repair, and
  still rebases and fetches the checkouts, whose `template` remotes simply
  resolve to nothing

#### Scenario: Bare path occupied by a non-bare repository

- **WHEN** a directory exists at the bare mirror's path but is not a bare
  repository
- **THEN** the run records a failure and does not fetch into it

#### Scenario: Stale bare mirror still usable

- **WHEN** the fetch of the bare mirror fails after it has been brought into
  shape
- **THEN** the run records the failure and continues with the checkouts, since
  the refs the bare mirror already holds remain readable and carry no tags

## REMOVED Requirements

### Requirement: Fetch the `template` remote in every mirror

**Reason**: Replaced by "The per-checkout step is generic". Naming the `template` remote, passing `--no-tags` to its fetch, skipping the template's own checkout, and failing a mirror that has no such remote were all consequences of the bare mirror holding tags. With the bare mirror tagless and every checkout carrying the remote, the correct per-checkout command is a rebasing pull and a pruned fetch of every remote, which is what generic tooling already does.

**Migration**: No action. The replacement requirement fetches the `template` remote as one of the remotes it fetches, so the `refs/remotes/template/*` a checkout ends with are unchanged. Two behaviours are deliberately dropped: a checkout without a `template` remote is no longer a failure, and the template's own checkout is no longer skipped. Run `mise run clone` to wire up a checkout whose `template` remote is missing.
