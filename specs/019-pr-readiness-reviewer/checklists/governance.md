# Governance Checklist: PR Readiness Reviewer

**Purpose**: Verify the feature respects Core Authority -- the architectural rule binding all
features. A Product Module may READ evidence, SUMMARIZE it, and render a verdict; it MUST NOT
create truth. This checklist is the feature's "does it respect Core Authority" gate.
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md) -- Roadmap F025 (Product Module, read-only; spec-dir 019)

## Core-vs-Module authority (the binding rule)

- [ ] CHK-G01 The spec states the module READS evidence, SUMMARIZES it, and VISUALIZES /
      reports a verdict -- it does NOT create truth (F024 Core Authority).
- [ ] CHK-G02 The verdict is a DERIVED reading of evidence; the module is never the authority
      on whether the PR is approved or merged (the human reviewer and the gate exit code are).
- [ ] CHK-G03 The module writes no truth-bearing artifact: it does not author or edit a
      `readiness-status.yaml`, `source-map.yaml`, `approvals[]`, or any per-table evidence
      file. It reads them as INPUTS only.
- [ ] CHK-G04 The "publish approval requested too early" guard ROUTES the call to a named
      human (`required_human_decision`); the module does not grant the publish or move the
      stage.

## Principle V -- stop at judgment calls

- [ ] CHK-G05 Business rollup / segment mappings are NOT decided by the module -- surfaced as
      a `required_human_decision`, never auto-filled.
- [ ] CHK-G06 PII publish-safety is NOT decided by the module -- surfaced as a
      `required_human_decision` routed to governance/owner.
- [ ] CHK-G07 Grain ambiguity and sentinel-vs-null are NOT decided by the module -- surfaced
      as `required_human_decisions[]`, never auto-resolved.
- [ ] CHK-G08 Every `required_human_decision` names the owner who must decide; an unassigned
      one is shown "UNASSIGNED" and flagged -- the module never self-assigns or self-resolves.
- [ ] CHK-G09 Conflicting evidence is SURFACED as a finding and NOT silently resolved by the
      module choosing one side (surface conflicts, never bury them).

## No self-approval (read-only boundary)

- [ ] CHK-G10 Forbidden operations explicitly list: cannot merge a PR.
- [ ] CHK-G11 Forbidden operations explicitly list: cannot approve a PR (no review submission,
      no required-approval grant).
- [ ] CHK-G12 Forbidden operations explicitly list: cannot resolve or reply to a review
      thread or review comment.
- [ ] CHK-G13 Forbidden operations explicitly list: cannot push/amend a commit or edit a PR
      body/title.
- [ ] CHK-G14 Forbidden operations explicitly list: cannot move, upgrade, or mark `pass` any
      readiness stage; cannot clear a blocker; cannot clear the mapping gate.
- [ ] CHK-G15 A request to "approve and merge" or "mark this stage pass" is DECLINED with the
      read-only / cannot-create-truth rationale (F024 / Principle V) -- the module returns the
      verdict instead.
- [ ] CHK-G16 The module has no special authority over its own PR -- it cannot self-approve
      when run against its own promotion.

## No fake confidence (rule #9)

- [ ] CHK-G17 `merge_ready` is a boolean (yes/no), never a numeric score; the spec says so
      explicitly.
- [ ] CHK-G18 A request for a numeric merge / confidence / health score is DECLINED, citing
      no-fake-confidence (rule #9), returning the boolean + explicit lists instead.
- [ ] CHK-G19 No field anywhere reads as a confidence number; readiness is expressed only as
      `merge_ready` + `blockers[]` + `warnings[]` + `required_human_decisions[]` + evidence.
- [ ] CHK-G20 Evidence traceability (the no-fake-confidence analog): every blocker / warning /
      required-decision carries a cited source; a line with no traceable source is a defect.

## Generic (no worked-example specifics)

- [ ] CHK-G21 The spec, plan, tasks, and both checklists contain ZERO C086 /
      `retail_store_sales` / pharmacy specifics (billing codes, segments, PII column names,
      per-table grain keys).
- [ ] CHK-G22 C086 / `retail_store_sales` are CITED as filled-instance references only, never
      inlined into the planned generic skill / template / doc (Principle VII).
- [ ] CHK-G23 Placeholders are obvious (`<table>`, `<source>`, `<PR#>`, named-owner
      placeholders) -- no worked-example answers baked in.

## Secrets / paths (Principle IX)

- [ ] CHK-G24 No secret, DSN, token, Kaggle / Power BI credential, or local machine path
      appears in any of the five files.
- [ ] CHK-G25 The module FLAGS a secret-shaped string or local path in a PR diff as a blocker
      and recommends STOP-rotate-sweep -- but never edits or removes it (read-only).
- [ ] CHK-G26 All five files are ASCII + UTF-8 no BOM, using `->` for arrows and `--` for
      dashes (no Unicode symbols, no smart quotes) -- Principle IX / Windows charmap.

## Allowed-vs-forbidden operations (clarity gate)

- [ ] CHK-G27 The spec carries an "Allowed operations" section (read-only observe + read +
      interpret + emit verdict + decline out-of-scope) and a "Forbidden operations" section
      (merge / approve / resolve / commit / edit / stage-move / define-meaning / re-run-gate /
      score), and they do not contradict.
- [ ] CHK-G28 Reading PR / CI / git state is classified as ALLOWED read-only observation, not
      a new gate and not a mutation (FR-009 / FR-013).
- [ ] CHK-G29 The module adds NO new gate / rule / validator / CI workflow; it READS recorded
      gate and CI results as evidence only (no new `retail check` rule is added).

## Evidence required (promotion honesty)

- [ ] CHK-G30 `merge_ready: yes` requires zero blockers AND zero open required-decisions,
      each observed line traceable to its source; pending / unknown lines are not treated as
      pass.
- [ ] CHK-G31 A claimed readiness stage / approval / mapping clearance must be backed by the
      committed `readiness-status.yaml` / `approvals[]` / `source-map.yaml` field, or it is a
      blocker naming the absence -- the module never invents the supporting evidence.
- [ ] CHK-G32 The Human approval boundary section states `merge_ready: yes` is NOT an approval
      and NOT a merge: the named human reviewer still approves and still merges.

## Notes

- This module is the F024 "Product Module, read-only" category embodied: its entire value is
  reading evidence and rendering a verdict; every checkbox above guards the line between
  reporting (allowed) and acting / creating truth (forbidden).
- The two structural guardrails are (1) report-not-act (CHK-G10..G16) and (2)
  boolean-not-score (CHK-G17..G20); together they keep the module inside Core Authority.
- Items are unchecked `[ ]` by design: this is the gate a reviewer walks before the feature's
  future deliverables are authored, not a self-attested pass.
