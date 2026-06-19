## 1. Discovery script

- [x] 1.1 Add `scripts/discover_local.py` that reads `repos.yml` and validates exactly one `template: true` entry (exit non-zero otherwise, before emitting anything)
- [x] 1.2 Implement an origin-remote resolver that normalizes SSH and HTTPS URLs (with/without trailing `.git`, case-insensitive) to `<org>/<repo>`
- [x] 1.3 Scan the base directory for candidates in both layouts: flat children of the base dir, and `mirrors/<org>/<repo>/`
- [x] 1.4 Match a candidate only when basename == `repo` AND resolved `origin` == `<org>/<repo>`; disambiguate same-named repos across orgs via origin
- [x] 1.5 Mark the discovered `template: true` entry as the template; warn (continue) when it is absent locally
- [x] 1.6 Report unrecognized extras and origin mismatches; exit zero whenever a valid subset is found
- [x] 1.7 Emit the subset as machine-readable output (`org`, `repo`, absolute path, template flag), sorted case-insensitively by `org` then `repo` for deterministic output
- [x] 1.8 Default the base directory to repo-sync's parent, overridable via argument/flag

## 2. Task runner wiring

- [x] 2.1 Add a named `mise` task for discovery in `mise.toml`, consistent with `fetch-inventory` and `clone`
- [x] 2.2 Confirm `mise run <task>` executes the script with the pinned Python interpreter and supports a non-default base directory

## 3. repo-sync AGENTS.md

- [x] 3.1 Add `AGENTS.md` at the repo root describing the repo purpose (mirror inventory, reconcile vs template, push back)
- [x] 3.2 Document the inventory/template model (`repos.yml`, single `template: true`) and the mirror-vs-sibling layouts
- [x] 3.3 Document the `mise run` tasks (`fetch-inventory`, `clone`, the new discovery task) and the OpenSpec workflow (explore/propose/apply/archive, specs under `openspec/`)
- [x] 3.4 Reference the discovery capability so the doc stays accurate to this change

## 4. Verification

- [x] 4.1 Verify flat-sibling discovery against the current session layout (`/home/user/*`) returns the expected subset with `cynkratemplate` flagged as template
- [x] 4.2 Verify a basename match with a mismatched origin is skipped and reported
- [x] 4.3 Verify an extra sibling not in `repos.yml` is reported and discovery still exits zero
- [x] 4.4 Verify deterministic output across two consecutive runs
- [x] 4.5 Verify a missing/duplicate `template: true` flag produces the documented behavior (warn-and-continue vs. hard error respectively)
