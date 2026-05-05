# Devcontainer security roadmap

The devcontainer in this directory deliberately ships in a tight default
configuration. Inside the container, an agent (Claude Code or otherwise)
can read and modify any file under `/workspace` — that includes the
repo itself and the `mirrors/<org>/<repo>/` clones — but cannot push, pull,
or otherwise reach the network beyond a single allowlisted endpoint.

This document plans the path from "locked down" to "useful for the full
clone → reconcile → push pipeline" described in the top-level
[`ROADMAP.md`](../ROADMAP.md), without losing the security properties at
each step.

## Reference

The Dockerfile and `init-firewall.sh` are adapted from Anthropic's
reference at
[`anthropics/claude-code/.devcontainer/`](https://github.com/anthropics/claude-code/tree/main/.devcontainer).
The upstream firewall whitelists GitHub, npm, the Anthropic API,
`statsig`, `sentry`, and the VS Code marketplace; ours starts from the
same iptables/ipset skeleton but ships only `api.anthropic.com`.

Background: [Claude Code devcontainer docs](https://code.claude.com/docs/en/devcontainer.md)
and [sandboxing docs](https://code.claude.com/docs/en/sandboxing.md).

## Stage 0 — current default

| Capability                              | Allowed |
| --------------------------------------- | ------- |
| Read any file in `/workspace`           | yes     |
| Modify any file in `/workspace`         | yes     |
| Modify files in `mirrors/<org>/<repo>/` | yes     |
| DNS, loopback, host network             | yes     |
| `api.anthropic.com` (Claude Code)       | yes     |
| `git push` / `git fetch` to GitHub      | no      |
| `gh repo clone` / `gh` API calls        | no      |
| `pip install`, `npm install` at runtime | no      |
| Arbitrary HTTPS (web fetch / search)    | no      |

Properties this preserves:

- **No exfiltration channel.** A compromised agent cannot push
  workspace contents to a GitHub repo, post them as a gist, paste them
  to a webhook, or POST to an attacker-controlled endpoint. The only
  reachable host is `api.anthropic.com`, which already sees the prompt
  contents by virtue of being the model provider.
- **No supply-chain pull.** A compromised agent cannot install a
  malicious npm/PyPI package mid-session. All Python deps are baked
  into the image at build time from the committed `requirements.txt`.
- **Revertible blast radius.** All destructive actions are confined to
  `/workspace`, which is a bind mount of the host repo; `git status` /
  `git restore` / `git reset` on the host recover any unwanted edit.
- **No privileged escalation path beyond the firewall script.** The
  `node` user can only sudo `/usr/local/bin/init-firewall.sh`; no
  general sudo, no other passwordless commands.

What this stage cannot do (yet):

- Run `mise run fetch-inventory` (needs `git ls-remote` over HTTPS).
- Run `mise run clone` (needs `gh repo clone`).
- Push curated changes back to foreign repos (the section 2.3 milestone
  in the top-level roadmap).

The intended workflow at stage 0 is: clone the mirrors on the host
(outside the container), let the agent reconcile / edit them inside,
review the diff on the host, push from the host.

## Stage 1 — read-only GitHub egress

**Goal:** allow the agent to refresh `repos.yml` and the mirror clones
from inside the container, without unlocking pushes.

**Change:** in `init-firewall.sh`, restore the upstream block that
fetches `https://api.github.com/meta` and adds the aggregated `web`,
`api`, and `git` CIDR ranges to the `allowed-domains` ipset. Keep the
default OUTPUT policy at DROP.

**Why this is still safe-ish:**

- `git push` over HTTPS goes to the same GitHub IPs as `git fetch`, so
  the firewall does not by itself prevent pushes. The push restriction
  has to come from a *credential* boundary: do not mount or generate
  any credential that has push scope on the foreign repos.
- Concretely: do not bind-mount `~/.config/gh/`, do not provide a
  `GITHUB_TOKEN` env var with `repo` scope, and do not run
  `gh auth login` inside the container. With no credential, `git push`
  fails with 403 even though the network reaches GitHub.
- A read-only fine-grained PAT (Contents: Read on the relevant repos)
  is acceptable to mount; a classic token or a token with `repo`
  scope is not.

**Residual risk:**

- A compromised agent can now exfiltrate workspace contents by writing
  them to a public gist via the GitHub API — *if* it has any token
  with gist scope. Mitigation is the same as above: only mount
  read-only fine-grained tokens.
- The CIDR list is fetched once at firewall init and not refreshed; if
  GitHub adds ranges mid-session, those are unreachable until the next
  firewall run. This is the same drift the upstream Anthropic config
  has and is acceptable.

**Verification:** the `init-firewall.sh` self-check should be extended
to assert that `https://api.github.com/zen` returns 200 *and* that
`https://gist.githubusercontent.com` (or another non-allowlisted host)
still fails.

## Stage 2 — PyPI / npm registry egress

**Goal:** allow `pip install` / `npm install` at runtime, so that
`requirements.txt` does not have to be a build-time-only contract and
small dev-only packages can be tried interactively.

**Change:** add `pypi.org`, `files.pythonhosted.org`, and
`registry.npmjs.org` to the `allowed-domains` ipset.

**Security cost — this is the biggest single jump in the roadmap:**

- PyPI and npm are the canonical supply-chain attack surface. A typo
  in a package name, or a transitive dep getting compromised, lands
  arbitrary code execution inside the container with full read/write
  on `/workspace`.
- The earlier stages' "no exfiltration channel" property weakens: a
  malicious package can phone home over the GitHub egress opened in
  stage 1.

**Required mitigations before flipping this on:**

- Pin every dependency to a hash, not just a version. `pip install
  --require-hashes -r requirements.txt`, with `pip-compile
  --generate-hashes` producing the file. For npm, `npm ci` against a
  committed `package-lock.json` with `--ignore-scripts`.
- Treat any unpinned `pip install` / `npm install` invoked from a
  Claude session as a privileged action requiring human review.
- Consider disabling install scripts entirely (`npm config set
  ignore-scripts true`) inside the image.

## Stage 3 — write-scoped GitHub credential for `repo-sync/*` branches

**Goal:** wire up section 2.3 of the top-level roadmap — push curated
changes back to foreign repos.

**Change:** mount a *single* fine-grained PAT scoped to:

- the inventory of foreign repos in `repos.yml`,
- "Contents: Read and write" only,
- and (recommended) restricted to refs matching `repo-sync/*` via
  branch protection on each foreign repo, so the token cannot
  overwrite `main`.

The firewall does not need to change — stage 1 already opened GitHub
egress; this stage opens the *credential* boundary, which is the real
control.

**Security cost:**

- A compromised agent can now write to all 59 foreign repos under the
  `repo-sync/*` namespace. Branch protection on `main` in each foreign
  repo is the last line of defense; without it, this stage is not
  safe.
- Token leakage via PR description / commit message / log is now a
  real concern. Add a pre-commit hook that scans staged diffs and
  reject commits matching `gh[ps]_[A-Za-z0-9]{36,}` or
  `github_pat_[A-Za-z0-9_]{80,}`.

**Required mitigations:**

- Branch protection on `main` (and any release branches) in every
  foreign repo, with "Restrict who can push" set to exclude the bot
  identity. Audit this with the existing inventory.
- Token TTL ≤ 30 days, rotated automatically.
- Push activity surfaced in a dashboard (section 2.4 of the top-level
  roadmap), so unexpected pushes are visible.
- Dry-run mode (also section 2.3) wired so the agent can produce a
  diff without holding the token.

## Stage 4 — general HTTPS egress (documentation lookups, etc.)

**Goal:** let the agent fetch arbitrary documentation pages, package
docs, RFCs, blog posts, etc. — i.e. enable `WebFetch` / `WebSearch`
inside the container.

**Change:** drop the firewall to allow OUTPUT to TCP/443 unconditionally,
or remove the firewall entirely. This is functionally equivalent to
not running `init-firewall.sh` at all.

**Security cost:**

- Free exfiltration channel. Any string the agent has read can be
  POSTed to any host. There is no longer a network-layer control;
  trust shifts entirely to the model provider's safety properties and
  to the credential boundary.
- This stage should only be enabled in environments where the
  workspace contents are not sensitive (public OSS code) or where an
  explicit "review before send" approval flow is in place for outgoing
  HTTP requests.

**Required mitigations:**

- Treat this as a per-task opt-in, not a default. The default branch
  of `.devcontainer/devcontainer.json` should remain at stage 0–1.
- If general egress is needed, prefer routing through an HTTP proxy
  with logging (mitmproxy, squid with access log) so a post-hoc audit
  is possible.

## Decision rule

Move one stage at a time, only when the milestone in the top-level
roadmap actually requires it:

| Top-level milestone                              | Minimum stage |
| ------------------------------------------------ | ------------- |
| 2.1 Clone (run inside container)                 | Stage 1       |
| 2.2 Reconcile (no network needed)                | Stage 0       |
| 2.3 Commit & push                                | Stage 3       |
| 2.4 Orchestration (CI runs the pipeline)         | Stage 3       |
| Interactive doc lookups during agent sessions    | Stage 4       |

Stage 2 (PyPI / npm) is orthogonal — adopt it only if the project
gains a workflow that genuinely needs runtime package installs;
otherwise keep deps baked into the image.
