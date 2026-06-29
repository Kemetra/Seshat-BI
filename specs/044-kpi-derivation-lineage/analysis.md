# Specification Analysis Report: 044-kpi-derivation-lineage

**Mode**: read-only cross-artifact consistency pass over spec.md, plan.md, tasks.md (+ constitution).
**Date**: 2026-06-29 | **Scope**: DEFINE-layer docs/template feature (no code).

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage | LOW | tasks.md T013 / spec FR-010 | FR-010 (router edit) is satisfied by T013, correctly marked OPTIONAL/SKIP-able after re-read. The conditional ("if INDEX enumerates references/") is resolved in plan.md as "no count claimed; routing-row + prose-mention only". Consistent across all three artifacts. | None -- conditional explicitly and consistently handled. |
| I1 | Inconsistency | LOW | spec "contracts" vs plan "contracts/" | "contracts" means the existing KPI-MC metric contracts under skills/.../contracts/, NOT a Spec-Kit /contracts/ interface dir. plan.md flags this explicitly. | None -- disambiguation note prevents drift. |
| A1 | Ambiguity | LOW | spec FR-005 / tasks T010 | FR-005 and T010 quote formula prose in ASCII (/ , *) while source contracts use Unicode glyphs. Intentional (Principle IX applies to NEW text); a verifier compares the RELATION, not the glyph. | None -- T015/T019 separate provenance (relation) from encoding (glyph). |
| U1 | Underspecification | LOW | spec FR-004 partition | The 4 base + 6 derived partition is asserted; justified in Assumptions ("read from the contracts, not invented") and re-derived by T009/T010 from prose. | None -- T001 + T015 make the partition itself provenance-checked. |

No CRITICAL or HIGH findings. No constitution MUST is violated (see alignment below).

## Coverage Summary Table

| Requirement | Has Task? | Task IDs | Notes |
|-------------|-----------|----------|-------|
| FR-001 (Derives-from section on template, no front-matter) | Yes | T005, T018 | T018 verifies no YAML front-matter. |
| FR-002 (net-sales base section) | Yes | T006, T015 | |
| FR-003 (ATV derived section: KPI-MC-02 + KPI-MC-04) | Yes | T007, T015 | |
| FR-004 (lineage doc; 4 base + 6 derived) | Yes | T008, T009, T010 | |
| FR-005 (every edge transcribed + cited) | Yes | T010, T012, T015 | T015 is the provenance gate. |
| FR-006 (no edge to non-contract node; no invented edge) | Yes | T011, T015 | |
| FR-007 (generic-only, no C086) | Yes | T016 | |
| FR-008 (no readiness self-grant, no executor/score) | Yes | T014, T017, T020 | |
| FR-009 (ASCII/UTF-8 no BOM; don't alter existing glyphs) | Yes | T019 | |
| FR-010 (router edit or recorded skip) | Yes | T013 | Conditional, resolved in plan.md. |
| SC-001 (doc partitions exactly 10 into 4+6) | Yes | T008-T010, T015 | |
| SC-002 (100% edges cited, 0 invented, 0 non-contract) | Yes | T015 | |
| SC-003 (template + 2 contracts have section; no front-matter; other 8 unchanged) | Yes | T005-T007, T018 | |
| SC-004 (0 C086 tokens) | Yes | T016 | |
| SC-005 (retail check exit 0; Principle-V edge stop holds) | Yes | T014, T015 | |
| SC-006 (0 executor/generator code) | Yes | T020 | |
| SC-007 (router lists doc or recorded skip) | Yes | T013 | |

Coverage: 17/17 requirement keys (FR + SC) have >=1 task = 100%.

## Constitution Alignment Issues

None. Verified against the principles the feature touches:

- Principle I (Agent-First, Gate-Enforced): all three assert "advances no readiness stage"; T020 verifies; retail check (T014) is the demonstrable gate. Aligned.
- Principle V (Agent Stops at Judgment Calls): every edge transcribed-with-citation; declaring a NEW edge is a carried stop-and-ask (spec Clarifications, plan Constitution Check, tasks scope guard + T012/T015). Aligned -- reserved item correctly NOT answered.
- Principle VII (C086 Is An Example): generic-only across all three; T016 enforces. Aligned.
- Principle VIII (Static-First, Live Deferred): committed text only; no executor, no generator, no live data, no fabricated score; T017/T020 enforce. Aligned.
- Principle IX (encoding): ASCII/UTF-8-no-BOM in NEW text; T019 enforces and excludes altering existing glyphs. Aligned.
- Hard rule #8 (docs-first): lineage doc hand-authored, no generator. Aligned.
- Hard rule #9 (no fabricated confidence/readiness): T017 enforces. Aligned.

## Unmapped Tasks

None that lack a rationale. Setup/grounding T001-T004 and gate tasks T014/T020 are cross-cutting (not 1:1 with an FR) but each supports the provenance/encoding/readiness guarantees above. No task references a file or component absent from spec/plan.

## Metrics

- Total Functional Requirements: 10 (FR-001..FR-010)
- Total Success Criteria (buildable/verifiable): 7 (SC-001..SC-007)
- Total Tasks: 20 (T001..T020)
- Coverage (requirements with >=1 task): 100% (17/17)
- Ambiguity Count: 1 (LOW -- glyph-vs-relation, already mitigated)
- Duplication Count: 0
- Critical Issues Count: 0
- High Issues Count: 0

## Verdict

CLEAN -- 0 critical, 0 high. The three artifacts are mutually consistent, fully cover the requirements, and align with every constitution principle the feature touches. The one Principle-V reserved item (no invented edge) is correctly carried unanswered.

## Next Actions

- No CRITICAL/HIGH issues -> the draft may proceed to the adversarial plan-review (stage 6).
- LOW notes (A1/U1) are pre-mitigated by the provenance task T015; no spec edit required.
- Reminder (the 042 lesson, out of analyze's reach): /speckit-analyze cross-checks only these three artifacts, NOT the live repo. The plan-review must verify the INDEX/contract live-file assumptions (FR-010, the edge prose) against the actual files.
