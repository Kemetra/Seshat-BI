---
description: "Task list for Decision Change Impact Map implementation"
---

# Tasks: Decision Change Impact Map

**Input**: Design documents from `specs/132-decision-change-impact-map/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED and REQUIRED. The spec's Independent Tests and SC-001..SC-013 demand fixture-backed
tests; this repo's convention is TDD (RED → GREEN → IMPROVE). Test tasks precede the behavior they pin.

**Organization**: Grouped by user story. MVP = US1 + US2 (both P1). US3/US4/US5 layer on top.

## Scope guard (read before starting)

**ALLOWED** — create/modify only:

- `src/seshat/impact_map.py` (NEW composer)
- `src/seshat/cli/commands/impact_map.py` (NEW thin read-only surface) + its registration in the CLI
  dispatch, mirroring `commands/explorer.py` / `commands/passport.py`
- A visibility-only promotion of `decision_gate._evidence_stale` to an importable shared helper
  (behavior-preserving; existing callers unchanged)
- `tests/unit/test_impact_map*.py`, `tests/integration/test_impact_map_surface.py`, and fixtures under
  `tests/` (materialized from `specs/132-decision-change-impact-map/contracts/fixtures/`)
- Additive documentation only where a task says so

**FORBIDDEN** — this feature MUST NOT:

- Create a second Decision Store, readiness engine, lineage authority, approval system, status model,
  or readiness stage
- Write/mutate any decision record, approval, supersession pointer, or `readiness-status.yaml`
- Change `docs/capabilities/capabilities.yaml`, `docs/roadmap/roadmap.md`, `.specify/memory/constitution.md`,
  templates, mappings, production contracts, CI workflows, `pyproject.toml`, or any lockfile — unless a
  task explicitly proves it essential (none currently does)
- Emit any numeric confidence/risk/trust/completeness/blast-radius score, percentage, or ranking
- Import a DB driver on the composer module path; require a live DB or Power BI connection
- Introduce a fourth metric/artifact-identity vocabulary
- **Commit, push, open a PR, or merge** — there are NO git tasks in this list

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create the module skeletons: empty `src/seshat/impact_map.py` and
  `src/seshat/cli/commands/impact_map.py` with module docstrings stating the read-only, no-mutation,
  no-score, offline contract (mirror the docstring posture of `explorer/build.py`). No logic yet.
- [ ] T002 [P] Materialize the fixture tree under `tests/fixtures/impact_map/` from the descriptors in
  `contracts/fixtures/README.md` — one subdir per family (direct, transitive, cycle, stale_evidence,
  missing_ref, conflict, incomplete_lineage, dangling_pointer, absent_store, malformed_store, preview,
  no_leak, non_approved_subject). Fixtures are generic; no worked-example real values
  as defaults (SC-012, NFR-005).

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Must complete before ANY user story implementation.

- [ ] T003 Promote `decision_gate._evidence_stale` to an importable shared helper (visibility-only,
  behavior-preserving) in `src/seshat/decision_gate.py`; keep existing in-module callers working.
- [ ] T004 [P] Add guard test `tests/unit/test_evidence_stale_promotion.py` asserting the promoted
  helper's output is identical to the pre-promotion behavior on a stale and a fresh fixture (no
  staleness-authority fork — research.md D2).
- [ ] T005 Implement in `src/seshat/impact_map.py` the read-only INPUT-LOADING layer that reuses (never
  re-implements): `decision_store.load_store` + `.decisions()`, `decision_store.scope_keys`,
  `decision_store.is_critical`, `decision_store.active_scope_conflicts`, `artifact_identity`,
  `readiness_projection.build_readiness_projection`, `readiness_classify.classify`/`CATEGORY_RANK`,
  `explorer.build._lineage`, the promoted staleness helper, `disclosure.scan_disclosure`, and
  `cli.guards.resolve_local_output`. This task wires imports + a `load_subject(repo_root, decision_id)`
  that returns the subject decision or a fail-closed condition; it computes NO impact yet. Establishes
  the reuse-only, no-new-authority posture (FR-001, FR-002).
- [ ] T006 [P] Add offline guard test `tests/unit/test_impact_map_no_driver.py` asserting the composer
  module source imports no DB driver (`import psycopg`, `import sqlalchemy`, `.connect(`, `DSN`) —
  mirrors HR9's `test_hr9_module_imports_no_database_driver` (NFR-002).

**Checkpoint**: inputs load and fail-closed; no impact computed yet.

---

## Phase 3: User Story 1 — Map direct impact (Priority: P1) 🎯 MVP

**Goal**: Given a superseded/evidence-stale approved decision, name the DIRECT downstream artifacts
with evidence paths, affected readiness stages, and next review actions.

**Independent Test**: `direct/` and `stale_evidence/` fixtures → each directly-citing artifact appears
once, `relation:"direct"`, resolvable evidence path, stage from readiness projection, next action from
`readiness_classify`, no score, no state write.

### Tests for US1 (write FIRST, must FAIL)

- [ ] T007 [P] [US1] `tests/unit/test_impact_map.py::test_direct_impact_superseded` — `direct/` fixture:
  assert direct artifact, `relation:"direct"`, non-empty `evidence_paths`, affected stage read from
  `readiness_projection`, next action from `readiness_classify` (SC-001).
- [ ] T008 [P] [US1] `tests/unit/test_impact_map.py::test_evidence_stale_trigger` — `stale_evidence/`
  fixture: subject `trigger` includes `evidence_stale` via the promoted helper; directly-derived
  artifacts listed with evidence paths (FR-003b/005).
- [ ] T009 [P] [US1] `tests/unit/test_impact_map_no_score.py` — no digit-then-`%` and no
  `score`/`confidence`/`risk`/`risk_score`/`trust`/`completeness`/`blast_radius`/`weight` key anywhere
  in the projection dict (SC-005 / INV-4).
- [ ] T010 [P] [US1] `tests/unit/test_impact_map.py::test_no_state_written` — after producing a map, no
  decision/approval/supersession pointer/`readiness-status.yaml` changed (FR-024, FR-025).
- [ ] T010a [P] [US1] `tests/unit/test_impact_map.py::test_non_approved_subject_reported` —
  `non_approved_subject/` fixture: a `proposed`/`pending` (non-approved) subject yields
  `blocking_condition.kind == "invalid_subject"` with `subject == null`, reported as *not a valid
  impact-map subject*, NOT as "no impact" and NOT a `subject` with a made-up trigger (spec Edge Case
  "Decision never approved"; FR-003 approved-only precondition).

### Implementation for US1

- [ ] T011 [US1] Implement scope→direct-artifact resolution in `src/seshat/impact_map.py`: for the
  single subject decision, for each `scope_keys(subject.scope)` entry, resolve to committed downstream
  artifacts (metric contracts, gold bindings via the explorer metric→gold edge, readiness evidence),
  producing `affected[]` entries with `relation:"direct"`, `artifact_id` (via `artifact_identity`), and
  `evidence_paths` (an artifact reached by more than one path from the subject is listed once, extra
  paths folded into its `evidence_paths`). Keeps the direct set separable from the transitive set
  (FR-007, FR-008, FR-009, FR-010).
- [ ] T012 [US1] Attach affected readiness stage(s) per affected artifact using
  `readiness_projection.build_readiness_projection` + `decision_gate._FLOW_TO_SPINE` (READ only;
  FR-017).
- [ ] T013 [US1] Attach next review action(s) per affected artifact using `readiness_classify.classify`
  + `CATEGORY_RANK` ordering (FR-018).
- [ ] T014 [US1] Enforce the no-score invariant structurally in the composer (no synthesized number
  ever placed in the dict) and the never-write contract (FR-023/024/025).

**Checkpoint**: direct-impact map works; T007–T010a pass.

---

## Phase 4: User Story 2 — Transitive impact + incomplete-lineage warnings (Priority: P1) 🎯 MVP

**Goal**: Follow existing lineage edges to name TRANSITIVE artifacts (distinctly labeled, full edge
evidence chain) and emit an explicit incomplete-lineage warning for every unresolved scope tag / edge —
never a silent drop, never an inferred edge, never a false "unaffected".

**Independent Test**: `transitive/`, `missing_ref/`, `incomplete_lineage/`, `cycle/` fixtures.

### Tests for US2 (write FIRST, must FAIL)

- [ ] T015 [P] [US2] `tests/unit/test_impact_map.py::test_transitive_impact_with_edge_chain` —
  `transitive/` fixture: dashboard artifact `relation:"transitive"` with the full ordered
  `evidence_paths` edge chain; a transitive-only artifact is never labeled `direct` (SC-002 / INV-9).
- [ ] T016 [P] [US2] `tests/unit/test_impact_map.py::test_unresolved_scope_tag_warns` — `missing_ref/`
  fixture: a zero-resolution scope tag produces `incomplete_lineage[]` (`unresolved_scope_tag`);
  nothing recorded "unaffected" (FR-012 / SC-004).
- [ ] T017 [P] [US2] `tests/unit/test_impact_map.py::test_unfollowable_edge_warns` — `missing_ref/`
  fixture: a missing-target edge produces `incomplete_lineage[]` (`unfollowable_edge`); no substitute
  edge inferred (FR-013).
- [ ] T018 [P] [US2] `tests/unit/test_impact_map.py::test_affected_and_incomplete_disjoint` —
  `incomplete_lineage/` fixture: `affected[]` and `incomplete_lineage[]` both non-empty and disjoint
  (FR-015 / SC-003 / INV-1); dual-reachable artifact appears once as `direct` (INV-2).
- [ ] T019 [P] [US2] `tests/unit/test_impact_map.py::test_cycle_terminates_and_is_recorded` — `cycle/`
  fixture: walk terminates in bounded time, records the cycle in `cycles[]`, never reports the cycle as
  a completed transitive path (FR-014 / SC-006).

### Implementation for US2

- [ ] T020 [US2] Implement the transitive walk in `src/seshat/impact_map.py`: a bounded DFS/BFS over the
  composed edge set (reusing `explorer._lineage` node ids + `cross-table-lineage` SKILL hop definitions
  and proven/unresolved/gap tiering — one existing lineage vocabulary only, no fourth scheme) with an
  explicit visited-set for cycle detection; label reached artifacts `transitive` with the full ordered
  edge `evidence_paths` (FR-009, FR-010, FR-011, NFR-006).
- [ ] T021 [US2] Implement incomplete-lineage detection: every unresolved scope tag, unfollowable edge,
  and (from Phase 5) dangling supersession pointer becomes an explicit `incomplete_lineage[]` entry;
  guarantee `affected[]`/`incomplete_lineage[]` disjointness and direct-dominance (FR-012/013/015,
  INV-1/INV-2).
- [ ] T022 [US2] Enforce cycle handling: on re-encounter, record a named cycle condition and stop the
  branch; never re-traverse (FR-014).

**Checkpoint**: MVP (US1+US2) complete; a truthful direct+transitive map that never reports a false
"unaffected". T007–T019 pass.

---

## Phase 5: User Story 3 — Preview + supersession-chain reading (Priority: P2)

**Goal**: Produce the map as a preview for a not-yet-superseded decision (no state change), and present
the existing `supersedes`/`superseded_by` pointer chain in order; a dangling pointer warns.

**Independent Test**: `preview/` and `dangling_pointer/` fixtures.

### Tests for US3 (write FIRST, must FAIL)

- [ ] T023 [P] [US3] `tests/unit/test_impact_map.py::test_preview_no_mutation` — `preview/` fixture:
  preview `affected[]` produced, `is_preview:true`, zero state writes (FR-004).
- [ ] T024 [P] [US3] `tests/unit/test_impact_map.py::test_supersession_chain_in_order` —
  `dangling_pointer/` fixture: resolvable chain presented in pointer order using existing store fields
  (FR-006).
- [ ] T025 [P] [US3] `tests/unit/test_impact_map.py::test_dangling_pointer_warns` — `dangling_pointer/`
  fixture: an unresolved `supersedes`/`superseded_by` yields `incomplete_lineage[]`
  (`dangling_supersession_pointer`); no fabricated history (FR-016 / SC-007).

### Implementation for US3

- [ ] T026 [US3] Implement preview mode (run against a not-yet-superseded approved decision) with a
  hard no-write guarantee (FR-004).
- [ ] T027 [US3] Implement supersession-chain reading from the store's existing pointers, in order;
  dangling pointers → `incomplete_lineage[]`; NO history/version model created (FR-006/016).

**Checkpoint**: US3 works independently; T023–T025 pass.

---

## Phase 6: User Story 4 — Fail closed on malformed/absent/incomplete evidence (Priority: P2)

**Goal**: Degrade safely — report the blocking condition, never crash, never emit a live-DB traceback,
never a false clean "no impact", never a numeric score, never a state write.

**Independent Test**: `absent_store/`, `malformed_store/`, `conflict/` fixtures + removed cited
evidence.

### Tests for US4 (write FIRST, must FAIL)

- [ ] T028 [P] [US4] `tests/unit/test_impact_map.py::test_absent_store_blocks` — `absent_store/`:
  `blocking_condition.kind = absent_store`; not "no artifacts affected" (FR-019).
- [ ] T029 [P] [US4] `tests/unit/test_impact_map.py::test_malformed_store_fails_closed` —
  `malformed_store/`: fails closed, names the store problem, writes nothing (FR-019 / SC-008).
- [ ] T030 [P] [US4] `tests/unit/test_impact_map.py::test_active_scope_conflict_surfaced` — `conflict/`:
  surfaces the conflict via `active_scope_conflicts`; not silently resolved (FR-020).
- [ ] T031 [P] [US4] `tests/unit/test_impact_map.py::test_missing_cited_evidence_warns` — removed cited
  evidence → `incomplete_lineage[]` (`missing_cited_evidence`); no resolvable path reported through it
  (FR-013 / SC-008).

### Implementation for US4

- [ ] T032 [US4] Implement the fail-closed layer: absent/malformed store (reuse the store's fail-closed
  load), active-scope conflict (reuse `active_scope_conflicts`), and unreadable inputs all set
  `blocking_condition` and refuse a false clean result; never crash, never traceback (FR-019/020,
  NFR-004, INV-5).

**Checkpoint**: US4 works independently; T028–T031 pass.

---

## Phase 7: User Story 5 — Dual reviewable output (Priority: P3)

**Goal**: Produce the machine-readable projection and a human-readable rendering of identical content;
disclosure-scan before write; contained write; deterministic.

**Independent Test**: `test_impact_map_surface.py` + `no_leak/` fixture.

### Tests for US5 (write FIRST, must FAIL)

- [ ] T033 [P] [US5] `tests/integration/test_impact_map_surface.py::test_human_machine_parity` —
  identical content set across both forms (SC-009).
- [ ] T034 [P] [US5] `tests/integration/test_impact_map_surface.py::test_byte_determinism` — two runs on
  identical inputs → byte-identical machine form modulo `generated_at` (SC-010 / INV-6).
- [ ] T035 [P] [US5] `tests/integration/test_impact_map_surface.py::test_disclosure_blocks_write` —
  `no_leak/` fixture: `scan_disclosure` blocks the write on a planted secret/PII/connection string; the
  projection records only repo-relative paths/identities, never raw PII, a connection string, or a
  credential (SC-011 / NFR-003 / SEC-001 / SEC-002 / SEC-003 / INV-7).
- [ ] T036 [P] [US5] `tests/integration/test_impact_map_surface.py::test_contained_write` — every written
  form lands only under the contained output root via `resolve_local_output` (FR-022).

### Implementation for US5

- [ ] T037 [US5] Implement deterministic ordering in the composer: sort `affected[]` by
  `(direct-first, artifact_id)`, each `affected[].evidence_paths` in traversal order,
  `incomplete_lineage[]` by `(kind,locator)`, `supersession_chain[]` in pointer order; exclude
  `generated_at` from any digest (NFR-001).
- [ ] T038 [US5] Implement the thin read-only surface in `src/seshat/cli/commands/impact_map.py`
  (mirror `commands/explorer.py`/`commands/passport.py`): build dict → `scan_disclosure` → render human
  form + write machine form under `resolve_local_output`; register the surface in the CLI dispatch
  (FR-021/022). Confirm this is the smallest addition consistent with research.md D9 (no broad CLI
  family, no UI, no new stage).

**Checkpoint**: all stories independently functional; T033–T036 pass.

---

## Phase 8: No-duplicate verification, docs & validation

- [ ] T039 `tests/unit/test_impact_map_no_duplicate.py` — assert the feature IMPORTS (does not
  re-implement) every reused authority (`decision_store`, `decision_gate`, `artifact_identity`,
  `readiness_projection`, `readiness_classify`, `explorer.build`, `disclosure`, `cli.guards`), adopts
  exactly one existing lineage-node vocabulary (no fourth scheme), and creates NO new Decision Store /
  readiness engine / lineage authority / approval system / status model / readiness stage / numeric
  score / broad CLI family / web UI (FR-001, FR-002, NFR-006, SC-013 / INV-11).
- [ ] T040 [P] Run the full unit + integration suite for the feature and confirm RED→GREEN for every
  test above; confirm `ruff format --check src tests` and `ruff check src tests` pass on the new/changed
  files (repo CI gate).
- [ ] T041 [P] `tests/unit/test_impact_map_no_leak.py` — perform the SC-012/NFR-005 no-leak scan: run
  the composer over generic fixtures and assert no worked-example table/column/policy/number/client/
  named-human token (from the enumerated worked-example token list) appears in any produced artifact.
  This is the *verification* of SC-012 (distinct from T002, which only constrains fixture authoring).
- [ ] T041a [P] Add an additive capability note DRAFT under `specs/132-decision-change-impact-map/` (NOT
  in `docs/capabilities/capabilities.yaml`) describing the shipped surface for a later, owner-gated
  capability-ledger edit; do not touch the ledger here.
- [ ] T042 Run the `quickstart.md` walkthrough against the fixtures and confirm the described reviewer
  experience matches actual output (direct/transitive split, incomplete-lineage warnings, cycles,
  blocking conditions, no score, no writes).

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1: T001–T002)** → no deps. T001 (skeletons) ∥ T002 (fixtures).
- **Foundational (P2: T003–T006)** → after Setup; BLOCKS all user stories (the composer's input layer +
  promoted staleness helper + guard tests). T003 (promote `_evidence_stale`) → T004 (its guard test);
  T005 (input-loading layer) depends on T003 and on T002 fixtures; T006 ∥ T004.
- **US1 (P3: T007–T014)** → after Foundational. Tests T007–T010a (RED) before impl T011–T014 (GREEN).
  T011 (direct resolution, single subject) depends on T005; T012/T013 (stages/actions) depend on T011;
  T014 (no-score/never-write enforcement) after T011–T013.
- **US2 (P4: T015–T022)** → after US1's direct resolution. Tests T015–T019 (RED) before impl T020–T022
  (GREEN). **T020 (transitive walk) depends on T011** (it walks outward from the direct set); T021
  (incomplete-lineage) depends on T020; T022 (cycle handling) folds into T020's visited-set. US1+US2 =
  MVP.
- **US3 (P5: T023–T027)**, **US4 (P6: T028–T032)**, **US5 (P7: T033–T038)** → after Foundational; each
  independently testable and can run in parallel after the MVP if staffed. Cross-story reuse (not a
  blocking dependency, but note): US3's dangling-pointer warning (T027) reuses US2's incomplete-lineage
  machinery (T021); US4's conflict path (T032) reuses the T005 input layer; US5's surface (T038) needs
  a complete projection dict, so it lands after the composer stories it renders.
- **Phase 8 (T039–T042)** → after the stories it verifies. T039 (no-duplicate) after all stories; T040
  (full suite + ruff) and T041 (no-leak scan) and T042 (quickstart walkthrough) after implementation;
  T041a (capability-note draft) has no code dependency and may run any time after T001.

### Within each story

- Tests (RED) before implementation (GREEN) — TDD.
- Input loading (T005) → direct resolution (T011) → transitive walk (T020) → incomplete-lineage (T021).
- Composer complete before the surface renders it (T038 after the dict is fully assembled).

### Parallel opportunities

- All `[P]` tests within a story run in parallel (distinct test functions/files).
- T001 ∥ T002; T004 ∥ T006.
- US3/US4/US5 can proceed in parallel after the MVP if staffed, since each is independently testable.
- In Phase 8, T040/T041/T041a are `[P]` (distinct concerns); T039 and T042 gate on prior implementation.

---

## Implementation Strategy

- **MVP first**: Setup → Foundational → US1 → US2 → STOP and validate the direct+transitive map (the
  truthful-no-false-"unaffected" core) before layering US3/US4/US5.
- **Incremental**: each later story adds value (preview/chain, fail-closed hardening, dual output)
  without breaking the MVP.
- **TDD throughout**: RED → GREEN → IMPROVE; fix implementation, not tests, unless a test is wrong.

## Notes

- `[P]` = different files, no dependencies. `[USn]` maps a task to its story for traceability.
- Every task stays within the Scope guard above. **No git task exists** — no commit, push, PR, or merge.
- The one refactor (T003) is visibility-only and behavior-preserving, guarded by T004.
