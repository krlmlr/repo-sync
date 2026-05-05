## Context

Roadmap §2.2 needs a single canonical template repo so reconcile can diff every foreign mirror against a known reference. The inventory (`repos.yml`) currently has no notion of "this one is the template". Mirrors are cloned by `scripts/clone.sh` with only `origin` configured. `cynkra/cynkratemplate` is already in the inventory; its name signals its intended role.

## Goals / Non-Goals

**Goals:**
- Mark exactly one inventory entry as the template and have downstream tooling read that flag.
- Ensure every non-template mirror has a `template` git remote pointing at the template repo, idempotently maintained on each `clone` run.
- Preserve the `template: true` flag across `fetch_inventory.py` refreshes (it is human-curated metadata, not derivable from `actions-sync`).

**Non-Goals:**
- Actually reconciling against the template (separate roadmap step §2.2 bullets 2-4).
- Fetching from the template remote on every clone run — only the remote URL is configured. Fetch is left to the reconcile step.
- Multiple templates or per-org templates. Exactly one template, globally.
- Bidirectional sync of template content into the template repo itself.

## Decisions

### Template flag location: `template: true` on the entry

**Decision**: Add a boolean `template: true` field to the chosen entry in `repos.yml`. Exactly one entry SHALL carry this flag.

**Rationale**: The template is a real repo in the inventory — duplicating its slug at the document root would split state. A per-entry flag keeps the inventory shape uniform and makes the template discoverable with a single pass.

**Alternative considered**: Top-level `template: <org>/<repo>` key. Rejected — introduces a second source of truth (the slug appears twice; they can drift).

### Template repo: `cynkra/cynkratemplate`

**Decision**: Mark `cynkra/cynkratemplate` as the template.

**Rationale**: The name explicitly identifies its purpose; it is already in the inventory (no new repo to provision). No alternative candidate has equally clear naming.

**Reversibility**: Changing the template later is a one-line edit in `repos.yml` plus one `clone` run to retarget every `template` remote.

### Remote name: `template`

**Decision**: Use the literal remote name `template` (matching roadmap wording) on every non-template mirror.

**Rationale**: Reserved-looking, descriptive, unlikely to collide with upstream-defined remotes. `origin` stays as the foreign repo's own GitHub URL.

### Remote URL: HTTPS via the template's GitHub slug

**Decision**: `https://github.com/<template-org>/<template-repo>.git`.

**Rationale**: Matches the auth model already used by `gh repo clone` (HTTPS + `gh` credential helper). Read-only access is sufficient — reconcile only fetches.

### Remote management: configure on every clone run, idempotently

**Decision**: After clone/update, the script runs `git remote set-url template <url>` if the remote exists, otherwise `git remote add template <url>`. The template repo's own mirror is skipped.

**Rationale**: `set-url` is idempotent and corrects drift if the template slug changes. Re-running the script normalises every mirror without manual cleanup. Skipping the template's own mirror avoids a self-pointing remote.

**Alternative considered**: A separate `add-template-remote` script and mise task. Rejected — the operation is conceptually part of "set up a usable mirror", and pairing it with clone keeps the entry-point count down.

### Inventory refresh preserves the flag

**Decision**: `scripts/fetch_inventory.py` reads the existing `repos.yml` (if present), extracts entries marked `template: true`, and re-applies the flag to matching entries in the new inventory before writing.

**Rationale**: Branches in `actions-sync` carry no template metadata. Without merge logic, every refresh would silently drop the flag. If the previously-flagged repo no longer appears in the new inventory, the writer SHALL fail loudly rather than silently dropping the flag.

### Validation: exactly one template

**Decision**: Both the writer (`fetch_inventory.py`) and the consumer (`clone.sh`) SHALL fail if zero or more than one entries carry `template: true`.

**Rationale**: Ambiguous template state has no sensible default; failing fast surfaces the misconfiguration before reconcile uses it.

## Risks / Trade-offs

- **Template repo renamed or transferred** → existing `template` remotes point to the old URL. Mitigation: `set-url` on every run normalises the URL, so a single re-run after updating `repos.yml` fixes every mirror.
- **Flag silently dropped on refresh** → if the inventory writer is updated incorrectly, the template designation could be lost. Mitigation: `fetch_inventory.py` fails when the previously-flagged repo is missing from the new branch list, and `clone.sh` fails when no entry is flagged.
- **HTTPS auth required for private templates** → currently `cynkratemplate` is public. If a future template is private, `gh`'s credential helper handles it transparently; no script change needed.

## Migration Plan

1. Edit `repos.yml`: add `template: true` to the `cynkra/cynkratemplate` entry.
2. Update `scripts/fetch_inventory.py` to preserve the flag.
3. Update `scripts/clone.sh` to configure the `template` remote on non-template mirrors.
4. Run `mise run clone` to backfill `template` remotes across already-cloned mirrors.
5. Mark the first bullet under §2.2 in `ROADMAP.md` as done.

Rollback: revert the `repos.yml` edit and the script changes; the stray `template` remotes in `mirrors/` are harmless and can be removed with `git remote remove template` if desired.
