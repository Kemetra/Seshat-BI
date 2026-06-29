# Phase 1 Data Model: Live-Surface Protocol Conformance Test

This feature adds no production data model. The "entities" below are test-only
constructs living inside `tests/unit/test_live_surface_protocol.py`.

## RecordingQueryRunner (test-only fake)

Satisfies the `QueryRunner` Protocol and records its use.

- **Constructed with**: a list of scripted results (one row-list per expected
  `.run()` call, consumed FIFO -- mirrors the existing `FakeRunner` pattern).
- **`run(sql, params=()) -> list[tuple]`**: records the invocation (at minimum a
  count and the SQL string, for optional inspection) and returns the next
  scripted result, or an empty list when scripts are exhausted.
- **Conformance recording**: the fake makes any access to an attribute other
  than `run` observable as a test failure. The exact mechanism is an
  implementation detail (for example, the fake exposes only `run` and a recorder,
  and a `__getattr__` raises `AssertionError` on any other database-shaped
  attribute such as `connection`, `cursor`, or `execute`). The test asserts
  `.run()` was the only Protocol method exercised.
- **Holds no**: connection, cursor, driver import, socket, or credential.

## Generic reconciliation fixture

- A `ReconcileTarget` (from `retail.validate`) with generic `silver`, `gold`,
  and a one-element `measures` tuple -- e.g. silver `silver.widgets`, gold
  `gold.fct_widgets`, measure `amount`. No C086/pharmacy names.
- **No-rows variant**: scripted result is one empty row-list, driving the
  `V-RC16` ERROR branch.
- **Passing variant**: scripted result is one row with equal silver/gold totals
  (e.g. `[(100, 100)]`), driving the no-finding branch (control case).

## Generic single-value expected-value fixture

- A single-value (non-ratio) expected-value contract with a generic measure
  name and an arbitrary approved value + tolerance -- e.g. value `100.00`,
  tolerance `0.00`. No C086 figure.
- **No-rows variant**: scripted result is one empty row-list, driving the `V-L4`
  ERROR branch.
- **Passing variant**: scripted result is one row at the approved value (e.g.
  `[(100.00,)]`), within tolerance, driving the no-finding branch (control case).

## Asserted outputs

- `Finding` objects from `retail.core`: the test reads `.severity`
  (`Severity.ERROR`) and `.rule_id` (`V-RC16` / `V-L4`). The test introduces no
  new `Severity` or status value.
