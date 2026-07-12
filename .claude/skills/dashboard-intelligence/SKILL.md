---
name: dashboard-intelligence
description: >-
  Coordinate the SHIPPED Seshat dashboard capabilities into one governed journey
  (spec 123, US2) -- from an APPROVED Report Intent through gap/duplication checks,
  contract-bound design, report composition, and dashboard QA, STOPPING at the human
  blueprint review. Use when someone asks to "build/design the dashboard end to end",
  "coordinate the dashboard work", or drive a subject area from an approved intent to
  a reviewable design in the Seshat BI repo. The AGENT is the runtime: this skill
  inspects committed state, picks ONE next allowed action, invokes the existing
  capability, and re-evaluates. It reuses `retail dashboard-gaps`,
  `retail dashboard-planner`, `dashboard-design`, the blueprint/visual-spec/
  composition templates, visual-to-contract binding, and dashboard QA -- it adds NO
  new CLI family, NEVER bypasses `semantic_model_ready: pass`, and NEVER self-grants
  `dashboard_ready: pass`. It fails closed with a named blocker on the first unmet
  precondition.
---

# dashboard-intelligence

The **coordinator** for the governed dashboard-intelligence journey (spec 123, US2).
Seshat already ships strong, individually-governed dashboard components; today a user
must wire them by hand and can reach visual implementation without a committed report
purpose. This skill turns that set of skills into ONE coherent, fail-closed sequence:
given an **approved Report Intent** (US1), approved metric contracts, and a ready
semantic model, it sequences the shipped capabilities in the correct order to produce
a reviewable dashboard design, and STOPS at the human blueprint-review seam.

You (the agent reading this) ARE the runtime. This skill is procedure, not an engine:
there is no daemon, no scheduler, no persisted counter. The self-heal loop below is
something YOU perform in-context, exactly like `retail-orchestrate`.

## Scope + non-negotiables (read first)

- **Compose, never fork (FR-008/FR-011).** Reuse the shipped capabilities as they
  are. Do NOT re-implement gap detection, planning, or design, and do NOT introduce a
  broad new CLI family to wrap them. The one small helper this skill leans on --
  `src/seshat/dashboard_coordinator.py` -- is a READ-ONLY state inspector, not a new
  verb; it decides the next allowed action and names any blocker.
- **The hard gate is `semantic_model_ready: pass` (FR-010).** Never design a
  data-bound visual before it. `warning` / `blocked` / `not_started` all FAIL the
  gate. The coordinator reads the gate; it never bypasses it and never re-derives it.
- **No self-grant of `dashboard_ready: pass` (FR-010, Principle V).** The highest
  outcome a happy path reaches is "STOP at the human blueprint review". The
  `dashboard_blueprint_approval` decision is a NAMED-human action recorded in the
  shipped Decision Store -- an agent identity never satisfies `approved_by`.
- **Fail closed (FR-033/FR-034).** On any unmet precondition, STOP with a blocked
  result that NAMES: (1) what is missing/invalid; (2) the evidence checked; (3) the
  responsible owner; (4) the action that would unblock progress. Never a numeric
  score (FR-035). Never proceed past a stop to "make progress".
- **Read-only + static (SEC-001).** No live DB, no Power BI Desktop, no PBIR
  authoring, no publish/refresh/export. The journey stops at committed on-disk
  artifacts; execution is the deferred F016 boundary.
- **ASCII only, UTF-8 no BOM** in anything you author (`->` arrows).

## Run-state: read the committed tree FIRST (no new state file)

Compute the current step from what is already on disk -- there is NO coordinator state
file to create. The helper `dashboard_coordinator.next_action(repo_root,
subject_area, tracked_files)` returns EITHER the single next allowed action OR a
`Blocked(what, evidence, owner, unblock)`. It is the load-bearing decision; the table
below is the sequence it enforces.

| What you observe (committed state) | Verdict / next action |
|------------------------------------|-----------------------|
| No committed `report-intent.yaml` for the subject area | BLOCKED -- run the `report-intent-interview` skill (US1) first. |
| Report Intent present but NOT owner-approved (no valid `report_intent_approval` in the Decision Store) | BLOCKED -- a named `report_owner` records the approval; agent never self-grants. |
| `semantic_model_ready` != `pass` | BLOCKED -- the hard gate; name the missing readiness, do NOT design. |
| A required intent metric has no approved contract | BLOCKED -- record a gap, route upstream to metric-contract definition (F009); never invent. |
| A visual binds no approved contract (orphan) | BLOCKED -- bind or drop; SC-003 requires zero orphan visuals. |
| All above hold + design authored | NEXT ACTION -- STOP at the human blueprint review seam (no self-grant). |

## Fixed sequence (delegate to the SHIPPED capabilities)

On each step: inspect committed state -> pick ONE next allowed action -> invoke the
capability responsible for it -> re-evaluate (FR-007). Never run two design steps
before re-reading state.

| Step | Precondition (verify FIRST) | Shipped capability to invoke | Produces |
|------|-----------------------------|------------------------------|----------|
| 1 Intent approved | committed `report-intent.yaml` + valid `report_intent_approval` (read via the decision gate) | `report-intent-interview` (US1) if absent | the approved Report Intent artifact |
| 2 Gap check | `semantic_model_ready: pass`; intent metrics/dimensions | `retail dashboard-gaps` | categorical Covered/Blocked/Planned inventory; a Blocked item STOPS the coordinator naming the blocker + owner |
| 3 Duplicate/extend | a proposed page | `retail dashboard-planner` | deterministic `new` / `extends <page>` / `duplicate of <page>` verdict (no score); a duplicate is surfaced for HUMAN decision |
| 4 Design | gap check clean; gate `pass` | `dashboard-design` (F011) | page blueprints + visual specs + the visual-contract binding map (every visual -> one approved contract) |
| 5 Compose | blueprints authored | the `report-composition.yaml` template | page order + navigation + cross-page filters; each blueprint `business_question` MUST trace to an intent question (FR-002a) |
| 6 QA | visuals authored | the shipped dashboard-QA anti-pattern catalog | per-visual / per-page QA findings |
| 7 STOP | design authored | (human) | STOP at the blueprint review seam -- never self-grant `dashboard_ready: pass` |

Invoke the SAME shipped surfaces the individual skills use. `retail dashboard-gaps`
and `retail dashboard-planner` are the existing read-only CLI verbs; `dashboard-design`
is the existing gated design verb; the templates + binding map are the existing
artifacts. This skill adds NONE of its own.

## The re-evaluate loop (a contract you follow; not a runtime)

1. **INSPECT** committed state via `dashboard_coordinator.next_action(...)`.
2. **If BLOCKED** -> STOP. Report `what / evidence / owner / unblock` verbatim. Do
   NOT edit around the blocker; if it is a Principle V judgment (which page answers
   which question, a duplicate decision, an approval) escalate to the named owner.
3. **If NEXT ACTION** -> invoke the ONE shipped capability responsible for it.
4. **RE-EVALUATE** (back to step 1). Never chain two capabilities without re-reading
   state.
5. When the next action is the **human blueprint review**, STOP. The MVP is a
   reviewable dashboard design (intent + blueprints + visual specs + composition +
   binding map); preview (US4) and PBIR (US7) are later slices, not part of this loop.

**No-progress brake:** if the same blocker (`what` + `evidence`) recurs after you
acted, STOP and escalate -- you are flip-flopping, not converging.

## STOP rules (FR-009 -- each maps to a named blocker)

The coordinator STOPS with a blocked result on ANY of:

- **Unresolved intent** -- no committed / no owner-approved `report-intent.yaml`.
- **Missing / unapproved contract** -- a required intent metric has no approved
  metric contract; route upstream (F009), never invent (FR-003/FR-004).
- **Missing required field** -- a dimension/field the design needs is absent from the
  governed model (surfaced by `retail dashboard-gaps` as Blocked -- missing field).
- **Orphan visual** -- a visual with no approved contract behind it (SC-003).
- **Missing / invalid blueprint approval** -- design authored but no valid
  `dashboard_blueprint_approval`; STOP at human review, never self-grant.
- **`semantic_model_ready` != pass** -- the hard gate (FR-010), never bypassed.

Every blocked result NAMES what/evidence/owner/unblock (FR-034). Never a score.

## What the agent must NOT do

- Do NOT bypass `semantic_model_ready: pass` -- never design a data-bound visual
  before the gate is `pass` (FR-010).
- Do NOT self-grant `dashboard_ready: pass` or record a `dashboard_blueprint_approval`
  -- those are the named report_owner's action (Principle V, no self-grant).
- Do NOT invent, define, or alter a metric -- bind only to approved contracts; a
  missing metric is a gap routed upstream to F009 (FR-003/FR-004).
- Do NOT emit an orphan visual (a visual with no approved contract) -- SC-003.
- Do NOT add a new CLI family or a parallel gap/planner/design implementation --
  compose the shipped ones (FR-008/FR-011).
- Do NOT open a DB or Power BI Desktop connection, author PBIR, or publish/refresh/
  export -- that is the deferred F016 execution boundary (SEC-001, FR-036).
- Do NOT fabricate a confidence/readiness/design/quality score -- use the categorical
  outcomes + named blockers only (FR-035).

## Generic, not tenant-specific

This skill and the helper are GENERIC (Principle VII). No tenant/subject-area
specifics live in the skill text or the helper -- `demo_report_area` /
`retail_store_sales` are worked EXAMPLES, never the schema. Worked values belong only
to a per-subject-area instance under `mappings/<subject-area>/`.

## See also

- The helper (the fail-closed decision, unit-testable): `src/seshat/dashboard_coordinator.py`.
- The upstream intent skill (US1): `.claude/skills/report-intent-interview/SKILL.md`.
- The gated design verb (F011): `.claude/skills/dashboard-design/SKILL.md`.
- The shipped read-only verbs: `retail dashboard-gaps` (spec 117), `retail dashboard-planner` (spec 116).
- The structural artifacts: `templates/dashboard-page-blueprint.yaml`, `templates/visual-spec.yaml`, `templates/report-composition.yaml`, `templates/visual-contract-binding-map.md`.
- The approval machinery (no self-grant): `src/seshat/decision_store.py`, `src/seshat/decision_gate.py`, `contracts/knowledge/approval-authority.yaml`.
- The spec + tasks: `specs/123-governed-dashboard-intelligence/{spec.md,plan.md,tasks.md}`.
- The conductor precedent: `.claude/skills/retail-orchestrate/SKILL.md`.
