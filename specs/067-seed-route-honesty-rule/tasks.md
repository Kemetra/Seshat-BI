# Tasks: Seed-Layer Route Honesty Rule

**Input**: Design documents from `specs/067-seed-route-honesty-rule/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Included and TDD-ordered -- the `retail check` rule family is test-gated;
the extension is verified by failing `seed` tests first, then the minimal rule edit.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 / US2 / US3 (see spec.md), or SETUP / NR (non-regression)

## Path Conventions

Single project. Rule: `src/retail/rules/routes.py`. Manifest:
`docs/routing/routes.yaml`. Tests: `tests/unit/test_routes.py` (existing A1 tests),
`tests/unit/test_routes_coverage.py` (existing A3 tests).

---

## Phase 1: Setup

- [ ] T001 [SETUP] Re-run the editable install in THIS worktree
  (`pip install -e .`) so `retail check` / pytest resolve against this checkout's
  `src/`, not another worktree's (memory: editable-install cross-worktree hazard).
  Confirm `python -c "import retail.rules.routes"` imports.

---

## Phase 2: Tests first (RED) -- author failing `seed` cases before touching the rule

- [ ] T002 [P] [US1] In `tests/unit/test_routes.py`, add a test: a manifest with a
  `status: seed` route whose every target IS a tracked file -> `A1` emits NO Finding.
  (Fails today: `seed` is currently an invalid status -> A1 errors.)
- [ ] T003 [P] [US1] Add a test: a `status: seed` route whose target does NOT resolve
  -> `A1` emits exactly one ERROR whose locator names the route (symmetric to the
  `built`-broken case).
- [ ] T004 [P] [US1] Add a test: a `status: seed` route with NO `targets` -> `A1`
  emits an ERROR (a seed route, like built, must name >=1 target).
- [ ] T005 [P] [US2] Add a test: a `status: partial` (invalid) route -> `A1` emits an
  ERROR whose message lists exactly the three accepted values `built`, `planned`,
  `seed`.
- [ ] T006 [P] [US2] Confirm the EXISTING `built` and `planned` A1 tests are present
  and assert no change is required to them (regression guard for FR-006). If the file
  lacks explicit `planned`-stale / `built`-broken cases, add them so the three-state
  behavior is fully pinned.
- [ ] T007 [NR] Run `pytest -m unit tests/unit/test_routes.py` and CONFIRM the new
  `seed` tests FAIL for the right reason (invalid-status rejection), proving the gap.

---

## Phase 3: Implementation (GREEN) -- minimal in-place edit

- [ ] T008 [US1][US2] In `src/retail/rules/routes.py`, widen
  `_VALID_STATUS = frozenset({"built", "planned"})` to add `"seed"`
  (`{"built", "planned", "seed"}`). This alone makes the unknown-status guard accept
  `seed` and keep rejecting others (satisfies US2 / FR-001, FR-005).
- [ ] T009 [US1] In the per-route loop of `check_routes_resolve()`, add `seed` to the
  SAME "must resolve" treatment as `built`:
  (a) the no-targets guard (`status == "built" and not targets`) MUST also fire for
  `seed`;
  (b) the per-target existence check (`status == "built" and not resolved`) MUST also
  fire for `seed`.
  Keep the `planned`-resolves-stale branch UNCHANGED. Word the `seed` ERROR messages
  to name the `seed` status (not "built") for locator clarity. (FR-003, FR-004, FR-006,
  FR-007 -- verify-only, no promotion logic.)
- [ ] T010 [US1] Update the module docstring in `src/retail/rules/routes.py` to
  document the third `seed` state (exists-but-initial-seed; targets must resolve like
  built; never auto-promoted). ASCII only (`--`, `->`).
- [ ] T011 [US1] Run `pytest -m unit tests/unit/test_routes.py`; all `seed` tests
  (T002-T005) and the existing `built`/`planned` tests (T006) now PASS (GREEN).

---

## Phase 4: Manifest vocabulary (DEFINE-layer mirror)

- [ ] T012 [US1] In `docs/routing/routes.yaml`, update the `status  -- built |
  planned` header comment to `built | planned | seed` and add the one-line meaning:
  `seed -> target exists but is only an initial-seed surface; every target must
  resolve (same existence rule as built).` Do NOT flip any of the ~29 existing routes
  to `seed` (out-of-scope non-goal -- the feature adds capability, not a
  reclassification). ASCII only.

---

## Phase 5: Non-regression verification (the crux of the scope decision)

- [ ] T013 [P] [NR] Run `pytest -m unit tests/unit/test_rules_wiring.py`; CONFIRM
  `EXPECTED_RULE_IDS` is UNCHANGED, `A1` present exactly once, count unchanged
  (FR-008). No id added.
- [ ] T014 [P] [NR] `git diff --exit-code docs/rules/rules-manifest.json` and the
  severity-posture golden fixture -> CONFIRM both are byte-identical (no regen
  required, FR-008).
- [ ] T015 [NR] In `tests/unit/test_routes_coverage.py`, add/confirm a case where a
  route carries `status: seed`; assert the `A3` id-set bijection produces the same
  result as for the same route marked `built` (FR-009). Run
  `pytest -m unit tests/unit/test_routes_coverage.py` -> PASS.
- [ ] T016 [NR] Run the full gate set: `ruff check`, `pytest -m unit`,
  `retail check`, `retail semantic-check`. CONFIRM `retail check` passes on the
  branch (the on-main routes are all `built` and resolve; no `seed` route was added,
  so zero new findings -- a genuine, not vacuous, pass) and no B1/B3 import-boundary
  regression (the `yaml` import stays lazy).

---

## Phase 6: Generic / honesty audit

- [ ] T017 [P] Grep the rule, the manifest edit, and the new fixtures for any
  C086/pharmacy literal (dataset path, KPI name); CONFIRM none present (FR-013,
  Principle VII). Fixtures use generic placeholder route ids/paths.
- [ ] T018 CONFIRM no promotion/self-grant logic was added (no completeness/count
  threshold comparing a seed surface to a "complete" bar); the seed -> built
  criterion (FR-016) remains an open Principle-V `[NEEDS CLARIFICATION]`, unresolved
  in code (FR-007).

---

## Dependencies / ordering

- T001 before everything (correct src on path).
- Phase 2 (RED, T002-T007) strictly BEFORE Phase 3 (GREEN, T008-T011) -- TDD.
- T008 before T009 (widen the set before branching on it); T011 after T008-T010.
- Phase 4 (T012) after Phase 3 (rule must accept `seed` before the manifest documents
  it) -- though the manifest edit does not itself flip a route, so order is soft.
- Phase 5 non-regression after the rule + manifest edits.
- T017/T018 last (audit over the final diff).

## Parallelizable

- T002-T006 are independent test additions to the same file; write together, but they
  touch one file so treat `[P]` as "author in one editing pass".
- T013, T014, T017 are independent read-only checks -> genuinely parallel.

## Out of scope (do NOT create tasks for)

- No new rule module, no new rule id, no `EXPECTED_RULE_IDS` edit, no manifest/golden
  regen (FR-008).
- No SC1 (`status_claims.py`) third-state change (spec C3 -- open_for_human).
- No seed -> built promotion logic (FR-016 -- Principle-V, open).
- No executor / Power BI / live-surface completeness probe (FR-014).
