# Phase 0 Research: Live-Surface Protocol Conformance Test

All items below were verified by direct read of the repository at planning time.
There are no open unknowns.

## R1 -- The QueryRunner seam and the no-rows contract

- `src/retail/validate.py` defines `QueryRunner` as a `typing.Protocol` with a
  single method `run(self, sql: str, params: tuple = ()) -> list[tuple]`. Every
  live check reaches the database only through this method; the real psycopg2
  runner is built lazily in the CLI handler, so the module import path is
  driver-free.
- `check_reconciliation(runner, target)` runs one query per measure. When the
  query returns no rows (`if not rows:`), it appends a `Finding` with
  `rule_id="V-RC16"`, `severity=Severity.ERROR`, and continues. There is no
  blocked/deferred path; no-rows is an ERROR non-pass.
- `check_expected_value(runner, name, expected)` routes a non-ratio contract to
  `_check_single`, which runs one aggregate query. On `not rows or not rows[0]`
  it returns a single `V-L4` ERROR `Finding`. Same no-rows -> ERROR contract.

**Decision**: Assert against `Severity.ERROR` + `rule_id` `V-RC16` / `V-L4`.
**Rationale**: This is the verified production contract; the originating idea's
"blocked-deferred" wording does not match the code and must not be inherited.
**Alternatives rejected**: Introducing a new `BLOCKED`/`DEFERRED` `Severity` --
rejected because it is a behavior change to the live surface and breaks the
test-only / opens-nothing basis of the work.

## R2 -- Existing fakes and prior coverage

- `tests/unit/test_validate.py` and `tests/unit/test_value_proxy.py` each define
  a `FakeRunner` that returns scripted rows FIFO and appends each SQL string to
  a `.calls` list. They do NOT assert that the call-site interacts only through
  `.run()` (they record SQL but tolerate any other access because none is made
  today).
- `test_validate.py` covers reconciliation clean / mismatch / NULL-total but has
  NO empty-rows (no-rows) test.
- `test_value_proxy.py::test_check_no_rows_is_error` ALREADY proves no-rows ->
  ERROR for the value check.

**Decision**: Build a new `RecordingQueryRunner` that mirrors the FIFO scripting
pattern and additionally makes any non-`.run()` access a test failure. Add the
genuinely-missing reconciliation no-rows ERROR coverage; for the value check,
reference the existing no-rows test and add only the conformance proof.
**Rationale**: Avoids duplicating settled coverage; adds the two genuinely-new
surfaces (recording conformance + reconciliation no-rows).

## R3 -- Generic fixtures

- A `ReconcileTarget` (defined in `validate.py`) needs silver, gold, and a
  measures tuple. Use generic names (e.g. `silver.widgets`, `gold.fct_widgets`,
  measure `amount`) -- never C086/pharmacy names.
- The expected-value single-value contract needs a generic measure name and an
  arbitrary approved value/tolerance. Use a round, obviously-synthetic value
  (e.g. `100.00`) -- never the C086 `Decimal('1552071.00')`.

**Decision**: All fixtures use generic, obviously-synthetic names and values.
**Rationale**: Principle VII (C086 is an example, not the schema); avoids the
c086-leak the plan-review axis checks for.

## R4 -- Driver-absence as proof

- The dev dependency set carries no DB driver; the suite passes with psycopg2
  absent. The `RecordingQueryRunner` holds no connection object, so it cannot
  open anything.

**Decision**: The module imports no driver and constructs no connection; passing
with no driver installed is part of the proof (SC-001), not incidental.
