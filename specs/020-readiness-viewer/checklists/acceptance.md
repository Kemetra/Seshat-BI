# Specification Quality Checklist: Readiness Viewer

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Roadmap feature**: F026 (spec-dir 020 = roadmap F026; roadmap F-number is authoritative)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- the slice is
      docs/templates/skill only; "shape" detail describes the artifact this feature
      delivers, not application code
- [x] Focused on user value and business needs (a stage-centric reading lens over
      readiness, distinct from F012's findings lens)
- [x] Written for non-technical stakeholders (the seven-stage matrix + evidence + approvals
      framing is reader-facing)
- [x] All mandatory sections completed (Why / Scope wall / F012 delta / Architecture /
      User Scenarios / Requirements / Success Criteria / approval boundary / allowed +
      forbidden ops / evidence / readiness stage / dependencies / non-goals / assumptions /
      deferred / see also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (the one open decision -- skill-vs-mode
      (a)/(b) -- is recorded as a Deferred decision with a recommended default + thinness
      criterion, not a blocker)
- [x] Requirements are testable and unambiguous (FR-001..FR-012)
- [x] Success criteria are measurable (SC-001..SC-007)
- [x] Success criteria are technology-agnostic (no implementation details -- they assert
      rendered behavior, generic-ness, read-only proof, and the delta holding)
- [x] All acceptance scenarios are defined (US1/US2/US3 each have Given/When/Then)
- [x] Edge cases are identified (zero items, malformed file, current_stage-vs-status
      conflict, pass-without-evidence, stray approval, score request)
- [x] Scope is clearly bounded (scope wall + F012 scope-delta section + non-goals present)
- [x] Dependencies and assumptions identified (F024 category, readiness spine, F012
      aggregation reuse)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (each FR maps to a US
      acceptance scenario and/or an SC)
- [x] User scenarios cover primary flows (matrix render, evidence references, approvals
      timeline)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Feature-specific acceptance (Readiness Viewer)

- [x] The three genuine F012 deltas are named and only those: (1) seven-stage status
      matrix, (2) evidence rendered as references not counts, (3) approvals timeline (F012
      does not read approvals[]). `next_action` is explicitly marked SHARED with F012, NOT
      a delta
- [x] The recommended shape is a named decision: (a) stage-view MODE reusing F012's
      aggregation (preferred), with (b) merge-into-F012 as the explicit fallback and a
      stated thinness criterion ("only durable difference is sort order + column labels")
- [x] The seven readiness stages are rendered as columns and named (Source Ready ->
      Mapping Ready -> Silver Ready -> Gold Ready -> Semantic Model Ready -> Dashboard
      Ready -> Publish Ready); each cell is the recorded status, never recomputed
- [x] Evidence is rendered as navigable references; empty evidence[] on a pass stage is
      flagged "evidence missing"; an absent referenced file is flagged "referenced file not
      found"; evidence is never fabricated or filled in
- [x] The approvals timeline RENDERS recorded approvals[] only; a pass gate lacking its
      required approval is flagged "approval not recorded"; no approval is established,
      inferred, or back-filled
- [x] No numeric health / confidence / percent-ready score is emitted; a score request is
      declined with the no-fake-confidence rationale (hard rule #9)
- [x] Read-only is provable: git status shows zero modified readiness-status.yaml / per-item
      artifacts after a run; no validator / SQL / DB connection is run
- [x] All four FUTURE deliverables are enumerated (skill/mode, templates/readiness-view.md,
      docs/tools/readiness-viewer.md, optional deferred src/retail/tools/readiness_viewer.py)
      and none is created this slice
- [x] Generic: C086 / retail_store_sales appear only as cited filled instances, never
      inlined into the skill or template (Principle VII)
- [x] ASCII only, UTF-8 no BOM; arrows as `->`, dashes as `--`; no secrets / DSNs / local
      machine paths (Principle IX)

## Notes

- This is a Product Module (read-only) slice (Principle VIII, roadmap rule #8): it adds no
  runtime code, so "implementation details" here means the skill/template field shapes,
  which are the artifact this feature delivers -- not application code.
- The headline risk is re-speccing F012. The spec mitigates it with a prominent
  "Relationship to shipped F012 (scope delta)" section, a same-inputs/different-view
  framing, the three-deltas-only constraint, and an explicit merge fallback -- so a
  reviewer can confirm F026 is the DELTA, not a duplicate.
- The one open decision (skill-vs-mode) is recorded as a Deferred decision with a
  recommended default and a thinness criterion, per the repo's defaults-then-deviations
  posture -- not a [NEEDS CLARIFICATION] marker.
- Principle V judgment calls (current_stage-vs-status conflicts, pass-without-evidence,
  stray approvals) are deliberately surfaced as flags for a named human (FR-010), never
  auto-resolved by the viewer.
