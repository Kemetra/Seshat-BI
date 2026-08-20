# Tasks: Capability-oriented setup ("Seshat Setup")

**Feature**: `specs/153-capability-oriented-setup/` | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

**Prerequisite SATISFIED**: issue #671 landed (`b456577c`). FR-018 remains a
permanent boundary.

**Spec status**: Draft. Planning and tasks may proceed; IMPLEMENTATION requires
owner ratification first.

TDD order: the failing test comes before the code. A task is done only when its
test was seen RED, then GREEN.

## Phase 0 -- Research (DONE, recorded in research.md)

- [x] **T001** R1 -- project evidence axes. Settled: `mappings/*/source-map.yaml`
  `meta.source_system`, `powerbi/*.pbip`, `dbt/dbt_project.yml`,
  `orchestration/dagster/`. `.seshat/` is KIT metadata, not project evidence.
- [x] **T002** R1b -- **absence is evidence**. Each check is a deterministic query
  over committed state, so a negative result is a citable finding, not a guess.
  This is what keeps `not-required` reachable and US1 AS1 satisfiable.
- [x] **T003** R2 -- vocabulary. Capability NAME from
  `docs/capabilities/capabilities.yaml`; capability->component mapping from the
  integration catalog. Neither edited, neither duplicated.
- [x] **T004** R3 -- strength is DERIVED per project, never a `Component` field.
- [x] **T005** R4 -- satisfied-state reuses the spec 148 discovery surface.
- [x] **T006** R5 -- capability-first reason text authored here; catalog `role`
  strings stay in the evidence layer only.

## Phase 1 -- Design

- [ ] **T007** `data-model.md`: `Capability`, `RequirementStrength` (four values),
  `DerivationEvidence`, `SetupPlanRow`, `SetupPlan`. Record that `undetermined`
  is an evidence marker, NOT a fifth strength.
- [ ] **T008** `quickstart.md`: the two US1 projects rendering different derived
  sets, with no package name in either.

## Phase 2 -- Derivation (US1, P1)

- [ ] **T009** [RED] A project with a source-map declaring a source system ->
  Database Connectivity `required`, reason naming that file. (FR-001, FR-008)
- [ ] **T010** [RED] A project with a `.pbip` -> Power BI Integration `required`,
  reason naming the artifact. (FR-001)
- [ ] **T011** [RED] A project with NO `.pbip` -> Power BI Integration is not
  `required`. (US1 AS3)
- [ ] **T012** [RED] A committed `dbt_project.yml` -> Transformation Engine
  derived from its presence; absent -> `not-required`, reason naming what was
  looked for and not found. (US1 AS1, FR-008)
- [ ] **T013** [RED] `orchestration/dagster/` absent -> Orchestration
  `not-required` -- NOT `undetermined`. Absence with a citable basis is a finding.
  (US1 AS1)
- [ ] **T014** [RED] Two projects of DIFFERENT shape -> different derived sets.
  A test that passes for both shapes proves nothing. (SC-002)
- [ ] **T015** [RED] The derived set is never the union of all curated profiles.
  (SC-002)
- [ ] **T016** [RED] Same evidence twice -> identical set and strengths. (FR-003)
- [ ] **T017** [RED] Derivation makes no network call and writes nothing --
  asserted on the module source and by running against a read-only fixture.
  (FR-004)
- [ ] **T018** [RED] Unreadable/contradictory evidence (a `source-map.yaml` that
  exists but will not parse) -> `undetermined` naming the missing evidence, NEVER
  defaulted to `required`. (FR-005)
- [ ] **T019** [RED] A capability already satisfied is reported satisfied and
  proposed for no change. (US1 AS4)
- [ ] **T020** [GREEN] Implement derivation.

## Phase 3 -- Requirement strength (US2, P2)

- [ ] **T021** [RED] Every row carries exactly one of the four values. (FR-007)
- [ ] **T022** [RED] Every row carries a reason citing project evidence; zero
  rows lack one. (FR-008, SC-003)
- [ ] **T023** [RED] Declining a `recommended` capability leaves remaining work
  able to proceed, and the decline is recorded so a later run does not re-propose
  it as new. (FR-009)
- [ ] **T024** [RED] Declining a `required` capability yields an explicit blocker
  with a next action, and setup does NOT report the project as set up, nor
  downgrade the strength to make the blocker disappear. (FR-010)
- [ ] **T025** [RED] An agent-requested capability outside derived need is
  reported as outside derived need, never promoted to `required`. (FR-006)
- [ ] **T026** [RED] `undetermined` is NOT one of the four strengths -- assert the
  strength vocabulary has exactly four members. (FR-007)
- [ ] **T027** [GREEN] Implement strength + decline recording.

## Phase 4 -- Presentation (US3, P3)

- [ ] **T028** [RED] The normal rendering contains no package, MCP, npm, or
  runtime identifier and no install command. **Non-vacuous**: build the forbidden
  set from the catalog's own `coordinate` values at test time, not a hardcoded
  list that silently stops matching when the catalog changes. (FR-012, SC-004)
- [ ] **T029** [RED] On explicit request, provider identity, compatibility/version
  state, and verification basis are all reachable -- sourced from the control
  plane, not recomputed. (FR-013)
- [ ] **T030** [RED] Where more than one provider could satisfy a capability, the
  selection and its basis are both reportable. (FR-014)
- [ ] **T031** [RED] Machine-readable status carries strength, satisfied,
  reason, and any blocker/undetermined marker -- enough to answer all five agent
  questions without provider internals. (FR-015, SC-008)
- [ ] **T032** [RED] No presentation or machine-readable output contains a
  secret, credential, connection string, or token. (FR-016, SC-011)
- [ ] **T033** [GREEN] Implement presentation + evidence path.

## Phase 5 -- Boundaries (the FRs that keep this a delta)

- [ ] **T034** [RED] **FR-018 as a real test, not a comment**: assert this
  feature's modules contain no approval decision, no `--yes`-style boolean
  authorization, and that authorization is the #671 gate's outcome. The weak model
  must be structurally un-inheritable even though it no longer exists.
- [ ] **T035** [RED] No second installer, resolver, verifier, or state store:
  assert the feature's modules perform no install, no version resolution, and no
  lock write. (FR-017)
- [ ] **T036** [RED] No second capability registry: assert
  `docs/capabilities/capabilities.yaml` and the integration catalog are READ, and
  that no new capability list is authored. (FR-011)
- [ ] **T037** [RED] Satisfaction never rests on install success -- it comes from
  the discovery/verification surface. (FR-019)
- [ ] **T038** [RED] `DEFAULT_PROFILE` is unchanged and profiles still work:
  derivation is an ADDITIONAL basis, not a replacement default (FR-002, and spec
  144 FR-006 protects the exported constant's value).
- [ ] **T039** [RED] Adding a capability/provider to the catalog changes the
  derived plan with no change to the user-facing journey. (FR-020, SC-010)

## Phase 6 -- Verification that the derivation actually derives

- [ ] **T040** Non-vacuity sweep: for each negative assertion, break the evidence
  and confirm the test FAILS. **Commit before poking**, so the restore cannot
  discard work.
- [ ] **T041** Platform-vacuity: no assertion keyed to a Windows literal -- CI is
  Linux.
- [ ] **T042** Prove `undetermined` is reachable AND not over-reachable: it fires
  on unreadable evidence and does NOT fire merely because a capability is unused.

## Phase 7 -- Gates

- [ ] **T043** `ruff format --check src/ tests/` and `ruff check src/ tests/`.
- [ ] **T044** `pytest -m unit` green. CI's unit job runs WITHOUT app extras.
- [ ] **T045** `seshat check` exit 0.
- [ ] **T046** Measure changed files with `cs review` if the CodeScene CLI is
  available; refactor a flagged function rather than suppressing. Note it was NOT
  installed during spec 154's build -- verify before claiming a health result.
- [ ] **T047** Diff contains no unrelated file.

## Out of scope

- Changing `DEFAULT_PROFILE` or displacing profile selection as the default.
- Any change to the catalog, installer, resolver, compatibility, lockfile,
  discovery, or the #671 approval gate.
- A second capability registry, installer, resolver, verifier, or state store.
- A marketplace, a graphical installer, or a broad CLI redesign.
- Live database or network access during derivation.
