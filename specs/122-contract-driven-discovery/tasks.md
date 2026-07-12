# Tasks: Contract-Driven Discovery-to-Decision Flow

**Input**: Design documents from `specs/122-contract-driven-discovery/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED -- the spec's success criteria (SC-001/003/004/005/007/009) require
seeded conformance fixtures, and the repo's workflow is TDD (write failing tests first).
Because most enforcement is REUSED (existing DS1-DS5 + gate), most "tests" here are
fixture/oracle tests over the new survey artifact shape and the bounded-flow stops,
plus DSN-redaction monkeypatch tests for the mandatory DB enumeration helper.

**Organization**: Grouped by user story in spec priority order. **MVP = US1** (the
Layer-A portfolio survey); no deep profiling occurs at MVP. Implementation is
deliberately anti-code: the load-bearing work is authoring the survey template + skill
and REUSING the existing store/profiler/gate. The four anti-scope-creep gates from the
spec review (no 2nd profiler, no new status/vocab/authority-row, no gate repair, no
flow-contract change) are enforced by boundary tests, not by trust.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 portfolio survey | US2 domain proposal | US3 scope proposal | US4 interview handoff | US5 bounded-flow routing

## Path notes

- Python package is `src/seshat/` (post-rename); console scripts `seshat`/`retail`.
- New agent verb lives under `.claude/skills/`; router block in `.seshat/kit-source.yaml`.
- Layer-A enumeration is agent-issued read-only metadata (R-2a); a thin helper is
  OPTIONAL and, if added, MUST mirror the validate/profile DSN-redaction path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new surfaces this feature introduces and the fixture root.

- [X] T001 [P] Create fixture root `tests/fixtures/portfolio-survey/` with a `README.md` naming the seeded scenario classes required by SC-001/004/005 (a >=5-table DB-schema metadata fixture; a file-folder fixture; a partial/unreachable-metadata fixture; a PII-hint fixture) -- synthetic data only, no worked-example specifics (Principle VII)

> **NOTE**: The `docs/capabilities/capabilities.yaml` producer row is deliberately NOT added here. The capability-inventory truthfulness oracle fails closed on a declared-but-unbuilt producer (a row with no `SKILL.md` reads as spec-only). The row is added in US1 (T011a) only AFTER the skill + router entry exist, so the inventory never claims a producer that is not yet built.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one new artifact shape (the Layer-A survey template) and its shape
oracle, which every later story reads. No new Decision Store, profiler, or gate rule.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Author blank template `templates/portfolio-survey.md` -- the Layer-A metadata survey shape from `specs/122-contract-driven-discovery/contracts/portfolio-survey.schema.md`: per-source header (source_kind, source_identity WITHOUT credentials, reachable_tables_total, coverage_limits, candidate domain/scope evidence) and per-table rows (inventory, declared types, declared PK/FK, candidate grain from metadata, approx row count, date/PII HINTS, structural-role hint, unavailable+reason). Placeholders only; ASCII arrows; UTF-8 no BOM
- [X] T004 Write failing shape-oracle tests in `tests/unit/test_portfolio_survey.py`: a valid survey fixture parses; and the fail-closed invariants FAIL a survey that contains ANY value-backed measurement (measured uniqueness/missingness/date-coverage, raw or masked samples, returns-column population) OR any raw suspected-PII value / credential / DSN / connection string OR a silently-omitted reachable table (FR-009/011/014)
- [X] T005 Implement the survey shape-oracle used by T004 as a test helper/parser (NOT a new `retail check` rule -- research R-4 defers a static rule until a filled target exists) in `tests/unit/test_portfolio_survey.py` (or a small `tests/support/` helper), greening T004

**Checkpoint**: The survey template exists and its metadata-only / no-PII / no-omission invariants are oracle-enforced.

---

## Phase 3: User Story 1 - Produce a Reviewable Multi-Table Portfolio Survey (Priority: P1) 🎯 MVP

**Goal**: An agent-conducted Layer-A survey that inventories EVERY reachable table's
metadata (no value-backed measurement, no agent-chosen cap) and writes one committed
survey artifact, stopping truthfully when metadata is unreachable.

**Independent Test**: Point the skill at a >=5-table fixture (DB-schema metadata and a
file folder); verify one committed survey covers every reachable table from metadata,
records hints (not rulings), states unreachable metadata per-table with its reason, and
contains no value-backed measurement and no raw PII/credentials/DSN.

### Tests for User Story 1 (write first, must fail)

- [X] T006 [P] [US1] Seed fixtures under `tests/fixtures/portfolio-survey/`: a DB-schema metadata fixture (>=5 tables: declared PKs/FKs, mixed types, a date column, a PII-suspect column name, one table with unreachable row-count) and a file-folder fixture (CSV + Excel), plus the expected committed survey for each (golden files)
- [X] T007 [US1] Write failing tests in `tests/unit/test_portfolio_survey.py` asserting the **golden survey fixtures** (T006) satisfy the T005 oracle (every reachable table present; hints not rulings; unreachable metadata stated with reason; no value-backed measurement; no raw PII/DSN). The golden files are the skill's REFERENCE target shape -- this is a recorded-artifact oracle over the fixtures, NOT a mechanical assertion that a function produced them (the survey is agent-conducted; mirrors 121's "rules verify the recorded outcome, not the conversation")
- [X] T008 [US1] Write failing monkeypatch tests for the mandatory DB enumeration helper's three DSN-leak failure modes (config-resolve, driver gate, `dialect.redact`) in `tests/unit/test_portfolio_enumerate.py` -- no real DB; a config/driver/connection error MUST surface only a **redacted** message, never leak `DATABASE_URL`/`ANALYTICS_DB_*` (FR-011, Codex #5, db-cli-must-mirror-validate-redact). (Unconditional: the DB branch always routes through the helper -- there is no inline-query alternative for DB.)

### Implementation for User Story 1

- [X] T009 [US1] Author `.claude/skills/retail-discover-portfolio/SKILL.md` (working name): the agent-conducted Layer-A survey procedure -- enumerate every reachable table by **calling the mandatory `enumerate_tables` helper for a DB source** (the agent MUST NOT issue its own raw `information_schema.tables` query and MUST NOT catch a raw connection/driver/config exception -- the helper returns rows or a redacted error, FR-011/Codex #5) or by an inline directory listing for a file folder; read each table's `information_schema.columns` metadata; author the survey from `templates/portfolio-survey.md`; NEVER sample values, NEVER measure, NEVER write raw PII/DSN; state unreachable metadata as `[PENDING LIVE PROFILE]`/`needs_sample`; STOP if no source metadata is readable (name the enabling step). Cite the two-layer boundary and the no-2nd-profiler rule explicitly
- [X] T010 [US1] Implement the mandatory read-only `enumerate_tables(schema)` in `src/seshat/` (the DB branch's only path) reusing the existing `QueryRunner`/`Dialect` seam for `information_schema.tables`, mirroring `run_validate`'s config-resolve + `_ensure_driver` gate + `dialect.redact(exc, config)` so a config/driver/connection failure returns a **redacted** error and never leaks the DSN; green T008. (No inline-DB-query alternative exists -- Codex #5.)
- [X] T011 [US1] Add the `retail-discover-portfolio` verb entry to `.seshat/kit-source.yaml` and REGENERATE the router block (do not hand-append); verify the generated `CLAUDE.md`/router banner echoes the new verb
- [X] T011a [US1] NOW that the skill + router entry exist, add the discovery/domain/scope producer row to `docs/capabilities/capabilities.yaml` (id, summary, the `SKILL.md` reference, and gap fields), and confirm the capability-inventory truthfulness oracle passes -- the row is truthful because the producer is built (deferred from Setup so the inventory never claims an unbuilt producer)
- [X] T012 [US1] Confirm the authored skill's SKILL.md cites the golden surveys (T006) as its target shape and that the golden fixtures pass the T005 oracle (recorded-artifact verification, not a mechanical "function produced X" assertion); run the T004/T005 oracle over the fixtures; confirm `retail check` stays exit 0 on the repo

**Checkpoint**: US1 (MVP) is fully functional -- a legible, metadata-only portfolio survey of an unfamiliar source, independently testable. No deep profiling occurred.

---

## Phase 4: User Story 2 - Propose a Retail Domain from Discovery Evidence (Priority: P2)

**Goal**: From the committed survey, the agent records a NON-CRITICAL `proposed` domain
decision in the EXISTING Decision Store, citing survey facts; never self-confirms.

**Independent Test**: Run the domain guess against a committed survey fixture; verify a
`proposed` record (with `confidence`, `proposed_by`=agent) validates under the EXISTING
DS1-DS5, sits in NO `blocking_decision_categories`, and is never given a critical type
or a new authority row; an ambiguous source yields alternatives/"undetermined".

### Tests for User Story 2 (write first, must fail)

- [X] T013 [P] [US2] Seed fixtures under `tests/fixtures/portfolio-survey/domain/`: a committed survey + expected `proposed` domain record (non-critical free-form `decision_type`, e.g. `domain_classification`), and an ambiguous-survey case expecting recorded alternatives or "undetermined"
- [X] T014 [US2] Write failing tests in `tests/unit/test_discovery_flow_stops.py` (domain section): the domain record validates under the EXISTING DS1-DS5 (reuse the shipped rules, add NO new rule), is non-critical, sits in no `blocking_decision_categories`, is `proposed` with `confidence`, `proposed_by`=agent; and a boundary assertion that `contracts/knowledge/approval-authority.yaml` gains NO row. **Grounding-fields assertion (Codex #4, FR-015)**: DS1-DS5 do NOT runtime-enforce the schema's required grounding fields for a `proposed` record (DS1 checks id/status/confidence/scope; DS5 only inspects `approved` records; the loader is shallow-parse), so add a FEATURE-LEVEL fixture assertion that the domain proposal actually carries non-empty `evidence` (cited survey facts), `proposed_by`, and `proposed_at` -- a record missing them must FAIL this feature test even though it passes `retail check`

### Implementation for User Story 2

- [X] T015 [US2] Extend `.claude/skills/retail-discover-portfolio/SKILL.md` with the domain-proposal step: record a non-critical `proposed` domain decision in `.seshat/semantic-decisions.yaml` citing survey evidence; record ambiguity explicitly; NEVER self-confirm, NEVER add a critical type or authority-map row; a named human confirms via the existing low-risk batch path (recorded status follows 121's convention -- do NOT re-pin)
- [X] T016 [US2] Add the `domain_guess`-stage local stop **in the skill's own logic** (NOT via the inherited gate -- the gate returns `pass` on an absent/empty store for this empty-`blocking_decision_categories` stage, FR-025): if no committed survey exists, the skill checks its own precondition and halts with a truthful local stop naming the missing survey. Green the T014 domain tests; `retail check` stays exit 0

**Checkpoint**: US1 + US2 both work; the domain proposal is a governed, non-critical store record validated by the existing gate.

---

## Phase 5: User Story 3 - Propose a Bounded First-Delivery Scope (Priority: P2)

**Goal**: A NON-CRITICAL `proposed` scope decision with deterministic, evidence-based
bounding (no numeric score/threshold/rank); Layer-B profiling is delegated to the
existing per-table profiler for in-scope tables only.

**Independent Test**: Run the scope proposal against a committed survey + domain record;
verify candidate tables/questions/KPI-names/exclusions/dependencies recorded as
`proposed`; an explicit user scope limit honored; cross-boundary evidence -> narrower
options or `needs_user_input`; partial acceptance -> bounded superseding record (original
-> superseded); and that each in-scope table is handed to `retail-onboard-table` (Layer B)
rather than deep-profiled in the survey.

### Tests for User Story 3 (write first, must fail)

- [X] T017 [P] [US3] Seed fixtures under `tests/fixtures/portfolio-survey/scope/`: a coherent-scope case, a cross-boundary case (multiple processes/grains) expecting `needs_user_input` or narrower options, an explicit-user-limit case, and a partial-acceptance case expecting a bounded superseding record with the original `superseded`
- [X] T018 [US3] Write failing tests in `tests/unit/test_discovery_flow_stops.py` (scope section): the scope record is non-critical `proposed`, sits in no `blocking_decision_categories`, carries NO numeric score/threshold/rank; deterministic bounding behaves per FR-018; partial acceptance yields a bounded superseding record and marks the original `superseded` so DS4 sees no two active records on one scope key (FR-019B); a boundary test that the SURVEY never gains value-backed per-table measurement (Layer B stays in `retail-onboard-table`, FR-013); and a **grounding-fields assertion (Codex #4, FR-017)** that the scope proposal carries non-empty `evidence` (cited survey + domain facts), `proposed_by`, and `proposed_at` -- since DS1-DS5 do not runtime-enforce those on a `proposed` record

### Implementation for User Story 3

- [X] T019 [US3] Extend the skill with the scope-proposal step: record a non-critical `proposed` scope decision citing survey + domain evidence; deterministic bounding (honor explicit limit; else one coherent process / one primary fact grain / KPIs sharing a model boundary); describe categorically only (coherent/cross-boundary/unresolved/needs-user-input -- prose, not a stored scale); no numeric score/threshold/rank; partial acceptance -> bounded superseding proposal (original -> superseded)
- [X] T020 [US3] Add the scope->Layer-B delegation step (FR-009B): for each in-scope table, hand it to the EXISTING `retail-onboard-table` / Source Ready profiler (do NOT profile in the survey, do NOT author `mappings/<table>/source-profile.md`); add the `scope_proposal`-stage local stop **in the skill's own logic** (NOT via the inherited gate, FR-025): if no domain proposal exists, halt naming the missing domain-guess decision; green T018; `retail check` stays exit 0

**Checkpoint**: US1 + US2 + US3 work; scope is deterministic and Layer-B is delegated, not duplicated.

---

## Phase 6: User Story 4 - Hand Grounded Discovery into the Business Knowledge Interview (Priority: P3)

**Goal**: A thin handoff that satisfies the interview's declared `required_inputs`,
loading the existing store first; this feature hands off, the interview (spec 121) runs.

**Independent Test**: With a committed Stage-1 per-table (Layer-B) profile of the
in-scope tables, a proposed scope, and a seeded store, invoke the handoff; verify the
interview receives exactly its declared inputs (the "committed discovery profile" is the
per-table Layer-B profile, NOT the Layer-A survey), existing decisions are presented for
confirmation/supersession (never overwritten), and this feature records no interview
outcomes / defines no KPI meaning / grants no approval.

### Tests for User Story 4 (write first, must fail)

- [X] T021 [P] [US4] Seed a handoff fixture: a committed per-table Layer-B profile + a proposed scope + a seeded store with an existing record; expected handoff presents the store's records for confirmation/supersession and satisfies the interview contract's three `required_inputs`
- [X] T022 [US4] Write failing tests in `tests/unit/test_discovery_flow_stops.py` (handoff section): the handoff satisfies exactly `contracts/interview/business-knowledge-interview.yaml`'s `required_inputs`; the "committed discovery profile" is the per-table Layer-B profile (not the survey); existing records are presented, none overwritten; the feature records no interview outcome and grants no approval

### Implementation for User Story 4

- [X] T023 [US4] Extend `.claude/skills/retail-discover-portfolio/SKILL.md` with the interview-handoff step: load the existing Decision Store first; present existing decisions for confirmation/supersession (never overwrite); pass the in-scope tables' Stage-1 per-table (Layer-B) profiles + the proposed scope into the existing Business Knowledge Interview; route KPI-meaning questions to the Retail KPI knowledge boundary; do NOT re-implement the interview; green T022

**Checkpoint**: US1-US4 work; the bounded flow reaches the interview boundary cleanly.

---

## Phase 7: User Story 5 - Route the Next Allowed Action Within the Bounded Discovery Flow (Priority: P3)

**Goal**: Determine the ONE next allowed action WITHIN the bounded flow from the existing
contracts and committed state; truthful local stops; NO global Decision Gate repair.

**Independent Test**: Seed committed states along the bounded flow (no survey; survey
only; survey+domain; survey+domain+scope) and verify exactly one next action within the
flow per state; a missing local input yields a truthful local stop naming what unblocks
it; a request to cross the handoff boundary stops truthfully; and NO change is made to
the flow contracts or the general Decision Gate.

### Tests for User Story 5 (write first, must fail)

- [X] T024 [P] [US5] Seed bounded-flow state fixtures under `tests/fixtures/portfolio-survey/flow/` (the four committed states above + a cross-the-handoff-boundary request) with expected next-action / local-stop outputs
- [X] T025 [US5] Write failing tests in `tests/unit/test_discovery_flow_stops.py` (routing section) as a **recorded-state oracle**: for each committed-state fixture (T024), assert the expected next-action / local-stop output is the ONE correct answer derivable from the existing stage contracts + that committed state. CRITICAL positive assertion (FR-025, the Codex absent-store finding): include a **seeded absent/empty-store case** and assert the feature's OWN local stop fires and names the missing store/survey -- AND assert that `compute_verdict` for these empty-`blocking_decision_categories` stages returns `pass` (not `blocked`) on that same absent/empty store, proving the local stop is the feature's own logic and NOT inherited from the gate. Also: crossing the handoff boundary -> truthful stop; boundary assertions that `contracts/knowledge/database-to-pbip-flow.yaml` is byte-UNCHANGED (FR-026) and no new engine/state file is introduced. The routing is agent-conducted (the agent reads the contracts + committed state); this oracle verifies the derivable answer per state, NOT a mechanical function call

### Implementation for User Story 5

- [X] T026 [US5] Document the bounded-flow routing in the skill (`.claude/skills/retail-discover-portfolio/SKILL.md`): the agent computes the one next allowed action within `portfolio discovery -> domain -> scope -> selected-table onboarding -> interview handoff -> stop` by READING the existing stage contracts and committed state -- explicitly agent-conducted, NO new engine, NO new state file, NO projection module. Every local stop names the concrete local missing artifact/decision and its unblock; the flow stops at the handoff boundary. Confirm each T024 recorded-state fixture's expected output matches what the documented procedure derives; `retail check` stays exit 0

**Checkpoint**: All five stories work; the flow is governed by truthful bounded-flow routing with no global-gate expansion.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Docs, glossary, and the final whole-feature validation.

- [X] T027 [P] Update `docs/glossary.md` with: Layer A (portfolio metadata survey), Layer B (deep per-table profile), portfolio survey, and the domain/scope non-critical-proposal lifecycle terms
- [X] T028 [P] Update `docs/knowledge-map.md` with the portfolio-survey discovery route note (if a route is cited by the skill), consistent with the existing readiness route
- [X] T029 Run `specs/122-contract-driven-discovery/quickstart.md` end-to-end against the fixtures; confirm SC-001/002/003/004/005/006/007/008/009 observably hold (SC-002 = the US1 survey + in-scope US4 Layer-B profiles support an interview with fewer question rounds than the in-scope column count; SC-006 = finalized decisions preserved, any change via supersession only -- the T018 partial-acceptance logic); confirm the four anti-scope-creep boundary tests pass (no 2nd profiler; no new status/vocab/authority-row; no gate repair; no flow-contract change)
- [X] T030 Final `retail check` exit 0 on the repo; `ruff format --check src tests` + `ruff check src tests` + `pytest -m unit -x -q` green; confirm no forbidden change (no new `retail check` rule at MVP, no `mappings/<table>/source-profile.md` authored by this feature, no top-level contract edited); and confirm the inherited scale-out invariant holds (FR-030): the discovery flow never selects a scale-out/big-data route -- it records scale evidence into the survey/scope but never chooses the route, which stays with the existing `silver_gold_model_planning` boundary (else python)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories (the survey template + oracle are consumed by every story).
- **User Stories (Phase 3+)**: All depend on Foundational. US1 is the MVP and must complete first (US2-US5 all read the survey US1 produces).
- **Polish (Phase 8)**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1, MVP)**: After Foundational. No dependency on other stories.
- **US2 (P2)**: After US1 (reads the committed survey).
- **US3 (P2)**: After US2 (reads the domain proposal; the `scope_proposal` contract requires it).
- **US4 (P3)**: After US3 (needs a proposed scope + in-scope Layer-B profiles).
- **US5 (P3)**: After US1-US4 conceptually (it projects over all of them), but its routing/stop logic can be built incrementally alongside each story's local stop; the dedicated routing tests (T024-T026) come last.

### Within Each User Story

- Tests written and FAILING before implementation (TDD).
- Fixtures/golden files before the skill step that must match them.
- Reuse existing rules/profiler/gate; add NO new `retail check` rule.
- Story complete and `retail check` exit 0 before moving to the next.

### Parallel Opportunities

- Setup T001/T002 in parallel.
- Foundational T003 (template) parallel with fixture seeding; T004/T005 (oracle) follow T003.
- Within a story, the `[P]` fixture-seeding tasks run parallel to authoring the prior story's docs.
- Polish T027/T028 in parallel.

---

## Parallel Example: User Story 1

```bash
# Seed fixtures and (optional) redaction tests together:
Task: "Seed DB-schema + file-folder survey fixtures + golden surveys in tests/fixtures/portfolio-survey/"   # T006
Task: "IF helper: DSN-redaction monkeypatch tests in tests/unit/test_portfolio_enumerate.py"                # T008
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup -> Phase 2 Foundational (survey template + oracle).
2. Phase 3 US1: author the skill's Layer-A survey step; green the golden/oracle tests.
3. **STOP and VALIDATE**: a metadata-only portfolio survey of a >=5-table source, no deep profiling, no raw PII/DSN. This is the shippable MVP.

### Incremental Delivery

1. Setup + Foundational -> survey shape ready.
2. US1 -> the portfolio survey (MVP).
3. US2 -> domain proposal (non-critical store record).
4. US3 -> scope proposal + Layer-B delegation.
5. US4 -> interview handoff.
6. US5 -> bounded-flow routing/stops.
Each story adds value without breaking the previous, and each keeps `retail check` exit 0.

### Anti-scope-creep watch (enforced by boundary tests, not trust)

- No second per-table profiler (T018, T020, T030).
- No new Decision Store status / `decision_type` enum member / authority-map row (T014, T018).
- No global Decision Gate repair; no flow-contract change (T025, T030).
- Batch resting-status NOT re-pinned -- follows 121's convention (T014/T018 assert the record is `proposed` at authoring and non-blocking; they do NOT assert a forced `approved`).

---

## Notes

- [P] = different files, no dependencies. [Story] label maps each task to its user story.
- This feature is deliberately anti-code: the only genuinely new code is the skill, the
  survey template, and a thin read-only DB enumeration helper (mandatory for the DB
  branch, so DSN redaction has one tested path). Everything else is reuse.
- Tests fail before implementation; commit after each task or logical group.
- Ratify seam is a human action ahead of implementation -- these tasks are the plan for
  implementation, not authorization to merge.
