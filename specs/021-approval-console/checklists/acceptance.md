# Specification Quality Checklist: Approval Console

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md) (Roadmap F027; on-disk dir `021-approval-console`)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- the slice is planning only;
      the runtime shape is named as a planned skill + templates + docs page, not coded
- [x] Focused on user value and business needs (the human-in-the-loop decision loop the kit
      lacked: a raised question becomes a reviewable, recorded decision)
- [x] Written for non-technical stakeholders (the decider is a named human; the spec speaks
      in requests, decisions, owners, and evidence)
- [x] All mandatory sections completed (Why / What it is NOT / Relationship to shipped /
      Architecture / User Scenarios / Requirements / Success Criteria / Human approval
      boundary / Allowed / Forbidden / Evidence / Readiness stage / Dependencies /
      Non-goals / Assumptions / Deferred / See also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (the one open decision is recorded as O-1 with
      a recommended, reversible default, not a blocker)
- [x] Requirements are testable and unambiguous (FR-001..FR-014 each have a verifiable check)
- [x] Success criteria are measurable (SC-001..SC-006: every field present, write-back
      lands, self-approval declined, zero C086, no new rule added, every cell traceable)
- [x] Success criteria are technology-agnostic (no implementation details -- they speak of
      artifacts, statuses, evidence, and decisions)
- [x] All acceptance scenarios are defined (each of US1/US2/US3 has Given/When/Then)
- [x] Edge cases are identified (chat-only approval, double-packaging, phantom question,
      sourceless default, blank owner, already-passed stage)
- [x] Scope is clearly bounded (the "What this feature is NOT" scope wall + Non-goals +
      Forbidden operations make the transcribe-never-author boundary explicit)
- [x] Dependencies and assumptions identified (F024 category, F005 slot, the mapping-gate
      write targets; the surfacing features F006/F008/F012)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (each FR maps to a US
      acceptance scenario and/or an SC)
- [x] User scenarios cover primary flows (package a request; record a decision; refuse to
      self-approve)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification (the planned deliverables are named
      as future outputs; none is authored here)

## Feature-specific acceptance (the load-bearing wall)

- [x] The console TRANSCRIBES the human's decision; it never picks the option, supplies the
      owner, or invents the rationale (FR-005; US3)
- [x] No approval lives only in chat: every recorded decision is written into a committed
      artifact -- `unresolved-questions.md` Resolution + `readiness-status.yaml`
      `approvals[]` (FR-008; SC-002; edge case)
- [x] The console CANNOT move a stage to `pass` without the required evidence AND a named
      human approval; the flip is mechanical, not discretionary (FR-007; US2/US3; SC-003)
- [x] A `recommended_default` is never auto-accepted; accepting it is an explicit named-owner
      decision (FR-006; US1/US2)
- [x] The recording owner's authority class must match the question class (FR-009; US3)
- [x] A decision contradicting a prior approval is surfaced, never silently overwritten
      (FR-010; US3)
- [x] No fabricated confidence/health score anywhere; explicit status + evidence + blockers
      only (FR-011; SC-006)
- [x] All artifacts generic; C086 cited, never inlined (FR-013; SC-004)
- [x] No new `retail check` rule, CLI verb, or Python; checker stays exit 0
      (FR-001; SC-005)

## Notes

- This is a planning slice (Principle VIII; roadmap rule #8): it writes only the five
  Spec-Kit files. The four runtime deliverables
  (`.claude/skills/approval-console/SKILL.md`, `docs/tools/approval-console.md`,
  `templates/approval-request.md`, `templates/approval-decision.md`) are ENUMERATED as
  planned future outputs, not authored here.
- Unlike F012 (read-only roll-up), this module WRITES into Core-Authority artifacts. It
  stays a Product Module -- not a truth-creator -- precisely because it only transcribes a
  named human's decision and only executes an already-approved step (the boundary gate).
- Principle V judgment calls are not auto-answered in the spec; the console packages them
  and records the named human's answer (the operational realization of Principle V).
- One open decision (O-1: whether to retain a standalone recorded request/decision copy
  alongside the per-table write-back) is recorded with a recommended, reversible default
  rather than a [NEEDS CLARIFICATION] marker.
