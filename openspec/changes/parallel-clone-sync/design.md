## Context

`clone.sh` and `sync.sh` are both a `while read slug` loop around a handful of `git` invocations.
The loop is the only thing making the work sequential:
the git commands inside it touch one mirror,
reach one upstream,
and share nothing with the next iteration.

The two tools are not Python.
Python appears in this repository exactly twice — `scripts/fetch_inventory.py`,
which is a task of its own,
and the `python3 -c` heredoc in `load_inventory` that turns `repos.yml` into a list of slugs.
Neither is in the loop.
So the question of how to parallelise is a question about bash,
and the answer is a process-level fan-out rather than anything thread- or asyncio-shaped.

## Goals / Non-Goals

**Goals:**

- Spend the run's wall clock waiting on several repositories at once.
- Keep the failure discipline exactly as it is:
  one bad repository is recorded and reported,
  never fatal to the batch.
- Keep the two orderings the mirrors depend on.
- Keep the output readable — a parallel run that cannot be read
  when something goes wrong has traded the wrong thing away.
- Leave a way to reproduce one repository's failure on its own.

**Non-Goals:**

- Retries, backoff or timeouts.
- Any change to what the git commands are or what they do.
- A progress bar, a summary table, or any other new reporting.
- Parallelising `fetch_inventory.py`.

## Decisions

### GNU parallel, not `xargs -P` and not `&` with `wait`

All three can run eight things at once.
They differ in what the run looks like afterwards,
which is the whole of the decision.

`xargs -P` gives each child the terminal directly,
so eight clones write into the same stream at the same time.
Git's own output is multi-line and unprefixed,
so `Resolving deltas: 100%` arrives with nothing to say which repository resolved them.
A failure has to be reassembled by eye from lines scattered across the run.

`&` plus `wait` is the same picture with the job control written by hand:
a `jobs` count to keep under a limit,
a `wait -n` loop,
and the same interleaved output at the end of it.

GNU parallel groups by default:
each job's stdout and stderr are held and printed together when it finishes.
Eight repositories then produce eight blocks in the order they complete,
and every block is one repository's story from `==> clone` to whatever ended it.
That is the property worth the dependency.

*Alternative considered*: `--tag`,
which prefixes every output line with the slug and makes even interleaved output attributable,
opening the door to `--line-buffer` and live progress.
It is a real option,
and it costs a tab and a repeated slug on every line of git's output.
Grouping already puts each repository's lines together;
tagging them as well is belt and braces on forty-eight-repository runs
where the `==>` header is right there at the top of the block.

### `parallel` re-invokes the script, rather than calling an exported function

GNU parallel runs its command through `$SHELL`.
That is the operator's login shell,
which is not necessarily bash —
and an `export -f`'d bash function does not survive being handed to zsh or fish.
The failure mode is remote from the cause:
a working script that stops working because of what somebody's terminal opens with.

A path to a script with its own shebang survives all of it.
So the per-mirror work is reached as `clone.sh --checkout <slug>`, `clone.sh --bare <slug>` and `sync.sh <slug>`.

The child entry points are worth having for their own sake.
A repository that failed inside a batch of eight is reproduced by running the same command the batch ran,
on its own,
with nothing else in the output — and,
with the flags being ordinary arguments,
under `bash -x` or a debugger if it comes to that.

Each child would otherwise re-parse `repos.yml` to learn which slug is the template —
forty-eight Python interpreters started to answer the same question.
The parent exports the answer instead,
and `load_template_slug` reads it,
falling back to parsing the inventory
when there is no parent to have set it,
which is what makes running a child by hand work.

### The failure list is a file, not an array

`fail` appended to a bash array,
and `report_failures` read it at the end.
In child processes that silently stops working:
the array lives in the child,
dies with it,
and the parent reports an empty list on a run
where half the inventory failed.
A quiet zero exit on a failed run is the worst outcome available here,
so this is the one part of the change that had to move rather than adapt.

The file is a `mktemp` in `$TMPDIR`,
its path exported
so children inherit it,
and each `fail` appends one short line.
Appends that small are not interleaved,
so no lock is needed.
The process that created the file removes it on exit;
a child that inherited the path must leave it,
since the parent has not read it yet.

The report is sorted before printing.
The order failures are recorded in is the order the jobs happened to finish in,
which varies between runs of the same broken tree —
and a report that reshuffles itself cannot be diffed against the last one.

### Ordering becomes a barrier between batches

Two orderings matter,
and neither survives being left to a loop's sort order once the loop is gone:

1. The template's checkout and bare mirror exist before any mirror is given a `template` remote pointing at them.
2. The bare mirror is fetched before any mirror fetches from it —
   otherwise `sync` propagates refs that were current at the last clone,
   with every appearance of being up to date.

Both become explicit:
`clone` runs the template's two mirrors as their own batch and waits for it before starting the rest;
`sync` fetches the bare mirror in the parent and only then fans out.
`load_inventory` accordingly yields `template_slug` and `other_slugs`
rather than one `ordered_slugs` list with the template sorted to the front —
the guarantee is now in the control flow,
where it can be seen,
rather than in a sort order that has to be remembered.

The template's two mirrors run side by side within their batch.
They are independent clones of one upstream,
so one failing still says nothing about the other,
exactly as before.

### Eight jobs by default

The work is network-bound:
a clone waits on GitHub far longer than it spends resolving deltas locally,
so the useful degree of parallelism is above the core count rather than equal to it,
and parallel's own default of one job per core is the wrong default here.

Eight is a compromise —
enough to hide the latency,
few enough to stay polite to GitHub over a handful of SSH connections
and to keep eight concurrent delta-resolutions from swamping a small machine.
`REPO_SYNC_JOBS` moves it,
and `REPO_SYNC_JOBS=1` restores the old behaviour exactly:
the same commands in the same order,
one at a time,
which is the state to reduce to when a failure does not make sense.

### Whether the bare mirror is usable is read from disk, not passed down

`sync` used to carry a `bare_present` flag from the check at the top into the loop.
A flag has to be passed to a child,
which means an environment variable,
which means a child run by hand needs to know to set it.

`template_bare_usable` asks the disk instead —
the directory is there
and it is a bare repository —
so parent and child reach the same verdict independently,
and a child run by hand reaches it too.
A *failed fetch* deliberately does not enter into it:
the refs the bare mirror already holds are still readable,
which is exactly the existing "stale bare mirror still usable" behaviour.

The parent reports a missing or non-bare mirror once,
before the fan-out,
and the children stay quiet about it.
Reporting it per mirror would bury the one fact worth knowing under forty-seven copies of itself.

### GNU parallel is checked for, not fallen back from

A sequential fallback would be a second code path through the same work,
taken only on machines nobody tests on,
and the specification would have to describe both.
`require_parallel` checks once,
before any work starts,
and says what to install.

It also checks that this is GNU parallel:
moreutils ships a different program under the same name,
which understands none of the options used here.
Without the check,
that machine gets forty-eight identical usage errors and no clue.

## Risks / Trade-offs

- **A new dependency.** GNU parallel is packaged everywhere
  (`apt install parallel`, `brew install parallel`)
  and is already present in the development container.
  Weighed against the alternative —
  hand-written job control and unreadable output —
  it is the cheaper side.
- **Output arrives in completion order, not inventory order.** `--keep-order` would restore inventory order
  at the cost of holding a finished job's output
  until every job before it has finished,
  which is exactly the progress feedback a long run is wanted for.
  The failure *report* is sorted,
  so the part that gets read after the fact is stable.
- **Eight concurrent SSH connections to GitHub.** Well inside anything GitHub objects to,
  and not an API call among them,
  so no rate limit is involved.
  `REPO_SYNC_JOBS` is there
  if a network disagrees.
- **A rebase conflict now stops inside a child.** It stopped inside a loop iteration before;
  either way the mirror is left mid-rebase for a human,
  and the failure is reported.
  What changes is that seven other repositories were worked on meanwhile.
- **`git` no longer sees a terminal**,
  so it prints no progress bars.
  The per-repository summary lines it writes on completion are unaffected,
  and eight simultaneous progress bars would have been noise.

## Migration Plan

Install GNU parallel;
run `mise run clone` or `mise run sync` as before.
No state changes: the same git commands run against the same directories,
and a `mirrors/` tree built by the sequential version is not distinguishable from one built by this.

To roll back,
`REPO_SYNC_JOBS=1` reproduces the old sequencing without touching the code.

## Open Questions

- Should `REPO_SYNC_JOBS` live in `mise.toml` as an `[env]` entry rather than as a default in `lib.sh`?
  That would make it visible where the tasks are,
  at the cost of the scripts no longer having a working default
  when run directly.
- Should `clone` gain `depends = ["install"]` as `sync` and `fetch-inventory` have?
  It reads `repos.yml` with PyYAML too.
  Carried over untouched from the previous change,
  which asked the same question.
