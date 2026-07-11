"""Live-Surface Protocol conformance test (feature 044) -- TEST-ONLY.

Exercises ``check_reconciliation`` (src/seshat/validate.py) and
``check_expected_value`` (src/seshat/value_proxy.py) WITHOUT a database. It is the
runtime/dynamic complement to the static AST guard in
``src/seshat/rules/never_execute.py`` (the "B1" module-scope-import guard): where
B1 proves no driver is imported at module scope, this module proves at runtime
that the live call-sites talk to the injected runner only through the
``QueryRunner`` Protocol method ``.run()`` -- so the surface opens nothing.

It asserts the EXISTING ERROR contract (no-rows -> a ``Severity.ERROR`` Finding,
``rule_id`` ``V-RC16`` for reconciliation, ``V-L4`` for the value check) and
introduces NO new ``Severity`` or status (there is no BLOCKED/DEFERRED member).
It modifies neither ``validate.py``, ``value_proxy.py``, nor ``never_execute.py``.
Generic fixtures only -- no C086/pharmacy values or gold names (Principle VII).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.core import Finding, Severity
from seshat.validate import ReconcileTarget, check_reconciliation
from seshat.value_proxy import ExpectedValue, check_expected_value

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# The recording fake (T002): satisfies the QueryRunner Protocol with .run()
# alone, records each invocation, and surfaces any other database-shaped
# attribute access as a test failure. Holds no connection/cursor/driver.
# ---------------------------------------------------------------------------


class RecordingQueryRunner:
    """A QueryRunner that implements ONLY ``run`` and records every invocation.

    Constructed with a FIFO list of scripted row-lists (mirrors the existing
    ``FakeRunner`` in test_validate.py / test_value_proxy.py). Each ``run`` call
    records the SQL and returns the next scripted result (or ``[]`` when the
    scripts are exhausted). It holds no connection, cursor, driver import,
    socket, or credential.

    Conformance recording: any access to a database-shaped attribute other than
    ``run`` (e.g. ``connection``, ``cursor``, ``execute``) raises
    ``AssertionError`` via ``__getattr__``, so a call-site that strays off the
    Protocol method fails a test instead of silently passing. Dunder lookups are
    excluded (raised as ``AttributeError``) so normal introspection is unaffected
    and recursion is avoided.
    """

    def __init__(self, results: list[list[tuple]]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.calls.append(sql)
        return self._results.pop(0) if self._results else []

    def __getattr__(self, name: str) -> object:
        # _results / calls are set in __init__, so they are found normally and
        # never reach here (no recursion). Dunders are ordinary introspection.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        raise AssertionError(
            f"call-site touched non-run runner attribute {name!r} "
            "-- the live surface must reach the database only through .run()"
        )


# ---------------------------------------------------------------------------
# Generic fixtures (no C086/pharmacy names or values)
# ---------------------------------------------------------------------------


def _reconcile_target() -> ReconcileTarget:
    """A generic reconciliation target -- one measure so the check yields at most
    one finding (T003, FR-009)."""
    return ReconcileTarget(
        silver="silver.widgets",
        gold="gold.fct_widgets",
        measures=("amount",),
    )


def _expected_value() -> ExpectedValue:
    """A generic single-value (non-ratio) expected-value contract: arbitrary
    approved value 100.00, tolerance 0.00, against a generic gold table/column
    (T007, FR-009)."""
    return ExpectedValue(
        value=Decimal("100.00"),
        tolerance_abs=Decimal("0.00"),
        aggregation="sum",
        column="amount",
        gold_table="gold.fct_widgets",
    )


# ===========================================================================
# User Story 1 (P1): reconciliation conformance + no-rows ERROR
# ===========================================================================


def test_reconciliation_no_rows_is_error() -> None:
    """T004: an empty result drives the V-RC16 ERROR branch (FR-004, C2)."""
    runner = RecordingQueryRunner([[]])  # one empty row-list
    findings = check_reconciliation(runner, _reconcile_target())
    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, Finding)
    assert finding.severity == Severity.ERROR
    assert finding.rule_id == "V-RC16"


def test_reconciliation_uses_only_run() -> None:
    """T005: the call-site reaches the runner only through .run() (FR-006, C1).

    The fake's __getattr__ raises on any non-run attribute, so reaching the end
    of the call without an AssertionError is the proof. We assert .run() WAS
    used (call recorded) but do NOT assert exact SQL text (FR-012, C5)."""
    runner = RecordingQueryRunner([[]])
    check_reconciliation(runner, _reconcile_target())
    # .run() was the only Protocol method exercised: a recorded call, and no
    # AssertionError from __getattr__ for connection/cursor/execute.
    assert len(runner.calls) == 1


def test_reconciliation_passing_result_no_finding() -> None:
    """T006 (control): equal silver/gold totals -> NO finding, proving the T004
    ERROR is caused by the empty result, not by the harness (FR-007, C3)."""
    runner = RecordingQueryRunner([[(100, 100)]])  # reconciling totals
    findings = check_reconciliation(runner, _reconcile_target())
    assert findings == []


# ===========================================================================
# User Story 2 (P2): value-proxy conformance + no-rows ERROR
# ===========================================================================


def test_value_check_no_rows_is_error() -> None:
    """T008: an empty result drives the V-L4 ERROR branch (FR-005, C2).

    Complements -- does not duplicate --
    tests/unit/test_value_proxy.py::test_check_no_rows_is_error (the prior art
    that first proved no-rows -> V-L4 ERROR); the new value here is the
    recording-fake Protocol-conformance proof applied to this call-site
    (FR-010)."""
    runner = RecordingQueryRunner([[]])  # one empty row-list
    findings = list(check_expected_value(runner, "amount", _expected_value()))
    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, Finding)
    assert finding.severity == Severity.ERROR
    assert finding.rule_id == "V-L4"


def test_value_check_uses_only_run() -> None:
    """T009: the call-site reaches the runner only through .run() (FR-006, C1);
    no exact-SQL-text assertion (FR-012, C5)."""
    runner = RecordingQueryRunner([[]])
    list(check_expected_value(runner, "amount", _expected_value()))
    assert len(runner.calls) == 1


def test_value_check_passing_result_no_finding() -> None:
    """T010 (control): a within-tolerance value -> NO finding (FR-007, C3)."""
    runner = RecordingQueryRunner([[(Decimal("100.00"),)]])  # at the approved value
    findings = list(check_expected_value(runner, "amount", _expected_value()))
    assert findings == []
