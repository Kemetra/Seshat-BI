# Tasks: First-Hour Compass / New-Table Author Onboarding Cockpit

**Branch**: `055-first-hour-compass-new-table` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Docs/template/skill-only slice (Principle VIII; hard rule #8). No runtime code, no
tests-as-code -- verification is static review + a `git status`-clean read-only proof.
Every authored file is generic (Principle VII), ASCII, UTF-8 no BOM.

## Phase 1: Author the MVP artifacts

- [ ] **T001** Author `templates/first-hour-compass.md` -- the generic single-table
  orientation-card template. Mirror `templates/readiness-view.md` header conventions
  (spec/roadmap-position note, renders-never-re-derives note, no-fake-confidence note,
  generic-not-C086 note, ASCII spine). Card fields: `<table>`; you-are-here
  (`current_stage`, verbatim); next stage + next artifact (first non-pass stage in
  pipeline order); authoring skill (from the cross-walk); STOP rows (blocking_reasons +
  approval-required flag); conflict flags. Placeholders only; C086 cited as a filled
  instance. Satisfies FR-001..FR-004, FR-006, FR-009..FR-012, FR-017.

- [ ] **T002** Embed the GENERIC stage -> authoring-skill cross-walk table (seven
  `<stage_key>` -> `<skill>` rows) inside the template (T001) and mirror it in the skill
  (T003) and tools doc (T004). Map each stage to a named authoring skill DIRECTORY
  (generic kit capability, per Clarifications Q3), never a table-specific assignment.
  Satisfies FR-005, FR-017. Depends on T001.

- [ ] **T003** Author `.claude/skills/first-hour-compass/SKILL.md` -- the read-only
  skill. Mirror the readiness-viewer read-only contract verbatim where it applies:
  F024 module-contract declaration (Product Module / `read-only`); "creates no truth /
  changes no state / infers no approval / fabricates no evidence / runs no validator /
  opens no DB / emits no score"; honest-state rules; the two-condition approval-flag
  rule read from the stage doc; the renders-never-re-derives evidence-chain table.
  State the deltas vs F026 (single-table, next-artifact, authoring-skill route) and vs
  F006 (stateful vs static). Include the read-only proof (`git status` clean). Satisfies
  FR-002, FR-005..FR-014, FR-017.

- [ ] **T004** Author `docs/tools/first-hour-compass.md` -- the usage+boundary doc.
  Mirror `docs/tools/readiness-viewer.md`: what it is, when to use it (and when to use
  readiness-viewer/F012 instead), how it reads readiness-status.yaml (evidence-chain
  table), the read-only contract, generic-not-C086, and a DEFERRED section enumerating
  `next_step.py` (not built this slice). Satisfies FR-015, FR-016, FR-017. Depends on
  T001, T003.

## Phase 2: Cross-link and verify

- [ ] **T005** Cross-link the three artifacts to each other and to the shipped
  parents/inputs: readiness-viewer skill + template + tools doc (the named F026
  parent), F006 onboarding-checklist (the static parent), `templates/readiness-status.yaml`
  (the input), ADR 0004 (canonical location), `docs/readiness/readiness-pipeline.md`
  (ordering), `docs/readiness/<stage>-ready.md` (per-stage gate + required-owner). Depends
  on T001, T003, T004.

- [ ] **T006** [P] Verify Principle-V surface-only behavior in the authored text: the
  card SURFACES the recorded STOP (blocking_reasons, required-owner flag) and NEVER
  populates an approval, clears a blocker, advances a stage, or resolves the four seams
  (grain/PII/rollup/identity). Confirm the four seams read as surfaced-recorded-only.
  Satisfies FR-006, FR-007, FR-008, FR-012, FR-014.

- [ ] **T007** [P] Verify hard rule #9: no numeric/percent/confidence/maturity score in
  any authored artifact; a score request is documented as DECLINED. Satisfies FR-009,
  SC-004.

- [ ] **T008** [P] Verify Principle VII (C086 leak scan): grep the three artifacts for
  worked-example specifics (billing codes, segments, PII column names, per-table grain
  keys, `retail_store_sales` used as an assignment rather than a cited example). Confirm
  generic placeholders only. Satisfies FR-005, FR-017, SC-005.

- [ ] **T009** [P] Verify readiness-pipeline ordering in the authored text: the next
  artifact is the artifact of the FIRST non-pass stage; no downstream stage is presented
  as reachable when an upstream gate is not `pass`; conflicts are surfaced not resolved.
  Satisfies FR-003, FR-012, SC-002.

- [ ] **T010** [P] Verify encoding/format: ASCII only, UTF-8 no BOM, `--` and `->`
  glyphs only, Windows-safe short paths. Satisfies FR-017.

- [ ] **T011** Read-only proof: confirm the design mandates zero writes -- after a
  render, `git status` shows zero modified `readiness-status.yaml` and zero per-table
  artifacts (the artifacts themselves are authored docs; a RENDER of a card writes
  nothing). Satisfies FR-008, SC-003. Depends on T001..T004.

## Dependencies

- T002 depends on T001.
- T004 depends on T001, T003.
- T005 depends on T001, T003, T004.
- T006..T010 are [P] (independent review passes over the authored text).
- T011 depends on T001..T004.

## Out of scope (deferred, enumerated)

- `src/retail/tools/next_step.py` resolver/scaffolder -- optional future read-only
  slice; NOT built here (FR-016).
- A machine-readable card export (JSON) -- deferred until a consumer exists.
- A numeric readiness score -- deferred until scoring rules exist (hard rule #9).
- Roadmap F-number assignment -- a human decision (Clarifications Q1).
