---
description: "Task list for Live-Surface Protocol Conformance Test"
---

# Tasks: Live-Surface Protocol Conformance Test (fake QueryRunner)

**Input**: Design documents from `/specs/044-live-surface-protocol/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This feature IS a test module. The "implementation" deliverable is
the pytest module itself; there is no separate production code to write.

**Organization**: Tasks are grouped by the two user stories. Both land in the
same new file (`tests/unit/test_live_surface_protocol.py`), so the per-story
tasks are sequential within that file rather than parallel.

## Path Conventions

Single project: `src/retail/` (read-only here), `tests/unit/` (the new file).

---

## Phase 1: Setup

- [ ] T001 Create `tests/unit/test_live_surface_protocol.py` with a module
  docstring stating: test-only; exercises `check_reconciliation`
  (`src/retail/validate.py`) and `check_expected_value`
  (`src/retail/value_proxy.py`) without a database; runtime complement to the
  static `never_execute.py` (B1) guard; asserts the existing ERROR contract and
  introduces no new `Severity`/status. Set `pytestmark = pytest.mark.unit`.
  Import `Severity` (and `Finding` as needed) from `retail.core`. (FR-001)

---

## Phase 2: Foundational (the recording fake -- blocks both stories)

- [ ] T002 Implement `RecordingQueryRunner` in the new module: constructed with a
  FIFO list of scripted row-lists (mirrors the existing `FakeRunner`); `run(self,
  sql, params=()) -> list[tuple]` records each invocation and returns the next
  scripted result (or `[]` when exhausted); holds NO connection/cursor/driver;
  makes any access to a non-`run` database-shaped attribute observable as a
  failure (e.g. `__getattr__` raising `AssertionError` for `connection` /
  `cursor` / `execute`). (FR-002, FR-003, FR-006; data-model.md)

**Checkpoint**: The fake exists and opens nothing; both stories can build on it.

---

## Phase 3: User Story 1 -- Reconciliation conformance + no-rows ERROR (P1)

**Goal**: Prove `check_reconciliation` uses only `.run()` and emits a `V-RC16`
ERROR on no rows. **Independent test**: this phase's tests pass on their own.

- [ ] T003 [US1] Add a generic reconciliation fixture: a `ReconcileTarget`
  (imported from `retail.validate`) with generic silver/gold names and a generic
  one-element measures tuple (e.g. `silver.widgets`, `gold.fct_widgets`,
  `amount`). No C086/pharmacy names. (FR-009; data-model.md)
- [ ] T004 [US1] Test `test_reconciliation_no_rows_is_error`: inject a
  `RecordingQueryRunner` scripted with one empty result; run
  `check_reconciliation`; assert exactly one `Finding`, `severity ==
  Severity.ERROR`, `rule_id == "V-RC16"`. (FR-004, C2)
- [ ] T005 [US1] Test `test_reconciliation_uses_only_run`: from the same run,
  assert the call-site invoked only `.run()` (no other runner attribute was
  accessed) and did NOT assert against exact SQL text. (FR-006, FR-012, C1, C5)
- [ ] T006 [US1] Test `test_reconciliation_passing_result_no_finding` (control):
  inject a `RecordingQueryRunner` scripted with one reconciling row (equal
  silver/gold totals, e.g. `[(100, 100)]`); assert NO finding -- proving the
  ERROR in T004 is caused by the empty result. (FR-007, C3)

**Checkpoint**: Reconciliation conformance + no-rows ERROR + control all pass.

---

## Phase 4: User Story 2 -- Value-proxy conformance + no-rows ERROR (P2)

**Goal**: Prove `check_expected_value` uses only `.run()` and emits a `V-L4`
ERROR on no rows, complementing (not duplicating) the existing no-rows test.

- [ ] T007 [US2] Add a generic single-value expected-value fixture: build a
  non-ratio expected-value contract via the existing constructor/parser in
  `retail.value_proxy`, with a generic measure name and an arbitrary approved
  value/tolerance (e.g. value `100.00`, tolerance `0.00`). No C086 figure.
  (FR-009; data-model.md)
- [ ] T008 [US2] Test `test_value_check_no_rows_is_error`: inject a
  `RecordingQueryRunner` scripted with one empty result; run
  `check_expected_value`; assert exactly one `Finding`, `severity ==
  Severity.ERROR`, `rule_id == "V-L4"`. Add a code comment referencing
  `tests/unit/test_value_proxy.py::test_check_no_rows_is_error` as the prior art
  this complements. (FR-005, FR-010, C2)
- [ ] T009 [US2] Test `test_value_check_uses_only_run`: from the same run, assert
  the call-site invoked only `.run()`; no exact-SQL-text assertion. (FR-006,
  FR-012, C1, C5)
- [ ] T010 [US2] Test `test_value_check_passing_result_no_finding` (control):
  inject a `RecordingQueryRunner` scripted with one within-tolerance row (e.g.
  `[(100.00,)]`); assert NO finding. (FR-007, C3)

**Checkpoint**: Value-proxy conformance + no-rows ERROR + control all pass.

---

## Phase 5: Polish & Verification

- [ ] T011 Run `pytest -m unit tests/unit/test_live_surface_protocol.py` with no
  DB driver installed; confirm it passes and opens no connection. (FR-011,
  SC-001)
- [ ] T012 Self-review against the contract: no new `Severity`/status (C4,
  FR-008); no C086/pharmacy value or gold name (C7, FR-009, SC-005); ASCII /
  UTF-8 without BOM; no modification to `validate.py`, `value_proxy.py`, or
  `never_execute.py` (FR-001). Optionally run the full `tests/unit` suite to
  confirm no regression.

---

## Dependencies

- T001 -> T002 -> (US1: T003 -> T004,T005,T006) and (US2: T007 -> T008,T009,T010).
- US1 and US2 share the one new file, so they are sequential within the file
  (not parallel), though logically independent.
- T011, T012 run after all test tasks.

## Notes

- No production code is created or modified; the only new file is
  `tests/unit/test_live_surface_protocol.py`.
- No new dependency is added; pytest + stdlib only.
- No dependency on any deferred capability (F016 Power BI execution adapter,
  F031-F033 runtimes).
