## Why

`mise run clone` asks the GitHub API for something it does not need.
`gh repo clone` resolves the repository through a GraphQL query
before it hands over to `git clone` —
one query per repository, forty-eight of them in a full run,
against a budget shared with every other `gh` command the user has run that hour.
When that budget is spent, the run does not degrade, it collapses:

```
==> clone cynkra/constructive
GraphQL: API rate limit already exceeded for user ID 1741643.
FAIL: clone cynkra/constructive
```

repeated for every entry in the inventory,
none of them cloned, none of them cloneable until the hour rolls over.
The failure is per-repo by construction — `clone` isolates failures —
but the cause is not: it is one exhausted counter,
and every repo hits it.

Nothing about mirroring a repository needs that query.
Git's own HTTPS transport is not on the API rate limit,
and `scripts/fetch_inventory.py` already reaches GitHub that way,
with `git ls-remote` and no `gh` in sight.
`clone` is the last step that spends API quota to do a git operation.

## What Changes

- **Clone with `git`, not with `gh`.**
  `scripts/clone.sh` runs `git clone https://github.com/<org>/<repo>.git`
  (and `git clone --mirror` for the template's bare mirror)
  in place of `gh repo clone`.
  A run of the whole inventory now costs zero API requests
  and cannot be rate-limited into failing wholesale.
- **Keep `gh` as the credential source.**
  Every git command that talks to GitHub carries
  `-c credential.helper= -c credential.helper='!gh auth git-credential'`,
  which is exactly what `gh` puts in front of the git commands it runs itself.
  Producing a token that way is a local read of `gh`'s own configuration,
  not a request.
  Private repositories keep working, and no token is written anywhere.
- **Authenticate the fetches too.**
  `git fetch --prune` in `clone`, and `git pull --rebase` in `sync`,
  currently inherit whatever credential helper the user's global git config has,
  which is not necessarily any.
  They now carry the same helper as the clone that created the mirror,
  so a private mirror updates on the strength of the same authentication
  that was good enough to fetch it in the first place.
  Local-path operations — the `template` remote, `reset`, `remote set-url` —
  are left as plain `git`: there is nothing there to authenticate to.
- Mirror remotes are HTTPS, always.
  `gh repo clone` honours `gh config get git_protocol`,
  so a contributor who prefers SSH used to get SSH remotes;
  they now get HTTPS.
  This is the protocol the credential helper is for,
  and the one that needs no key on the machine.
- Forks lose the `upstream` remote that `gh repo clone` adds
  when the clone is of your own fork.
  A mirror wants `origin` and `template` and nothing else.

## Capabilities

### New Capabilities

<!-- None: this change moves an existing capability off the API; it adds no new one. -->

### Modified Capabilities

- `clone`: the clone transport becomes `git clone` over HTTPS
  with `gh` as the credential helper,
  and a run of the full inventory is required to consume no API quota.
- `sync`: the upstream-facing commands authenticate through `gh`
  the same way `clone` does.
- `env-setup`: `gh` remains a prerequisite,
  but as the thing that holds the credential, not the thing that clones.

## Impact

- **`scripts/lib.sh`** — two helpers: the HTTPS URL for a slug,
  and the `git` invocation that carries `gh`'s credential helper.
- **`scripts/clone.sh`** — clones and origin fetches go through them.
- **`scripts/sync.sh`** — `git pull --rebase` goes through them.
- **`ROADMAP.md`** — §2.1 records the transport it actually uses.
- **Existing mirrors**: unaffected.
  A mirror already on disk is updated by `git fetch`, as before;
  only its authentication becomes explicit.
  A mirror cloned over SSH keeps its SSH `origin` until someone changes it.
- No new dependencies, and one fewer reason to need `gh` at all.

## Out of Scope

- Removing the `gh` dependency outright.
  A credential helper is a small enough surface to keep,
  and it is the one part of `gh` that costs nothing to call.
- Rate-limit backoff or retry.
  There is no request left in `clone` to back off from;
  adding a retry loop would be machinery guarding an empty room.
- `scripts/fetch_inventory.py`, which already talks to GitHub over git.
