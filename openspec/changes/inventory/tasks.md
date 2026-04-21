## 1. Project Setup

- [x] 1.1 Verify branch-name encoding — confirmed `<org>/<repo>`; infra branches excluded
- [ ] 1.2 Create `scripts/` directory and `pyproject.toml` with `PyYAML` as a dependency
- [ ] 1.3 Pin Python version (`.python-version` or `pyproject.toml` `requires-python`)

## 2. Fetch & Parse Script

- [ ] 2.1 Create `scripts/fetch_inventory.py` with a function that runs `git ls-remote --heads` on `krlmlr/actions-sync` and returns branch names
- [ ] 2.2 Implement branch-name parsing: split on first `/`, skip names without `/`, return list of `(org, repo)` tuples sorted case-insensitively
- [ ] 2.3 Add a guard that raises an error and exits non-zero if the parsed tuple list is empty

## 3. Persist

- [ ] 3.1 Implement `write_repos_yml(tuples, path)` serialising to `repos.yml` using PyYAML block style under the `repos:` key
- [ ] 3.2 Wire fetch + parse + write into a `__main__` entry point: `python -m scripts.fetch_inventory` overwrites `repos.yml`
- [x] 3.3 Verify `repos.yml` is valid YAML and contains expected entries — 59 repos committed, case-insensitive sort applied

## 4. Tests

- [ ] 4.1 Unit-test branch-name parsing: valid `org/repo`, name without slash (skipped), multiple slashes (split on first)
- [ ] 4.2 Test that output is sorted case-insensitively by org then repo
- [ ] 4.3 Test that empty result raises an error

## 5. Documentation

- [x] 5.1 Commit initial `repos.yml` — done
- [ ] 5.2 Update `ROADMAP.md` section 1 task list to reflect what is complete
- [ ] 5.3 Add a note in `README.md` explaining `repos.yml` source and how to refresh manually (`python -m scripts.fetch_inventory`)
