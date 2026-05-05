## Context

The project currently uses inline Python code in various places to parse and manipulate YAML files. This approach has several drawbacks:
- Requires understanding both Python and YAML in the same context
- Harder to test YAML operations independently
- Less transparent about what YAML transformations are happening
- Requires maintaining YAML parsing libraries

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
**Decision**: Focus on scripts and task runners that manipulate YAML. Leave library code that uses PyYAML for data processing.
**Rationale**: Clear boundary between "YAML file operations" (yq) vs "YAML data transformation" (Python libraries). Avoids over-engineering.

## Risks / Trade-offs

**[Dependency Risk]** → Mitigation: `yq` is a widely-used, well-maintained project (github.com/mikefarah/yq). Version pinning in mise.toml ensures reproducibility.

**[Performance]** → Trade-off: Subprocess calls to `yq` may be slightly slower than inline Python for simple operations. This is acceptable given the clarity gains.

**[Refactoring Scope]** → Mitigation: Start with obvious candidates (scripts, configuration processors). Defer refactoring of complex Python logic that happens to touch YAML.

**[Learning Curve]** → Mitigation: `yq` syntax is learnable and well-documented. Developers will benefit from the clarity of explicit YAML operations.
