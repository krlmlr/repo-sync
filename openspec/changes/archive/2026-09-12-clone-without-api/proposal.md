## Why

`mise run clone` asks the GitHub API for something it does not need.
`gh repo clone` resolves the repository through a GraphQL query before it hands over to `git clone` —
one query per repository, forty-eight of them in a full run,
against a budget shared with every other `gh` command the user has run that hour.
When that budget is spent, the run does not degrade, it collapses:

```
==> clone cynkra/constructive
GraphQL: API rate limit already exceeded for user ID 1741643.
FAIL: clone cynkra/constructive
```

repeated for every entry in the inventory, none of them cloned, none of them cloneable until the hour rolls over.
The failure is per-repo by construction — `clone` isolates failures —
but the cause is not: it is one exhausted counter, and every repo hits it.

Nothing about mirroring a repository needs that query.
Git's own transport is not on the API rate limit,
and `scripts/fetch_inventory.py` already reaches GitHub that way, with `git ls-remote` and no `gh` in sight.
`clone` is the last step that spends API quota to do a git operation.

## What Changes

- **Clone with `git` over SSH, not with `gh`.**
  `scripts/clone.sh` runs `git clone git@github.com:<org>/<repo>.git`
  (and `git clone --mirror` for the template's bare mirror) in place of `gh repo clone`.
  A run of the whole inventory now costs zero API requests and cannot be rate-limited into failing wholesale.
- **`gh` is no longer used at all.**
  SSH authenticates with a key that lives in the agent and in the account,
  so there is no credential for the scripts to obtain, hold or hand over:
  no helper to configure, and nothing token-shaped to leak into a remote URL or a process argument list.
  The prerequisite becomes SSH access to GitHub, in place of `gh auth login`.
- **Normalise `origin` on every run.**
  A mirror cloned before this change carries an HTTPS `origin`;
  `clone` rewrites it to the SSH URL, exactly as it already normalises the `template` remote.
  Which transport a mirror speaks should follow from the inventory, not from the day it was created.
- Forks lose the `upstream` remote that `gh repo clone` adds when the clone is of your own fork.
  A mirror wants `origin` and `template` and nothing else.

## Capabilities

### New Capabilities

<!-- None: this change moves an existing capability off the API; it adds no new one. -->

### Modified Capabilities

- `clone`: the clone transport becomes `git clone` over SSH,
  a run of the full inventory is required to consume no API quota,
  and `origin` is normalised to the SSH URL on every run.
- `env-setup`: the prerequisite is SSH access to GitHub rather than an authenticated `gh`.

## Impact

- **`scripts/lib.sh`** — one helper: the SSH URL for a slug.
- **`scripts/clone.sh`** — clones over SSH and normalises `origin`.
- **`scripts/sync.sh`** — unchanged.
  It fetches and rebases through remotes that are already configured, and does not care what they say.
- **`mise.toml`**, **`ROADMAP.md`** — the prerequisite and the transport.
- **Existing mirrors**: no manual migration.
  The next `clone` rewrites `origin` from HTTPS to SSH and carries on fetching.
- **One dependency dropped.** `gh` is no longer required by any script here.

## Out of Scope

- `scripts/fetch_inventory.py`, which reads a public branch list with an anonymous `git ls-remote` over HTTPS.
  It costs no quota and needs no key;
  leaving it alone keeps the one task that runs before any of this is set up runnable before any of this is set up.
- Rate-limit backoff or retry.
  There is no request left in `clone` to back off from; adding a retry loop would be machinery guarding an empty room.
- Rewriting the `template` remote, which is a relative local path and has no transport to choose.
