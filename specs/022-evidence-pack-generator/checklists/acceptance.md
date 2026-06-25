# Specification Quality Checklist: Evidence Pack Generator

**Purpose**: Validate specification completeness and quality before proceeding to planning/build
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)  **Roadmap feature**: F028 (dir 022)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- the future module is
      described by behavior + the 10-section contract, not by code
- [x] Focused on user value and business needs (a single traceable late-stage pack)
- [x] Written for non-technical stakeholders (reviewer / data-owner can read it)
- [x] All mandatory sections completed (Why / scope wall / scope delta / architecture /
      user stories / requirements / success criteria / approval boundary / allowed +
      forbidden ops / evidence / readiness stage / dependencies / non-goals / assumptions /
      deferred decisions / see also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (open items recorded under "Deferred decisions")
- [x] Requirements (FR-001..FR-013) are testable and unambiguous
- [x] Success criteria (SC-001..SC-006) are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined (US1-US4, Given/When/Then)
- [x] Edge cases are identified (blank template, incomplete F013 handoff, source
      disagreement, score request, live-data request, worked-example specifics)
- [x] Scope is clearly bounded ("What this feature is NOT" wall + F013 scope delta + non-goals)
- [x] Dependencies and assumptions identified (F024 depends; F013 consumed; F008-F015 sources)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (compose; missing->blocker; surface publish state;
      in-progress)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Feature-Specific Acceptance

- [x] The 10-section contract is fixed, ordered, and complete (01-source-profile ..
      10-release-notes) -- FR-001
- [x] Every section is mapped to an EXISTING committed source artifact and links back to it
      -- FR-002 (source map in plan.md Phase 1)
- [x] A missing / unfilled / blank-template source is recorded as a `blocked` section with a
      blocking reason -- never fabricated -- FR-003, SC-003
- [x] Section 08 EMBEDS / references the FILLED F013 handoff pack and NEVER re-authors,
      edits, or redefines it -- FR-004 (scope delta)
- [x] The pack SURFACES `publish_ready` + the recorded approval read from
      `readiness-status.yaml` and prints a publish-ready claim ONLY on `pass` + a named
      approval -- FR-005, FR-006, SC-004
- [x] The module writes NO approval, moves NO stage to `pass`, and edits NO source artifact
      (including the F013 handoff) -- FR-005, SC-005
- [x] Each section status is one of the four explicit statuses + evidence[] + blocking_reasons[];
      a `warning` never auto-promotes to `pass`; NO numeric confidence/health score -- FR-007
- [x] An in-progress pack at an intermediate late stage renders present sections, blocks
      absent ones, states the current stage, and claims no unreached stage -- FR-008
- [x] Disagreeing sources are surfaced with both source links + a `warning` for human
      resolution; never silently reconciled -- FR-009
- [x] The module reads ONLY committed artifacts -- no live DB / PBIP read, no Power BI
      execution adapter (F016), no publish/deploy -- FR-010
- [x] All artifacts stay generic (no C086 / retail_store_sales specifics) -- FR-011, SC-006
- [x] The four FUTURE deliverables (SKILL.md, docs/tools doc, two templates) are ENUMERATED
      as planned outputs and NOT created in this slice -- plan.md "PLANS (not created)"
- [x] No `retail check` rule added, no new readiness stage defined, no gate altered -- FR-013

## Notes

- This is a planning-only slice (5 spec-kit files). "No implementation details" here means
  the future module is described by its 10-section behavior contract, not by code -- the
  skill/doc/templates are enumerated as planned outputs, not authored.
- The single highest-risk content is the F013 boundary: both features "compose evidence."
  The spec holds it one-directionally and repeats it (scope-delta section + FR-004 + section
  08 source map): F028 CONSUMES and EMBEDS F013; it never redefines it or records the approval.
- The second guardrail is publish authority: "generator" must not become "approver." The pack
  surfaces `publish_ready` and asserts publish-ready only on a recorded `pass` + named approval.
- Principle V judgment calls (publish authorization, source disagreements, grain/PII/rollup,
  sentinel-vs-null) are surfaced as stop-and-ask `warning`/`blocked` items, never auto-resolved.
