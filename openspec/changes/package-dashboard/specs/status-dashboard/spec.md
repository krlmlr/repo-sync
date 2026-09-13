## Purpose

Present a collected snapshot as one page that ranks the portfolio by what needs attention, and publish that snapshot beside it
as a stable machine-readable document, so the same reading serves a maintainer glancing at a table and a program deciding what
to work on next.

## ADDED Requirements

### Requirement: The snapshot is published as a document in its own right

The system SHALL publish the collected snapshot at a stable location beside the page, as the machine-readable version of
everything the page shows. It SHALL carry its schema version, and its field names SHALL be stable across publications: a
field SHALL be added or marked deprecated rather than repurposed.

#### Scenario: Snapshot is retrievable without the page

- **WHEN** a consumer requests the published snapshot's URL
- **THEN** the current snapshot is returned as a machine-readable document, with no scraping of the page required

#### Scenario: Page and document cannot disagree

- **WHEN** the page displays a value for a package
- **THEN** that value is present as a field in the published snapshot the page read, rather than being derived during display

#### Scenario: Field meaning is stable

- **WHEN** a metric's definition changes such that an existing field would mean something new
- **THEN** a new field is published and the old one is marked deprecated, rather than the existing field changing meaning

### Requirement: The page is a client over the snapshot

The page SHALL obtain its data from the snapshot at view time rather than carrying data baked into its markup, so that a new
collection is visible on reload without the page being rebuilt. Where fetching is not available to the viewer, the page SHALL
use a snapshot embedded in the document instead.

#### Scenario: Published page picks up a new collection

- **WHEN** a new snapshot is published and the page is reloaded without being rebuilt
- **THEN** the page shows the new reading

#### Scenario: Local page opened from the filesystem

- **WHEN** a locally rendered page is opened directly from disk, where fetching a neighbouring file is not permitted
- **THEN** the page renders from the snapshot embedded in it, with the same layout and the same values as the published page

#### Scenario: Snapshot cannot be loaded

- **WHEN** the page can neither fetch nor find an embedded snapshot
- **THEN** it says so plainly instead of rendering an empty table

### Requirement: The page ranks by attention and shows why

The page SHALL present packages ordered by their attention score by default, and SHALL display the reasons recorded for each
score beside it, so that a ranking can be checked rather than trusted.

#### Scenario: Worklist at the top

- **WHEN** the page is opened with no interaction
- **THEN** the packages needing most attention appear first, each showing the reasons that put it there

#### Scenario: Nothing needs attention

- **WHEN** every package scores zero
- **THEN** the page says the portfolio is clear rather than presenting an arbitrary order as a ranking

### Requirement: The table can be reordered and narrowed

The page SHALL let a viewer sort by any presented metric and narrow the table by a text filter over package identity, without
a server and without reloading.

#### Scenario: Sort by a metric

- **WHEN** a viewer sorts by commits since the last release
- **THEN** the rows reorder by that field, and absent values sort together rather than as zero

#### Scenario: Filter by name

- **WHEN** a viewer types part of an organisation or repository name
- **THEN** only matching rows remain, and the aggregate counts state that a filter is applied

### Requirement: Absent and stale data are shown as such

The page SHALL distinguish a value that was measured from one that is absent because it does not apply, and from one carried
forward because the package could not be read. A group the snapshot does not carry SHALL be omitted rather than rendered
empty.

#### Scenario: Stale row

- **WHEN** an entry's values were carried forward from an earlier collection
- **THEN** the row is marked stale and shows when those values were last actually observed

#### Scenario: Template group absent

- **WHEN** the snapshot was collected on a machine without the mirrors
- **THEN** the page omits the template section entirely and says it was not collected, rather than showing every package as fully in step

#### Scenario: Metric does not apply

- **WHEN** a repository is not an R package
- **THEN** its CRAN and package-version cells read as not applicable, distinct from a measured zero

### Requirement: Snapshots are retained as history

The system SHALL retain published snapshots, and SHALL maintain a portfolio-level series recording, per collection, the
counts that describe the reading as a whole. The page SHALL be able to present that series as a trend.

#### Scenario: A snapshot is retained per publication

- **WHEN** a collection is published
- **THEN** its snapshot is retained alongside the current one, identified by when it was collected

#### Scenario: Portfolio trend

- **WHEN** several collections have been published
- **THEN** the page can show how the portfolio-level counts have moved across them

#### Scenario: History is unavailable

- **WHEN** no retained history can be read
- **THEN** the current reading still renders in full and the trend is omitted

### Requirement: Publication is scheduled, self-establishing and reversible

The system SHALL publish on a schedule and on demand. It SHALL create the publication branch on first run when it does not
exist. Publication SHALL be disableable without affecting collection, and removing the published output SHALL affect nothing
but the page.

#### Scenario: First run with no publication branch

- **WHEN** publication runs and the branch does not exist
- **THEN** it is created and the page and snapshot are published to it

#### Scenario: Unchanged reading

- **WHEN** a collection produces output identical to what is already published
- **THEN** nothing is committed, so the publication history records changes rather than runs

#### Scenario: Publication disabled

- **WHEN** scheduled publication is turned off
- **THEN** local collection and local rendering continue to work unchanged

### Requirement: Rendering works without collecting

Rendering SHALL take a snapshot as its input and require no network access, so that the page can be developed and verified
against a recorded snapshot.

#### Scenario: Render from a recorded snapshot

- **WHEN** the renderer is run against a snapshot file with no network available
- **THEN** it produces the page, and the same snapshot always produces the same page
