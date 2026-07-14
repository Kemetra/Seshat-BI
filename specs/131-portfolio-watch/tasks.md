# Tasks: Portfolio Watch

**Input**: Design documents from `specs/131-portfolio-watch/`

**Prerequisites**: plan.md, spec.md, research.md (D1-D8), data-model.md, contracts/ (summary + snapshot), quickstart.md

**Tests**: TDD is REQUESTED for this feature. Test tasks precede implementation in each story (RED -> GREEN). All tests are offline (no DB, no network) -- the MVP is read-only over committed fixtures.

**Organization**: Tasks are grouped by user story. MVP = US1 + US2 + US3 (all P1). US4 is P2 (later slices).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 / US4 (setup/foundational/polish carry no story label)
- Every implementation task names an exact file path.

## Path Conventions

- Aggregator library: `src/seshat/portfolio_watch.py` (pure, stdlib-only)
- Tests: `tests/unit/`, `tests/integration/`, fixtures under `tests/fixtures/portfolio_watch/`
- Skill: `.claude/skills/portfolio-watch/SKILL.md`
- Optional CLI surface: `src/seshat/cli/commands/watch.py`
- Docs: `docs/tools/portfolio-watch.md`; capability entry: `docs/capabilities/capabilities.yaml`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: scaffold the module + test locations. No behavior yet.

- [ ] T001 Create the empty pure-module scaffold `src/seshat/portfolio_watch.py` with a module docstring stating: read-only, stdlib-only at import, COMPOSITION not a second source of truth, no DB, no write-back beyond the local summary/snapshot, no numeric score (mirror the `agent_next.py` / `readiness_projection.py` docstring posture).
- [ ] T002 [P] Create the fixture directory `tests/fixtures/portfolio_watch/` with a generic multi-scope repo fixture (several committed `readiness-status.yaml` scopes at mixed stages; NO C086/pharmacy specifics -- Principle VII) used by all stories.
- [ ] T003 [P] Add generic per-dimension evidence fixtures under `tests/fixtures/portfolio_watch/`: a committed source-drift-findings artifact, an approval seam, a semantic-audit/report-intent input, a metric-contract + TMDL snippet, and at least one scope deliberately MISSING a dimension's evidence (for US3).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared reader-composition + data shapes every story needs. MUST complete before US1/US2/US3.

- [ ] T004 Define the frozen dataclasses in `src/seshat/portfolio_watch.py` for the data-model entities: `CoveredDimensionFinding` (dimension, state, class, measured, evidence, owner, source_surface), `PrioritizedNextAction` (category, action), `ConditionChange` (key, label), and the summary/snapshot container shapes. No logic yet.
- [ ] T005 [P] Define the closed **degradation state** set (`covered` | `[PENDING LIVE]` | `stale` | `not_applicable_with_reason` | `unreadable`) and the closed **change-label** set (`new` | `resolved` | `unchanged` | `current_condition_no_baseline`) as module constants in `src/seshat/portfolio_watch.py` (data-model.md), so no state/label is invented ad hoc.
- [ ] T006 Implement the governed-scope enumerator: read the scope set from the committed readiness paths the spine tracks (via the shipped `status_surface` / `readiness_projection` inputs), NOT the live `portfolio_enumerate` DB path (research D6). Returns the reused Governed Scope shape.
- [ ] T007 [P] Write the foundational unit test `tests/unit/test_portfolio_watch_shapes.py` asserting: the dataclasses are frozen; the degradation/label sets are exactly the closed sets from data-model.md; the enumerator lists every fixture scope and opens no DB connection (no `Dialect`/DSN import on the path).

**Checkpoint**: shapes + scope enumeration exist and are import-clean (stdlib-only).

---

## Phase 3: User Story 1 -- Read a recurring portfolio summary (Priority: P1, MVP)

**Goal**: one read-only summary per governed scope with per-dimension findings (each cited or truthfully degraded), open blockers, a human-attention flag, and exactly ONE prioritized next action via the shipped fixed rank -- no score.

**Independent test**: run over the multi-scope fixture; confirm every scope is listed, every `covered` finding cites committed evidence, the one next action's category equals the highest-ranked open category, and no numeric score appears.

### Tests (write first -- RED)

- [ ] T008 [P] [US1] Write `tests/unit/test_portfolio_watch_summary.py` (RED): summary lists every fixture scope; each covered dimension finding carries a committed `evidence` citation + `source_surface` (INV-2); NO numeric health/confidence/priority score appears anywhere (INV-1, FR-020).
- [ ] T009 [P] [US1] Write `tests/unit/test_portfolio_watch_next_action.py` (RED): for a scope whose top open condition is a missing approval, `prioritized_next_action.category == approval` (highest of the shipped `readiness_classify` rank) and `action` equals the scope's RELAYED `next_action`, never a synthesized string (FR-005, SC-003); a top-category tie surfaces both actions, unbroken by a number.
- [ ] T010 [P] [US1] Write `tests/unit/test_portfolio_watch_attention.py` (RED): a scope with an unmet/invalid approval or a relayed Principle-V drift blocker sets `requires_human_attention=true` and names an `owner`; a fully-clean scope is NOT flagged and its next action is its own terminal/next-stage action (FR-006, US1 #4).

### Implementation (GREEN)

- [ ] T011 [US1] Implement the per-dimension join in `src/seshat/portfolio_watch.py`: for each scope, read each dimension from its shipped source per the data-model dimension->source map (drift, metric_drift, semantic_audit/report_intent, readiness projection, approval_inbox, review_integration) and build `CoveredDimensionFinding`s with citations. NEVER re-run a surface's own check (FR-003); relay its committed output.
- [ ] T012 [US1] Implement the prioritized-next-action selector: classify each scope's open conditions with the shipped `readiness_classify` rank, pick the highest-ranked category, and RELAY that scope's recorded `next_action` (from the readiness projection / `agent_next` per-table document). No computed priority (FR-005, D4).
- [ ] T013 [US1] Implement the summary assembler `build_portfolio_watch_summary(repo_root)`: enumerate scopes (T006), join dimensions (T011), select next actions (T012), attach `open_blockers` + `requires_human_attention` + `owner`, add the `portfolio` measured-count block + `scopes_with_no_evidence`, and reuse the shipped disclosure-scan shape for `disclosure` (SEC-002). Read-only; deterministic.
- [ ] T014 [US1] Make T008/T009/T010 pass (GREEN); confirm no per-scope artifact is written by summary assembly (SC-008) via the test.

**Checkpoint**: a standalone read-only summary exists (useful even with no baseline yet).

---

## Phase 4: User Story 2 -- Distinguish changes from existing conditions (Priority: P1, MVP)

**Goal**: persist a prior-run snapshot and diff the current summary against it into `new`/`resolved`/`unchanged`; first run = current-condition-no-baseline; standing conditions never re-alerted.

**Independent test**: run twice on two committed states; run-1 has 0 `new` (writes baseline); run-2 labels are the exact set-difference/intersection against run-1's snapshot; a standing condition is `unchanged` once.

### Tests (write first -- RED)

- [ ] T015 [P] [US2] Write `tests/unit/test_portfolio_watch_condition_key.py` (RED): the Condition Key is the magnitude-free tuple `(scope_id, dimension, class, subject_locator)`; a magnitude wiggle on the same class produces the SAME key (no churn) (D3, SNAP-4, FR-010).
- [ ] T016 [P] [US2] Write `tests/unit/test_portfolio_watch_diff.py` (RED): given prior + current key sets, `new = current-prior`, `resolved = prior-current`, `unchanged = current & prior`; deterministic sorted output (FR-008, FR-012, SC-006).
- [ ] T017 [P] [US2] Write `tests/unit/test_portfolio_watch_first_run.py` (RED): no prior snapshot (and a corrupt/unreadable prior snapshot) -> every condition `current_condition_no_baseline`, explicitly NOT `new`, with a stated "no baseline available" note (FR-009, SNAP-3, the `observed=None` honesty).
- [ ] T018 [P] [US2] Write `tests/unit/test_portfolio_watch_scope_set_change.py` (RED): a scope present in only one of the two runs is reported as `scope_added`/`scope_removed`, not misattributed to condition changes inside a missing scope (FR-011).

### Implementation (GREEN)

- [ ] T019 [US2] Implement the Condition Key derivation + the snapshot serializer/reader in `src/seshat/portfolio_watch.py` per the snapshot contract: `schema_version`, `captured_at_revision` (git HEAD), magnitude-free `conditions[]`, implied scope set. Local artifact only (SNAP-1); no secret/data (SNAP-2).
- [ ] T020 [US2] Implement the change classifier: pure sorted set-diff of current keys vs the prior snapshot -> `new`/`resolved`/`unchanged`; absent/unreadable prior -> `current_condition_no_baseline` (fail-closed, D3). Attach `change_labels[]` to the summary and emit scope-set changes.
- [ ] T021 [US2] Wire the run flow: read prior snapshot -> build summary (US1) -> classify changes -> write the fresh snapshot under `.seshat/watch/`. Writing the snapshot is the only new write beyond the summary (SC-008).
- [ ] T022 [US2] Make T015-T018 pass (GREEN); add an integration test `tests/integration/test_portfolio_watch_two_runs.py` exercising quickstart Steps 1-3 (first run baseline -> mutate fixture -> second run labels) and asserting duplicate suppression (SC-005) + determinism (SC-006).

**Checkpoint**: the recurring summary is baseline-diffable (the core value over the point-in-time control room).

---

## Phase 5: User Story 3 -- Handle unavailable/stale/partial/incompatible evidence truthfully (Priority: P1, MVP)

**Goal**: every not-cleanly-readable dimension is one of the four non-`covered` states; nothing is fabricated; partial portfolios do not fail the run.

**Independent test**: fixtures for (a) live-only no-DSN, (b) evidence older than HEAD, (c) no producer/no evidence yet, (d) unknown schema version, (e) partial portfolio; each yields the specified marker; run does not fail.

### Tests (write first -- RED)

- [ ] T023 [P] [US3] Write `tests/unit/test_portfolio_watch_pending_live.py` (RED): a dimension whose evidence needs a live re-profile with no DSN -> `[PENDING LIVE]`, never a fabricated comparison (FR-013), consistent with `docs/readiness/source-drift.md`.
- [ ] T024 [P] [US3] Write `tests/unit/test_portfolio_watch_stale.py` (RED): evidence captured at a revision older than current HEAD/`source_revision` -> `stale`, citing captured-at vs current; not shown as a current condition (FR-014).
- [ ] T025 [P] [US3] Write `tests/unit/test_portfolio_watch_not_applicable.py` (RED): no shipped producer for a scope OR no evidence produced yet -> `not_applicable_with_reason` (naming the reason); never counted covered/clean (FR-015).
- [ ] T026 [P] [US3] Write `tests/unit/test_portfolio_watch_unreadable.py` (RED): an evidence artifact declaring an unknown schema version -> `unreadable` (naming the version); excluded from any pass/clean claim; a per-scope read error degrades that dimension to `unreadable`, never a fabricated pass (FR-016, FR-022).
- [ ] T027 [P] [US3] Write `tests/unit/test_portfolio_watch_partial.py` (RED): a partial portfolio (some scopes evidenced, some empty) is summarized for covered scopes with empty scopes listed in `scopes_with_no_evidence`; the run does NOT fail/block (FR-017).

### Implementation (GREEN)

- [ ] T028 [US3] Implement the truthful-degradation logic in the per-dimension join (T011): detect no-DSN live legs (`[PENDING LIVE]`), stale-by-revision (`stale`), no-producer/no-evidence (`not_applicable_with_reason`), unknown/unparseable schema version + read errors (`unreadable`). Never upgrade a degraded state to `covered`.
- [ ] T029 [US3] Ensure partial-portfolio robustness: a per-scope/per-dimension read failure marks only that cell degraded and never aborts the whole run (FR-017/FR-022). Make T023-T027 pass (GREEN).

**Checkpoint**: MVP complete -- a re-runnable, baseline-diffable, truthfully-degrading, offline read-only summary (US1+US2+US3).

---

## Phase 6: Interface surfacing (MVP delivery of US1-US3)

**Purpose**: expose the shipped MVP through the sanctioned surfaces (skill + at most one narrow CLI surface). No behavior change.

- [ ] T030 Author the agent-facing skill `.claude/skills/portfolio-watch/SKILL.md` (sibling of `retail-control-room`): read-only, invoke-and-present; states the scope wall (aggregates never re-derives; no gate/rule/approval; no score; no DB; relays Principle-V, decides none); calls `build_portfolio_watch_summary` and presents it.
- [ ] T031 [P] Add the ONE narrow read-only CLI surface `src/seshat/cli/commands/watch.py` (e.g. `retail watch --format json`) mirroring the shipped read-only projection verbs + the ratified `status --format json` precedent (FR-023, D7). No broad verb family; wire it into the CLI dispatcher only as a single read-only command.
- [ ] T032 [P] Add an integration test `tests/integration/test_watch_cli.py` (or skill-contract test) asserting the surface is read-only, emits the summary shape, opens no DB, and prints no score.

**Checkpoint**: MVP is invokable by agent (skill) and, for CI/agent-less use, by the one JSON surface.

---

## Phase 7: User Story 4 -- Broaden coverage and reporting formats (Priority: P2, later)

**Goal**: fold in an additional shipped dimension and add a deterministic human-readable digest over the same machine-readable summary. Same read-only, no-score posture.

**Independent test**: an added dimension cites its shipped surface + follows the degradation rules; the digest is a pure rendering (identical inputs -> identical digest); neither adds a score, a write-back, a DB need, or a gate.

- [ ] T033 [US4] Add one additional shipped-surface dimension to the join (e.g. reconciliation/review-pack), sourced + cited from its shipped module, following the same degradation rules; add its unit test (FR-004/FR-013..FR-016).
- [ ] T034 [P] [US4] Implement a deterministic human-readable digest renderer over the machine-readable summary (pure rendering; no new data, no score) + a determinism test (identical summary -> identical digest) (FR- US4, SC- rendering).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: docs, capability registration, and the whole-feature invariants.

- [ ] T035 [P] Write `docs/tools/portfolio-watch.md` (read-only tool doc, sibling of `docs/tools/dashboard-planner.md` / `dashboard-gap-detector.md`): what it aggregates, the degradation states, the baseline-diff, the no-gate/no-score/no-DB scope wall, and that "recurring" = re-runnable (no scheduler, FR-024).
- [ ] T036 Add ONE `portfolio-watch` entry to `docs/capabilities/capabilities.yaml` (`state`, `authority: advisory`, `surface: skill` (+ the one CLI surface), `requirements: []`), consistent with the `retail-control-room` entry shape. Do NOT regenerate other entries.
- [ ] T037 [P] Add a cross-cutting invariant test `tests/unit/test_portfolio_watch_invariants.py`: (a) no numeric health/confidence/priority/quality score in any produced artifact (INV-1, SC-003); (b) no DSN/secret/real-host string in summary or snapshot (SEC-002, SC-012); (c) no Principle-V ruling originated -- every relayed seam names an owner (FR-021, SC-010); (d) summary assembly changes no committed per-scope artifact (SC-008).
- [ ] T038 Verify `retail check` exit behavior is UNCHANGED and the rule inventory is unchanged (no gate/rule added, FR-019/SC-009); run `ruff format --check src tests`, `ruff check src tests`, `pytest -m unit -x -q`. Confirm all produced spec/docs/text is ASCII + UTF-8 no BOM.

---

## Dependencies & Execution Order

- **Setup (Phase 1)** -> **Foundational (Phase 2)** block everything.
- **US1 (Phase 3)** is the first independently-testable slice (summary). **US2 (Phase 4)** and **US3 (Phase 5)** each build on the US1 join but are independently testable; US2 adds the snapshot/diff, US3 adds degradation to the same join. All three are P1/MVP.
- **Phase 6 (interface)** surfaces the completed MVP; depends on US1-US3.
- **US4 (Phase 7)** is P2, after the MVP.
- **Polish (Phase 8)** last.

**MVP scope**: Phases 1-6 (Setup + Foundational + US1 + US2 + US3 + interface). Delivers a re-runnable, baseline-diffable, truthfully-degrading, offline read-only summary via skill + one JSON surface.

## Parallel opportunities

- Setup: T002, T003 in parallel.
- Foundational: T005, T007 in parallel with T004/T006 respectively (different concerns).
- Within each story, all RED test tasks marked [P] run in parallel (distinct files) before their GREEN implementation.
- Phase 6: T031, T032 in parallel after T030.
- Polish: T035, T037 in parallel with T036.

## Independent test criteria (per story)

- **US1**: summary lists every scope; covered findings cited; one ranked next action; no score.
- **US2**: run-1 baseline + 0 `new`; run-2 exact set-diff labels; standing condition `unchanged` once; deterministic.
- **US3**: each degradation fixture yields its specified marker; partial portfolio does not fail.
- **US4**: added dimension cited + degradable; digest deterministic; no score/write-back/DB/gate added.
