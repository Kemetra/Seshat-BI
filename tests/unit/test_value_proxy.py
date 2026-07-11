"""TDD tests for the L4 value proxy (src/seshat/value_proxy.py).

L4 re-computes a measure's aggregate against the live gold table and asserts it
still equals the contract's APPROVED value, within tolerance -- the live
counterpart to L3's static filter-set drift check (metric_drift.py).

Driver-free, mirroring validate.py: the check runs against a QueryRunner Protocol
(`run(sql, params) -> list[tuple]`), so these tests need no database and no
psycopg2. A value defect is Severity.ERROR (a proven regression), like validate's
penny-mismatch -- never a static WARNING.

Values are Decimal-exact: the contract carries them as quoted strings so YAML never
hands us a fragile float; the comparison is Decimal(str(...)) vs Decimal(str(...)).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.core import Severity
from seshat.value_proxy import (
    ExpectedValue,
    check_expected_value,
    parse_expected_value,
)

pytestmark = pytest.mark.unit


class FakeRunner:
    """A QueryRunner whose results are scripted per-call (FIFO); records SQL."""

    def __init__(self, results: list[list[tuple]]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.calls.append(sql)
        return self._results.pop(0) if self._results else []


# ---------------------------------------------------------------------------
# parse_expected_value -- pure; absent => None (skip); malformed => ValueError
# ---------------------------------------------------------------------------


def test_parse_absent_block_is_none_skip() -> None:
    """A contract with no expected_value block parses to None (the caller skips)."""
    definition = {"additive": False, "denominator": {}}
    binds_to = {"gold_table": "gold.fct_sales_rss"}
    assert parse_expected_value(definition, binds_to) is None


def test_parse_single_aggregate_block() -> None:
    definition = {
        "expected_value": {
            "value": "1552071.00",
            "tolerance_abs": "0.00",
            "aggregation": "sum",
            "column": "total_spent",
        }
    }
    binds_to = {"gold_table": "gold.fct_sales_rss"}
    ev = parse_expected_value(definition, binds_to)
    assert isinstance(ev, ExpectedValue)
    assert ev.value == Decimal("1552071.00")
    assert ev.tolerance_abs == Decimal("0.00")
    assert ev.aggregation == "sum"
    assert ev.column == "total_spent"
    assert ev.gold_table == "gold.fct_sales_rss"


def test_parse_value_is_decimal_not_float() -> None:
    """The string '1552071.00' must Decimal-parse exactly, never via a binary float."""
    definition = {
        "expected_value": {
            "value": "0.1",
            "tolerance_abs": "0",
            "aggregation": "sum",
            "column": "x",
        }
    }
    ev = parse_expected_value(definition, {"gold_table": "g.t"})
    assert ev is not None
    # Decimal('0.1') is exact; float 0.1 is 0.1000000000000000055...
    assert ev.value == Decimal("0.1")
    assert ev.value != Decimal(0.1)  # the fragile-float trap we are avoiding


def test_parse_ratio_block_needs_no_column() -> None:
    """aggregation: ratio recomputes num/den from the L3 blocks; no `column` needed."""
    definition = {
        "additive": False,
        "numerator": {"aggregation": "count_rows", "filter": []},
        "denominator": {"aggregation": "count_rows", "filter": []},
        "expected_value": {
            "value": "0.5037",
            "tolerance_abs": "0.0001",
            "aggregation": "ratio",
        },
    }
    ev = parse_expected_value(definition, {"gold_table": "gold.fct_sales_rss"})
    assert ev is not None
    assert ev.aggregation == "ratio"


def test_parse_malformed_unknown_aggregation_raises() -> None:
    definition = {
        "expected_value": {
            "value": "1",
            "tolerance_abs": "0",
            "aggregation": "median",  # not in the whitelist
            "column": "x",
        }
    }
    with pytest.raises(ValueError, match="aggregation"):
        parse_expected_value(definition, {"gold_table": "g.t"})


def test_parse_malformed_missing_column_for_aggregate_raises() -> None:
    definition = {
        "expected_value": {"value": "1", "tolerance_abs": "0", "aggregation": "sum"}
    }
    with pytest.raises(ValueError, match="column"):
        parse_expected_value(definition, {"gold_table": "g.t"})


def test_parse_malformed_non_numeric_value_raises() -> None:
    definition = {
        "expected_value": {
            "value": "not-a-number",
            "tolerance_abs": "0",
            "aggregation": "sum",
            "column": "x",
        }
    }
    with pytest.raises(ValueError, match="value"):
        parse_expected_value(definition, {"gold_table": "g.t"})


def test_parse_missing_gold_table_raises() -> None:
    definition = {
        "expected_value": {
            "value": "1",
            "tolerance_abs": "0",
            "aggregation": "sum",
            "column": "x",
        }
    }
    with pytest.raises(ValueError, match="gold_table"):
        parse_expected_value(definition, {})


# ---------------------------------------------------------------------------
# check_expected_value -- single aggregate against a fake runner
# ---------------------------------------------------------------------------


def _ev(**kw) -> ExpectedValue:
    base = dict(
        value=Decimal("1552071.00"),
        tolerance_abs=Decimal("0.00"),
        aggregation="sum",
        column="total_spent",
        gold_table="gold.fct_sales_rss",
    )
    base.update(kw)
    return ExpectedValue(**base)


def test_check_exact_match_no_finding() -> None:
    runner = FakeRunner([[(Decimal("1552071.00"),)]])
    findings = list(check_expected_value(runner, "TotalSales", _ev()))
    assert findings == []
    # SQL aggregates the quoted column from the quoted gold table
    sql = runner.calls[0]
    assert '"total_spent"' in sql
    assert '"gold"."fct_sales_rss"' in sql
    assert "sum(" in sql.lower()


def test_check_within_tolerance_no_finding() -> None:
    runner = FakeRunner([[(Decimal("1552071.50"),)]])
    findings = list(
        check_expected_value(runner, "TotalSales", _ev(tolerance_abs=Decimal("1.00")))
    )
    assert findings == []


def test_check_on_tolerance_boundary_is_inclusive_pass() -> None:
    """|gap| == tolerance is a PASS (inclusive boundary)."""
    runner = FakeRunner([[(Decimal("1552072.00"),)]])
    findings = list(
        check_expected_value(runner, "TotalSales", _ev(tolerance_abs=Decimal("1.00")))
    )
    assert findings == []


def test_check_outside_tolerance_is_error() -> None:
    runner = FakeRunner([[(Decimal("1400000.00"),)]])
    findings = list(check_expected_value(runner, "TotalSales", _ev()))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert findings[0].rule_id == "V-L4"
    assert "TotalSales" in findings[0].message


def test_check_no_rows_is_error() -> None:
    runner = FakeRunner([[]])
    findings = list(check_expected_value(runner, "TotalSales", _ev()))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


def test_check_null_aggregate_is_error() -> None:
    runner = FakeRunner([[(None,)]])
    findings = list(check_expected_value(runner, "TotalSales", _ev()))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


def test_check_unparseable_aggregate_is_error() -> None:
    runner = FakeRunner([[("not-a-number",)]])
    findings = list(check_expected_value(runner, "TotalSales", _ev()))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


def test_check_rejects_unsafe_identifiers() -> None:
    """A malicious gold_table/column must be rejected by the identifier quoting,
    before any SQL is built (same hardening as validate.py)."""
    runner = FakeRunner([])
    ev = _ev(gold_table="gold.fct; DROP TABLE gold.x")
    with pytest.raises(ValueError, match="unsafe SQL identifier"):
        list(check_expected_value(runner, "TotalSales", ev))
    assert runner.calls == []


# ---------------------------------------------------------------------------
# check_expected_value -- ratio (recompute numerator-count / denominator-count)
# ---------------------------------------------------------------------------


def _ratio_ev(**kw) -> ExpectedValue:
    base = dict(
        value=Decimal("0.5037"),
        tolerance_abs=Decimal("0.0001"),
        aggregation="ratio",
        column=None,
        gold_table="gold.fct_sales_rss",
        numerator_count_sql_filter='"discount_applied" = TRUE',
        denominator_count_sql_filter='"discount_applied" IS NOT NULL',
    )
    base.update(kw)
    return ExpectedValue(**base)


def test_check_ratio_match_no_finding() -> None:
    # numerator 4219, denominator 8376 -> 0.50370... within 0.0001 of 0.5037
    runner = FakeRunner([[(4219,)], [(8376,)]])
    findings = list(
        check_expected_value(runner, "DiscountedTransactionRate", _ratio_ev())
    )
    assert findings == []
    assert len(runner.calls) == 2  # one count for numerator, one for denominator


def test_check_ratio_drift_is_error() -> None:
    # numerator 4219, denominator 12575 -> 0.3355 (the floor bug) -> outside tolerance
    runner = FakeRunner([[(4219,)], [(12575,)]])
    findings = list(
        check_expected_value(runner, "DiscountedTransactionRate", _ratio_ev())
    )
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert findings[0].rule_id == "V-L4"


def test_check_ratio_zero_denominator_is_error() -> None:
    """A zero denominator must not raise ZeroDivisionError; it's an ERROR finding."""
    runner = FakeRunner([[(0,)], [(0,)]])
    findings = list(
        check_expected_value(runner, "DiscountedTransactionRate", _ratio_ev())
    )
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
