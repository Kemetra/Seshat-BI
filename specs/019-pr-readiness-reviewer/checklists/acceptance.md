# Specification Quality Checklist: PR Readiness Reviewer

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md) -- Roadmap F025 (spec-dir 019; roadmap F-number wins)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- the artifacts this feature
      plans are a Markdown skill, a Markdown template, and a Markdown doc; "shape" here means
      verdict fields, not application code
- [x] Focused on user value and business needs (one structured "is this PR safe to merge"
      verdict that replaces a hand-reconstructed checklist)
- [x] Written for non-technical stakeholders (a reviewer can read the verdict and act)
- [x] All mandatory sections completed (Why / What-it-is-NOT / Relationship-to-shipped /
      Architecture / User Scenarios / Requirements / Success Criteria / Human-approval-boundary
      / Allowed-ops / Forbidden-ops / Evidence-required / Readiness-stage / Dependencies /
      Non-goals / Assumptions / Deferred / See-also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (the one design choice -- field set + gating
      rule -- is fixed in the spec/plan, not deferred)
- [x] Requirements are testable and unambiguous (FR-001..FR-014 each map to an acceptance
      scenario or success criterion)
- [x] Success criteria are measurable (SC-001..SC-006: blocker/warning operationalized,
      every line source-traceable, score declined, read-only holds, no new rule added)
- [x] Success criteria are technology-agnostic (no implementation details in SC)
- [x] All acceptance scenarios are defined (US1 verdict; US2 blocker-vs-warning; US3
      claim-vs-evidence + too-early-publish + decline-to-act)
- [x] Edge cases are identified (missing/pending/conflicting evidence; score request;
      secret-in-diff; unassigned required-decision; self-PR)
- [x] Scope is clearly bounded (What-it-is-NOT wall; read-only; no new gate; Non-goals + Out
      of scope present)
- [x] Dependencies and assumptions identified (F024 upstream by roadmap identity; F005 spine;
      reads the gates' recorded results, does not depend on them as its own gate)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (ask for a verdict; classify findings; cross-check
      claims; decline to act)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Acceptance Criteria (feature-specific)

- [x] CHK-A01 The verdict has EXACTLY the six fields: `merge_ready`, `blockers[]`,
      `warnings[]`, `required_human_decisions[]`, `evidence[]`, `next_action` [FR-004]
- [x] CHK-A02 `merge_ready` is a derived boolean ("no blocker and no open required-decision
      found"), explicitly NOT a score and NOT an approval [FR-010, Human approval boundary]
- [x] CHK-A03 The gating rule is explicit: blocker OR open required-decision -> `no`; warnings
      do not alone flip it; required-decision is a SEPARATE gating class that also gates `yes`
      [FR-005]
- [x] CHK-A04 The blocker-vs-warning distinction is operationalized and testable (one-blocker
      -one-warning PR is `no`; remove the blocker and it is `yes`, warning still listed)
      [SC-002, US2]
- [x] CHK-A05 The module observes all required PR facts at their default severities: state,
      mergeability, CI/workflow, threads, review comments, tests-declared-vs-run, no-raw-data,
      no-secrets/no-paths [FR-006]
- [x] CHK-A06 The claim-vs-evidence cross-checks are specified: readiness-stage,
      approvals, source-map approval metadata, PR-body drift; stage-`pass` claim unsupported
      by evidence is a blocker [FR-007, US3]
- [x] CHK-A07 The too-early-publish guard is a `required_human_decision` routed to a named
      owner that sets `merge_ready: no`; no approval, no stage move [FR-008, US3]
- [x] CHK-A08 Every blocker/warning/required-decision carries a cited source (PR fact or
      committed path+field); a line with no source is a defect [FR-011, SC-003]
- [x] CHK-A09 Missing -> `unknown` (names its source, never assumed `pass`); pending CI -> a
      blocker for `yes`; conflicting evidence -> surfaced, not resolved [FR-012]
- [x] CHK-A10 A numeric merge/confidence/health score request is DECLINED with the rule-#9
      rationale [FR-010, SC-004]
- [x] CHK-A11 The feature adds NO Python, NO CLI verb, NO `retail check` rule (verified by
      the diff), NO CI workflow; it reads recorded gate/CI results as evidence [FR-013, SC-006]
- [x] CHK-A12 The three future deliverables (SKILL.md, template, doc) are ENUMERATED in
      plan.md/tasks.md and NOT created in this spec-only slice [Scope wall]

## Notes

- The spec is a planning/docs-only slice (Principle VIII, hard rule #8): it writes the five
  Spec-Kit files and ENUMERATES three future deliverables; it adds no runtime code, no new
  gate, no `retail check` rule, and no CI workflow.
- `required_human_decisions[]` is deliberately a SEPARATE gating class from `blockers[]` (a
  Principle-V human-judgment item, not a defect); both gate `merge_ready: yes`. This was a
  conscious design decision recorded in FR-005 so it is testable.
- Principle V judgment calls (publish-too-early, PII publish-safety, grain/sentinel/rollup)
  are surfaced as `required_human_decisions[]` routed to a named owner, never auto-resolved.
- Reading PR / CI / git state is read-only OBSERVATION, classified as an Allowed operation; it
  is not a new gate and not a mutation (FR-009/FR-013).
