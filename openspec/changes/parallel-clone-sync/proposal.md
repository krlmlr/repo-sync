## Why

A `clone` or `sync` run is forty-eight independent conversations with GitHub,
held one after another.

Each of them spends almost all of its time waiting —
on a TCP handshake,
on an SSH key exchange,
on GitHub deciding which objects to send —
and while one waits,
nothing else happens.
The run therefore costs the sum of every wait,
on a machine that was idle for nearly all of it.

Measured over eight repositories of the inventory:

- `clone` into an empty `mirrors/`: 9.6s serial, 3.3s eight at a time.
- `sync` over that tree with nothing to fetch: 5.9s serial, 1.9s.

Six times that inventory is the real one,
and the difference is the difference between a command you run while you wait and one you start and walk away from.

Nothing about the work asks for the ordering.
Each mirror talks to its own upstream and reads the template's bare mirror;
no mirror reads, writes or waits for another.
The two orderings that do matter —
the template's mirrors before the mirrors that point at them,
and the bare mirror's fetch before the fetches that read it —
are barriers between batches,
not a reason to walk the whole inventory in single file.

## What Changes

- **The inventory is worked on several repositories at a time.**
  `parallel` fans the per-repository work out,
  eight jobs by default,
  `REPO_SYNC_JOBS` to choose another number.
  `REPO_SYNC_JOBS=1` puts the run back in single file,
  which is what to reach for when reading a confusing failure.
- **GNU parallel, specifically.**
  Its output is grouped:
  each job's stdout and stderr are held and printed together when the job finishes,
  so a repository's lines arrive as one block.
  `xargs -P` would shuffle eight repositories' lines into each other and leave every failure to be reassembled by eye.
- **Each script re-invokes itself once per repository.**
  `clone.sh --checkout <slug>`, `clone.sh --bare <slug>` and `sync.sh <slug>` are the child entry points,
  and they are also usable by hand:
  a repository that failed in a batch of eight can be reproduced on its own,
  in isolation,
  with one command.
- **The orderings become explicit barriers.**
  `clone` finishes both of the template's mirrors before starting anything that points at them;
  `sync` finishes the bare mirror's fetch before any mirror fetches from it.
  Neither now rests on a walk happening to reach the template first.
- **Failures are collected in a file rather than in a shell array.**
  The work happens in child processes,
  and an array a child appends to dies with it —
  the parent would report an empty list on a run
  where half the inventory failed.
  The report is sorted,
  so two identical runs produce identical output.
- **GNU parallel becomes a prerequisite**,
  checked for at startup and named in `mise.toml` beside the SSH one.

## Capabilities

### New Capabilities

<!-- None: this change is about how the existing work is scheduled. -->

### Modified Capabilities

- `clone`: the inventory is mirrored several repositories at a time,
  and the template's two mirrors become a barrier rather than the first steps of a walk.
- `sync`: the mirrors are rebased and fetched several at a time,
  behind the bare mirror's fetch.
- `env-setup`: GNU parallel joins SSH access as a documented prerequisite.

## Impact

- **`scripts/lib.sh`** —
  the fan-out,
  the failure log,
  the parallel check,
  and `other_slugs` in place of `ordered_slugs`.
- **`scripts/clone.sh`** — two batches with a barrier between them,
  and a `--checkout` / `--bare` child entry point.
- **`scripts/sync.sh`** — one batch behind the bare fetch,
  and a per-slug child entry point.
- **`mise.toml`**, **`ROADMAP.md`** — the prerequisite and the concurrency.
- **Existing mirrors**: nothing to migrate.
  The same git commands run against the same directories,
  in a different order.
- **One dependency added.** GNU parallel is required by `clone` and `sync`.

## Out of Scope

- Retry or backoff on a failed clone.
  A repository that fails still fails; running eight at a time changes when it is attempted,
  not what happens when it does not answer.
- Per-repository timeouts. `parallel` can impose one (`--timeout`),
  but choosing a number that is generous enough for `duckdb-r`
  and tight enough to be worth having is a separate question from whether the work runs concurrently.
- `scripts/fetch_inventory.py`,
  which is one `git ls-remote` and has nothing to fan out.
- How `s` and `h` discover repositories.
- Parallelism inside a single git operation (`git clone --jobs`, `fetch.parallel`),
  which is a different axis:
  this change is about the repositories,
  not about the submodules in one.
