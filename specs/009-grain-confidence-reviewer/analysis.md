# Cross-Artifact Analysis: 009-grain-confidence-reviewer

**Date**: 2026-06-24 | **Scope**: spec.md + plan.md + tasks.md, cross-checked
against `.specify/memory/constitution.md`, `docs/roadmap/roadmap.md`,
`docs/readiness/readiness-model.md`, `docs/readiness/mapping-ready.md`, and
`src/retail/profile.py`.

This is the `/speckit-analyze` pass for this feature: a read-only consistency and
constitution-alignment check across the three authored artifacts. No artifact was
edited as a result; findings are recorded for the implementing slice.

## Result summary

| Dimension | Result |
|-----------|--------|
| Spec <-> Plan <-> Tasks consistency | PASS -- all 11 FRs and 5 SCs trace into tasks |
| Constitution alignment (I-IX + spine) | PASS -- no principle weakened; the two CRITICAL rails (no fake confidence; no auto-resolve grain) are enforced in all three artifacts |
| Roadmap alignment | PASS with one NAMING note (feature dir 009 vs roadmap "F008"); recorded, not blocking |
| Grounding in existing code | PASS -- reuses `PkProof`; invents no new measurement |
| Generic-only (Principle VII) | PASS -- no C086 specifics in any artifact |
| Open `[NEEDS CLARIFICATION]` left in artifacts | NONE (auto-decisions taken with recorded defaults; human seams routed to `unresolved-questions.md`, not left as spec placeholders) |

## Coverage check (requirement -> task traceability)

- **FR-001..FR-011**: every functional requirement is referenced by at least one
  task (verified: tasks cite FR-001 through FR-011). T001-T002 cover FR-001/FR-008/
  FR-010 setup; T003-T007 cover FR-002/FR-003/FR-004/FR-009; T008-T012 cover
  FR-005/FR-006; T013-T014 cover FR-007/FR-008; T015-T018 cover FR-011/FR-010/SC gates.
- **SC-001..SC-005**: all five success criteria are referenced (T018 -> SC-001/SC-002;
  T004/T005 -> SC-003; T009/T010 -> SC-004; T013/T014 -> SC-005).
- **User stories**: US1, US2, US3 each map to a phase (Phase 2/3/4) with an
  independent test and a checkpoint. No orphan story; no story without tasks.
- **Edge cases**: the spec's six edge cases (no prior version, PK rename, composite
  reorder, stale profile, gold reshape, PII regression) are each carried into tasks
  (T008/T011/T012).

No requirement is un-tasked; no task is un-anchored to a requirement.

## Constitution alignment (the two CRITICAL rails + the rest)

1. **No fake confidence (hard rule #9; readiness-model.md "No fake confidence").**
   Enforced consistently: spec "What confidence means here" + FR-003/FR-004/FR-009;
   plan Constitution Check row "Readiness spine"; tasks T004 ("explicitly forbid a
   numeric score and an auto high/medium/low label") + T017/T018 re-check. Confidence
   is the measured `PkProof` + status + blockers, never a number. PASS.

2. **Grain is a Principle-V human seam -- surface, do not auto-resolve.** Enforced:
   spec US3 + FR-007/FR-008; plan Constitution Check row V; tasks T013/T014. The skill
   hard-stops on a non-unique grain, a PII move, and any approve request, and routes
   each to `unresolved-questions.md` with a named owner. It never self-grants
   approval, never writes `Gate status: CLEARED`, never picks a PK/grain. PASS.

3. **Principle IV (mapping gate) / readiness spine.** The feature DEEPENS Mapping
   Ready and adds NO new gate and NO new state field -- it maps the card to the four
   existing statuses and records evidence/blockers into the existing
   `readiness-status.yaml`. Consistent across all three artifacts. PASS.

4. **Principle VIII (live deferred).** The live profile re-run is the deferred
   DB-read boundary; without DSN/`db` extra the skill reads committed numbers or
   reports `[PENDING LIVE PROFILE]` and never fabricates (spec FR-002/FR-004 sc.4;
   plan; tasks T007). PASS.

5. **Principle VII (generic).** No C086/pharmacy specifics in spec/plan/tasks; C086
   cited as the filled instance only; T017 is a dedicated generic-only sweep. PASS.

6. **Principles II/III/VI/IX.** No fork, no new read surface, deviation->`warning`
   (not auto-pass), no secrets in tracked files, ASCII/UTF-8-no-BOM/short paths --
   all consistent. PASS.

## Grounding check

- The measured signal is REAL and reused, not invented: `src/retail/profile.py`
  defines `PkProof(total, distinct_pk, null_pk, is_unique)` with
  `is_unique = (total == distinct_pk and null_pk == 0)`. The spec/plan/tasks cite
  exactly these fields and forbid re-implementing the query. VERIFIED.
- `source-map.yaml`'s load-bearing diff fields (`meta.grain`, `meta.primary_key`,
  per-column `pii:`, `gold_placement`) exist in `templates/source-map.yaml`. VERIFIED.
- The rule count is 27 (G6 confirmed present at `src/retail/rules/g6.py`); spec
  SC-002 and plan both say 27. VERIFIED. (Some older docs still say 26 -- a
  pre-existing stale-count issue flagged in the constitution's Sync Impact Report;
  not introduced or "corrected" here, to avoid scope creep -- see Findings F2.)

## Findings (recorded; none blocking the draft)

- **F1 (LOW, naming) -- feature number vs roadmap id.** This feature's directory is
  `009-grain-confidence-reviewer`, but the roadmap lists this SCOPE as **F008**
  ("Grain Confidence + Mapping Diff Reviewer"), while roadmap **F009** is a different
  feature ("Metric Contract Store + Retail KPI Packs"). The number was assigned by the
  worktree/branch convention (next free `specs/00N`), independent of the roadmap's
  F-numbering. The spec/plan/tasks state plainly that this advances **Mapping Ready**
  and implements the **F008 scope**, so intent is unambiguous, but the dir number and
  the roadmap F-number diverge. RECORDED for a human: either renumber, or add a note
  reconciling the two numbering schemes. (Recorded as an auto-decision; reversible.)

- **F2 (LOW, pre-existing) -- stale "26 rules" strings in older docs.** Several
  `docs/superpowers/*` and `docs/worked-examples/c086-pharmacy.md` lines still say "26
  rules"; the live count is 27 (G6). This is a pre-existing discrepancy the
  constitution Sync Impact Report already flagged for a follow-up patch. This feature
  does NOT touch those files and correctly uses 27. No action in this slice.

- **F3 (INFO) -- single-file edit coordination.** US1 and US2 both edit one
  `SKILL.md`. Tasks.md notes they touch different sections and recommends sequencing
  or coordination to avoid a write conflict. Not a defect; an implementation note.

- **F4 (INFO) -- no research.md/data-model.md/contracts.** Intentional: no new code
  surface, data model, or API. Consistent with the kit's prior skill-only slices
  (005, 006). Recorded so the absence is not read as an omission.

## Conclusion

The three artifacts are mutually consistent, fully traceable (FR/SC/story/edge-case
coverage complete), and aligned with the constitution and the readiness spine. The
two CRITICAL rails -- evidence-backed confidence (never a number) and grain as a
human seam (never auto-resolved) -- are enforced redundantly in spec, plan, and
tasks. The only divergence is the LOW naming note F1 (dir 009 vs roadmap F008),
recorded for a human. The chain is ready to implement.
