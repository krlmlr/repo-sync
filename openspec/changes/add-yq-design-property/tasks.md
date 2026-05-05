## 1. Add yq to Project Configuration

- [x] 1.1 Add `yq` to `mise.toml` under `[tools]` (e.g. `yq = "4"`)
- [x] 1.2 Run `mise install` to verify yq installs correctly
- [x] 1.3 Confirm `yq --version` reports the pinned major version

## 2. Refactor `scripts/clone.sh`

- [x] 2.1 Replace the inline Python block (lines 8-30) that parses `repos.yml` with `yq` invocations
- [x] 2.2 Use `yq` to count entries with `.repos[] | select(.template == true)` and validate exactly one template exists
- [x] 2.3 Use `yq` to extract the template slug (`.repos[] | select(.template == true) | .org + "/" + .repo`)
- [x] 2.4 Use `yq` to emit ordered slugs (template first, then non-template entries)
- [x] 2.5 Verify error messages still match the existing scenarios in `openspec/specs/clone/spec.md` (no template / multiple templates)
- [x] 2.6 Run `mise run clone` against a sample inventory and confirm identical behavior

## 3. Refactor `scripts/fetch_inventory.py`

- [x] 3.1 Decide scope: the script's core data flow is Python-native, but the YAML I/O at boundaries (`load_template_flags`, final `yaml.dump`) are candidates
- [x] 3.2 Replace `yaml.safe_load(path.read_text())` in `load_template_flags` with a `yq` subprocess call returning the flagged entries as JSON
- [x] 3.3 Replace the final `yaml.dump({"repos": repos}, ...)` write with a pipeline that emits JSON to `yq -P` for YAML output, preserving block style and sort
- [x] 3.4 Confirm output is byte-for-byte identical to the previous PyYAML output (per `persist-inventory` spec's deterministic-output scenario)
- [x] 3.5 If byte-equivalence is not achievable with `yq`, document the diff and update the spec scenario accordingly

## 4. Remove Unused YAML Dependencies

- [x] 4.1 After refactoring, check if PyYAML is still imported anywhere in `scripts/`
- [x] 4.2 If no longer used, remove `PyYAML` from `requirements.txt`
- [x] 4.3 Re-run `mise run install` and confirm no missing-module errors

## 5. Document Design Principle

- [x] 5.1 Add a "Design principles" section to `ROADMAP.md` (or new `DESIGN.md`) capturing the yq preference
- [x] 5.2 Wording: "Prefer `yq` for YAML file operations over inline Python or PyYAML; use Python only when the YAML is loaded into a structure that participates in non-trivial program logic"
- [x] 5.3 Include a short example contrasting an inline-Python YAML read with the equivalent `yq` invocation
- [x] 5.4 Cross-reference the principle from `openspec/specs/yaml-operations/spec.md`

## 6. Testing and Validation

- [x] 6.1 Run `mise run fetch-inventory` and verify `repos.yml` content matches expectations
- [x] 6.2 Run `mise run clone` and verify mirrors are processed in template-first order
- [x] 6.3 Re-run both tasks and confirm idempotent behavior (no spurious diffs)
- [x] 6.4 Validate against existing scenarios in `clone`, `persist-inventory`, and the new `yaml-operations` specs
