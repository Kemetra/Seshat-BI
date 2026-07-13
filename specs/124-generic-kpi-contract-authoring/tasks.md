# Tasks: Generic KPI Knowledge Registry and Governed Project Metric-Contract Authoring

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [research.md](./research.md), [contracts/](./contracts/)

**Prerequisites**: spec + plan + data-model + contracts complete (this package).

**Tests**: INCLUDED (TDD -- author the failing fixture/RED before the artifact/GREEN where a static rule or structural check exists).

**Organization**: phased by user story; each story is an independently testable slice. This is a SPECIFICATION package -- the tasks below are the implementation backlog for a LATER build feature; no task is executed or checkbox-ticked here.

## Format: `[ID] [P?] [Story] Description (traceability)`

- `[P]` = parallelizable (different files, no incomplete dependency).
- `[Story]` = `US1` registry | `US2` answerability | `US3` draft | `US4` binding | `US5` custom | `US6` wave | `US7` extension.
- Every task cites the FR(s)/SC(s)/entity it realizes.

> No checkbox is pre-marked. A box is ticked only against a verified deliverable in the build feature; repo Status headers and checkboxes are known-stale.

---

## Phase 1: Setup

- [x] T001 Confirm the target artifact paths from plan.md (registry `skills/retail-kpi-knowledge/registry.yaml`; answerability scorecard location; template edit target) exist or are creatable; no path exceeds the Windows repo-relative limit. (plan Structure Decision)
- [x] T002 [P] Enumerate the worked-example no-leak token list (C086 pharmacy: billing codes, insurance PII; retail_store_sales: `gold.fct_sales_rss`, `total_spent`, `quantity`, `transaction_id`, `discount_applied`, `customer_id`, 12575, 50.37%, Q1-Q4 rulings, the named human) as the fixture for the leakage scan; this fixture also enforces the generic/no-client-embedding requirement. (FR-001, FR-040, SC-012)
- [x] T002a [P] Assert the three-layer boundary holds across every authored artifact: product (registry + generic knowledge), project decision (Decision Store, referenced only), project contract (F009 YAML) -- and that no artifact reaches into SQL/DAX/Python/Big-data/Semantic/Dashboard/Publish ownership. (FR-002)

## Phase 2: Foundational (blocking prerequisites)

- [x] T003 [US1] Author the registry schema loader expectations from `contracts/generic-kpi-registry.schema.md` (field set, enums, uniqueness invariants) as the RED fixture. (FR-004, FR-005, FR-006)
- [x] T004 [US1] Author the answerability decision-rule fixture from `contracts/kpi-answerability.schema.md` (the 6 fail-closed derivation rules) as RED. (FR-007, FR-009, FR-041, FR-042)

## Phase 3: User Story 1 -- Establish the authoritative registry (P1 -- MVP)

**Goal**: one machine-readable registry indexing all 13 `KPI-MC-NN` exactly once, drift reconciled or documented.
**Independent test**: load the registry alone; every ID once, all fields present, no client token, every drift item named.

- [x] T005 [US1] Author `skills/retail-kpi-knowledge/registry.yaml` with one entry per `KPI-MC-01..13`, each carrying id/slug/canonical_name/aliases/domain/metric_kind/lifecycle/knowledge_contract_ref/derives_from/required_concepts/required_decision_types/source_roles. (FR-003, FR-004, entity GenericKpiRegistryEntry)
- [x] T006 [US1] Set `metric_kind` per KPI across the 7-value taxonomy (base/derived/ratio/time_transform/snapshot/quality/slice); preserve stable IDs. (FR-005, FR-006)
- [x] T007 [US1] Reconcile lifecycle drift IN THE REGISTRY: MC-11 (Net Sales Growth %) and MC-13 (YTD Net Sales) -> `seeded`; MC-12 (Same-Store) -> `planned`; record each as a resolved drift item naming README/packs/candidates. (SC-002, spec drift section)
- [x] T008 [P] [US1] Update `skills/retail-kpi-knowledge/references/id-conventions.md` MC range to reflect 13 assigned IDs. (SC-002)
- [x] T009 [P] [US1] Update `skills/retail-kpi-knowledge/references/kpi-derivation-lineage.md` to add MC-11/12/13 edges (from the registry `derives_from`, not a second graph). (FR-025, SC-002)
- [x] T010 [P] [US1] Reconcile the seed-count in `SKILL.md` / `INDEX.md` / `README.md` (10 -> 13) OR record it as documented drift if an owner ruling is needed. (SC-002)
- [x] T011 [US1] Record the em-dash-vs-ASCII `--` scorecard-template/SL1 divergence as an owner-flagged drift item; do NOT edit the shipped template. (spec drift section, Explicit STOP 5)
- [x] T012 [US1] Run the no-leak scan (T002 tokens) over `registry.yaml`; assert zero worked-example tokens. (FR-040, SC-012)

**Checkpoint**: registry loads; 13 unique IDs; all fields; drift documented; no leakage.

## Phase 4: User Story 2 -- Source-to-KPI answerability (P1 -- MVP)

**Goal**: a truthful per-source coverage artifact using the five statuses, failing closed.
**Independent test**: fixture source + Decision Store -> each row one of five statuses, blockers/evidence/next-action named, no score, lookalike -> `Blocked -- needs business definition`.

- [x] T013 [US2] Author the answerability artifact generator spec: read registry requirements + committed source-profile/source-map + Decision Store; emit rows in the scorecard shape. (FR-043, entity KpiAnswerabilityRow)
- [x] T014 [US2] Implement the six-step fail-closed derivation (Planned -> Out-of-scope -> missing field -> needs definition -> stale evidence -> Covered); never infer from a lookalike column. (FR-009, FR-041)
- [x] T015 [US2] For multi-fact KPIs, name every required `source_role` and block on any absent one. (FR-042)
- [x] T016 [US2] Assert no digit-`%` token, no ranking, no readiness grant; align output so SL1 lints it unchanged. (FR-008, SC-003)
- [x] T017 [P] [US2] Fixture: `total_sales` unresolved -> `Blocked -- needs business definition`, not `Covered`. (SC-004)
- [x] T018 [P] [US2] Fixture: inventory KPI vs sales-only fact -> `Out of scope`; Planned KPI -> `Planned`. (US2 scenarios 4,5)

**Checkpoint**: answerability artifact is truthful, evidence-bound, SL1-lintable.

## Phase 5: User Story 3 -- Draft a project contract from approved decisions (P1 -- MVP)

**Goal**: a governed F009 draft with structured provenance, honest `blocked` when Gold is absent.
**Independent test**: fixture approved decisions + evidence -> draft with generic_kpi_ref-or-custom, decision_refs, source_evidence; no approval -> refused.

- [x] T019 [US3] Add the four optional provenance fields to `templates/metric-contract.yaml` (`generic_kpi_ref`, `custom`, `decision_refs`, `source_evidence`) per `contracts/project-contract-provenance.md`; keep every existing field unchanged. (FR-011, FR-014, entity ProjectMetricContract)
- [x] T020 [US3] Implement the draft precondition: require an approved `kpi_definition` + applicable `policy_ruling`; else stop and name the missing decision. (FR-013, SC-005)
- [x] T021 [US3] Enforce exactly-one-of `generic_kpi_ref` / `custom: true`; allow a project name to differ from the generic canonical name without duplicating an entry; record `decision_refs` + `source_evidence` as structured refs establishing the end-to-end provenance chain. (FR-011, FR-012, FR-021, FR-034, SC-006)
- [x] T022 [US3] When no Gold binding exists, set `readiness.status: blocked`, reason `physical gold binding is not materialized`, with a concrete next action; never `pass`. (FR-016, SC-007)
- [x] T023 [US3] Assert the draft contains no DAX/SQL/visual/connection string/raw PII/unbacked gold path. (FR-015, SEC-001, SEC-002)
- [x] T024 [P] [US3] Record slice-vs-metric handling: a "by branch/product/category" request becomes a slice note, not a new contract. (FR-010, FR-031)

**Checkpoint**: MVP complete -- registry + answerability + governed draft with provenance.

## Phase 6: User Story 4 -- Checkpoint-B binding and handoff (P2)

**Goal**: complete the same contract with gold-only binding; `pass` only when fully valid.
**Independent test**: binding + valid decisions + fresh evidence + empty blockers + named approval -> eligible `pass`; remove any one -> refused.

- [x] T025 [US4] Complete the contract with actual gold-only `binds_to` (never silver/bronze). (FR-044)
- [x] T026 [US4] Gate `pass` on: binding exists AND decisions valid (not superseded) AND evidence not stale AND blockers empty AND named-human approval recorded -- reusing the existing decision gate and realizing the declared `kpi_contracts` stage outputs (no new flow/spine stage). (FR-017, FR-032, FR-033, SC-007)
- [x] T027 [US4] Detect superseded decisions and changed evidence; refuse `pass` and name the offender. (FR-018)
- [x] T028 [P] [US4] Emit clean SQL/DAX/Python/Big-data handoff INTENT (prose only); implement none. (FR-019)
- [x] T029 [P] [US4] Fixture matrix: remove each `pass` precondition independently -> refused. (SC-007)

**Checkpoint**: Checkpoint-B `pass` is honest and reversible on drift.

## Phase 7: User Story 5 -- Custom KPIs safely (P2)

**Goal**: author a custom project KPI without mutating the registry.
**Independent test**: custom draft with approved definition + policies + eligible owner -> `custom: true`, no registry change; no owner -> refused.

- [x] T030 [US5] Author a custom contract requiring approved definition, grain, additivity, unit, policies, required fields, and a NAMED ELIGIBLE owner; mark `custom: true`, no `generic_kpi_ref`. (FR-020, FR-021)
- [x] T031 [US5] Assert authoring a custom KPI with no eligible owner stops and names the missing owner. (FR-020, SC-008)
- [x] T032 [US5] Assert the generic registry is unchanged by any custom authoring (registry diff = empty). (FR-021, SC-008)
- [x] T033 [P] [US5] Document the separate contribution/review workflow to promote a custom KPI to generic; do NOT perform it. (FR-022, Explicit STOP 4)

**Checkpoint**: custom KPIs are governed and isolated from the product registry.

## Phase 8: User Story 6 -- First expansion wave (P3)

**Goal**: specification-ready coverage for the four D10 KPIs; concepts + policy slots only.
**Independent test**: per-KPI registry entry + knowledge contract with no baked-in value, no duplicated formula.

- [x] T034 [US6] Author `contracts/discounted-transaction-rate.md` (net-new generic) with discount denominator as an OWNER POLICY SLOT; from first principles, NOT the worked-example 50.37%/Q2 denominator; assign next MC id; add registry entry. (FR-023, FR-024, SC-009)
- [x] T035 [US6] Author `contracts/average-basket-size-units.md` (from Planned) referencing UNITS (not currency); grain/additivity as concepts; `derives_from` quantity/transaction metrics without duplicating formulas; add registry entry. (FR-023, FR-025)
- [x] T036 [P] [US6] Reconcile Net Sales Growth % (MC-11) registry lifecycle to `seeded` across all projections; comparison basis stays an owner policy slot (no YoY-vs-prior-period, no fiscal-year start baked in). (FR-023, FR-024)
- [x] T037 [P] [US6] Reconcile YTD Net Sales (MC-13) registry lifecycle to `seeded`; year-start stays an owner policy slot. (FR-023, FR-024)
- [x] T038 [US6] Update relevant packs/field-requirements/aliases for the four; assert each wave KPI is independently testable and independently reviewable; assert no duplicated formula and no prohibited baked-in value. (FR-025, FR-026, SC-009)
- [x] T039 [P] [US6] Assert the eight FR-027 KPIs (Same-Store, Inventory Turnover, GMROI, Out-of-Stock, Customer Retention, CLV, Net Sales vs Target, Promotion Uplift) remain `planned` (metadata + blockers only). (FR-027)

**Checkpoint**: four wave KPIs specification-ready; eight remain honestly Planned.

## Phase 9: User Story 7 -- Routine extension (P3)

**Goal**: a bounded extension checklist + at most two narrow static consistency rules.
**Independent test**: well-formed addition -> pass; each malformed case -> a structural error; no business-meaning adjudication; no readiness granted.

- [x] T040 [US7] Author `skills/retail-kpi-knowledge/checklists/kpi-extension-checklist.md`: the bounded artifact + validation set to add a future generic KPI. (FR-028)
- [x] T041 [US7] Implement static consistency Rule A (registry): duplicate id/slug/canonical_name, alias==canonical collision, dangling `derives_from`/`knowledge_contract_ref`, bad lifecycle, product-level binding/client-token leakage. Structure/traceability only; grants no readiness. (FR-029, FR-030, FR-040)
- [x] T042 [US7] Implement static consistency Rule B (provenance): neither-or-both `generic_kpi_ref`/`custom`, unresolved `generic_kpi_ref`, malformed `decision_refs`/`source_evidence`. Does NOT check decision approval (that is the existing gate). Cap at two rules total. (FR-029, FR-030)
- [x] T043 [P] [US7] Fixture matrix: each malformed case -> ERROR naming the defect; well-formed -> pass, no readiness. (SC-010)
- [x] T044 [P] [US7] Register the new rule id(s) in `EXPECTED_RULE_IDS` and regenerate the rules manifest (mirrors SL1's manifest bump). (FR-029)

## Phase 10: Cross-cutting validation

- [x] T045 [P] Secret/PII scan over all authored artifacts (reuse the C2/SEC posture): no raw PII, no connection string, no credential. (SC-011, SEC-001, SEC-002, SEC-003)
- [x] T046 [P] No-leak scan over the registry + the two new generic contracts against the T002 token list. (SC-012, FR-040)
- [x] T047 ASCII-only + UTF-8-no-BOM check over every authored file; `git diff --check`. (Quality bar)
- [x] T048 `retail check` green (the new rules pass on the repo); rules manifest count updated; confirm the flow is delivered agent-first via `retail-kpi-knowledge` routing with NO new broad CLI family and NO new orchestration engine, realizing the `kpi_contracts` stage without adding a flow/spine stage, and preserving the end-to-end provenance chain. (FR-029, FR-030, FR-033, FR-034, FR-035, FR-036)

---

## Traceability summary (every task -> a story + requirement)

| Story | Tasks | Realizes |
| --- | --- | --- |
| US1 | T003, T005-T012 | FR-003..FR-006, FR-040, SC-001, SC-002 |
| US2 | T004, T013-T018 | FR-007..FR-009, FR-041..FR-043, SC-003, SC-004 |
| US3 | T019-T024 | FR-010..FR-016, FR-031, FR-034, SC-005, SC-006, SC-007 |
| US4 | T025-T029 | FR-017..FR-019, FR-033, FR-044, SC-007 |
| US5 | T030-T033 | FR-020..FR-022, SC-008 |
| US6 | T034-T039 | FR-023..FR-027, SC-009 |
| US7 | T040-T044 | FR-028..FR-030, SC-010 |
| cross | T001, T002, T002a, T045-T048 | FR-001, FR-002, FR-032..FR-036, SEC-001..003, SC-011, SC-012, quality bar |

**MVP = Phases 1-5 (US1+US2+US3)** -- independently implementable and reviewable without US4-US7.
