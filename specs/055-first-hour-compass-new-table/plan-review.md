# Adversarial Plan-Review: First-Hour Compass / New-Table Author Onboarding Cockpit

**Branch**: `055-first-hour-compass-new-table` | **Date**: 2026-07-01
**Reviewer stance**: single default-adverse skeptic, READ-ONLY (reports fixes, edits nothing).
**Artifacts reviewed**: spec.md, plan.md, tasks.md, analysis.md, checklists/requirements.md.

## Verdict

**Verdict**: PASS-WITH-NOTES

**PASS-WITH-NOTES.**

All five required upstream stages are present (specify, clarify, plan, tasks, analyze).
Analyze is CLEAN (0 critical / 0 high). No critical or high skeptic finding survives.
Three low/medium NOTES are recorded for the implementer to honor at authoring time; none
blocks ratification.

## The five axes

### 1. Hidden-principle-violation -- CLEAN

- The card never self-grants: FR-007 reads the approval REQUIREMENT from the stage doc's
  "Required owner / approval" field and flags a missing approval; it never decides the
  requirement, infers, establishes, or back-fills an approver. This is the exact
  two-condition rule the shipped readiness-viewer uses -- a proven Principle-V-safe seam.
- The card never advances/resolves: FR-006 (blockers verbatim), FR-008 (no writes, git
  clean), FR-012 (surface conflicts, never resolve), FR-014 (four seams surfaced-only).
- The "next artifact" pointer (FR-003) does NOT decide readiness -- it reads the FIRST
  non-pass stage from recorded per-stage statuses in fixed pipeline order. It presents an
  already-recorded position; it computes no new truth.
- FR-013 keeps the card off the gate path (gate exit code stays the authority; no new
  `retail check` rule). Principle I honored.

### 2. Assumes-deferred-capability -- CLEAN

- No artifact references F016 (Power BI Execution Adapter) or F031-F033 spec-only
  runtimes. The Compass reads static committed files (`readiness-status.yaml`, stage
  docs) only; the agent is the runtime (invoke-and-present), matching the sibling.
- `next_step.py` is explicitly DEFERRED and enumerated-not-built in all three artifacts
  (FR-016; plan "Deferred"; tasks "Out of scope"). The MVP depends on nothing unbuilt.

### 3. C086-leak -- CLEAN (with NOTE-1)

- Spec FR-005/FR-017 and plan risk note require generic `<table>`/`<stage_key>`/`<skill>`
  placeholders; C086/retail_store_sales cited only as a filled instance. T008 is a
  dedicated leak-scan verification pass. The plan mitigation matches the sibling verbatim.
- The risk is real at AUTHORING time (the only filled readiness-status.yaml is C086) but
  is correctly guarded at the plan level. See NOTE-1.

### 4. Fabricated-confidence -- CLEAN

- FR-009 / SC-004: no numeric health/percent-ready/confidence/maturity score anywhere;
  a score request is DECLINED citing readiness-model "No fake confidence". T007 verifies.
  Orientation is the recorded stage + next artifact + explicit statuses + evidence +
  blockers -- categorical, never a number.

### 5. Over-scope -- CLEAN

- Deliverables are three docs files + an embedded generic cross-walk. No runtime code, no
  new gate, no DB, no live recompute. YAGNI honored (add the seam, not the implementation).
- FR-007's read of the stage doc's required-owner field at render time is in-scope and
  identical to the shipped sibling's behavior -- not new machinery.

## Notes (honor at authoring time; none blocks ratification)

- **NOTE-1 (medium, C086 discipline at authoring)**: The single filled instance is
  retail_store_sales. When T001/T002 author the template + cross-walk, the implementer
  MUST use placeholder rows and MUST NOT copy retail_store_sales's recorded stage values,
  grain key, segments, or PII column names as if they were the schema. The plan/tasks
  already mandate this (T008 scan); this note simply flags it as the single highest
  authoring-time risk to watch.
- **NOTE-2 (low, traceability)**: analysis.md LOW-1/LOW-2 -- SC-001 and SC-006 are
  covered by tasks (T001/T009) but not cited by SC-ID. Cosmetic; optional polish.
- **NOTE-3 (low, cross-walk assignment authority)**: Clarifications Q3 lets the cross-walk
  name a generic authoring SKILL DIRECTORY per stage. The implementer should keep the
  per-stage assignment presented as generic kit structure (which skill authors which
  stage), and NOT as a claim about any one table's progression. This stays inside
  Principle VII; flagged only so a reviewer confirms the framing at authoring time.

## Uncertainty disclosure

No CRITICAL finding was identified, and I hold no CRITICAL I am unsure about. The design
is a faithful single-table delta of a shipped, principle-audited sibling (F026), which is
the strongest evidence that its read-only / no-self-grant / no-score contract holds. The
only genuine residual risk is authoring-time C086 discipline (NOTE-1), which is a build
concern the ratified tasks already guard, not a spec defect.
