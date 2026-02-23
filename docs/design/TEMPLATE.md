<!--
TEMPLATE.md — Software Design Document (New Feature)

How to use:
1) Copy this file to docs/design/DXXXXXXXX-feature-name.md.
2) Fill in all sections.
3) Remove the entire “Glossary & Template Notes” section before review/merge.
4) Once the feature is implemented, set Status to “READ-ONLY” and do not edit content.
5) If you extend or change the feature later, create a NEW document with a NEW Document ID and reference the old one(s) in “Related Documents”.
-->

# Software Design Document — <Feature Name>

## Document Metadata

- **Document ID:** D00000001
- **Title:** <Feature Name>
- **Author(s):** <Name(s)>
- **Owner:** <Team/Person responsible for ongoing ownership>
- **Created (YYYY-MM-DD):** <date>
- **Last Updated (YYYY-MM-DD):** <date>
- **Status:** DRAFT | IN REVIEW | APPROVED | IMPLEMENTED | READ-ONLY
- **Target Release / Milestone:** <version / milestone>
- **Repository / Area:** <repo/path/subsystem>
- **Tracking:** <issue/epic link or identifier>
- **Reviewers:** <names>
- **Approvers:** <names>

---

## 1. Summary

A short, plain-English summary of:
- what problem this feature addresses,
- what the solution is,
- what success looks like.

---

## 2. Background & Problem Statement

### 2.1 Context
Explain where this feature fits (product area, subsystem, user journey, etc.).

### 2.2 Problem
Describe the pain, limitation, or opportunity.

### 2.3 Goals
- G1: <goal>
- G2: <goal>

### 2.4 Non-Goals
Explicitly list what is *not* being done in this feature.
- NG1: <non-goal>

---

## 3. Stakeholders & Users

- **Primary user(s):** <who uses it directly>
- **Secondary user(s):** <admins, operators, etc.>
- **Stakeholders:** <teams/roles impacted>
- **Operational owner:** <who runs/supports it>

---

## 4. Requirements

### 4.1 Functional Requirements
Use numbered “FR-” items.
- **FR-1:** <requirement>
- **FR-2:** <requirement>

### 4.2 Non-Functional Requirements
Use numbered “NFR-” items.
- **NFR-1 (Performance):** <e.g. p95 latency, throughput>
- **NFR-2 (Reliability):** <uptime, retries, idempotency>
- **NFR-3 (Security):** <auth, permissions, secrets>
- **NFR-4 (Maintainability):** <testability, observability>
- **NFR-5 (Compatibility):** <backwards compatibility expectations>

### 4.3 Constraints
- **C-1:** <tech/language/platform constraints>
- **C-2:** <licensing, third-party restrictions, policy constraints>

---

## 5. Proposed Solution

### 5.1 High-Level Approach
Explain the chosen approach at a conceptual level.

### 5.2 Alternatives Considered
Include at least one alternative and why it was not chosen.
- **Alt A:** <description> — *Rejected because…*
- **Alt B:** <description> — *Rejected because…*

### 5.3 Trade-offs
What do we gain, and what do we accept?
- <trade-off 1>
- <trade-off 2>

---

## 6. Design

### 6.1 Architecture Overview
Describe the components/modules involved and how they interact.

**Diagram (optional):**
- <Insert Mermaid diagram, ASCII diagram, or link to an image>

### 6.2 Data Model / Structures
- Entities / objects:
  - <entity>: <fields, types, invariants>
- Storage:
  - <where persisted, if applicable>
- Serialisation format:
  - <json/binary/custom, versioning strategy>

### 6.3 Interfaces / APIs
- Public functions/classes/modules:
  - <signature/contract>
- CLI/flags (if applicable):
  - <command> <args>
- Network endpoints (if applicable):
  - <method> <path> — <request/response>

### 6.4 Behaviour & Flows
Step-by-step description(s) for key flows:
- Flow A: <happy path>
- Flow B: <edge case>
- Flow C: <failure mode>

### 6.5 Error Handling Strategy
- Error categories and how they surface (return values/exceptions/status codes).
- Logging rules (what is logged, what must never be logged).
- Recovery behaviour (retry, fallback, abort).

### 6.6 Performance Considerations
- Expected hot paths.
- Complexity notes (Big-O where useful).
- Limits (max sizes, batching, streaming).

### 6.7 Security Considerations
- AuthN/AuthZ model
- Threats considered (e.g. injection, privilege escalation, data leakage)
- Secret handling and storage
- Audit/logging requirements

### 6.8 Observability
- Metrics (names and what they mean)
- Logs (key log lines/fields)
- Tracing (spans, correlation IDs)
- Dashboards/alerts (if relevant)

### 6.9 Language & Syntax Changes (if applicable)
- New/changed keywords and tokens.
- Grammar updates (EBNF or equivalent).
- Parser impacts (new parse paths, ambiguity handling).
- User-facing examples for valid/invalid syntax.

### 6.10 Compiler / Runtime Lowering (if applicable)
- AST/IR additions or changes.
- Lowering strategy from syntax to runtime operations.
- Runtime data structures/registries introduced or modified.
- Fallback behaviour for non-matching cases.

### 6.11 Behaviour Compatibility Matrix (if applicable)
Capture before/after behaviour for affected constructs.

| Construct | Before | After | Notes |
|---|---|---|---|
| `<construct>` | `<old behavior>` | `<new behavior>` | `<compatibility notes>` |

---

## 7. Compatibility & Migration

### 7.1 Backwards Compatibility
- What existing behaviour must remain unchanged?
- What changes are breaking (if any)?

### 7.2 Migration Plan
- Data migrations (if needed)
- Rollout steps (feature flags, staged rollout, canary)
- Rollback plan

---

## 8. Testing Strategy

### 8.1 Unit Tests
- What must be covered?
- Key edge cases

### 8.2 Integration / System Tests
- Environments needed
- External dependencies to simulate

### 8.3 Performance Tests
- Benchmarks to run
- Success thresholds

### 8.4 Security Tests
- Static checks, dependency scanning, fuzzing (if relevant)

### 8.5 Regression / Golden Tests (if applicable)
- Parser/tokenizer golden cases
- Compiler/IR snapshot checks
- End-to-end language examples that must not regress

---

## 9. Implementation Plan

### 9.1 Work Breakdown
- **Task 1:** <description> — Owner: <name>
- **Task 2:** <description> — Owner: <name>

### 9.2 Milestones
- M1: <date/condition>
- M2: <date/condition>

### 9.3 Open Questions
- Q1: <question>
- Q2: <question>

### 9.4 Risks & Mitigations
- **R-1:** <risk> — *Mitigation:* <plan>
- **R-2:** <risk> — *Mitigation:* <plan>

---

## 10. Acceptance Criteria

Concrete, testable conditions that define “done”.
- **AC-1:** <criterion>
- **AC-2:** <criterion>

---

## 11. Decision Log

Record major decisions and when they were made.
- **(YYYY-MM-DD)** Decision: <summary> — Rationale: <why>

---

## 12. Related Documents

### 12.1 References
- <links to specs, tickets, prior discussions>

### 12.2 Related Design Docs
- **Previous / superseded:** D00000000 — <title>
- **Follow-up / extension:** D00000002 — <title>

---

## 13. Appendix (Optional)

- Examples
- Extra diagrams
- Detailed calculations
- Glossary (project-specific terms only)

---

# Glossary & Template Notes (REMOVE THIS SECTION BEFORE SUBMITTING)

## Document IDs
- Every design document must have a unique ID in the format **D########** (e.g. **D00000001**).
- IDs are never reused, even if a feature is cancelled.

## Read-only rule
- When the feature is implemented, set **Status = READ-ONLY** and do not change the document.
- If you need to extend, change, or rework the feature later:
  - create a **new** design document with a **new** ID,
  - reference the previous document(s) in **Related Design Docs**,
  - clearly state what is changing and why.

## Status meanings (suggested)
- **DRAFT:** authoring in progress
- **IN REVIEW:** reviewers assigned, feedback ongoing
- **APPROVED:** accepted for implementation
- **IMPLEMENTED:** shipped/merged, awaiting final tidy-up (if any)
- **READ-ONLY:** final; historical record

## Writing guidance
- Prefer clear, direct language.
- Use lists and IDs (FR-/NFR-/AC-) so discussions stay anchored.
- If something is uncertain, put it in **Open Questions** rather than hiding it.
