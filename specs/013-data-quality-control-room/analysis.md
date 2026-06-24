# Cross-Artifact Analysis: data quality control room (feature 013)

**Date**: 2026-06-24 | **Scope**: spec.md, plan.md, tasks.md vs constitution v1.6.0 + roadmap (F012)

This is the /speckit-analyze cross-artifact consistency pass. It checks the three
authored artifacts against each other and against the governing docs. No code is
written; findings are recorded here.

## Verdict

**PASS -- no blocking findings.** The three artifacts are internally consistent,
fully traceable, and aligned with the constitution and roadmap. The feature's
load-bearing constraint (aggregate-only, no new validator/gate, no fake confidence) is
stated in all three artifacts and enforced by the Constitution Check and the success
criteria. Minor advisory notes are recorded below; none block drafting.

## Coverage checks (automated)

| Check | Result |
|-------|--------|
| Every FR (FR-001..FR-012) referenced by >= 1 task | PASS (12/12; FR-001 -> T002, FR-007 -> T014, etc.) |
| Every SC (SC-001..SC-004) referenced by a verification task | PASS (SC-001 -> T019, SC-002 -> T020, SC-003 -> T021, SC-004 -> T022) |
| Every P1 user story has a task phase | PASS (US1 -> Phase 3, US2 -> Phase 4, US3 -> Phase 5) |
| Artifacts ASCII + UTF-8 no BOM | PASS (0 non-ASCII bytes in all three; no BOM) |
| No worked-example specifics leaked | PASS (generic throughout; C086 only cited as a reference instance) |

## Consistency findings (spec <-> plan <-> tasks)

1. **Scope wall is consistent across all three.** "No new validator, no new gate,
   read-only, no fabricated score" appears in spec ("What this feature is NOT"), plan
   (Constitution Check rows VIII + rule 9, marked load-bearing), and tasks (T004
   foundational contract, T014 guard, T020 no-new-check invariant). No artifact
   weakens it. CONSISTENT.

2. **Pure-skill + one-template decision is identical in spec and plan.** Both cite the
   same deciding reason as feature 006 (read-fan-out + invoke-and-interpret posture;
   a CLI is YAGNI and DEFERRED). Tasks build exactly two files (T002 skill, T003/T006
   template) plus an orchestration pointer (T017). CONSISTENT.

3. **Evidence chain is single-sourced.** The spec's "Aggregates, never re-derives"
   table is reproduced as the skill's contract in T005, and every per-table-row task
   (T007/T008) requires a traceable source path per cell (FR-008). No task introduces
   a number without a source. CONSISTENT.

4. **Readiness mapping is correct.** The feature maps to the cross-cutting roll-up
   fields that already exist in readiness-status.yaml (top-level evidence[] /
   blocking_reasons[]) and is positioned as the portfolio sibling of the per-table
   readiness-scorecard.md. "Advances all stages" is correctly read as cross-stage
   roll-up, not stage-advancing (spec Assumptions; plan design note 5). CONSISTENT
   with roadmap F012 row and readiness-pipeline ("the conductor executes; the
   readiness status records").

## Constitution / roadmap alignment

- **Principle V (Agent Stops at Judgment Calls)**: honored -- read-only; never clears
  or self-assigns a blocker; surfaces conflicts rather than resolving them (FR-006,
  FR-011, T013, T015).
- **Principle VII (C086 is an example)**: honored -- generic skill + template; T019
  greps for and forbids worked-example specifics.
- **Principle VIII (Static-first, live deferred; no new validator)**: honored and
  load-bearing -- adds NO rule (count unchanged), shows recorded live results and marks
  stale ones rather than running them (FR-003, FR-010); SC-002 verifies the unchanged
  rule count + dependencies = [].
- **Principle IX (secrets/encoding/paths)**: honored -- no DSN/.env read; ASCII +
  UTF-8 no BOM (verified 0 non-ASCII bytes); short repo-relative paths.
- **Roadmap rules 7/8/9**: honored -- generic (7), template+skill before any code
  reporter (8), explicit statuses + measured counts, no fabricated score (9).

## Advisory notes (non-blocking; for the implementer)

- **A-1 (naming)**: the skill name is a placeholder <control-room-skill>; T001
  recommends retail-control-room. Keep it short for the Windows MAX_PATH limit
  (Principle IX). This is the one open implementation choice and it is reversible.
- **A-2 (second fixture table)**: the multi-table acceptance replay (T021, SC-003)
  needs a second table beyond mappings/c086/. The spec assumes a minimal generic
  stub is acceptable; the implementer should add a small generic fixture rather than a
  second worked example (to preserve Principle VII). Recorded, not a blocker.
- **A-3 (no research.md/data-model.md)**: deliberately omitted (plan records this) --
  there is no new data model or technical unknown. If /speckit-analyze tooling
  expects those files, their absence here is intentional, not a gap.
- **A-4 (feature-number vs roadmap-number)**: the directory is 013-... (the assigned
  slot) while the roadmap lists this scope as F012. The spec/plan reference "F012"
  explicitly so the mapping is unambiguous; no artifact claims the roadmap row is 013.
  Flagged for human awareness; not a defect in these artifacts.

## What was NOT auto-decided (escalated to human -- Principle V)

None of the Principle-V judgment classes (grain, PII publish-safety, business-rollup /
segment mappings, product identity) arise in THIS feature: it only AGGREGATES evidence
that per-table artifacts already recorded; it makes none of those calls itself. So
there are no open_for_human items originating in this feature. (Where those decisions
exist, they live in the per-table unresolved-questions.md / blocking-reasons.md
the control room merely displays -- with the named owner copied from source, never
self-assigned.)
