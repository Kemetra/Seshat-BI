# Specification Quality Checklist: Companion Tools Architecture

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Roadmap feature**: F024 (on-disk spec 018)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- this slice is planning text
- [x] Focused on architectural value: a normative authority taxonomy F025-F033 declare against
- [x] Written for an architecture stakeholder (the architecture owner) and a reviewer
- [x] All mandatory sections completed (Why / scope wall / relationship / architecture / user
      scenarios / requirements / success criteria / approval boundary / allowed + forbidden ops
      / evidence / stage affected / dependencies / non-goals / assumptions / deferred / see also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (open decisions recorded as deferred, not blockers)
- [x] Requirements are testable and unambiguous (FR-001..FR-014)
- [x] Success criteria are measurable (SC-001..SC-007)
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined (US1/US2/US3 each Given/When/Then)
- [x] Edge cases are identified (dual-fit tie-break, truth-creating proposal, adapter asked to
      define, Module asked to approve, undeclared tool, sub-axis ambiguity)
- [x] Scope is clearly bounded (the scope wall; the orthogonality of categories vs layers)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover the primary flows (classify a tool; resolve module/adapter; place
      Maintenance Automation)
- [x] Feature meets the measurable outcomes defined in Success Criteria
- [x] No implementation details leak into the specification

## Taxonomy-specific completeness (this feature)

- [x] Exactly FIVE categories are defined as a closed set (FR-001)
- [x] The authority matrix is present and shows ONLY Core Authority with create-truth and
      grant-approval (FR-002, SC-002)
- [x] The Module sub-vocabulary is the closed set { read-only, artifact-writing,
      execution-capable } (FR-003)
- [x] The Adapter sub-vocabulary is the closed set { local-only, DB-connected,
      external-service-connected, publish-capable } (FR-004)
- [x] The module-vs-adapter seam (external trust/connectivity boundary) makes the two
      categories disjoint (FR-005, SC-003)
- [x] Maintenance Automation is defined distinctly from a human-invoked Module (FR-006)
- [x] The five categories are stated ORTHOGONAL to the Six product layers; the layers are not
      replaced or renumbered (FR-007, SC-006)
- [x] The shipped surfaces are classified to prove the taxonomy is real (FR-014)
- [x] F025-F033 can each declare a category against this contract with no gap (SC-007)

## Honesty + scope guardrails (verify before planning)

- [x] No numeric/maturity score for any tool; readiness stays status + evidence + blockers
      (FR-011; rule #9)
- [x] No runtime code, UI, dbt, Dagster, or Power BI execution added (FR-010)
- [x] No `retail check` rule, CLI verb, conformance checker, or readiness stage added; the
      conformance check is enumerated and deferred (FR-012; rule #8)
- [x] The five future deliverables are ENUMERATED, not created this slice (FR-009)
- [x] Generic only: zero C086 / retail_store_sales specifics; the worked example is cited, not
      inlined (FR-013, SC-004; Principle VII)

## Notes

- The spec is a planning/architecture-definition slice (Principle VIII, roadmap rule #8): it
  ships no runtime code, so "implementation details" here means the category/matrix/sub-axis
  shapes, which are the artifact this feature delivers -- not application code.
- The central modelling decision -- that the five authority categories are ORTHOGONAL to the
  six functional layers (a tool carries two coordinates) -- is recorded in "Relationship to
  shipped features", not left as a clarification marker. This is the literal meaning of
  "formalize, do not reinvent".
- The five future deliverables (`product-modules.md`, `core-vs-modules-and-adapters.md`, ADR
  0006, `module-contract.md`, `adapter-contract.md`) are enumerated as planned outputs and are
  scheduled as Phase 7 build tasks in `tasks.md`, never as this slice's output.
- Principle V judgment calls (a proposed truth-creating tool, an adapter asked to define what
  it executes) are deliberately surfaced as stop-and-ask edge cases, not auto-resolved.
