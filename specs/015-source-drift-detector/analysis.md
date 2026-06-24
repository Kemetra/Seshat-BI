# Cross-Artifact Analysis: source drift detector (F014, spec 015)

**Date**: 2026-06-24 | **Scope**: spec.md + plan.md + tasks.md vs constitution,
roadmap, and the readiness spine. Read-only consistency pass (speckit-analyze
posture); no artifacts were modified by this analysis.

## Method

Cross-checked the three chain artifacts against each other and against the
authoritative sources: `.specify/memory/constitution.md` (v1.6.0), the nine roadmap
hard rules, `docs/readiness/readiness-model.md` + `source-ready.md`, and the
templates the design mirrors. Verified ASCII/no-BOM mechanically and confirmed every
cross-referenced artifact resolves.

## Mechanical checks (deterministic)

| Check | Result |
|-------|--------|
| ASCII-only, no BOM on spec.md / plan.md / tasks.md | PASS -- 0 non-ASCII bytes, no BOM in all three |
| All See-also / cross-ref targets exist | PASS -- every referenced path resolves EXCEPT `docs/checklists/` (does not yet exist) |
| `docs/checklists/` absence | EXPECTED -- plan Phase 0 (T001) explicitly says "create if absent"; this is a deliverable of the slice, not a dangling reference. Not a defect. |
| No drift "score" anywhere in artifacts | PASS -- only measured magnitudes + four statuses + blocking reasons |
| Generic (#7) -- no worked-example specifics | PASS -- C086 appears only as a cited filled-baseline example; no pharmacy columns/codes/segments inlined |

## Consistency findings (spec <-> plan <-> tasks)

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| A1 | INFO | The three user stories (US1 shape drift, US2 Principle-V hard-stops, US3 spine wiring) map 1:1 from spec -> tasks Phases 3/4/5. | Coherent; no action. |
| A2 | INFO | All twelve FRs are covered by tasks: FR-001->T004-T006; FR-002->T008; FR-003->T019; FR-004->T009/T013/T019; FR-005->T005; FR-006->T012/T014/T015; FR-007->T011; FR-008->T017; FR-009->T006; FR-010->T022; FR-011->T016; FR-012->T020. | Full traceability; no gap. |
| A3 | INFO | Plan's Constitution Check (11 rows) and spec's hard-rule citations agree: design-only (#8), no fake confidence (#9), generic (#7), Principle-V seams (V). | Aligned. |
| A4 | LOW | spec, plan, and tasks all decline to create `research.md`/`data-model.md`/`quickstart.md`. | Intentional and stated (docs slice; taxonomy IS the data model). Consistent with sibling specs 002-006 shipping spec.md alone. No action. |
| A5 | LOW | The shape-drift severity defaults in the spec taxonomy table (e.g. retype = warning/blocked escalation) are restated in tasks T009/T010. | Consistent; the doc (T010) is the authority, the template (T009) mirrors it. No conflict. |

No HIGH or CRITICAL findings. No contradictions between artifacts.

## Constitution / roadmap alignment

- **Principle V (the load-bearing one for this feature)**: grain/PK, returns-rule,
  PII-surface, and identity-bearing semantic-pair drift are designed AS human seams
  -- measured + classified + raised to `unresolved-questions.md`, never auto-rejudged
  (spec US2 + FR-006; plan Constitution row V; tasks T012-T015). The detector
  disposes of MEASUREMENT, a human disposes of JUDGMENT.
- **Roadmap #8 (docs-first, Later tier)**: the slice ships a doc + template +
  checklist and explicitly defers the runtime/CLI/comparator (spec "measure/judge
  boundary"; plan Technical Context; tasks have no `src/` work). Correct for a
  "Later"-tier row.
- **Roadmap #9 (no fake confidence)**: enforced in FR-005 + T005 + T018; measured
  per-class magnitudes are allowed, a rolled-up score is forbidden until scoring
  rules exist. Aligned with `readiness-model.md`.
- **Roadmap #7 / Principle VII (generic)**: FR-010 + T022; C086 cited not copied.
- **Principle VIII (static-now / live-deferred)**: the mechanical re-profile reuses
  the deferred-live `profile.py` seam; `[PENDING LIVE RE-PROFILE]` + `warning` when
  the boundary is absent (FR-009, edge cases). Correct.
- **Readiness spine**: Source Ready status mapping is to the four spine statuses
  only; downstream-suspect flagging (FR-008/T017) respects "the detector flags, the
  gate disposes" -- it never auto-demotes a downstream stage.

## Numbering note (verified, not a defect)

The task input cited "Roadmap F014" while the feature/branch is `015-source-drift-
detector`. Confirmed against `docs/roadmap/roadmap.md`: F014 = "Source Drift
Detector" (Layer 2, Later, Source Ready) -- this IS that feature. Roadmap's own F015
= "Reconciliation Ledger" (Gold Ready), a DIFFERENT later feature NOT specified
here. The spec's "Naming note" section documents this so a reader is not misled. The
spec-dir number (015) was assigned to avoid parallel-worktree collision per the run
instructions. No content was mis-scoped.

## Auto-decisions recorded (clarifications the chain answered with repo defaults)

1. **Scope = design-only (docs/templates/checklist), no runtime.** Default for a
   "Later"-tier roadmap row under hard rule #8. Reversible: a later spec builds the
   runtime.
2. **Drift report location = `mappings/<table>/source-drift-report.md`.** ADR 0003
   per-table working set, co-located with the baseline profile. Reversible.
3. **No `readiness-status.yaml` schema change.** Reuse `evidence[]` /
   `blocking_reasons[]` / status; a `drift` sub-record is a deferred decision.
   Reversible.
4. **Checklist home = `docs/checklists/source-drift.md` (create if absent).**
   Confirmed `docs/checklists/` does not yet exist; the slice creates it. Reversible.
5. **Tolerance policy deferred; until set, any measured movement is an observation at
   `warning`.** Avoids inventing a fake-confidence threshold (#9). Reversible.

## Items NOT auto-answered (Principle-V human seams -- left open by design)

These are NOT chain clarifications to default away; they are the feature's POINT --
the detector raises them, a named human decides:

1. Whether a grain/PK no longer unique on re-profiled data implies a new grain.
2. Whether a changed/disappeared returns column means a new returns rule.
3. Whether a newly-appeared or reappeared PII-looking column is publish-safe
   (default stays drop).
4. Whether a fanned-out identity pair changes entity identity.
5. Per-feature business-rollup/segment re-mapping if a categorical's value set
   drifted -- the playbook never invents these; an analyst supplies the table.

## Verdict

The four chain artifacts are internally consistent, fully traceable (stories <-> FRs
<-> tasks), ASCII/no-BOM clean, generic, and aligned with the constitution (esp.
Principle V), the readiness spine, and roadmap hard rules #7/#8/#9. The only
"missing" referenced path (`docs/checklists/`) is a planned deliverable, not a
dangling link. Ready to proceed to implementation when the Later-tier work is
scheduled.
