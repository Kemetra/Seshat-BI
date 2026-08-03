"""Live figures, compiled from approved contracts and fetched through a fake.

No driver is imported anywhere in this module's import path -- the same discipline
`validate.py` and `value_proxy.py` keep -- so every compilation rule and every
refusal is verifiable with no database present.

What is NOT verified here is that the compiled SQL returns the right answer from a
real Postgres. That boundary is stated in the design and lives in
`tests/live_db/`.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from seshat.report.model import ReportError
from seshat.report.observe import (
    FigureRequest,
    compile_query,
    observe,
)

pytestmark = pytest.mark.unit

_BASE = {
    "name": "TotalSales",
    "binds_to": {"gold_table": "gold.fct_sales_rss", "columns": ["total_spent"]},
    "definition": {"kind": "base", "aggregation": "sum", "filter": []},
}

_COUNT = {
    "name": "TransactionCount",
    "binds_to": {"gold_table": "gold.fct_sales_rss", "columns": ["transaction_id"]},
    "definition": {"kind": "base", "aggregation": "count_rows", "filter": []},
}

_RATIO = {
    "name": "DiscountedTransactionRate",
    "binds_to": {"gold_table": "gold.fct_sales_rss", "columns": ["discount_applied"]},
    "definition": {
        "numerator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_true"}],
        },
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_not_null"}],
        },
        # The EXPLICIT rate declaration. Structural division is not enough: an
        # average also divides and is not a percentage.
        "expected_value": {
            "value": "0.5037",
            "tolerance_abs": "0.0001",
            "aggregation": "ratio",
        },
    },
}


class FakeRunner:
    """Records the SQL it was asked to run and replays canned rows."""

    def __init__(self, rows: list[tuple] | None = None) -> None:
        self.rows = rows if rows is not None else [(Decimal("1552071"),)]
        self.sql: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.sql.append(sql)
        return self.rows


def _request(contract_id: str = "TotalSales", **kwargs) -> FigureRequest:
    defaults = {
        "visual_id": "v01",
        "contract_id": contract_id,
        "unit_kind": "currency",
        "label": None,
    }
    return FigureRequest(**{**defaults, **kwargs})


# --- compilation ------------------------------------------------------------


def test_a_sum_compiles_to_one_aggregate() -> None:
    query = compile_query(_BASE)
    assert query.sql == 'SELECT sum("total_spent") FROM "gold"."fct_sales_rss"'
    assert query.is_ratio is False


def test_a_row_count_needs_no_column() -> None:
    query = compile_query(_COUNT)
    assert query.sql == 'SELECT count(*) FROM "gold"."fct_sales_rss"'


def test_a_ratio_compiles_to_one_query_over_one_snapshot() -> None:
    """Both counts in a single statement, so the numerator and denominator cannot
    straddle a write and produce a ratio that never existed."""
    query = compile_query(_RATIO)
    assert query.is_ratio is True
    assert query.sql.count("SELECT") == 1
    assert 'count(*) FILTER (WHERE "discount_applied" IS TRUE)' in query.sql
    assert 'count(*) FILTER (WHERE "discount_applied" IS NOT NULL)' in query.sql


def test_a_filter_on_a_base_aggregate_becomes_a_where_clause() -> None:
    contract = {
        **_BASE,
        "definition": {
            "kind": "base",
            "aggregation": "sum",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    assert 'WHERE "total_spent" IS NOT NULL' in compile_query(contract).sql


def test_an_unknown_aggregation_refuses() -> None:
    contract = {**_BASE, "definition": {"kind": "base", "aggregation": "median"}}
    with pytest.raises(ReportError, match="aggregation 'median'"):
        compile_query(contract)


def test_an_unknown_filter_op_refuses_rather_than_dropping_it() -> None:
    """A dropped filter changes the number without changing the citation."""
    contract = {
        **_BASE,
        "definition": {
            "kind": "base",
            "aggregation": "sum",
            "filter": [{"column": "total_spent", "op": "greater_than_zero"}],
        },
    }
    with pytest.raises(ReportError, match="filter op 'greater_than_zero'"):
        compile_query(contract)


def test_a_column_aggregate_without_a_column_refuses() -> None:
    contract = {
        "name": "X",
        "binds_to": {"gold_table": "gold.t", "columns": []},
        "definition": {"kind": "base", "aggregation": "sum"},
    }
    with pytest.raises(ReportError, match="needs a bound column"):
        compile_query(contract)


def test_a_missing_gold_table_refuses() -> None:
    contract = {**_BASE, "binds_to": {"columns": ["total_spent"]}}
    with pytest.raises(ReportError, match="binds_to.gold_table"):
        compile_query(contract)


def test_an_unsafe_identifier_refuses_before_any_sql_is_built() -> None:
    contract = {
        **_BASE,
        "binds_to": {"gold_table": "gold.t; DROP TABLE x", "columns": ["c"]},
    }
    with pytest.raises((ReportError, ValueError)):
        compile_query(contract)


def test_a_definition_that_is_neither_family_refuses() -> None:
    contract = {**_BASE, "definition": {"kind": "calculated", "expression": "1+1"}}
    with pytest.raises(ReportError, match="neither a base aggregate nor a ratio"):
        compile_query(contract)


# --- observing --------------------------------------------------------------


def test_a_scalar_becomes_an_exact_decimal() -> None:
    runner = FakeRunner([(Decimal("1552071"),)])
    result = observe(runner, [_request()], {"TotalSales": _BASE})
    assert result[0]["value"] == Decimal("1552071")
    assert isinstance(result[0]["value"], Decimal)
    assert result[0]["contract_id"] == "TotalSales"
    assert result[0]["metric"] == "TotalSales"


def test_a_float_from_the_driver_is_parsed_through_its_string_form() -> None:
    """Going via str() is what keeps a driver's float from poisoning the figure."""
    runner = FakeRunner([(123.42,)])
    result = observe(runner, [_request()], {"TotalSales": _BASE})
    assert result[0]["value"] == Decimal("123.42")


def test_a_ratio_divides_the_two_counts() -> None:
    runner = FakeRunner([(6337, 12580)])
    result = observe(
        runner,
        [_request("DiscountedTransactionRate", unit_kind="ratio")],
        {"DiscountedTransactionRate": _RATIO},
    )
    assert result[0]["value"] == Decimal(6337) / Decimal(12580)


def test_no_rows_yields_pending_not_a_number() -> None:
    result = observe(FakeRunner([]), [_request()], {"TotalSales": _BASE})
    assert result[0]["value"] is None


def test_a_null_scalar_yields_pending() -> None:
    result = observe(FakeRunner([(None,)]), [_request()], {"TotalSales": _BASE})
    assert result[0]["value"] is None


def test_an_unparseable_scalar_yields_pending() -> None:
    result = observe(FakeRunner([("n/a",)]), [_request()], {"TotalSales": _BASE})
    assert result[0]["value"] is None


def test_a_zero_ratio_denominator_yields_pending_not_a_crash() -> None:
    runner = FakeRunner([(0, 0)])
    result = observe(
        runner,
        [_request("DiscountedTransactionRate", unit_kind="ratio")],
        {"DiscountedTransactionRate": _RATIO},
    )
    assert result[0]["value"] is None


def test_a_labelled_request_refuses_because_the_grouping_is_not_governed() -> None:
    """The grouping column lives only in the binding map's prose table. Inferring
    it would make the report the place a breakdown is decided."""
    with pytest.raises(ReportError, match="breakdown"):
        observe(
            FakeRunner(),
            [_request(label="North", visual_id="v06")],
            {"TotalSales": _BASE},
        )


def test_a_request_for_a_contract_that_was_not_supplied_refuses() -> None:
    with pytest.raises(ReportError, match="no approved contract"):
        observe(FakeRunner(), [_request("Invented")], {"TotalSales": _BASE})


def test_a_ratio_contract_declared_as_currency_refuses() -> None:
    """The one unit fact that IS derivable, checked rather than trusted."""
    with pytest.raises(ReportError, match="declares itself a rate"):
        observe(
            FakeRunner(),
            [_request("DiscountedTransactionRate", unit_kind="currency")],
            {"DiscountedTransactionRate": _RATIO},
        )


def test_a_base_contract_declared_as_ratio_refuses() -> None:
    with pytest.raises(ReportError, match="does not declare itself a rate"):
        observe(FakeRunner(), [_request(unit_kind="ratio")], {"TotalSales": _BASE})


def test_reading_gold_never_reports_a_readiness_pass() -> None:
    """A successful live read is data, not an approval."""
    result = observe(FakeRunner(), [_request()], {"TotalSales": _BASE})
    assert "status" not in result[0]
    assert "readiness" not in result[0]


def test_the_observation_shape_is_what_the_bundle_already_consumes() -> None:
    """The seam does not move, which is the point of putting it at the bundle."""
    result = observe(FakeRunner(), [_request()], {"TotalSales": _BASE})
    assert set(result[0]) == {
        "visual_id",
        "contract_id",
        "metric",
        "unit_kind",
        "label",
        "value",
    }


# --- the real committed contracts -------------------------------------------


def _committed(name: str) -> dict:
    path = (
        Path(__file__).parents[2]
        / "mappings/retail_store_sales/metrics"
        / f"{name}.yaml"
    )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    [
        "TotalSales",
        "TotalQuantity",
        "TransactionCount",
        "AvgTransactionValue",
        "DiscountedTransactionRate",
    ],
)
def test_every_approved_contract_compiles(name: str) -> None:
    """All five shipped contracts, not fixtures resembling them.

    A contract this module cannot compile is a contract whose figure can never go
    live, so the coverage is asserted rather than assumed.
    """
    query = compile_query(_committed(name))
    assert query.sql.startswith("SELECT ")
    assert '"gold"."fct_sales_rss"' in query.sql


def test_the_revenue_contract_compiles_to_the_sum_its_evidence_records() -> None:
    """Its readiness evidence records a penny-exact total_spent sum, so the live
    statement had better be exactly that sum."""
    query = compile_query(_committed("TotalSales"))
    assert query.sql == 'SELECT sum("total_spent") FROM "gold"."fct_sales_rss"'
    assert query.is_ratio is False


def test_the_discount_rate_is_recognized_as_a_ratio() -> None:
    query = compile_query(_committed("DiscountedTransactionRate"))
    assert query.is_ratio is True
    assert "IS TRUE" in query.sql and "IS NOT NULL" in query.sql


def test_the_average_contract_divides_a_sum_by_a_filtered_count() -> None:
    """AvgTransactionValue's two sides aggregate DIFFERENTLY -- sum over count --
    and its denominator counts only rows with a known amount. Both sides still
    resolve in one statement, so the average cannot be taken across a write."""
    query = compile_query(_committed("AvgTransactionValue"))
    assert query.is_ratio is True
    assert query.sql.count("SELECT") == 1
    assert 'sum("total_spent")' in query.sql
    assert 'count(*) FILTER (WHERE "total_spent" IS NOT NULL)' in query.sql


def test_a_filtered_column_aggregate_excludes_rows_rather_than_zeroing_them() -> None:
    """A CASE with no ELSE yields NULL, which sum/avg skip. An ELSE 0 would drag
    an average down by every excluded row."""
    contract = {
        "name": "Filtered",
        "binds_to": {"gold_table": "gold.t", "columns": ["amount"]},
        "definition": {
            "numerator": {
                "aggregation": "average",
                "filter": [{"column": "amount", "op": "is_not_null"}],
            },
            "denominator": {"aggregation": "count_rows", "filter": []},
        },
    }
    sql = compile_query(contract).sql
    assert 'avg(CASE WHEN "amount" IS NOT NULL THEN "amount" END)' in sql
    assert "ELSE 0" not in sql


def test_an_average_divides_but_is_not_a_rate() -> None:
    """The distinction that is easy to get backwards, pinned.

    AvgTransactionValue's SQL divides a sum by a count, exactly as a rate's does.
    It is money per transaction, so it renders as 123.42 and NOT as 1.23%. Keying
    the unit check on "the query divides" instead of "the contract declares a rate"
    would force it to a percentage.
    """
    contract = _committed("AvgTransactionValue")
    query = compile_query(contract)
    assert query.is_ratio is True  # the SQL shape
    result = observe(
        FakeRunner([(Decimal("1552071"), 12575)]),
        [_request("AvgTransactionValue", unit_kind="currency")],
        {"AvgTransactionValue": contract},
    )
    assert result[0]["value"] == Decimal("1552071") / Decimal(12575)


def test_an_average_declared_as_a_rate_refuses() -> None:
    """The inverse guard: it is not a rate, so it may not be shown as one."""
    contract = _committed("AvgTransactionValue")
    with pytest.raises(ReportError, match="does not declare itself a rate"):
        observe(
            FakeRunner([(Decimal("1"), 1)]),
            [_request("AvgTransactionValue", unit_kind="ratio")],
            {"AvgTransactionValue": contract},
        )


def test_the_shipped_rate_contract_declares_itself_one() -> None:
    from seshat.report.model import declares_a_rate

    assert declares_a_rate(_committed("DiscountedTransactionRate")) is True
    assert declares_a_rate(_committed("AvgTransactionValue")) is False
    assert declares_a_rate(_committed("TotalSales")) is False
