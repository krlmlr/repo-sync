## Context

`mirrors/` holds one checkout per inventory entry,
and every non-template mirror has a `template` remote pointing at the template's mirror by relative path.
The next roadmap steps read from that remote (§2.2, diff against the template)
and eventually write through it (§2.3, publish curated changes).

Two properties of the current wiring do not survive that.
A non-bare repository refuses a push to the branch it has checked out,
and a working tree is state that has nothing to do with the refs but is nevertheless what a fetch sees.
Both are solved by the same move: put a bare repository behind the remote.

The mirrors are refreshed by hand today, by sweeping git across them with `s` from `scriptlets`.
`s` is `h git`, and `h`'s discovery is `fd -HILg .git` — every path whose basename is `.git`.
A linked worktree has one (a `.git` *file*), which is why worktrees are included.
A bare repository has none.
So the sweep that keeps the mirrors current is exactly the tool that cannot keep a bare mirror current.

## Goals / Non-Goals

**Goals:**

- A `template` remote whose far end can be fetched from and pushed to, with no working tree in the way.
- Keep the template's checkout: it is the copy to read and reconcile against.
- One command that leaves every mirror in step with both its own upstream and the template, covering the bare mirror that no sweep reaches.
- Preserve the failure discipline the clone script already has: one bad repo is reported, not fatal.

**Non-Goals:**

- Pushing to the bare mirror or through it to GitHub.
- Bare mirrors for repositories nothing fetches from locally.
- Changing how `h`/`s` discover repositories.

## Decisions

### The bare mirror sits at `mirrors/<org>/<repo>.git`

Beside the checkout, not inside it and not in a directory of its own.
The `.git` suffix is the conventional name for a bare repository,
it cannot collide with an inventory entry (no `repo` field ends in `.git`),
and it keeps the `template` remote URL a one-character edit of the relative path already specified:
`../../<org>/<repo>` becomes `../../<org>/<repo>.git`.

Git resolves a relative remote URL from the top of the working tree that carries the remote — verified, including from a subdirectory —
so the whole `mirrors/` tree stays movable, as before.

*Alternative considered*: `mirrors/.bare/<org>/<repo>.git`.
It keeps `mirrors/<org>/` free of anything but checkouts, which would suit a future `discover-local` scan,
but it costs the relative-path symmetry and puts the mirror somewhere no one looks.
A discovery scan can skip a `.git` suffix as easily as a `.bare` directory.

### `--mirror`, not `--bare`

A `--bare` clone has no fetch refspec configured,
so `git fetch` in it updates nothing — it would need a refspec written by hand to be refreshable at all.
`--mirror` sets `+refs/*:refs/*` and `remote.origin.mirror`,
so a plain `git fetch --prune` brings every ref in line with GitHub, which is precisely what the mirror is for.

### Both mirrors of the template, both before anything points at them

The clone script already processes the template first, so that the relative path resolves by the time it is written into a remote.
The bare clone joins it there.
The two are independent clones of the same upstream,
so a failure in one says nothing about the other: both are attempted, and each reports separately.

A directory at the bare path that is not a bare repository is a failure, not something to fetch into blindly.

### `sync` rebases where `clone` resets

`clone` is the re-baselining tool: it resets each mirror hard onto `origin/HEAD`, discarding whatever was there.
`sync` is the gentle one: `git pull --rebase`, which keeps commits that have not been pushed yet
and stops on a conflict rather than dropping them.
Having both is the point — the two names then mean different things, and neither has to guess which one the operator wanted.

No `--autostash`.
A mirror with a dirty working tree fails its pull, loudly, and the run says so;
silently stashing and unstashing hides the one thing worth knowing.

### The order inside `sync`

1. Fetch the bare mirror. Nothing else reaches it.
2. `git pull --rebase` in each mirror.
3. Fetch `template` in each non-template mirror.

Step 1 before step 3 is what makes the run worth anything:
fetching `template` from a bare mirror that was last refreshed at clone time
propagates stale refs with every appearance of being up to date.
Step 2 is independent of the others,
so a mirror whose rebase stopped on a conflict
still gets the template refs it will be reconciled against.

### What counts as a failure

- A missing mirror directory is **skipped**, not failed:
  cloning is `clone`'s job, and `sync` works on what exists.
- A mirror that exists but has no `template` remote is a **failure**,
  naming `mise run clone` as the repair.
  Something that exists must be wired correctly.
- A missing or non-bare template mirror is a **failure**,
  and the `template` fetches are then skipped rather than
  each failing separately against a path that does not resolve.
- Failures are collected and reported at the end with a non-zero exit,
  as in `clone`.

### `scripts/lib.sh`

The template-designation rule — exactly one `template: true`, or a hard error —
is a specified behaviour that both tools must implement identically.
Extracting it (with the paths, the failure list and the report)
into a sourced, non-executable `lib.sh`
means the rule has one implementation rather than two copies that can drift.

## Risks / Trade-offs

- **Disk**: a second copy of the template.
  It is one repository out of the whole inventory, and bare — no working tree.
- **Two things to keep in step**: checkout and bare mirror can diverge.
  `clone` refreshes both, `sync` refreshes both;
  the checkout's `origin` and the bare mirror's `origin` are the same URL,
  so they converge on the same upstream.
- **`git pull --rebase` can stop mid-rebase** in a mirror with local commits.
  That is reported and left for a human;
  the rest of the run continues, and the template fetch still happens.
- **Existing clones** carry the old `template` URL until `mise run clone` runs.
  The rewrite is the already-specified idempotent normalisation,
  so the first run after this change fixes every mirror.

## Migration Plan

Run `mise run clone`.
It creates the bare mirror and rewrites every `template` remote URL in place.
Nothing needs deleting; the old URL is overwritten, not added to.
`mise run sync` is then the day-to-day command.

To roll back: point the remotes at the checkout again and delete
`mirrors/<org>/<repo>.git`. No state lives only in the bare mirror.

## Open Questions

- Should `sync` also cover the flat-sibling layout that `discover-local-subset`
  proposes? It walks `mirrors/` today, as `clone` does.
  Answering it belongs with that change, once discovery has a shape.
- Should `clone` gain `depends = ["install"]` as `sync` and `fetch-inventory`
  have? It reads `repos.yml` with PyYAML too. Left alone here as pre-existing.
