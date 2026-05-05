## Context

The project currently uses inline Python code in two places to parse and manipulate `repos.yml`:

1. **`scripts/clone.sh`** embeds a multi-line `python3 -c "..."` block that loads YAML, validates the `template: true` flag, and emits ordered slugs back to bash. This is pure YAML wrangling living inside a shell script.
2. **`scripts/fetch_inventory.py`** uses `yaml.safe_load`/`yaml.dump` at its I/O boundaries to read existing template flags and write the new inventory.

Inline Python for YAML has several drawbacks:
- The `clone.sh` case forces shell readers to context-switch into Python for what is fundamentally a query against a YAML document
- Harder to test YAML operations independently of the surrounding logic
- Less transparent about what YAML transformations are happening
- Requires maintaining PyYAML as a runtime dependency

## Goals / Non-Goals

**Goals:**
- Establish `yq` as the standard tool for YAML operations
- Add `yq` to mise.toml as a required development tool
- Document and enforce preference for `yq` over inline Python
- Refactor existing Python code where YAML operations can be delegated to `yq`

**Non-Goals:**
- Replace all Python in the project (only YAML-specific operations)
- Migrate to a YAML-centric configuration system
- Change the project's overall architecture

## Decisions

### 1. Add `yq` to mise.toml
**Decision**: Add `yq` as a required tool with appropriate version pin.
**Rationale**: Makes it available to all developers and CI/CD without additional setup steps. Mise already manages tool versions, so this is the natural place.
**Alternatives Considered**:
- Package manager (apt/brew): Less consistent across environments
- Git submodule: Overkill for a single binary tool

### 2. Replace Inline Python YAML Code with `yq` Calls
**Decision**: Where Python code exclusively reads/modifies YAML, replace with `yq` invocations via subprocess or shell.
**Rationale**: Improves clarity and separates concerns. YAML operations become explicit shell commands that can be tested independently.
**Alternatives Considered**:
- Keep mixed approach: More complex to maintain, inconsistent patterns
- Pure Python solution: Loses the benefits of `yq`'s specialized tooling

### 3. Scope of Refactoring
**Decision**: Refactor `scripts/clone.sh` (high value: pure YAML query inside shell) and the YAML I/O at the edges of `scripts/fetch_inventory.py` (read existing flags, write final inventory). Keep Python for the in-memory transforms (`parse_repos`, `apply_template_flags`) where the data participates in non-trivial program logic.
**Rationale**: Clear boundary — YAML file operations (yq) vs. data transformation that happens to start/end as YAML (Python). Avoids contorting `yq` into doing work that's clearer in code.

## Risks / Trade-offs

**[Dependency Risk]** → Mitigation: `yq` is a widely-used, well-maintained project (github.com/mikefarah/yq). Version pinning in mise.toml ensures reproducibility.

**[Performance]** → Trade-off: Subprocess calls to `yq` may be slightly slower than inline Python for simple operations. This is acceptable given the clarity gains.

**[Refactoring Scope]** → Mitigation: Start with obvious candidates (the `clone.sh` inline Python block, `fetch_inventory.py`'s YAML edges). Defer or skip refactoring of complex Python logic that happens to touch YAML.

**[Output byte-equivalence]** → Risk: `persist-inventory`'s "Deterministic output" scenario requires byte-for-byte identical YAML across runs. `yq` and PyYAML may differ in quoting, key order, or trailing whitespace. Mitigation: Test before committing the refactor; if `yq` output differs, either pin `yq` formatting flags or update the spec scenario to allow the new canonical form.

**[Learning Curve]** → Mitigation: `yq` syntax is learnable and well-documented. Developers will benefit from the clarity of explicit YAML operations.
