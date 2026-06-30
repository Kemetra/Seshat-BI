# Adversarial Plan-Review: DF1 Parked-On Map (Stage 6)

**Stance**: single default-adverse skeptic, READ-ONLY (reports fixes, edits nothing).
**Inputs reviewed**: spec.md, plan.md, tasks.md, research.md, data-model.md,
contracts/df1-rule-contract.md, analysis.md (all present and committed on
`051-parked-on-map`).

**Verdict**: PASS-WITH-NOTES. analyze ran CLEAN (0 critical / 0 high); tasks + all
design artifacts are present; no axis trips a CRITICAL or HIGH. Three LOW notes for the
builder; none blocks ratify.

## Axis 1 -- hidden-principle-violation

- **Gate-enforced (I)**: DF1 is a non-zero-exit static rule wired into `retail check`
  (FR-001, contract). Not advisory. PASS.
- **Stops-at-judgment (V)**: no grain/PII/rollup/identity question is silently
  answered. The carve-out block is correctly empty and the one orchestration call (IL1
  F-number) is left OPEN for the human. The five clarifications resolved are all
  reversible engineering/posture calls (severity, ship-criterion, edge inventory,
  empty-posture, no-amendment) -- legitimately within delegated authority. PASS.
- **Static-first (VIII)**: lazy `import yaml`, stdlib substring anchor test,
  membership tests against `tracked_files`; no module-scope connection import (B1 would
  itself flag one). PASS.
- **Hard rule 9**: categorical, no score (FR-008). The only numeric token is SC-003's
  "100% of cases", which is a test-coverage assertion about the gate, NOT a fabricated
  readiness/confidence value attached to an edge. PASS (see note R3).

No hidden violation found.

## Axis 2 -- assumes-deferred-capability

This is the highest-risk axis for an F016-adjacent idea, and it is clean. Every
artifact treats F016 / pbi-tools / L3-ops / F031-F033 as PARKED inputs that DF1 merely
RECORDS, never as runtimes it consumes:
- The rule reads only committed roadmap text + tracked deferred-spec/spec files
  (research.md verified all five evidence paths are in `git ls-files`).
- The seed manifest declares NO `shipped_when_tracked` for any v1 edge, so DF1 does not
  assume any parked target has shipped -- it asserts the opposite (they remain parked),
  which is exactly the verified repo state.
- "Blocker resolves" is defined against the manifest's tracked EVIDENCE file, NOT
  against an F016 implementation file (which by design does not exist). The contract
  branch 9/10 logic never touches an F016 runtime. PASS.

## Axis 3 -- c086-leak

Manifest schema, rule, and all five seed edges are generic kit roadmap features (F016
and named dependents) + tracked infra spec paths. Every "C086/pharmacy" string in the
artifacts is a negative guard (forbidding the leak), confirmed by scan. Test fixtures
are synthetic. PASS.

## Axis 4 -- fabricated-confidence

No edge carries a confidence/probability/readiness number; findings are yes/no ERRORs.
FR-008 forbids it; data-model finding shape has no score field. PASS.

## Axis 5 -- over-scope

The only new runtime artifacts are: `parked_on.py`, `docs/quality/parked-on.yaml`, the
`__init__.py` wiring line, the `EXPECTED_RULE_IDS` +1, the regenerated
`rules-manifest.json`, one test file, and a roadmap ledger row. No F016/F031-F033
machinery (FR-014, SC-006, tasks scope guard). YAGNI honored -- the seam, not the
implementation. PASS.

## Notes for the builder (LOW, non-blocking)

- **R1 (traceability)**: tasks T005/T009 implement FR-001/002/003/010 without an inline
  FR tag (analyze finding A1). Coverage exists; optionally tag at build.
- **R2 (anchor fidelity)**: the five seed `anchor` sentences must be copied
  byte-literal from `docs/roadmap/roadmap.md` at build (T002/T003). The greatest live
  risk is a near-miss anchor that passes review prose but fails the substring test --
  T003 + the T012 live guard are the correct gates; ensure T013's ledger edit does NOT
  reword any line used as an anchor (tasks already warn this).
- **R3 (numeric-token hygiene)**: SC-003's "100%" is a coverage metric, not a
  readiness score, and is fine; keep it out of any finding message so it cannot be
  misread as a per-edge confidence value.

## Disposition

PASS-WITH-NOTES. Spec is ratifiable. The Status front-matter remains **Draft** (a
human, not this workflow, flips it to Ratified). No CRITICAL uncertainty to flag.
