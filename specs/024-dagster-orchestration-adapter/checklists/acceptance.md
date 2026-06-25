# Specification Quality Checklist: Dagster Orchestration Adapter

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Roadmap feature**: F030 (spec-dir 024)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details leak in (no Dagster code, no asset code, no `pyproject` content) -- the asset graph and project layout are ENUMERATED as future shape, not authored
- [x] Focused on the authority boundary and user value (runs approved steps; decides no stage)
- [x] Written so a non-Dagster reviewer can state what the adapter MAY run and MUST NOT do
- [x] All mandatory sections completed (Why, scope wall, F005 reconciliation, architecture, user stories, requirements, success criteria, human approval boundary, allowed/forbidden ops, evidence, readiness stage, dependencies, non-goals, assumptions, deferred decisions, see also)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (open specifics -- schedules/sensors cadence, concrete code -- recorded as Deferred decisions, not blockers)
- [x] Requirements are testable and unambiguous (FR-001..FR-012 each have an observable check)
- [x] Success criteria are measurable (SC-001..SC-007: five-files-only, closed allowed/forbidden lists, per-edge gate semantics, four load-bearing stories, boundary resolved, F005 reconciliation, generic+ASCII)
- [x] Success criteria are technology-agnostic where they can be (authority/evidence properties, not Dagster API specifics)
- [x] All acceptance scenarios are defined (US1-US4 each Given/When/Then)
- [x] Edge cases are identified (gate OPEN, mid-run judgment call, validate-cannot-connect, publish-not-ready, direct downstream request, version skew, evidence-vs-human-edit conflict)
- [x] Scope is clearly bounded ("What this feature is NOT" wall; planning-only; creates no Dagster file)
- [x] Dependencies and assumptions identified (F024 category, F029 dbt, F005 conductor; F016 downstream; F031/F033 referenced siblings)

## Feature Readiness

- [x] Every functional requirement maps to an acceptance criterion or success criterion
- [x] User scenarios cover the four named load-bearing acceptances (failed-validation-stops-downstream; approval-gate-reads-committed-approval; completed-run-writes-evidence-flips-no-stage; no-self-approval)
- [x] Feature meets the measurable outcomes in Success Criteria
- [x] No implementation details leak into the specification (FUTURE outputs enumerated, not created)

## Acceptance criteria mapped to requirements

- [x] CHK-A1 (US1 / FR-005): a failed gate asset fails closed and halts ALL downstream assets; the run records the failure with measured numbers; no stage flips
- [x] CHK-A2 (US2 / FR-006): every human-seam asset READS the committed approval (`Gate status`, `approvals[]`) as its only GO signal and HALTS if absent; never self-grants; never invents a parallel marker
- [x] CHK-A3 (US3 / FR-007): a completed run writes a derived `dagster-run-evidence.md` record (per-asset gate command, exit, measured numbers, timestamp, commit sha, blocked reasons + owners) and flips NO stage / writes NO approval / writes NO `Gate status`
- [x] CHK-A4 (US4 / FR-004): no asset can write a stage `pass`, `Gate status: CLEARED`, an approval, a metric/mapping/grain ruling, or a Power BI publish; the Forbidden operations section enumerates each
- [x] CHK-A5 (FR-002 / SC-003): the asset graph is specified with per-edge gate semantics (STOP edges vs HUMAN-SEAM edges); the terminal publish asset is gated on `publish_ready = pass` and only TRIGGERS F016
- [x] CHK-A6 (FR-003 / SC-002): the closed set of steps Dagster MAY run is explicit (load bronze, profile, dbt/SQL migrations, `retail check`, `retail validate`, semantic check, handoff pack, write run evidence)
- [x] CHK-A7 (FR-008 / SC-006): the F005 reconciliation is explicit -- conversational conductor vs unattended/CI sibling; same sequence + authority; neither self-approves
- [x] CHK-A8 (FR-009): the auto-update posture is stated (pin dagster + dagster-dbt together, PR-only, definitions-load smoke, no automerge on majors) with the shared policy deferred to F031/F033
- [x] CHK-A9 (FR-012): the readiness stage affected is stated as ALL stages, DECIDES none
- [x] CHK-A10 (FR-001 / SC-001): exactly five planning files are produced; zero Dagster files created
- [x] CHK-A11 (FR-010, FR-011 / SC-007): all five files are generic (no worked-example specifics baked in) and ASCII-only, UTF-8 no BOM

## Notes

- This is a planning-only slice (Principle VIII, roadmap rule #8): it adds no runtime code, no
  Dagster file, and no `retail check` rule. "Implementation details" here means Dagster asset
  code -- which this slice deliberately ENUMERATES as future shape rather than authoring.
- The four named acceptances from the feature brief are deliberately raised to load-bearing
  User Stories (US1-US4), each P1, each with Given/When/Then scenarios, so the safety properties
  are testable rather than prose.
- The derived-evidence vs authored-truth boundary is the spec's load-bearing decision; it is
  resolved in its own subsection AND reflected in the Allowed/Forbidden operations so a reviewer
  can state the single reconciling sentence.
- Principle-V judgment calls (grain, PII, business rollup, segment, sentinel-vs-null) are
  surfaced as stop-and-ask halts (US4 / FR-004), not auto-answered in the spec.
- Open specifics (schedules/sensors cadence, the concrete Dagster project + asset code) are
  recorded as Deferred decisions with the implementation slice as their home, not as
  [NEEDS CLARIFICATION] blockers.
