# Cross-Artifact Analysis: Severity-Posture Regression Lock (044)

**Scope**: Non-destructive consistency + quality pass over `spec.md`, `plan.md`,
`tasks.md` (read-only; this report is the only write). Run after stage 4.

**Date**: (date pending -- operator to fill)

## Method

- Built the requirement inventory from `spec.md` (12 FRs, 6 SCs, 3 user stories,
  5 key entities, 4 refused Principle-V clarifications + 3 advisor-resolved).
- Mapped every FR and SC to the task(s) that satisfy it and every task back to a
  requirement.
- Checked terminology, constitution alignment, deferred-capability assumptions,
  duplication, ambiguity, and the Principle-V carve-out handling.

## Coverage matrix (requirement -> task)

| Req | Covered by | Status |
|-----|------------|--------|
| FR-001 (committed golden record) | T004, T011, T012 | OK |
| FR-002 (OBSERVE, not read from registry) | T001, T006 | OK |
| FR-003 (snapshot fails closed on drift) | T008, T009, T015 | OK |
| FR-004 (actionable regen message) | T009 | OK |
| FR-005 (deterministic byte-stable regen) | T004, T005, T011 | OK |
| FR-006 (generic-only record) | T007 | OK |
| FR-007 (no new gating rule / id) | T016, T017 | OK |
| FR-008 (no live exec; planted fixtures) | T003, T006, T007 | OK |
| FR-009 (grain represents multi-class) | T002, T004, T018 | OK (gated by T000) |
| FR-010 (L3 coverage boundary explicit) | T010 | OK (gated by T000) |
| FR-011 (explicit no-finding marker) | T006 | OK |
| FR-012 (data-structure comparison) | T008, T018 | OK |
| SC-001 (downgrade caught 100%) | T018 | OK |
| SC-002 (twice -> byte-identical) | T014 | OK |
| SC-003 (intentional change = confined diff) | T014 | OK |
| SC-004 (0 new gating rules/ids) | T016, T017 | OK |
| SC-005 (0 example-domain identifiers) | T007 | OK |
| SC-006 (every rule has an entry) | T015 | OK |

Every FR and SC maps to at least one task; every task maps back to a requirement.
No orphan requirements, no orphan tasks.

## User-story coverage

- US1 (drift guard, P1) -> Phase 3 (T006-T010). OK.
- US2 (deterministic regeneration, P2) -> Phase 4 (T011-T014). OK.
- US3 (new-rule coverage, P3) -> Phase 5 (T015-T016). OK.

Each story is independently testable as its acceptance scenarios describe; the
test-first ordering (T008 RED before T013 GREEN) is explicit in Dependencies.

## Findings

### CRITICAL: none

### HIGH: none

### MEDIUM

- **M1 -- Grain-dependent serialization detail under-specified until the human
  gate.** T004's sort key and the artifact's exact shape differ between the three
  grain options (flat set vs per-branch vs per-fixture-case). This is INTENTIONAL
  and correct: the plan and tasks treat grain as a post-gate parameter (T000
  blocks T004) rather than guessing, per Principle V. Recorded as a tracked
  consequence, not a defect -- the implementer fills it after the ruling. No
  artifact edit required now.

- **M2 -- Branch/message-key stability (only if grain option (b) is chosen).** If
  the human rules grain = (rule_id, branch/message-key), the chosen sub-key must
  be stable across message-text edits (e.g. a branch tag, not the full message
  string), or innocuous message wording changes would flake the lock. The plan's
  Implementation Notes flag the multi-class rule but do not pin a sub-key scheme.
  Mitigation: add this caution at T004 time once grain is ruled. Low effort,
  deferred to the gated task. Not blocking the draft.

### LOW

- **L1 -- Date placeholders.** spec, plan, tasks, checklist, and this report all
  carry "(date pending)". This is deliberate (the workflow cannot invent a date)
  and the operator must fill them at ratification. Consistent across artifacts.

- **L2 -- Branch vs spec-dir name asymmetry.** The branch is
  `044-045-severity-posture-lock` (the hook prepended `044-` to the short name,
  which already carried `045-`), while the spec dir is
  `specs/044-severity-posture-lock`. feature.json points at the spec dir, so
  downstream resolution is correct; the doubled number is cosmetic only. Noted
  for operator awareness.

## Terminology consistency

"Severity class / ERROR / WARNING / INFO", "registered rule", "severity posture",
"golden record", "grain", and "L3 governance surface" are used consistently across
all three artifacts and match the source code (`core.Severity`,
`registry.all_rules`, `semantic.verdict_to_finding`). No competing synonyms.

## Constitution / hard-rule alignment

- Principle I (gate-enforced): the lock fails closed and protects the exit floor.
  No weakening. OK.
- Principle V (stops at judgment): grain + L3 coverage are REFUSED and gated by
  T000; not silently resolved. OK -- this is the load-bearing check and it holds.
- Principle VII (C086 is an example): record is generic; fixtures mandated
  synthetic/generic (T007, FR-006, SC-005). OK.
- Principle VIII (static-first): planted-fixture observation only; no DB/network/
  Power BI/agent (FR-008, T003/T006/T007). OK.
- Principle IX (Windows-safe text): UTF-8 no-BOM, `\n`, trailing newline, stable
  order, `.gitattributes` pin, data-comparison (FR-005, FR-012, T004, T005, T008).
  OK -- mirrors the proven 043 approach.
- Hard rule #9 (no fake confidence): exact observed posture, no numeric score. OK.

## Deferred-capability check

No artifact assumes the Power BI Execution Adapter (F016) or the spec-only
runtimes (F031-F033). The lock is pure static/test-only. Out-of-Scope sections in
plan and tasks state this explicitly. OK.

## Verdict

- analyze_verdict: **clean** (0 critical, 0 high)
- analyze_critical: 0
- analyze_high: 0

The two MEDIUM items are grain-dependent refinements correctly deferred behind the
Principle-V human gate (T000); they are tracked consequences of refusing a
judgment call, not consistency defects. The draft is internally consistent and
ready for adversarial plan-review.
