# Software Design Document — Per-Project Runtime Config and Merged Policy Loading

## Document Metadata

- **Document ID:** D00000001
- **Title:** Per-Project Runtime Config and Merged Policy Loading
- **Author(s):** Colin J.D. Stewart
- **Owner:** Colin J.D. Stewart
- **Created (YYYY-MM-DD):** 2026-02-23
- **Last Updated (YYYY-MM-DD):** 2026-02-23
- **Status:** APPROVED
- **Target Release / Milestone:** Next minor release
- **Repository / Area:** komply / CLI + scan engine

---

## 1. Summary

Add a per-project runtime config file at `.komply/00-config.xml` and change policy loading from "pick one config directory" to a merged model:

- project runtime config applies only to the current scan target (`repo_root`)
- project policy XML files override only matching tool fallback policies by policy name
- missing project policies do not remove unrelated tool fallback policies

The first runtime setting is project-wide ignored folders (for example `build/`, `vendor/`, generated code directories), applied before per-policy filtering and during traversal pruning for performance.

---

## 2. Background & Problem Statement

### 2.1 Context

Komply currently resolves exactly one XML policy directory:

- `--config-dir` if provided
- local `<repo_root>/.komply` if present
- tool fallback `<tool_root>/.komply`

It then loads `*.xml` policies from that single directory and scans recursively with policy-local `<filters>` plus a few hard-coded exclusions (for example `.git/`).

### 2.2 Problem

Two limitations exist:

- There is no project-wide runtime config for common scan settings like ignored folders.
- A local `.komply/` directory behaves like a full replacement of tool policies, so defining one local policy can unintentionally drop other fallback policies.

This produces duplicated excludes, inconsistent scan scope, and unnecessary filesystem traversal.

### 2.3 Goals

- G1: Add a per-project runtime config file inside `.komply/` using XML for consistency.
- G2: Keep all Komply project files under `.komply/`.
- G3: Introduce merged policy loading where local policy files override only matching fallback policies.
- G4: Support project-wide ignored folders applied across all policies.
- G5: Improve performance by pruning ignored directories during traversal.

### 2.4 Non-Goals

- NG1: Replacing XML policy files with a different policy format.
- NG2: Adding machine-global/user-home runtime config.
- NG3: Supporting every future runtime setting in v1 (v1 focuses on ignored folders).
- NG4: Allowing project runtime config to modify tool-global behavior outside the current `repo_root` scan.

---

## 3. Stakeholders & Users

- **Primary user(s):** Developers running `komply` in repositories with local overrides and generated/vendor/build directories.
- **Secondary user(s):** CI maintainers configuring repository scans in automation.
- **Stakeholders:** Repository maintainers defining policy coverage and defaults.
- **Operational owner:** Colin J.D. Stewart (current maintainer).

---

## 4. Requirements

### 4.1 Functional Requirements

- **FR-1:** Komply shall support an optional per-project runtime config file at `<repo_root>/.komply/00-config.xml`.
- **FR-2:** `repo_root` for runtime config lookup shall be the effective scan root (`--repo-root` when provided, otherwise current working directory).
- **FR-3:** `.komply/00-config.xml` shall be parsed as runtime configuration, not as a policy file.
- **FR-4:** Runtime config shall apply only to the current scan target (`repo_root`) and shall never modify tool fallback config directories globally.
- **FR-5:** Runtime config v1 shall support project-wide ignored directories (repo-relative paths).
- **FR-6:** Files under ignored directories shall not be scanned by any policy.
- **FR-7:** Ignored directories shall be applied before policy `<filters>` matching.
- **FR-8:** Komply shall load project policy XML files from `<repo_root>/.komply/*.xml` excluding reserved runtime config filenames.
- **FR-9:** Komply shall load tool fallback policy XML files from `<tool_root>/.komply/*.xml` when available.
- **FR-10:** Effective policies shall be merged by policy identity (policy filename stem, e.g. `cpp`, `py`), where a project policy overrides only the matching fallback policy.
- **FR-11:** Fallback policies without a corresponding project override shall remain active.
- **FR-12:** If `<repo_root>/.komply/` exists but contains only runtime config (and/or no project policies), Komply shall still use tool fallback policies.
- **FR-13:** Invalid runtime config XML shall fail the run with a configuration error and existing exit behavior (`2`).

### 4.2 Non-Functional Requirements

- **NFR-1 (Performance):** Ignored directories must be pruned during traversal to avoid scanning descendants.
- **NFR-2 (Reliability):** Missing `.komply/00-config.xml` must not be treated as an error.
- **NFR-3 (Security):** Runtime config parsing must be data-only XML parsing (no code execution).
- **NFR-4 (Maintainability):** Runtime config loading and merged policy resolution must be isolated in testable helper functions.
- **NFR-5 (Compatibility):** Existing projects with no local `.komply/` changes must preserve current behavior.

### 4.3 Constraints

- **C-1:** Runtime supports Python `>=3.10`; avoid new dependencies.
- **C-2:** XML parsing should reuse the standard library parser already used for policy XML (`xml.etree.ElementTree`).
- **C-3:** Changes should remain localized to CLI/config resolution and scan engine policy loading/traversal.

---

## 5. Proposed Solution

### 5.1 High-Level Approach

Split "config resolution" into two independent concerns:

- Runtime config source (project-only): `<repo_root>/.komply/00-config.xml`
- Policy sources (merged): project policies + tool fallback policies

Then compute the effective policy set as:

- `effective = tool_policies overridden by project_policies_by_stem + project_only_policies`

Runtime config provides global ignored directories that are enforced during traversal before policy matching and policy `<filters>`.

### 5.2 Alternatives Considered

- **Alt A:** `.komply.json` runtime config — *Rejected because hand-editing is less friendly (no comments, strict syntax) and XML is already used in this repository.*
- **Alt B:** `.komply/config.komply` (custom extension) — *Rejected for v1 because XML tooling/highlighting is weaker and the file format would still need explicit documentation as XML.*
- **Alt C:** `.komply/config.xml` — *Rejected in favor of `00-config.xml` to keep the runtime config visually sorted first in directory listings.*
- **Alt D:** Keep local `.komply/` as full replacement of tool fallback policies — *Rejected because it causes unrelated fallback policies to disappear when only one local override is intended.*

### 5.3 Trade-offs

- Reserving `00-config.xml` introduces a special filename, but keeps all project-level Komply files together and avoids format sprawl.
- Merged policy loading is more complex than single-directory selection, but matches user expectations and prevents accidental policy loss.
- XML runtime config is more verbose than a line-based ignore file, but consistent with existing policy authoring and supports comments.

---

## 6. Design

### 6.1 Architecture Overview

Components involved:

- `src/lib/main.py`
  - resolve `repo_root`
  - resolve project `.komply` directory path
  - load optional runtime config from `.komply/00-config.xml`
  - resolve tool fallback `.komply` directory (existing env-driven logic)
  - call engine with both policy sources + runtime config

- `src/lib/engine.py`
  - load project policies and fallback policies
  - exclude reserved runtime config filename from policy discovery
  - merge policies by filename stem
  - traverse repository with directory pruning using runtime ignored directories
  - evaluate files with existing policy matching and filters

**Diagram (optional):**

- `CLI -> main.main() -> resolve repo_root -> load .komply/00-config.xml -> resolve project/tool policy dirs -> engine.load+merge policies -> pruned traversal -> policy matching -> report`

### 6.2 Data Model / Structures

- Entities / objects:
  - `ProjectRuntimeConfig`
    - `version: int` (required, v1 = `1`)
    - `ignore_directories: tuple[str, ...]` (repo-relative normalized paths)
  - `PolicySourceSet` (internal helper concept)
    - `project_policy_dir: Path | None`
    - `tool_policy_dir: Path | None`
  - `EffectivePolicyMap` (internal helper concept)
    - key: policy stem (`str`)
    - value: `Policy`

- Storage:
  - runtime config: `<repo_root>/.komply/00-config.xml`
  - project policies: `<repo_root>/.komply/*.xml` excluding reserved names
  - fallback policies: `<tool_root>/.komply/*.xml` excluding reserved names

- Serialisation format:
  - XML, UTF-8 encoded
  - distinct runtime root tag and version attribute

**Proposed v1 runtime config format**

```xml
<komply-config version="1">
  <scan>
    <ignore-directory path="build" />
    <ignore-directory path="dist" />
    <ignore-directory path="vendor" />
    <ignore-directory path="src/generated" />
  </scan>
</komply-config>
```

Validation rules (v1):

- root tag must be `<komply-config>`
- `version` attribute is required and must equal `1`
- `<scan>` is optional
- `<ignore-directory path="...">` entries are optional and repeatable
- `path` must be non-empty, repo-relative, normalized (no absolute paths)
- `.` and empty paths are invalid

Reserved filenames (v1):

- `00-config.xml` is reserved for runtime config and must never be loaded as a policy file

### 6.3 Interfaces / APIs

- Public functions/classes/modules (internal API changes):
  - `main.py`
    - `resolve_project_komply_dir(repo_root: Path) -> Path`
    - `load_project_runtime_config(repo_root: Path) -> ProjectRuntimeConfig`
    - resolve tool fallback policy dir separately from project `.komply`
  - `engine.py`
    - `scan_repository(..., project_policy_dir: Path | None, tool_policy_dir: Path | None, runtime_config: ProjectRuntimeConfig | None = None) -> ScanReport`
    - `load_effective_policies(project_policy_dir, tool_policy_dir) -> list[Policy]`

- CLI/flags (if applicable):
  - No new flags in v1
  - Existing `--config-dir` behavior should be reinterpreted/documented carefully if retained (see Open Questions)

- Network endpoints (if applicable):
  - N/A

### 6.4 Behaviour & Flows

Step-by-step description(s) for key flows:

- Flow A: Project runtime config + fallback policies
  1. User runs `komply` in project root (or passes `--repo-root`).
  2. `main.py` checks `<repo_root>/.komply/00-config.xml` and loads runtime settings if present.
  3. `main.py` gathers project policy XML files from `<repo_root>/.komply` (excluding `00-config.xml`).
  4. `main.py` also resolves tool fallback policy directory.
  5. `engine.py` merges policies by stem.
  6. Traversal prunes ignored directories from runtime config.
  7. Remaining files are matched/evaluated.

- Flow B: Local policy override of one fallback policy
  1. Tool fallback has `cpp.xml` and `py.xml`.
  2. Project `.komply/` contains only `cpp.xml`.
  3. Effective policies are local `cpp` + fallback `py`.
  4. Fallback `py` remains active.

- Flow C: Project `.komply/` contains only runtime config
  1. Project has `.komply/00-config.xml` and no project policy XML files.
  2. Komply applies runtime config to this run.
  3. Komply still loads fallback tool policies.
  4. No "No XML policies found" error occurs solely because local `.komply/` exists.

- Flow D: Invalid runtime config XML
  1. `main.py` finds `.komply/00-config.xml`.
  2. XML parse or schema validation fails.
  3. Komply reports configuration error and exits with code `2`.

### 6.5 Error Handling Strategy

- Error categories and how they surface:
  - Invalid runtime config XML -> configuration error (stderr + exit `2`)
  - Invalid project policy XML / fallback policy XML -> existing configuration error behavior
  - Missing runtime config file -> not an error

- Logging rules:
  - Error messages must include file path and concise reason.
  - Do not print file contents.

- Recovery behaviour:
  - No retries.
  - Abort on invalid runtime config to avoid silent misconfiguration.

### 6.6 Performance Considerations

- Expected hot paths:
  - Filesystem traversal and file reads dominate runtime.

- Complexity notes:
  - Merging policies by stem is small (`O(P)` with `P` policy count) and not performance-critical.
  - Traversal pruning for ignored directories can materially reduce work on large repos.

- Limits:
  - `ignore-directory` entries expected to be low cardinality.
  - Normalize ignore paths once and use prefix checks during traversal.

Performance-first design choice:

- Prefer explicit traversal pruning (for example `os.walk` with in-place directory filtering) over `rglob()` plus post-filtering. This adds some code complexity but avoids expensive descent into known-ignored trees.

### 6.7 Security Considerations

- AuthN/AuthZ model:
  - N/A (local CLI tool)

- Threats considered:
  - Malformed XML causing crashes -> handled via parse/validation errors
  - Absolute or malformed ignore paths -> reject during validation

- Secret handling and storage:
  - No secrets in scope

- Audit/logging requirements:
  - N/A

### 6.8 Observability

- Metrics:
  - N/A for v1

- Logs:
  - Existing final summary and configuration error output
  - Optional future enhancement: report whether runtime config was loaded (verbose mode)

- Tracing:
  - N/A

- Dashboards/alerts:
  - N/A

### 6.9 Language & Syntax Changes (if applicable)

- N/A (no language/parser syntax changes to checked source code)

### 6.10 Compiler / Runtime Lowering (if applicable)

- N/A

### 6.11 Behaviour Compatibility Matrix (if applicable)

| Construct | Before | After | Notes |
|---|---|---|---|
| No local `.komply/` | Tool fallback policies load | Same | Backward compatible |
| Local `.komply/` with only `00-config.xml` | Local `.komply` may shadow fallback and fail policy load | Fallback policies still load; runtime config applies | Intentional fix |
| Local `.komply/cpp.xml` with fallback `py.xml` | Local `.komply` replaces fallback dir (drops `py.xml`) | Local `cpp` overrides only `cpp`; fallback `py` remains | New merge behavior |
| `00-config.xml` in `.komply/` | Would be treated as policy XML today if discovered | Reserved runtime config, excluded from policy load | New behavior |

---

## 7. Compatibility & Migration

### 7.1 Backwards Compatibility

- Existing projects without local `.komply/` changes continue to work as before.
- Existing XML policy format remains unchanged.
- Exit codes remain unchanged.

Behavior changes (intentional):

- A local `.komply/` directory no longer implies "replace all fallback policies"; it becomes a source of overrides plus runtime config.
- Reserved filename `00-config.xml` is no longer available for policy definitions.

### 7.2 Migration Plan

- Data migrations:
  - None

- Rollout steps:
  - Implement merged policy loading and runtime config parsing
  - Add system tests first for merged behavior and reserved config filename handling
  - Update `README.md` with `.komply/00-config.xml` schema and policy merge semantics

- Rollback plan:
  - Remove `.komply/00-config.xml` and/or local overrides; fallback policies continue to function

---

## 8. Testing Strategy

### 8.1 Unit Tests

- `main.py` runtime config loading:
  - valid `.komply/00-config.xml`
  - missing file returns defaults
  - invalid XML
  - invalid root tag / version
  - invalid `ignore-directory` path values

- `engine.py` merged policy resolution:
  - local override replaces matching fallback stem only
  - fallback-only policies remain
  - project-only policies are added
  - reserved `00-config.xml` excluded from policy loading

- `engine.py` ignore matching / traversal pruning helpers:
  - exact directory ignore
  - nested ignore path
  - sibling not ignored
  - normalization edge cases (`./build`, trailing slash)

### 8.2 Integration / System Tests

- System tests to write first (mandatory for implementation):
  - `.komply/00-config.xml` ignored folders are applied across all policies
  - local `.komply/00-config.xml` does not prevent tool fallback policies from loading when no local policy XML exists
  - local `cpp.xml` overrides fallback `cpp.xml` while fallback `py.xml` still applies
  - invalid `.komply/00-config.xml` returns exit code `2`
  - reserved `00-config.xml` is not treated as a policy file

- Environments needed:
  - Temporary directories only; no external dependencies

### 8.3 Performance Tests

- Benchmarks to run:
  - Compare scan runtime on a synthetic repo with a large ignored directory (`vendor/`, `build/`) before vs after traversal pruning

- Success thresholds:
  - Ignore-pruned scans should traverse materially fewer files/directories (qualitative threshold acceptable for v1)

### 8.4 Security Tests

- Validation tests for invalid/absolute ignore paths
- Malformed XML runtime config regression coverage

### 8.5 Regression / Golden Tests (if applicable)

- N/A

---

## 9. Implementation Plan

### 9.1 Work Breakdown

- **Task 1:** Add runtime config loader for `.komply/00-config.xml` in `src/lib/main.py` (XML parse + validation) — Owner: Colin J.D. Stewart
- **Task 2:** Refactor policy source resolution to separate project policy dir and tool fallback policy dir — Owner: Colin J.D. Stewart
- **Task 3:** Implement effective policy merge by stem in `src/lib/engine.py` — Owner: Colin J.D. Stewart
- **Task 4:** Implement reserved filename exclusion (`00-config.xml`) in policy discovery — Owner: Colin J.D. Stewart
- **Task 5:** Add traversal pruning for runtime ignored directories — Owner: Colin J.D. Stewart
- **Task 6:** Add system tests first for merge semantics/runtime config behavior — Owner: Colin J.D. Stewart
- **Task 7:** Add unit tests for loader/merge helpers — Owner: Colin J.D. Stewart
- **Task 8:** Update `README.md` documentation — Owner: Colin J.D. Stewart

### 9.2 Milestones

- M1: System tests written and failing for runtime config + merged policy loading
- M2: Implementation complete and tests passing
- M3: README updated with `.komply/00-config.xml` and merge semantics

### 9.3 Open Questions

- Q1: Should `--config-dir` be deprecated, repurposed as "project policy dir only", or retained as a hard override that bypasses merge behavior?
- Q2: Should runtime ignored directories support glob patterns in v1, or remain exact repo-relative directory paths only?

### 9.4 Risks & Mitigations

- **R-1:** Merge semantics introduce regressions in policy precedence — *Mitigation:* Add explicit unit/system tests for local override, fallback retention, and project-only additions.*
- **R-2:** Reserved filename handling accidentally excludes legitimate policy files — *Mitigation:* Reserve only exact filename `00-config.xml` and document it clearly.*
- **R-3:** Traversal refactor changes matching behavior unintentionally — *Mitigation:* Preserve current matching/filter functions and add regression tests for existing matcher kinds.*

---

## 10. Acceptance Criteria

- **AC-1:** A project can define `.komply/00-config.xml` with ignored directories, and files under those directories are excluded from all policy scans.
- **AC-2:** `.komply/00-config.xml` applies only to the current scan target (`repo_root`) and does not modify tool-global defaults.
- **AC-3:** Local policy XML files override only matching fallback policies by filename stem.
- **AC-4:** Fallback policies without local overrides remain active.
- **AC-5:** A local `.komply/` directory containing only `00-config.xml` does not disable fallback policy loading.
- **AC-6:** Invalid `.komply/00-config.xml` fails with a configuration error and exit code `2`.
- **AC-7:** Automated tests cover runtime config parsing, reserved filename exclusion, merged policy precedence, and ignored-folder behavior.
