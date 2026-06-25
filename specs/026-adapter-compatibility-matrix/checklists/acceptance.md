# Specification Quality Checklist: Adapter Compatibility Matrix

**Purpose**: Validate specification completeness and quality before proceeding to the future authoring slice
**Created**: 2026-06-25
**Roadmap feature**: F032 (on-disk spec-dir 026)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- the doc/template field
      shapes ARE the artifact this feature plans, not application code
- [x] Focused on user value and business needs (the kit stays durable; a maintainer always
      knows which adapter versions are verified and what proves it)
- [x] Written for non-technical stakeholders (the record-vs-policy distinction is the throughline)
- [x] All mandatory sections completed (Why, Scope wall, Relationship to shipped features,
      Architecture, User Scenarios, Requirements, Success Criteria, Human approval boundary,
      Allowed/Forbidden operations, Evidence required, Readiness stage affected, Dependencies,
      Non-goals, Assumptions, Deferred decisions, See also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (the one organizing decision -- record F032 vs
      policy F031 as separate features -- is recorded as a default in Assumptions, not a blocker)
- [x] Requirements are testable and unambiguous (FR-001..FR-015 each map to an SC and a task)
- [x] Success criteria are measurable (SC-001..SC-008; row counts, presence checks, exit codes,
      absence-of-score, boundary statements)
- [x] Success criteria are technology-agnostic (about recording/boundary/no-fake-confidence
      behavior, not tooling)
- [x] All acceptance scenarios are defined (3 P1 user stories, each with scenarios + an
      independent test)
- [x] Edge cases are identified (transitive dependency moves, parked adapter, open upper bound,
      PR-bumps-past-range, named-but-unrun smoke test, missing owner, enforcement-logic intrusion)
- [x] Scope is clearly bounded (record-not-policy, track-not-build, name-not-run-smoke-tests,
      planning-only this slice; explicit Forbidden operations + Non-goals)
- [x] Dependencies and assumptions identified (F024 upstream category; F031 paired policy;
      F029/F030/F016 tracked-not-built; cited by roadmap F-number)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (FR -> SC -> task traceability)
- [x] User scenarios cover primary flows (record one adapter / assemble the full matrix /
      UNKNOWN-is-never-compatible -- the three loads)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## F032-Specific Risk Checks (the things this feature could get wrong)

- [x] **Record vs policy boundary holds.** The spec states F032 is the RECORD and F031 is the
      POLICY; the matrix carries no PR gate, CI fail condition, merge block, or enforcement logic
      (FR-010/FR-012, SC-005). [Constitution Governance: no module creates truth/enforcement it
      does not own]
- [x] **Record vs build boundary holds.** F032 TRACKS the versions of the F029/F030/F016
      adapters; it does not author, modify, or execute any adapter's runtime code (FR-011, SC-006).
- [x] **Smoke tests named, not authored/run.** The matrix NAMES each required smoke test and
      records its last result + date; it does not write or run smoke-test code or wire CI
      (FR-006, Forbidden operations).
- [x] **Every adapter present.** All nine named adapters/dependencies are required as rows; a
      missing adapter is a defect (FR-003, SC-002).
- [x] **Range + smoke test per row.** Every row requires a version RANGE and a named smoke test;
      a row missing either is a defect (FR-004/FR-005/FR-006, SC-003).
- [x] **UNKNOWN is never compatible.** An untested version/range/adapter is recorded `unknown`,
      never supported/`pass`/inferred (FR-007, US3, SC-004) -- the no-fake-confidence
      instantiation (hard rule #9 / Principle IX).
- [x] **No numeric score.** No numeric compatibility/confidence score anywhere; explicit status
      + evidence only (FR-008, SC-004).
- [x] **Owner attests; agent does not.** A supported status requires a named owner attesting a
      passed smoke test; the agent never self-attests or self-promotes (FR-009, Human approval
      boundary).
- [x] **Readiness stage affected = none directly.** Stated plainly, not force-fit to a spine
      stage; explained as a Maintenance Automation record (FR-014, Readiness stage affected).
- [x] **Planning-only.** The two deliverables are enumerated as future outputs, NOT created this
      slice; no runtime code, CLI, rule, CI, or adapter artifact (FR-001/FR-002/FR-015, SC-001/SC-008).
- [x] **Generic, not C086.** No pharmacy / retail_store_sales specifics in any field shape or
      example; C086 is an example, never inlined (FR-013, SC-007, Principle VII).

## Notes

- This spec is a docs/planning-only slice (Principle VIII, roadmap rule 8): it adds no runtime
  code, so "implementation details" here means the doc/template/record field shapes, which ARE
  the artifact this feature plans -- the two deliverables are enumerated, not created.
- The organizing decision (F032 record vs F031 policy as separate features) is recorded with a
  recommended, reversible default (separate, to keep the record honest and the policy
  enforceable) rather than a [NEEDS CLARIFICATION] marker, per the defaults-then-deviations
  posture -- the same way 010 handled its storage-path O-1.
- The classic Principle V data judgment calls (grain, PII, business rollup) are deliberately
  stated as N/A for a version record rather than fake-fitted; the only judgment call here is
  "is this version verified?", which is surfaced as the UNKNOWN-not-compatible stop-and-ask.
- Sibling specs in this batch (F024/F029/F030/F031) are drafted in parallel, so they are cited
  by roadmap F-number (the authoritative identity), not by assumed content.
