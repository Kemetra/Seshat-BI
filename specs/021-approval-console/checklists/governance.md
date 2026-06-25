# Governance Checklist: Approval Console

**Purpose**: The "does it respect Core Authority" gate for F027. Each item maps to the
spec's Forbidden operations + Human approval boundary. Unchecked `[ ]` = to be verified
when the planned deliverables are authored; this slice's job is to PROVE the spec encodes
each guard.
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md) (Roadmap F027; on-disk dir `021-approval-console`)

## Core-vs-Module authority

- [ ] CHK-G01 The console is a MODULE: it may READ evidence, SUMMARIZE it, write DERIVED
      evidence, and EXECUTE an approved step -- it MUST NOT create truth. The spec states
      this and names F027 as the first concrete Product Module under F024's category.
- [ ] CHK-G02 The only writes are TRANSCRIPTIONS of a named human's decision into existing
      Core-Authority artifacts (`unresolved-questions.md` Resolution + `readiness-status.yaml`
      `approvals[]`); the console defines no new truth artifact (FR-008).
- [ ] CHK-G03 The console does NOT define business meaning of a metric / mapping / rollup --
      that is the human's decision (F007/F009 own the definition artifacts); the console only
      records the chosen answer (Non-goals).

## Principle V -- stop-and-ask (the feature's reason to exist)

- [ ] CHK-G04 The console TRANSCRIBES the decision; it never picks `selected_option`,
      supplies/forges `owner`, or invents `rationale` (FR-005; Forbidden ops).
- [ ] CHK-G05 The named human is the sole decider for every judgment call the console
      packages; the console packages and records, it does not decide (Human approval boundary).
- [ ] CHK-G06 A `recommended_default` is NEVER auto-accepted; accepting it is an explicit
      named-owner decision recorded with owner + date + rationale (FR-006).
- [ ] CHK-G07 The recording owner's authority class MUST match the question class (analyst /
      governance / data-owner / metric-owner); a wrong-authority decision is refused (FR-009).

## No self-approval / no self-grant

- [ ] CHK-G08 The console declines a request to "just approve it" / self-approve when there
      is no named human answer, citing Principle V, and changes no artifact (US3; SC-003).
- [ ] CHK-G09 The console MUST NOT move a readiness stage to `pass` without the required
      evidence AND a named human approval; a `pass` flip is mechanical (executor of an
      approved step), gated on both being present (FR-007; the forbidden line, verbatim).
- [ ] CHK-G10 A decision contradicting a prior recorded approval is SURFACED, never silently
      overwritten (FR-010; conflict-surfacing posture).
- [ ] CHK-G11 A decision lives nowhere only-in-chat: it is not recorded until it lands in a
      committed artifact (FR-008; edge case).

## No fake confidence

- [ ] CHK-G12 A request and a decision carry explicit status + evidence + blockers, NEVER a
      numeric health/confidence score; a score request is declined (FR-011; SC-006).
- [ ] CHK-G13 `remaining_blockers` is the explicit reason a recorded decision does NOT always
      mean the stage is `pass` -- no number stands in for that judgment (Key Entities; FR-007).

## Generic (no worked-example leakage)

- [ ] CHK-G14 All planned artifacts are generic; C086 / pharmacy specifics (billing codes,
      segment rollups, insurance/PII columns, pharmacy grain keys) are CITED, never inlined
      (FR-013; SC-004; Principle VII).
- [ ] CHK-G15 The request/decision templates use placeholders (`<table>`, `<source>`,
      `<question_id>`, `<owner>`), not one table's answers.

## Secrets / paths (Principle IX)

- [ ] CHK-G16 No secrets, DSNs, tokens, or credentials in any artifact; the console opens no
      DB connection and runs no SQL (Non-goals; Forbidden ops).
- [ ] CHK-G17 No local machine paths; all paths repo-relative and `<= 200` chars (Windows
      MAX_PATH); ASCII + UTF-8 no BOM (`--` for dashes, `->` for arrows).

## Allowed vs Forbidden operations (the boundary stated explicitly)

- [ ] CHK-G18 ALLOWED: package a request; transcribe a decision; write the decision through
      to the named committed artifacts; flip a stage to `pass` ONLY with approval AND
      evidence; surface conflicts -- the spec's Allowed operations list matches these.
- [ ] CHK-G19 FORBIDDEN: pick the option / supply the owner / invent rationale / auto-accept
      a default / pass without evidence / wrong-authority record / overwrite a prior approval
      / emit a score / add a rule-CLI-Python / publish Power BI / inline C086 -- the spec's
      Forbidden operations list matches these.
- [ ] CHK-G20 The console never calls the Power BI execution adapter / publishes Power BI;
      that is F016 (parked), execution-only and gated on Semantic Model Ready (Non-goals).

## Evidence required

- [ ] CHK-G21 Every request `evidence` line cites a committed source path (and row/line where
      applicable); a value with no traceable origin is a defect (FR-012; Evidence required).
- [ ] CHK-G22 A decision's `owner` + `date` ARE the approval evidence that lets a stage be
      `pass`; a `pass` with no `approvals[]` entry is a defect, and a stage flip also requires
      the stage's own required evidence already recorded (Evidence required; FR-007/FR-008).

## Notes

- This checklist is the feature's Core-Authority gate. The decisive risk for F027 -- a module
  that WRITES into Core-Authority artifacts -- is sliding from transcribing a decision to
  authoring one. CHK-G04..CHK-G11 are the items that hold that line.
- All items are `[ ]` (to verify) because the runtime deliverables are PLANNED, not authored
  in this slice; the spec is verified to ENCODE each guard so the later authoring slice has
  an explicit gate to pass.
