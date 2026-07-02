# Cross-Artifact Analysis: Feature 062 Scaffold-Rule Generator + Doctor

**Scope**: read-only consistency pass over spec.md, plan.md, tasks.md,
research.md, data-model.md, contracts/scaffold-cli.md. No artifact was modified.

## Method

- Requirement coverage: every FR/SC/User-Story cross-checked against tasks and
  design docs.
- Consistency: terminology, the write/print boundary, and the exit-code contract
  compared across all artifacts.
- Constitution alignment: Principles I, V, VII, VIII, IX re-checked against the
  authored artifacts.
- Duplication / drift: checked for contradictory claims between docs.

## Coverage matrix (summary)

| Artifact element                  | Covered by                                  | Status |
|-----------------------------------|---------------------------------------------|--------|
| US1 author mode (P1)              | Phase 3 T005-T011                           | OK     |
| US2 doctor mode (P2)              | Phase 4 T012-T017                           | OK     |
| US3 place-list guard (P3)         | Phase 2 T003-T004                           | OK     |
| FR-001 command takes id+title     | T010, T011 (author-mode dispatch)           | OK     |
| FR-002 stub module written        | T007, T010                                  | OK     |
| FR-003 generic stub               | T008                                        | OK     |
| FR-004 failing test stub          | T009, T010                                  | OK     |
| FR-005 EXPECTED_RULE_IDS insert   | T007, T010                                  | OK     |
| FR-006/007 print regen cmds       | T007, T010                                  | OK     |
| FR-008 print glossary row         | T007, T010                                  | OK     |
| FR-009 refuse/overwrite           | T006                                        | OK     |
| FR-010 input validation           | T005                                        | OK     |
| FR-011 doctor single id           | T012, T013                                  | OK     |
| FR-012 doctor sweep               | T013                                        | OK     |
| FR-013 doctor writes nothing      | T015                                        | OK     |
| FR-014 exit-code contract         | T014                                        | OK     |
| FR-015 unverifiable place         | T012                                        | OK     |
| FR-016 stdlib-only                | T018                                        | OK     |
| FR-017 place-list guard           | T004                                        | OK     |
| FR-018 not the authority          | design (plan/data-model); NO dedicated task | GAP-1  |
| FR-019 UTF-8/ASCII                | T010                                        | OK     |
| FR-020 subcommand surface         | T011                                        | OK     |
| SC-001 one-command boilerplate    | T010, T011                                  | OK     |
| SC-002 honest red                 | T009                                        | OK     |
| SC-003 doctor finds drift         | T013                                        | OK     |
| SC-004 zero golden/glossary write | T007, T015                                  | OK     |
| SC-005 place-list guard-tested    | T004                                        | OK     |
| SC-006 no DB/network/exec         | T018, T019                                  | OK     |

## Findings

### GAP-1 (LOW): FR-018 (helper is not the authority) has no dedicated test task

FR-018 says the helper MUST NOT self-grant a wiring "pass" or claim a rule is
approved. This is architecturally satisfied -- Doctor's model (data-model.md
DoctorReport) only emits present/missing/unverifiable per place and a has_drift
boolean; there is no "approved"/"pass" verdict anywhere in the contract or the
value objects, so the property holds by construction. But no task asserts the
ABSENCE of an approval verdict. Suggested (non-blocking) fix at implement time:
fold an assertion into T014/T016 that the DoctorReport exposes no "approved/pass"
field and Doctor's non-zero exit means "drift found," never "rule rejected."
Severity LOW because the design makes the violation unreachable; this is
defense-in-depth, not a missing capability.

### OBS-1 (informational): partial SC id tagging in tasks

Only SC-002/003/004 are literally tagged in tasks.md; SC-001/005/006 are covered
by prose (T010/T011, T004, T018/T019). Not a defect -- coverage exists; the tags
are just not exhaustive. No action needed.

### OBS-2 (informational): the write/print asymmetry is consistently stated

The load-bearing boundary (EXPECTED_RULE_IDS is a WRITE; golden records +
glossary are PRINT-only) is stated identically in spec (Clarifications + FR-005
vs FR-006/007/008), plan (Design Decision 5), research (R5), data-model (repo
files table), and contract. No contradiction found. This is the axis most likely
to be challenged in plan-review; it is internally consistent.

### OBS-3 (informational): stale-premise correctly avoided

The grounding flagged that the idea's original "40-vs-45 count drift / D-rule
unbuilt" motivation is historical (that rule shipped). The spec/research do NOT
restate that as a current failing state; they cite only the still-true drift (a
registered rule with no glossary row). Correctly handled.

## Consistency checks

- Terminology ("five wiring places," "write/print split," "doctor," "drift")
  used uniformly across all six artifacts. OK.
- Exit-code contract identical in plan (Design Decision 4), research (R6),
  contract, and tasks (T014). OK.
- No contradiction on "Doctor writes nothing" (FR-013, data-model, contract,
  T015). OK.
- Constitution: Principles I/V/VII/VIII/IX each have a matching FR + task; no
  principle is contradicted. OK.

## Verdict

- Critical findings: 0
- High findings: 0
- Medium findings: 0
- Low findings: 1 (GAP-1, defense-in-depth test suggestion; design already makes
  the violation unreachable)

Cross-artifact set is internally consistent and constitution-aligned. The single
LOW is a non-blocking hardening suggestion for implement time.
