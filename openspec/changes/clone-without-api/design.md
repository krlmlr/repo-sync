## Context

`scripts/clone.sh` creates each mirror with `gh repo clone <org>/<repo> <dest>`.
That command is not a thin wrapper around `git clone`.
Before it forks git at all it queries the GraphQL API,
to resolve the repository's canonical name
and to learn whether it is a fork whose parent deserves an `upstream` remote.
The query is small; the point is that there is one per repository,
drawn from the same hourly budget as every other `gh` command
the same user has run — `gh pr list`, `gh run watch`, a CI job under the same token.

The inventory currently holds 48 repositories, 49 clones counting the template's
bare mirror. A fresh run makes 49 GraphQL queries before it has fetched a byte
of anything. When the budget is already spent, all 49 fail identically,
and `clone`'s failure isolation — which exists so one unreachable repo
does not end the batch — turns into 49 copies of the same message.

Git's transport is a separate service with separate limits.
`git clone` over HTTPS is not counted against the API rate limit,
and the project already relies on this:
`scripts/fetch_inventory.py` reads the whole inventory out of
`git ls-remote --heads` rather than asking the API for a branch list.

What `gh` is genuinely needed for is the credential.
The mirrors include private repositories, and `gh` holds the token that reaches
them — in its config file or the system keyring, depending on how the user
authenticated. Handing that token to git is a local operation:
`gh auth git-credential get` reads the stored credential and prints it
in git's credential-helper protocol. No request, no quota.

## Goals / Non-Goals

**Goals:**

- A full `mise run clone` consumes no GitHub API quota,
  and so cannot fail wholesale because some unrelated command spent it.
- Private repositories keep cloning and fetching with no token configuration
  beyond the `gh auth login` the project already requires.
- No token is written to disk, to a remote URL, or to a process argument list
  that another user on the machine can read.
- One rule, stated once, for how every GitHub-facing git command in this repo
  authenticates — so `clone` and `sync` cannot drift apart.

**Non-Goals:**

- Dropping `gh`. It stays, as the credential source.
- Supporting SSH remotes. See the decision below.
- Retrying, backing off, or detecting rate limits.
  The change removes the requests rather than managing them.

## Decisions

### `git clone` over HTTPS, with the URL built from the slug

`https://github.com/<org>/<repo>.git`, formed by string concatenation from the
`repos.yml` entry. The inventory is already the authority on what a repository
is called — `fetch_inventory.py` writes it from the branch names in
`krlmlr/actions-sync`, and `clone.sh` already derives the destination path
from it. Asking the API to confirm a name we then ignore buys nothing.

*Alternatives considered.*
Keeping `gh repo clone` and adding backoff: it makes a full run take an hour
in the bad case and still fails if the budget is spent by something else.
Keeping `gh repo clone` and batching the metadata into one GraphQL query:
fewer requests, but still a nonzero cost for information nothing reads,
and a good deal more machinery.
SSH (`git@github.com:<org>/<repo>.git`): no API cost either, but it needs a key
on the machine and in the account, which HTTPS-plus-`gh` does not.

### Authentication by per-invocation credential helper

Every GitHub-facing git command runs as:

```
git -c credential.helper= -c credential.helper='!gh auth git-credential' <args>
```

This is what `gh` itself puts in front of the git commands it runs
(`AuthenticatedCommand` in its git client), and it is worth copying exactly,
including the empty first value. `credential.helper` is a multi-valued config
key: helpers are consulted in order until one answers. Setting it to the empty
string clears the list, so a helper configured globally — a stale
`store` file, an OS keychain holding a revoked token — cannot answer ahead of
`gh` and send git off with a credential that no longer works.

The helper fires only when GitHub asks for authentication, so public
repositories clone anonymously and never invoke `gh` at all.

*Alternatives considered.*
`gh auth setup-git` writes the same helper into the user's **global** git
config: correct, but a mirroring script has no business editing config outside
its own tree, and it would silently change how the user's unrelated
repositories authenticate.
`https://x-access-token:$(gh auth token)@github.com/...` puts the token in the
remote URL, which git then writes into `.git/config` of every mirror —
48 copies of a live credential on disk, and in the process table while the
clone runs.
`-c http.extraHeader="Authorization: ..."` has the same process-table exposure,
and the header follows redirects to wherever GitHub points.

### The helper goes on remote-facing commands only

`git clone`, and the `git fetch --prune` / `git pull --rebase` that talk to
`origin`. Not on `git remote add`, `git remote set-url`, `git reset --hard`,
`git rev-parse`, and not on the `template` fetch — that remote is a relative
path to a directory a few levels up, and there is no one there to authenticate to.

This is a change for the fetches, which until now inherited whatever the user's
global config happened to provide. In practice that was `gh auth setup-git`'s
helper, if the user had ever run it: a mirror of a private repository could be
cloned successfully by `gh` and then fail to update on the next run, for want of
a credential the clone never needed to ask the user for. Routing both through
the same helper closes that gap.

### HTTPS unconditionally, ignoring `gh config get git_protocol`

`gh repo clone` builds its URL from that preference, so a contributor who set it
to `ssh` used to get SSH remotes. Reading the preference is free — it is a local
config lookup — but honouring it would mean the authentication story differs per
machine, and the credential helper, which is the whole mechanism here, applies to
HTTPS only.

Existing mirrors are not rewritten. A mirror cloned over SSH keeps its `origin`
and keeps working; only repositories cloned from now on are affected.

## Risks / Trade-offs

- **`gh` absent or unauthenticated, with private repos in the inventory.**
  Git prompts for a username on a terminal, or fails outright when there is
  none. → The same failure mode as today, and it stays per-repo: `clone`
  records the failure and moves on. Public repositories are unaffected, since
  no credential is ever requested for them. `env-setup` continues to state the
  prerequisite.

- **A repository renamed upstream.** `gh repo clone` resolved the new name
  through its query; `git clone` follows GitHub's HTTP redirect and clones the
  right content, but leaves `origin` pointing at the old URL. → Acceptable: the
  redirect keeps working, and `mise run fetch-inventory` is the mechanism for
  learning the new name. This does mean a rename is no longer noticed at clone
  time, which was never something the script reported anyway.

- **Forks no longer get an `upstream` remote.** → Intended. A mirror carries
  `origin` and, if it is not the template, `template`. A third remote appearing
  only for the repositories that happen to be forks of the authenticated user
  is inconsistency, not a feature.

- **`gh` must be on `PATH` under that name**, since the helper string names it.
  → It already must be, for the current `gh repo clone` to work at all.

## Migration Plan

None. The change is confined to how a clone is invoked; the mirror tree it
produces is byte-identical in layout to what `gh repo clone` produced, so
`mise run clone` against an existing tree takes the `fetch` path as usual and
notices nothing. The repositories that failed against the exhausted rate limit
clone on the next run, whatever the counter says.
