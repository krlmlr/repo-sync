## 1. Project Setup

- [ ] 1.1 Verify branch-name encoding by running `git ls-remote --heads https://github.com/krlmlr/actions-sync` and documenting the actual format
- [ ] 1.2 Create `scripts/` directory and add `pyproject.toml` (or `requirements.txt`) with `PyYAML` as a dependency
- [ ] 1.3 Add `.python-version` or document required Python version in `README.md`

## 2. Fetch & Parse Implementation

- [ ] 2.1 Create `scripts/fetch_inventory.py` with a function that runs `git ls-remote --heads` on `krlmlr/actions-sync` and returns raw branch names
- [ ] 2.2 Implement branch-name parsing: split on first `/`, skip names with no `/`, return sorted list of `(org, repo)` tuples
- [ ] 2.3 Add a guard that raises an error and exits non-zero if the parsed tuple list is empty

## 3. Persist Implementation

- [ ] 3.1 Implement `write_repos_yml(tuples, path)` that serialises the sorted tuple list to `repos.yml` using PyYAML block style under the `repos:` key
- [ ] 3.2 Wire fetch + parse + write into a `__main__` entry point: `python -m scripts.fetch_inventory` writes `repos.yml` at the repo root
- [ ] 3.3 Manually run the script and verify `repos.yml` is valid YAML and contains expected entries

## 4. Tests

- [ ] 4.1 Add unit tests for branch-name parsing covering: valid `org/repo`, name without slash (skipped), name with multiple slashes (split on first)
- [ ] 4.2 Add a test that verifies output is sorted (lexicographic by org then repo)
- [ ] 4.3 Add a test that verifies empty result raises an error

## 5. GitHub Actions Workflow

- [ ] 5.1 Create `.github/workflows/refresh-inventory.yml` with a daily cron schedule and `workflow_dispatch` trigger
- [ ] 5.2 Add a workflow step that installs Python dependencies and runs `python -m scripts.fetch_inventory`
- [ ] 5.3 Add a workflow step that diffs the generated `repos.yml` against HEAD and commits + pushes only if changed
- [ ] 5.4 Verify the workflow fails the run when the script exits non-zero (no `continue-on-error`)

## 6. Documentation & Cleanup

- [ ] 6.1 Add `repos.yml` to `.gitignore` exclusion list if needed, or commit an initial populated version
- [ ] 6.2 Update `ROADMAP.md` to mark section 1 tasks as complete once the workflow is merged
