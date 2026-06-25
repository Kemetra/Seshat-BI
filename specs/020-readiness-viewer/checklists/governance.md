# Governance Checklist: Readiness Viewer

**Purpose**: Confirm the feature respects Core Authority -- that a read-only display
module reads, summarizes, and visualizes recorded truth without ever creating it.
**Created**: 2026-06-25
**Roadmap feature**: F026 (spec-dir 020 = roadmap F026; roadmap F-number is authoritative)
**Feature**: [spec.md](../spec.md)

This is the feature's "does it respect Core Authority" gate. Each item maps to the spec's
Forbidden operations and Human approval boundary. Items are unchecked `[ ]` -- they are
the gate a reviewer applies to the authored artifacts in the implementation slice.

## Core-vs-Module authority

- [ ] The viewer is a Product Module (read-only); it READS / SUMMARIZES / VISUALIZES
      evidence but creates NO truth (Core Authority owns truth) -- stated in the spec and
      to be enforced in the skill/mode text
- [ ] It renders `current_stage` and per-stage `status` EXACTLY as the
      `readiness-status.yaml` records them; it never recomputes, re-derives, or upgrades a
      stage status [Forbidden: recompute/upgrade status]
- [ ] It never decides a gate `pass`/`fail`; a `pass` it shows is one the Core Authority
      file already records, backed by the same evidence
- [ ] It writes DERIVED rendering only (the matrix / references / timeline); it writes no
      truth back to any per-item artifact
- [ ] It reuses F012's aggregation (recommended shape (a)) or is a mode of F012 (shape
      (b)); it does not fork or re-implement a second source of truth

## Principle V -- stop-and-ask (surface, never resolve)

- [ ] A conflict between `current_stage` and the per-stage statuses is SURFACED as a flag
      for a named human; the viewer does NOT resolve it by picking one [FR-010]
- [ ] A `pass` stage with empty `evidence[]` is SURFACED as "evidence missing"; the viewer
      does NOT hide it or treat the stage as complete [FR-005, FR-010]
- [ ] An approval that references a `not_started` stage is SURFACED as a conflict; the
      viewer does NOT reconcile or delete it [FR-006, FR-010]
- [ ] Grain / PII / business-rollup judgment calls remain Core Authority decisions; the
      viewer only renders their recorded readiness state, never adjudicates them

## No self-approval

- [ ] The viewer establishes NO approval and grants NONE; approvals are created by named
      humans and recorded in `approvals[]` by the Core Authority flow [Human approval
      boundary]
- [ ] The approvals timeline RENDERS recorded `approvals[]` only -- {stage, owner, date}
      verbatim, in date order; it never establishes, infers, or back-fills an approval
      [Forbidden: infer/back-fill approval]
- [ ] A `pass` gate whose required approval is absent is flagged "approval not recorded";
      the viewer never treats an unapproved gate as approved [FR-006]
- [ ] The viewer never moves a readiness stage to `pass` and never advances a stage
      [Forbidden: advance stage / write pass]

## No fake confidence

- [ ] The viewer emits NO numeric health / confidence / percent-ready score anywhere
      [Forbidden: numeric score; hard rule #9]
- [ ] A request for "one readiness score / percent-ready per item" is DECLINED with the
      readiness-model "No fake confidence" rationale; the four explicit statuses across the
      seven stages are returned instead [FR-008, SC-007]
- [ ] Every rendered value traces to a named committed source (path, and line/section
      where applicable); a value with no traceable source is a defect [Evidence required]

## Generic (no C086 / retail_store_sales)

- [ ] The skill/mode and `templates/readiness-view.md` are generic; C086 /
      retail_store_sales appear only as cited filled instances, never inlined [Forbidden:
      inline worked-example specifics; Principle VII]
- [ ] No billing codes, segment rollups, PII column names, or per-table grain keys are
      baked into any artifact; placeholders (`<table>`, `<source>`) are used

## Secrets / paths / encoding

- [ ] No secrets, DSNs, tokens, Kaggle / Power BI credentials, or local-machine paths in
      any artifact [Principle IX]
- [ ] All artifacts are ASCII only, UTF-8 without BOM; arrows as `->`, dashes as `--` (no
      Unicode symbols, no smart quotes)
- [ ] Repo-relative paths stay short (Windows path budget)

## Allowed-vs-forbidden operations (the boundary)

- [ ] ALLOWED operations match the spec: READ readiness-status.yaml + referenced evidence
      files; SUMMARIZE / VISUALIZE as matrix + references + timeline; REUSE F012's
      read-fan-out; SURFACE conflicts and gaps; STOP and report
- [ ] FORBIDDEN operations match the spec and are each mapped to a check above: recompute/
      upgrade status; advance stage / write pass; infer/back-fill approval; fabricate/fill
      evidence; run validator / SQL / DB connection; emit a numeric score; inline C086;
      resolve a current_stage-vs-status conflict
- [ ] The module changes NO state: `git status` shows zero modified `readiness-status.yaml`
      or per-item artifacts after a run, and no `approvals[]` entry was added [FR-007,
      SC-003, SC-005]

## Evidence-required

- [ ] The view renders, per item: the seven-stage matrix (each cell = recorded `status`),
      per-stage `evidence[]` as references (with missing / not-found flags), the
      `approvals[]` timeline (with "approval not recorded" flags), and the single
      `next_action` -- all traceable to a committed source [Evidence required]
- [ ] Missing / partial input is shown as missing: no `readiness-status.yaml` -> "no
      readiness file"; malformed -> "readiness file incomplete: `<file>`"; never an invented
      status, evidence reference, or approval [FR-009]
- [ ] No new validator, gate, or `retail check` rule is added; `retail check` stays exit 0
      and no new rule is added [FR-007, SC-002; Principle VIII]

## Notes

- The governing risk is a read-only viewer quietly creating truth: recomputing a status it
  was meant only to display, inferring an approval to "complete" a timeline, or filling a
  missing-evidence gap to make a stage look done. The checks above map each of those to a
  Forbidden operation, so a reviewer can confirm the viewer renders Core Authority state
  without becoming a second author of it.
- The approvals timeline gets specific scrutiny: it is the one place a display module is
  most tempted to infer ("this stage is pass, so someone must have approved it"). The
  no-self-approval checks require the timeline to render recorded approvals only and to
  flag -- never fill -- a gate whose approval is absent.
