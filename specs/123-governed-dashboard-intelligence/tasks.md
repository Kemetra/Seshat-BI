# Tasks: Governed Dashboard Intelligence and PBIR Authoring

**Feature**: 123-governed-dashboard-intelligence | **Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: INCLUDED. This repo is TDD (Constitution Principle I — enforcement lives in checkers; memory: put the oracle ON the risk). Every new rule/gate/writer gets a test that sits on the real danger, not adjacent to it.

**Organization**: Tasks grouped by user story (priority order). Each user-story phase is an independently testable increment. **No checkbox is pre-marked** — nothing is implemented; a box is ticked only against a verified deliverable (memory: bulk checkbox-marking lies).

**Delivery gates (do NOT silently skip — memory: no silent caps):**
- **Sample-gated (D10)**: US7 increments 2 (KPI cards), 4 (slicers/nav), 5 (interactions), and column/bar in 3 are BLOCKED until the owner supplies a real Desktop-authored PBIR reference sample. Only page-shell (1) and lineChart (part of 3) are unblocked today.
- **ADR-gated (D11)**: any US7 *creation* writer is BLOCKED until a new PBIR-creation ADR is owner-ratified by name (Principle V human seam).
- **Approval seams (Principle V)**: `report_intent_approval` and `dashboard_blueprint_approval` are named-human actions; tasks author the machinery, never the approval.

---

## Phase 1: Setup

- [ ] T001 Confirm dev env: `python -m pytest -m unit -q` green on this branch baseline; `ruff format --check src tests` + `ruff check src tests` clean (memory: ruff format --check is the CI gate)
- [ ] T002 Reserve the next free `DL`-series rule id for the Report Intent shape rule by reading `docs/rules/rules-manifest.json` and `tests/unit/test_rules_wiring.py` `EXPECTED_RULE_IDS` (memory: regenerate manifest, don't hand-append); record the chosen id in `research.md` D5

## Phase 2: Foundational (blocking prerequisites for all stories)

- [ ] T003 [P] Add `report_intent_approval` to `CRITICAL_DECISION_TYPES` in `src/seshat/decision_store.py` (additive; FR-037)
- [ ] T004 [P] Add eligibility row `report_intent_approval: [report_owner]` to `contracts/knowledge/approval-authority.yaml`
- [ ] T005 Wire `report_intent_approval` into `blocking_decision_categories` of the `report_intent` AND `dashboard_blueprint` stages in `contracts/knowledge/database-to-pbip-flow.yaml` (realizes FR-032 through the existing gate)
- [ ] T006 [P] Test (RED→GREEN): assert an UNAPPROVED report intent yields `blocked` (not a false `pass`) at the decision gate — sits on the spec-122-review gap where empty-category stages returned `pass`; add to `tests/unit/test_decision_gate.py` with a fixture (memory: verifier must sit on the risk)
- [ ] T007 [P] Test: `report_intent_approval` validity — an agent identity is rejected, a `report_owner`-authored record passes `approval_is_valid`; add to `tests/unit/test_decision_store.py`

## Phase 3: User Story 1 — Capture Report Intent (P1, MVP)

**Goal**: a conversational request → committed, reviewable `report-intent.yaml` + a named-human `report_intent_approval`.
**Independent test**: run the interview against `retail_store_sales` (approved contracts + ready model); confirm the artifact captures FR-002 fields, every metric resolves to an approved contract, and a vague request is refused until audience/purpose/≥1 question resolve.

- [ ] T008 [P] [US1] Author `templates/report-intent.yaml` per data-model.md (FR-002 fields; metric name+store_ref+status_required triple; four-status readiness, no score; open_questions ledger)
- [ ] T009 [P] [US1] Author `contracts/report/report-intent.yaml` stage contract per `contracts/report-intent-stage.md` (mirrors `dashboard-blueprint.yaml`)
- [ ] T010 [P] [US1] Author `contracts/interview/report-intent-interview.yaml` per `contracts/report-intent-interview.md` (mirrors business-knowledge-interview; different required_inputs/focus)
- [ ] T011 [US1] Test (RED): DL5 shape-rule tests — required fields present, purpose in enum, ≥1 business question, valid owner shape, `pass` never with empty evidence; exclude `templates/` + test paths; assert `<no-finding>` on a well-formed instance (`tests/unit/test_report_intent_rule.py`)
- [ ] T012 [US1] Implement DL5 rule in `src/seshat/rules/report_intent.py` (mirror `design_review_evidence.py`/DL4: presence-only, grants no approval)
- [ ] T013 [US1] Wire DL5 across the 9 rule surfaces (regenerate `rules-manifest.json`, `severity-posture.json`, `EXPECTED_RULE_IDS` + count, glossary, wiring-meta/count tests) — verify `<no-finding>` on `main` BEFORE landing (memory: rule emits-on-main; retail check rule wiring recipe)
- [ ] T014 [US1] Author the `report-intent-interview` skill `.claude/skills/report-intent-interview/SKILL.md` (reuse load-existing-first, batch/critical grouping, PII mask, record+STOP; never self-grant)
- [ ] T015 [US1] Author a FILLED worked instance `mappings/retail_store_sales/design/report-intent.yaml` (exercises the template; Principle VII — example, not schema)
- [ ] T016 [US1] Integration test: metric-name resolution — an intent naming an unapproved metric records a gap + `readiness: blocked`, never invents the metric (FR-003/FR-004); `tests/integration/test_report_intent_journey.py`

**Checkpoint**: US1 delivers a reviewable Report Intent standalone (no downstream needed).

## Phase 4: User Story 2 — Coordinate existing dashboard capabilities (P1, MVP)

**Goal**: given approved intent + contracts + ready model, sequence the shipped capabilities to a reviewable design, failing closed.
**Independent test**: with a HAND-AUTHORED approved intent fixture, run the coordinator; confirm it picks one next action, invokes the shipped capability, re-evaluates, and STOPS with a named blocker on the first unmet precondition — never bypassing `semantic_model_ready: pass` nor self-granting `dashboard_ready: pass`.

- [ ] T017 [P] [US2] Create a hand-authored approved-intent fixture under `tests/fixtures/report_intent/` so US2 is testable without running US1
- [ ] T018 [US2] Author the coordinator skill `.claude/skills/dashboard-intelligence/SKILL.md`: inspect committed state → one next allowed action → invoke shipped capability (`retail dashboard-gaps` → `retail dashboard-planner` → `dashboard-design` → compose → dashboard-qa → human review) → re-evaluate; STOP rules per FR-009 (NO new CLI family — FR-011)
- [ ] T019 [US2] Integration test: fail-closed matrix (FR-033) — `semantic_model_ready`≠pass, missing contract, orphan visual, missing approval each yield a `blocked` result naming what/evidence/owner/unblock (FR-034); assert no self-grant of `dashboard_ready: pass`; `tests/integration/test_coordinator.py`
- [ ] T020 [US2] Integration test: happy path — coordinator produces blueprints + visual specs + `report-composition.yaml`, each visual traces to an approved contract + mapped field (SC-003 zero orphans); blueprint `business_question` traces to an intent question (FR-002a)

**Checkpoint**: US1 + US2 = MVP — reviewable dashboard design, stops at human review, no preview/PBIR (SC-012).

## Phase 5: User Story 6 — Approve & version the blueprint (P2, gates PBIR slices)

**Goal**: named-human `dashboard_blueprint_approval` via the shipped Decision Store; supersession on change.

- [ ] T021 [P] [US6] Test: extend RS1 to recognize `report_owner` (FR-022a) — a `report_owner`-authored `dashboard_blueprint_approval` is accepted by RS1; assert this is the ONLY class added (one-class, not a spine refactor); `tests/unit/test_readiness_status.py`
- [ ] T022 [US6] Add `report_owner` to `_AUTHORITY_CLASSES` in `src/seshat/rules/readiness_status.py` (single-class additive; FR-022a/FR-037)
- [ ] T023 [US6] Integration test: post-approval blueprint change marks prior approval `superseded` (DS4, with `superseded_by`), preserves history, requires renewed approval before compilation; unchanged blueprint needs no re-approval (FR-023/FR-024)

## Phase 6: User Story 4 — Blueprint preview (P2)

**Goal**: deterministic, data-free SVG preview of approved design.

- [ ] T024 [US4] Test (RED): `blueprint_preview` determinism — identical inputs → byte-identical SVG; every data value is a labeled PLACEHOLDER; no live-data/PBIR/DAX side effect (FR-015/FR-016/SC-006); `tests/unit/test_blueprint_preview.py`
- [ ] T025 [US4] Implement pure `src/seshat/blueprint_preview.py` (stdlib only; `sorted(...)` inputs; renders pages/sections/positions/types/titles/questions/contract-names/filters/narrative/nav/freshness/theme/grid/a11y/mobile/rtl intent)
- [ ] T026 [US4] Author skill/workflow `.claude/skills/powerbi-dashboard-design/workflows/blueprint-preview.md` invoking the function (Option-B: skill, no new CLI verb)
- [ ] T027 [US4] Test: a request for "realistic values" with no approved data source yields labeled placeholders, refuses to fabricate (FR-016/SEC-002)

## Phase 7: User Story 5 — Dashboard semantic audit (P2)

**Goal**: report-level categorical audit distinct from per-visual QA; no score.

- [ ] T028 [US5] Author skill/workflow `.claude/skills/powerbi-dashboard-design/workflows/dashboard-semantic-audit.md` — emits the spec-fixed closed enum (`covered/incomplete/missing/conflicting/warning/blocked/not_applicable_with_reason`); each finding cites committed evidence + names owner; reuses shipped tool OUTPUTS (FR-020), recomputes nothing
- [ ] T029 [US5] Test: audit emits categorical findings for the FR-018 checks against fixtures (intent question with no page → `missing`; diagnostic w/o drivers → `incomplete`; monitoring+diagnostic on one page → `conflicting`); assert NO numeric score anywhere (FR-020/FR-035); `tests/integration/test_semantic_audit.py`
- [ ] T030 [US5] Test: audit reuses the recorded `dashboard-planner` verdict + filled `a11y-rtl-readiness-checklist.md` (cites, never re-derives CT1 contrast)

## Phase 8: User Story 3 — Dashboard pattern library (P2)

**Goal**: generic, named patterns as design guidance; no KPI meaning.

- [ ] T031 [P] [US3] Author generic pattern docs under `docs/patterns/dashboard/` (Executive Performance, Sales Diagnosis, Branch Performance, Inventory Health, Product Performance, Promotion Effectiveness, Returns & Refunds, Customer Behavior, Data Quality Control Room, Action & Exceptions) — guidance only, no named KPIs
- [ ] T032 [US3] Author a pattern-recommendation skill entry that maps intent `purpose` → candidate pattern(s); presents multiple/partial fits for human choice (FR-014); unavailable requirements surface as gaps via `retail dashboard-gaps` (FR-013)
- [ ] T033 [US3] Test: a pattern assuming an unavailable metric/dimension surfaces a gap, never fabricates (FR-013)

## Phase 9: User Story 7 — PBIR compiler (P3, SAMPLE- + ADR-GATED)

**Goal**: compile supported elements from an approved blueprint into committed PBIR, bounded/deterministic/reversible.

- [ ] T034 [US7] **HUMAN SEAM (D11)**: draft the PBIR-creation ADR under `docs/decisions/00NN-pbir-creation-*.md` (per-increment creation allow-list, bind-only-to-approved-map, deterministic ID minting, verified-sample-per-type). Owner ratifies by name — the agent drafts, never self-grants. All tasks below are BLOCKED until ratified.
- [ ] T035 [US7] Test (RED): `create_page`/`create_visual_container` determinism + no-partial-write + deterministic ID minting (hash of `report_id`+element slug, never random/time-based — FR-027/US7#4); staged-tree-then-commit; `tests/unit/test_pbir_compile.py`
- [ ] T036 [US7] Implement `src/seshat/pbir_compile.py` orchestration reusing the four shipped adapters + the single new create primitive (inherit allow-list/stage-validate-commit/path-guard/FR-003 snapshot)
- [ ] T037 [US7] **Increment 1 (page shells) — UNBLOCKED**: copy the live report's real empty `page.json` into `tests/fixtures/pbir/page_shell.Report/`; compile a page shell against it; test byte-determinism + FR-003
- [ ] T037a [US7] Test: preconditions gate — compile attempted without a valid `dashboard_blueprint_approval` yields `blocked` naming the missing approval (FR-025/US7#5); compile requesting a shape with no verified sample yields `blocked` naming the missing sample, writes nothing (FR-029/US7#2); `tests/unit/test_pbir_compile.py`
- [ ] T038 [US7] **Increment 3 (lineChart) — UNBLOCKED**: compile a lineChart visual using the verified data-goblin `visual_fmt.Report` sample; bind only to approved-map fields
- [ ] T039 [US7] **BLOCKED — owner sample required**: Increment 2 (KPI cards) — do NOT ship until a real Desktop-authored `card` sample is supplied; log the gap, do not use the `geometry.Report` placeholder
- [ ] T040 [US7] **BLOCKED — owner sample required**: Increment 3 column/bar charts — same hold as Increment C precedent; owner sample required
- [ ] T041 [US7] **BLOCKED — owner sample required**: Increment 4 (slicers + navigation) — no fixture exists
- [ ] T042 [US7] **BLOCKED — owner sample required**: Increment 5 (supported interactions) — no fixture exists

## Phase 10: User Story 8 — PBIR validation (P3)

**Goal**: verify committed PBIR (compiler- or human-built) matches the approved design; grants no approval.

- [ ] T043 [US8] Reconcile the boundary text in `.claude/skills/powerbi-dashboard-design/workflows/visual-implementation-review.md`: the page may be built by a human in Desktop OR by the US7 compiler; F016 remains the owner of the still-forbidden live publish (FR-030)
- [ ] T044 [US8] Extend `templates/visual-implementation-trace.md` with page-level + blueprint-conformance rows (keep four-status vocab; grants no approval — FR-031)
- [ ] T045 [US8] Implement read-only `retail pbir-validate-blueprint` (justify the one CLI verb vs Option-B via the R1/R2 check-surface precedent); reports expected-vs-actual for pages/visuals/types/bindings/fields/titles/geometry/theme/nav/interactions/relative-refs/trace; flags unapproved additions + missing elements
- [ ] T046 [US8] Test: a manually-added unapproved visual is flagged; preview↔PBIR divergence flagged; validator records evidence/deviations only, grants no `dashboard_ready: pass` (FR-031); `tests/integration/test_pbir_validate.py`
- [ ] T046a [US8] Test: no-publish boundary (FR-036/SC-011) — assert no publish/refresh/export/schedule path is reachable from the compiler or validator (F016 remains the only, deferred, publish owner); `tests/integration/test_no_service_publish.py`

## Phase 11: Polish & cross-cutting

- [ ] T047 [P] Update `docs/capabilities/capabilities.yaml` with the new skills/rule (authoritative `state:` — memory: stale Draft headers)
- [ ] T048 [P] Fix the stale `pbir-authoring-adapter/SKILL.md` Increment-D omission noted in Conflict #4 (doc-only)
- [ ] T049 Run full gate: `retail check` + `kit-lint` + `pytest -m unit` + ruff format/check; per-FR grep sweep to confirm each ratified FR is exercised (memory: bulk checkbox-marking lies — mark per verified deliverable)
- [ ] T050 Final whole-branch review on Opus (memory: final review by Opus) before any merge decision

---

## Dependencies & sequencing

- **Setup (P1) → Foundational (P2) → US1 → US2** = the MVP path; US2 depends on US1's artifact (fixture in T017 makes US2 independently testable).
- **US6** (approval+versioning, incl. FR-022a) gates the PBIR slices (US7/US8) — sequence before Phase 9.
- **US4, US5, US3** (P2) are independent of each other; any order after MVP.
- **US7** is SAMPLE-gated (D10) + ADR-gated (T034/D11): only T037 (page shell) + T038 (lineChart) are buildable today; T039–T042 are BLOCKED pending owner samples.
- **US8** depends on US7 having produced something to validate (or a human-built page) + the boundary reconcile (T043).

## Parallel opportunities

- Foundational: T003/T004 (different files) ∥; T006/T007 (different test files) ∥.
- US1: T008/T009/T010 (three different new files) ∥.
- US3: T031 (docs) ∥ other stories.
- Polish: T047/T048 ∥.

## MVP scope

**US1 + US2** (Phases 1–4). Delivers a reviewable dashboard design end-to-end on `retail_store_sales`, fails closed, stops at human review — with no preview, no PBIR, no publish.

## Human seams that STOP this plan (not cleared by tasks)

1. Spec ratification (Principle V). 2. PBIR-creation ADR (T034). 3. `report_intent_approval` + `dashboard_blueprint_approval` (named-human). 4. Owner-supplied PBIR samples (T039–T042).
