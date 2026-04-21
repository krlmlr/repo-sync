## 1. Project Setup

- [x] 1.1 Verify branch-name encoding by running `git ls-remote --heads https://github.com/krlmlr/actions-sync` — confirmed `<org>/<repo>`; infra branches excluded
- [ ] 1.2 Create `scripts/` directory and `pyproject.toml` with `PyYAML` as a dependency
- [ ] 1.3 Pin Python version (`.python-version` or `pyproject.toml` `requires-python`)

## 2. Fetch & Parse Script

- [ ] 2.1 Create `scripts/fetch_inventory.py` with a function that runs `git ls-remote --heads` on `krlmlr/actions-sync` and returns branch names
- [ ] 2.2 Implement branch-name parsing: split on first `/`, skip names without `/`, return sorted list of `(org, repo)` tuples
- [ ] 2.3 Add a guard that raises an error and exits non-zero if the parsed tuple list is empty

## 3. Persist

- [ ] 3.1 Implement `write_repos_yml(tuples, path)` serialising to `repos.yml` using PyYAML block style under the `repos:` key
- [ ] 3.2 Wire fetch + parse + write into a `__main__` entry point: `python -m scripts.fetch_inventory` overwrites `repos.yml`
- [x] 3.3 Verify `repos.yml` is valid YAML and contains expected entries — done (59 repos committed)

## 4. Tests

- [ ] 4.1 Unit-test branch-name parsing: valid `org/repo`, name without slash (skipped), multiple slashes (split on first)
- [ ] 4.2 Test that output is sorted lexicographically by org then repo
- [ ] 4.3 Test that empty result raises an error

## 5. GitHub Actions Workflow

- [ ] 5.1 Create `.github/workflows/refresh-inventory.yml` with daily cron and `workflow_dispatch` trigger
- [ ] 5.2 Workflow step: install Python deps and run `python -m scripts.fetch_inventory`
- [ ] 5.3 Workflow step: diff generated `repos.yml` against HEAD; commit and push only if changed
- [ ] 5.4 Confirm workflow fails (non-zero) when the script exits non-zero — no `continue-on-error`

## 6. Documentation & Cleanup

- [x] 6.1 Commit initial `repos.yml` — done
- [ ] 6.2 Update `ROADMAP.md` section 1 task list to reflect what is complete
- [ ] 6.3 Add a note in `README.md` (or create one) explaining `repos.yml` source and how to refresh manually
