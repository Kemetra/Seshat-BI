# Cross-Artifact Analysis: Generic KPI Knowledge Registry and Governed Project Metric-Contract Authoring

**Feature**: `124-generic-kpi-contract-authoring`

**Date**: 2026-07-13

**Scope**: non-destructive consistency + quality pass across spec.md, plan.md, data-model.md, tasks.md, research.md, quickstart.md, contracts/, and checklists/requirements.md. No artifact was modified by the analysis except the two fixes recorded in Section 5.

## 1. Coverage of owner-directed decisions (D1-D10)

| Decision | Where realized | Status |
| --- | --- | --- |
| D1 product scope (generic) | FR-001, FR-040; SC-012 | COVERED |
| D2 three-layer boundary | FR-002; data-model layering | COVERED |
| D3 one authoritative registry | FR-003..FR-006; research D1 | COVERED |
| D4 generic vs project naming | FR-011, FR-012, FR-031 | COVERED |
| D5 custom KPIs | FR-020..FR-022; US5 | COVERED |
| D6 one contract, two checkpoints | FR-013, FR-016, FR-017, FR-018; US3/US4 | COVERED |
| D7 answerability (5 statuses, no score) | FR-007..FR-009, FR-041..FR-043; contracts/kpi-answerability | COVERED |
| D8 metrics vs slices | FR-010, FR-031 | COVERED |
| D9 agent-first (no CLI family) | FR-035, FR-036; plan Constitution I | COVERED |
| D10 first expansion wave + honest Planned | FR-023..FR-027; research R7 | COVERED |

All ten present and cited by FR. Zero reopened.

## 2. Mechanical coverage counts (verified by scan)

- Functional requirements: 41 unique IDs, all referenced by a US and/or an SC; none dangling.
- Success criteria: 12 (SC-001..SC-012), each with a *(Verify: ...)* method, none numeric-score-based.
- Security requirements: 3 (SEC-001..SEC-003).
- User stories: 7 (US1..US7), each with Why / Independent Test / Acceptance Scenarios.
- Edge cases: 21 (matches the required set exactly).
- Non-Goals: 18 bullets (a superset of the required 17 -- "second readiness engine" and "new spine stage" are listed as one required item but authored as an explicit pair; no required exclusion is missing).
- Data-model entities: 7 of 7 required (GenericKpiRegistryEntry, GenericKpiKnowledgeContract, ProjectKpiDecision, KpiAnswerabilityRow, ProjectMetricContract, KpiPack, WorkedExample).
- Tasks: 49 (T001..T048 + T002a); every story task carries a `[USn]` tag; the untagged (T001, T002, T002a, T045-T048) are the declared cross-cutting setup/validation tasks; each task cites an FR/SC/entity. Requirement->task coverage confirmed for FR-001 and FR-002 (T002/T002a; the earlier gap is closed).

## 3. Consistency checks

- **Traceability (tasks -> US -> FR/SC)**: the tasks.md traceability table maps every story's tasks to FRs/SCs; spot-checks confirm each `T###` parenthetical FR exists in spec.md.
- **Four status vocabularies kept distinct** (data-model Section "Status vocabularies"): answerability(5) / contract(4) / decision(9) / gate(3). The `warning` (contract) vs `warn` (gate) spelling is preserved verbatim; no artifact conflates them.
- **No-duplicate / single-owner**: the reuse table anchors every reuse to a committed path; exactly one authoritative registry (FR-003); the F009 contract is the only contract format (additive fields, no second store/format/engine/stage -- FR-032, FR-033).
- **ASCII gate**: all authored bytes are ASCII (`--`, `->`). The scorecard-template em-dash vs this-spec ASCII divergence is documented as COSMETIC (non-functional) drift -- verified in source that SL1 (`src/seshat/rules/scorecard.py:86`) normalizes both dash forms to `--`, so it lints either correctly; the shipped template is NOT edited (owner-flagged; T011).
- **Boundary**: no artifact under `skills/`, `templates/`, `mappings/`, `docs/metrics/`, or `contracts/knowledge/` was created or edited; all authored bytes live under `specs/124-generic-kpi-contract-authoring/`.

## 4. Validation results (run 2026-07-13)

- ASCII-only scan over the package: CLEAN (zero non-ASCII bytes).
- UTF-8-no-BOM scan: CLEAN (no BOM on any file).
- `git diff --check`: CLEAN (no trailing whitespace / conflict markers).
- `seshat check` (static governance gate, `--format json`): `exit_code: 0`, `findings: []` -- green over the repo with the spec-124 package present.
- No commit, push, PR, merge, or ratification performed. Status remains `Draft`.

## 5. Findings and fixes applied (from the `/speckit-analyze` detection passes)

The `/speckit-analyze` skill was run (prerequisites script resolved FEATURE_DIR to this package; all docs present). Read-only detection passes A-F produced the findings below; each was remediated by editing the spec-124 package only (no implementation file, no commit).

| ID | Category | Severity | Location | Finding | Resolution |
| --- | --- | --- | --- | --- | --- |
| E1 | Coverage gap | HIGH | data-model.md | `GenericKpiKnowledgeContract` named in spec Key Entities but had no dedicated data-model block | FIXED -- full entity block added; all 7 required entities now explicit |
| E2 | Coverage gap | HIGH | tasks.md | FR-001, FR-002 had no task citation (requirement->task reverse-coverage gap) | FIXED -- T002 (FR-001) + new T002a (FR-002); traceability row updated |
| E3 | Coverage gap | MEDIUM | tasks.md | FR-012, FR-026, FR-033, FR-034, FR-035 not cited by any task | FIXED -- added to T021, T038, T026, T048 + traceability rows |
| F1 | Inconsistency | LOW | spec.md drift section | dash divergence stated as a functional SL1 mismatch | FIXED -- verified in source (`scorecard.py:86` normalizes both dashes); reworded to cosmetic/non-functional |
| B1 | Ambiguity | INFO | checklists/requirements.md:16 | literal token "[NEEDS CLARIFICATION]" flagged by a placeholder scan | NOT A DEFECT -- it is the checklist item asserting no such markers remain |
| N1 | Consistency | INFO | spec.md FR numbering | FR IDs non-contiguous (037/038/039 unused) from mid-draft regrouping | DOCUMENTED, not a defect -- every FR ID is unique and referenced; zero dangling refs to 037-039 (scan-verified); IDs are stable labels (repo treats rule/decision IDs likewise); renumbering declined to avoid churn |

Post-fix re-scan: all 41 FRs and all 12 SCs are cited in tasks.md; 0 CRITICAL, 0 unresolved HIGH.

## 6. Open clarifications requiring an owner

None that block the spec. The Principle-V approval seams (plan "Explicit STOPs") are runtime human actions, not spec ambiguities:
1. `kpi_definition` / `policy_ruling` approval (`metric_owner`).
2. PII-handling ruling for customer/identity KPIs (`data_owner`/`governance`).
3. Checkpoint-B `pass` (named human).
4. Custom-to-generic promotion (separate contribution workflow).
5. Whether to reconcile the shipped scorecard template's em-dash strings to ASCII (documented drift; owner call; out of scope here).

One faithful refinement of the owner directive is recorded (research R7): the four D10 wave KPIs are 1 net-new + 1 from-Planned + 2 reconcile-existing. This is honest status per D10 ("keep X honestly Planned"), not a contradiction, and reopens no decision.

## 7. Metrics

- Total functional requirements: 41 (all referenced by >=1 task).
- Total success criteria: 12 (all referenced by >=1 task).
- Total tasks: 49 (T001..T048 + T002a).
- Requirement coverage: 100% (41/41 FRs, 12/12 SCs mapped in tasks.md).
- Ambiguity count: 0 (the one placeholder hit is the checklist's own "no markers remain" assertion).
- Duplication count: 0.
- Critical issues: 0. Unresolved HIGH: 0.

## 8. Verdict

The package is internally consistent, fully covers D1-D10 / US1-US7 / the 7 entities / the 21 edge cases / the required non-goals, has 100% FR and SC task coverage, is ASCII/UTF-8-no-BOM clean, passes `git diff --check` and `seshat check` (exit 0), and touches no implementation file. Ready for owner review. Status: `Draft` (not ratified). No commit, push, PR, merge, or ratification performed.

## Next Actions

No CRITICAL or unresolved HIGH issues. The package may proceed to owner review. This chain STOPS here (specification only): no `/speckit-implement`, no commit, no ratification. The owner's decisions to make: the five Principle-V approval seams (Section 6) and whether to normalize the shipped scorecard template's em-dashes to ASCII (cosmetic drift).
