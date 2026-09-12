## Context

`scripts/clone.sh` creates each mirror with `gh repo clone <org>/<repo> <dest>`.
That command is not a thin wrapper around `git clone`.
Before it forks git at all
it queries the GraphQL API,
to resolve the repository's canonical name
and to learn whether it is a fork
whose parent deserves an `upstream` remote.
The query is small;
the point is that there is one per repository,
drawn from the same hourly budget as every other `gh` command the same user has run —
`gh pr list`, `gh run watch`, a CI job under the same token.

The inventory currently holds 48 repositories, 49 clones counting the template's bare mirror.
A fresh run makes 49 GraphQL queries
before it has fetched a byte of anything.
When the budget is already spent,
all 49 fail identically,
and `clone`'s failure isolation — which exists so one unreachable repo does not end the batch —
turns into 49 copies of the same message.

Git's transport is a separate service with separate limits.
Neither `git clone` over SSH nor over HTTPS is counted against the API rate limit,
and the project already relies on this:
`scripts/fetch_inventory.py` reads the whole inventory out of `git ls-remote --heads`
rather than asking the API for a branch list.

## Goals / Non-Goals

**Goals:**

- A full `mise run clone` consumes no GitHub API quota,
  and so cannot fail wholesale
  because some unrelated command spent it.
- Private repositories keep cloning and fetching.
- No credential is written to disk, to a remote URL, or to a process argument list
  that another user on the machine can read.
- The mirror tree ends up with one transport throughout,
  whenever each mirror in it was created.

**Non-Goals:**

- Retrying, backing off, or detecting rate limits.
  The change removes the requests
  rather than managing them.
- Changing `sync`,
  which operates through remotes `clone` has already configured.
- Changing `fetch_inventory.py`.

## Decisions

### `git clone` over SSH, with the URL built from the slug

`git@github.com:<org>/<repo>.git`, formed by string concatenation from the `repos.yml` entry.
The inventory is already the authority on what a repository is called —
`fetch_inventory.py` writes it from the branch names in `krlmlr/actions-sync`,
and `clone.sh` already derives the destination path from it.
Asking the API to confirm a name we then ignore buys nothing.

SSH carries the authentication in a key
that is already in the agent and already on the account.
That leaves the scripts with no credential to handle at all,
which is a smaller thing to get right than handling one carefully:
nothing to configure, nothing to expire mid-run, nothing token-shaped
that could end up in a `.git/config` or a `ps` line.

*Alternatives considered.*
Keeping `gh repo clone` and adding backoff:
it makes a full run take an hour in the bad case
and still fails
if the budget is spent by something else.
Keeping `gh repo clone` and batching the metadata into one GraphQL query:
fewer requests,
but still a nonzero cost for information nothing reads,
and a good deal more machinery.
HTTPS with `gh` as a credential helper
(`-c credential.helper='!gh auth git-credential'`,
which is what `gh` puts in front of its own git commands):
it also costs no quota,
and it needs no key on the machine —
but it keeps `gh` as a dependency for the sake of a credential
that SSH does not need,
and it leaves the tooling holding a token.

### `origin` is normalised on every run

`git remote set-url origin "$(github_url "$slug")"` runs before the fetch, on both the checkout and the bare mirror.
Mirrors created before this change have an HTTPS `origin`;
without the rewrite they would keep it indefinitely,
and the tree's transport would be a record of when each mirror was cloned
rather than a property of the tree.

This is the same treatment `configure_template_remote` already gives the `template` remote,
for the same reason,
and the `clone` spec already calls that one "drift normalised".
Extending it to `origin` costs one command
and makes the change self-applying:
an existing mirror tree needs no migration step.

*Alternative considered.*
Rewriting only on a fresh clone,
and leaving existing mirrors on HTTPS. Cheaper,
but "use SSH" would then be true only of repositories cloned after today,
and a `mise run clone` would not be enough to make the tree consistent —
which is the one thing that command is for.

### `sync` is untouched

`git pull --rebase` and `git fetch template` use remotes
that `clone` has already configured;
they neither know nor care which transport those remotes name.
Once `clone` has normalised `origin`,
`sync` pulls over SSH without having been told anything.

## Risks / Trade-offs

- **SSH access is now a hard prerequisite**,
  where an HTTPS clone of a public repository needed nothing at all.
  A machine with no key on the account cannot mirror even the public entries.
  → Accepted, and documented in `env-setup` and `mise.toml`.
  This is a mirroring toolkit for repositories the operator has write access to;
  §2.3 of the roadmap pushes back through these same remotes,
  so the key is needed either way.

- **The host key must be known.**
  A first SSH connection to an unknown host prompts,
  and a non-interactive run with no answer available fails —
  48 times,
  which resembles the failure this change is fixing.
  → Documented as part of the prerequisite: `github.com` in `known_hosts` before the first run.
  Deliberately *not* worked around with `StrictHostKeyChecking=accept-new`,
  which would trade a legible one-time setup step for a silently weaker trust decision on every run.

- **`origin` normalisation overwrites a deliberately-set URL.**
  Someone who pointed a mirror at a fork or a local path will find it rewritten.
  → Accepted: `mirrors/` is a generated tree,
  and `clone` already resets its working trees hard onto `origin/HEAD` and rewrites `template` remotes.
  A mirror is not the place to keep a local decision.

- **A repository renamed upstream.**
  `gh repo clone` resolved the new name through its query;
  `git` over SSH gets a clear "repository moved" error
  rather than a redirect.
  → It is reported as a per-repo failure,
  which is the honest outcome:
  the inventory is stale,
  and `mise run fetch-inventory` is what fixes it.

- **Forks no longer get an `upstream` remote.** → Intended.
  A mirror carries `origin` and,
  if it is not the template, `template`.
  A third remote appearing only for the repositories
  that happen to be forks of the authenticated user
  is inconsistency, not a feature.

## Migration Plan

None to run by hand.
The mirror tree's layout is unchanged,
so `mise run clone` against an existing tree takes the `fetch` path as usual,
rewriting each `origin` from HTTPS to SSH on the way past.
The repositories
that failed against the exhausted rate limit clone on the next run,
whatever the counter says.
