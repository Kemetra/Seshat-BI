# Tasks: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Input**: Design documents from `specs/121-business-knowledge-interview/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED -- the spec's success criteria (SC-002/SC-003/SC-008) require seeded
conformance fixtures, and the repo's workflow is TDD (write failing tests first).

**Organization**: Grouped by user story. Implementation phase order is
dependency-driven and differs from spec priority in one place: US5 (P3, gate verdicts)
is implemented before US3 (P2, review artifact) because FR-025 embeds the gate verdict
inside the review artifact -- building US3 first would mean stubbing the verdict and
reworking it. See `implementation-graph.md` for the full task DAG, serialized
hotspots, and parallel waves.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 interview | US2 decision store | US3 review artifact | US4 knowledge contracts | US5 gate verdicts

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the two new directory surfaces this feature introduces.

- [ ] T001 Create `contracts/README.md` defining the top-level product-contracts directory: what a product contract is, contracts-vs-templates distinction per research R-4, and the fail-closed reading rule
- [ ] T002 [P] Create fixture roots `tests/fixtures/decision-store/valid/` and `tests/fixtures/decision-store/invalid/` with a `README.md` naming the seeded scenario classes required by SC-002 and SC-003

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Store shapes, authority mapping, and the fail-closed loader every story consumes.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 [P] Author blank decision-store template `templates/semantic-decisions.yaml` (grain, PK, relationship, PII, exclusion, blueprint, publish records) matching `specs/121-business-knowledge-interview/contracts/decision-record.schema.json`, placeholders only (Principle VII)
- [ ] T004 [P] Author blank template `templates/kpi-contracts.yaml` (KPI-meaning decisions + VAT/returns/discount/cost policy rulings) matching the same schema
- [ ] T005 [P] Author blank template `templates/cleaning-rules.yaml` (missing-value + cleaning rulings that start from RC1-RC16 and cite the triggering data fact on deviation) matching the same schema
- [ ] T006 [P] Author `contracts/knowledge/approval-authority.yaml` mapping each of the ten critical decision types to its eligible authority class(es) using snake_case class tokens, verifying the vocabulary against `docs/glossary.md` and the `docs/readiness/` stage docs (research R-7)
- [ ] T007 Write failing unit tests for the fail-closed store loader in `tests/unit/test_decision_store.py`: parse the three store files with the `{decisions, batches}` layout, unique well-formed ids, status/type/confidence vocabulary, scope non-empty, unknown status or malformed record or unknown top-level key treated as unresolved -- never skipped
- [ ] T008 Implement the decision-record + batch-set models and the fail-closed store loader (`{decisions, batches}` file layout) in `src/retail/decision_store.py` to green T007 (stdlib + pyyaml only; no new dependencies)

**Checkpoint**: Store shapes exist and load fail-closed -- user stories can begin.

---

## Phase 3: User Story 2 - Record Decisions in a Project Decision Store (Priority: P1) 🎯 MVP part 1

**Goal**: The nine-status lifecycle, approval metadata validity, batch integrity, and
immutability/supersession -- enforced by the DS1-DS4 static rules inside `retail check`.

**Independent Test**: Seed stores covering every status and every critical decision
type; verify round-trip, that every invalid-record class fails `retail check` with a
non-zero exit, and that a `high`-confidence proposal is never consumable as approved.

### Tests for User Story 2 (write first, must fail)

- [ ] T009 [P] [US2] Seed fixtures under `tests/fixtures/decision-store/`: one valid store trio (every status, every critical type, a valid batch with an exclusion, a supersession pair) and one invalid store per class -- incomplete approval, ineligible authority class, agent-identity approver, critical type inside a batch, unresolved supersede reference, two active records conflicting on the same scope, in-place-edited approved record, unknown status, raw-PII-shaped value
- [ ] T010 [US2] Write failing rule tests in `tests/unit/test_decision_store_rules.py` asserting DS1-DS4 verdicts over the T009 fixtures (severity per research R-1: provable defects ERROR, heuristic guards WARNING; fail-closed defaults regardless of severity)

### Implementation for User Story 2

- [ ] T011 [US2] Implement DS1 (store layout/schema/status/id/scope validity + committed-value PII-shape guard) and DS2 (approval-metadata completeness incl. evidence_identity, RS1 name+class shape, authority-class eligibility via `contracts/knowledge/approval-authority.yaml`, evidence resolvability, reviewed_scope coverage) in `src/retail/rules/decision_store.py`, registered in the rule registry; confirm the R-1 severity classes against the RS1 precedent
- [ ] T012 [US2] Implement DS3 (no critical types in batches; exclusions recorded; batch confirmation valid) and DS4 (approved-record immutability via supersession-only; supersedes/superseded_by resolve both ways; no conflicting active records on the same scope) in `src/retail/rules/decision_store.py`
- [ ] T013 [US2] Update the rule-registry snapshot test, regenerate `docs/rules/rules-manifest.json` via `retail manifest`, and confirm `retail check` stays exit 0 on the repo itself

**Checkpoint**: The Decision Store is a governed, gate-enforced artifact.

---

## Phase 4: User Story 1 - Answer a Focused Business Interview (Priority: P1) 🎯 MVP part 2

**Goal**: The agent-conducted interview verb: discovery-grounded questions, hybrid
batch/critical grouping, masked samples, pause/resume, every outcome recorded.

**Independent Test**: Walk the interview against a worked-example discovery profile
per `specs/121-business-knowledge-interview/contracts/interview-protocol.md`: low-risk
items arrive as one batch (item-level exclusion works), critical items arrive
individually with masked evidence, early exit leaves only open statuses, nothing is
auto-approved, and re-running presents existing decisions for confirmation.

### Implementation for User Story 1

- [ ] T014 [P] [US1] Author product contract `contracts/interview/business-knowledge-interview.yaml` (validating against `specs/121-business-knowledge-interview/contracts/knowledge-contract.schema.json`): allowed routes, required inputs (committed discovery profile), stop rules, hybrid grouping, masking default, pause/resume and re-run semantics, recording obligations, NFR-003 question bound
- [ ] T015 [US1] Create the gated interview verb `.claude/skills/business-knowledge-interview/SKILL.md`: agent-conducted flow per the interview contract; consumes the Stage-1 discovery profile; confirm-or-supersede on re-run; never self-grants approval; never emits numeric confidence; exits by regenerating the review artifact and reporting the gate verdict
- [ ] T016 [US1] Register the verb in `.seshat/kit-source.yaml` and regenerate the kit-router block in `CLAUDE.md` (do not hand-edit the generated block)
- [ ] T017 [P] [US1] Extend the C2 secret/PII scan posture to the three store paths (any rule-side change lands in the existing C2 rule module under `src/retail/rules/`) and add masked-sample shape-guard tests in `tests/unit/test_decision_store.py` (no raw suspected-PII values in any committed store file)

**Checkpoint**: MVP complete -- interview conducts, records, and is gate-enforced.

---

## Phase 5: User Story 4 - Route Stages Through Knowledge Contracts (Priority: P2)

**Goal**: Per-stage Knowledge Contracts for the 11 Database-to-PBIP flow stages, with
routing boundaries enforced as data.

**Independent Test**: Every stage entry validates against the schema; boundary probes
route correctly -- a KPI-meaning question in the DAX stage routes to Retail KPI
(AC-008), Big-data requires recorded scale evidence else Python (AC-009), and no
entry grants an execution adapter meaning/mapping/metric/semantic/approval authority.

### Implementation for User Story 4

- [ ] T018 [P] [US4] Author `contracts/knowledge/database-to-pbip-flow.yaml` with all 11 stage entries (discovery -> evidence_pack) per `specs/121-business-knowledge-interview/contracts/knowledge-contract.schema.json`: allowed routes referencing existing knowledge-map routes only, required inputs/outputs, stop rules naming what unblocks them, blocking decision categories, handoffs, non-goals, evidence requirements
- [ ] T019 [P] [US4] Author `contracts/report/dashboard-blueprint.yaml`: the blueprint-approval stage contract gating the PBIP prototype (Blueprint -> Compiler -> Validation stated as future; no visual implementation, FR-036 to FR-038)
- [ ] T020 [US4] Write contract conformance tests in `tests/unit/test_knowledge_contracts.py`: schema validity of every entry; the three boundary probes above; unknown-route and missing-stop-rule entries fail closed
- [ ] T021 [US4] Add the new routes to `docs/knowledge-map.md` (business knowledge interview / decision store / decision gate rows + routing-boundary bullets) without modifying any knowledge-base content (FR-031)

**Checkpoint**: Stage authority is declared as data and conformance-tested.

---

## Phase 6: User Story 5 - Enforce Blocking Gates with Clear Verdicts (Priority: P3)

**Goal**: Deterministic pass/warn/blocked verdicts projected from the store into the
readiness spine, plus the DS5 consistency rule.

**Independent Test**: Every SC-003 seeded scenario (pending grain / PII / KPI meaning /
policy, unapproved blueprint, missing evidence, conflicting records, malformed store,
stale critical vs non-critical evidence) produces blocked for exactly the stages in
the blocking matrix and pass once resolved -- zero false passes.

**Note**: Implemented before US3 (P2) because the review artifact embeds the verdict
(FR-025); depends on US2 (loader/rules) and US4 (blocking categories per stage).

### Tests for User Story 5 (write first, must fail)

- [ ] T022 [US5] Write failing verdict tests in `tests/unit/test_decision_gate.py` covering every SC-003 scenario plus the staleness split from clarify Q1, asserting named blocking decisions on blocked and cited evidence on pass

### Implementation for User Story 5

- [ ] T023 [US5] Implement the pass/warn/blocked projection in `src/retail/decision_gate.py` per `specs/121-business-knowledge-interview/contracts/gate-verdicts.md`: deterministic recompute from store + cited evidence, blocking categories read from `contracts/knowledge/database-to-pbip-flow.yaml`, stale-evidence detection via each approval's recorded `evidence_identity` (research R-10), fail-closed on any malformed input
- [ ] T024 [US5] Implement the readiness-spine projection in `src/retail/decision_gate.py`: contribute `blocking_reasons[]`/`warning` entries per the stage mapping (Source/Mapping, Semantic Model, Dashboard, Publish) -- the spine remains the sole stage-state authority (FR-001, R-6)
- [ ] T025 [US5] Implement DS5 (verdict consistency: no pass without evidence; blocked names concrete decisions; recomputation matches recorded blocking reasons) in `src/retail/rules/decision_store.py`; extend `tests/unit/test_decision_store_rules.py`, the registry snapshot, and regenerate `docs/rules/rules-manifest.json`

**Checkpoint**: Gates are computable, fail-closed, and spine-integrated.

---

## Phase 7: User Story 3 - Review Interview Outcomes in One Readable Artifact (Priority: P2)

**Goal**: The deterministic, regenerable human-readable review artifact.

**Independent Test**: Generate from a store seeded with decisions in every status; all
eleven FR-025 sections present and accurate; masked values only; regeneration is
byte-identical (SC-008); a reviewer can answer "what blocks and why" from the artifact
alone (SC-004).

### Tests for User Story 3 (write first, must fail)

- [ ] T026 [P] [US3] Author blank template `templates/business-interview-review.md` with the eleven FR-025 sections (approved / pending / blocking / rejected / deferred / PII handling / KPI-impacting / grain & relationships / cleaning & missing-value / next questions / gate verdict)
- [ ] T027 [US3] Write failing determinism + completeness tests in `tests/unit/test_interview_review.py`: same store => byte-identical output; every section present; blocking entries name id + unblocking question; no raw suspected-PII values

### Implementation for User Story 3

- [ ] T028 [US3] Implement the deterministic generator (store -> `evidence/business-interview-review.md` in the workspace) in `src/retail/interview_review.py`, using `src/retail/decision_gate.py` for the gate-verdict section; stable ordering for diffability (NFR-001/002); confirm the workspace evidence-directory convention against the spec-112 evidence-pack packaging before finalizing the output path

**Checkpoint**: All five stories functional and independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T029 [P] Add the decision statuses, gate verdicts, DS rule family, and critical decision types to `docs/glossary.md`; confirm no synonym for an existing term is introduced (NFR-005)
- [ ] T030 [P] Walk `specs/121-business-knowledge-interview/quickstart.md` end-to-end against a worked example under `docs/worked-examples/` and fix any drift found
- [ ] T031 Run the full gate set and confirm green: pytest suite, `retail check` exit 0 on the repo, rule-manifest snapshot, UTF-8-without-BOM and <= 200-char repo-relative path check over all new files (Principle IX)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)**: none.
- **Foundational (P2)**: after Setup; **blocks all stories**. Within it: T007 -> T008; T003-T006 parallel.
- **US2 (P3)**: after Foundational. T009 -> T010 -> T011 -> T012 -> T013 (T011/T012 share `src/retail/rules/decision_store.py` -- serialized).
- **US1 (P4)**: after Foundational; approval-validity behavior depends on US2 (DS2). T014 may start right after Foundational; T015 -> T016; T017 after T008 (shares `tests/unit/test_decision_store.py` with T007 -- serialized).
- **US4 (P5)**: after Foundational only -- T018/T019 are pure data files and may run in parallel with US2/US1 work; T020 after T018+T019; T021 after T018.
- **US5 (P6)**: after US2 (loader + rules) and US4 (blocking categories). T022 -> T023 -> T024 -> T025 (T025 shares the rules file and manifest with T011/T012/T013 -- serialized after them).
- **US3 (P7)**: after US5 (verdict section, FR-025). T026 parallel; T027 -> T028.
- **Polish (P8)**: after all stories; T029/T030 parallel; T031 last.

### Story Dependency Graph (summary)

```text
Setup --> Foundational --> US2 --> US1  (MVP = US2 + US1)
                      \--> US4 -------\
                            US2 + US4 --> US5 --> US3 --> Polish
```

Full task-level DAG, serialized hotspots, and parallel waves:
[implementation-graph.md](./implementation-graph.md).

### Parallel Opportunities

- Wave after Setup: T003, T004, T005, T006 together.
- Wave after Foundational: T009 (US2 fixtures), T014 (US1 contract), T018, T019 (US4 contracts) together -- four different files, three different stories.
- T017 (US1) and T026 (US3 template) are data/test-file tasks parallel to their phase peers.
- Polish: T029 + T030 together.

---

## Parallel Example: after Foundational completes

```bash
# Four tasks, three stories, no shared files:
Task: "Seed decision-store fixtures in tests/fixtures/decision-store/"          # T009 [US2]
Task: "Author contracts/interview/business-knowledge-interview.yaml"            # T014 [US1]
Task: "Author contracts/knowledge/database-to-pbip-flow.yaml"                   # T018 [US4]
Task: "Author contracts/report/dashboard-blueprint.yaml"                        # T019 [US4]
```

---

## Implementation Strategy

### MVP First (US2 + US1)

1. Phases 1-2 (Setup + Foundational).
2. Phase 3 (US2): the store becomes a governed artifact -- **stop and validate** via the US2 independent test.
3. Phase 4 (US1): the interview verb lands -- **stop and validate** via the protocol walkthrough. This is the demonstrable MVP: interview -> recorded, gate-enforced decisions.

### Incremental Delivery

Each subsequent phase adds one independently testable increment: US4 (stage authority
as data) -> US5 (computable gates) -> US3 (owner-readable review) -> Polish. Stop at
any checkpoint; nothing later breaks an earlier story.

### Notes

- Verify test tasks FAIL before implementing their story.
- Commit after each task or logical group; `retail check` must stay exit 0 at every commit (Layer C hook).
- No new dependencies anywhere; static core stays stdlib-only on its import path.
