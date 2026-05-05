## 1. Add yq to Project Configuration

- [ ] 1.1 Add `yq` to `mise.toml` with appropriate version constraint
- [ ] 1.2 Run `mise install` to verify yq installs correctly
- [ ] 1.3 Test `yq --version` to confirm it's available in PATH

## 2. Identify Refactoring Candidates

- [ ] 2.1 Scan Python scripts for YAML parsing libraries (PyYAML imports, open().read() with yaml, etc.)
- [ ] 2.2 Document which scripts and functions perform YAML read/write operations
- [ ] 2.3 Prioritize candidates: start with simple read/write operations, defer complex transformations

## 3. Refactor YAML Operations

- [ ] 3.1 Replace inline YAML reads in `scripts/fetch_inventory.py` with `yq` calls (if applicable)
- [ ] 3.2 Replace inline YAML modifications in scripts with `yq eval -i` (if applicable)
- [ ] 3.3 Update subprocess calls to use `yq` instead of Python YAML libraries
- [ ] 3.4 Test refactored scripts to ensure identical behavior

## 4. Remove Unused YAML Dependencies

- [ ] 4.1 Check if PyYAML is still needed after refactoring
- [ ] 4.2 If no longer used, remove PyYAML from dependencies
- [ ] 4.3 Update `requirements.txt` or equivalent

## 5. Document Design Principle

- [ ] 5.1 Create or update `DESIGN.md` (or similar) with the yq design principle
- [ ] 5.2 Add guidance: "Prefer `yq` for YAML file operations over inline Python"
- [ ] 5.3 Add example usage patterns in documentation
- [ ] 5.4 Update code review guidelines to reference this principle

## 6. Testing and Validation

- [ ] 6.1 Run all existing tests to ensure refactored code behaves identically
- [ ] 6.2 Verify `mise run <task>` works correctly with refactored scripts
- [ ] 6.3 Test in CI/CD environment to confirm yq availability
