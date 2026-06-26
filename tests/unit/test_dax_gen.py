"""Unit tests for the DAX Generator (src/retail/dax_gen.py).

Phase 1: kind:base + kind:ratio, generate -> verify -> refuse. The headline
property is the round-trip: every emitted measure re-verifies as `pass`.
"""

import pytest

from retail.dax_gen import GenResult

pytestmark = pytest.mark.unit


def test_genresult_success_populates_outputs_only():
    r = GenResult.success(dax="SUM(T[c])", tmdl_block="measure X = SUM(T[c])")
    assert r.ok is True
    assert r.dax == "SUM(T[c])"
    assert r.tmdl_block == "measure X = SUM(T[c])"
    assert r.reason is None


def test_genresult_refuse_has_none_outputs():
    r = GenResult.refuse("unsupported kind 'foo'")
    assert r.ok is False
    assert r.dax is None
    assert r.tmdl_block is None
    assert r.reason == "unsupported kind 'foo'"


def test_genresult_rejects_ok_without_dax():
    with pytest.raises(ValueError):
        GenResult(ok=True, dax=None, tmdl_block=None)


def test_genresult_rejects_refusal_with_dax():
    with pytest.raises(ValueError):
        GenResult(ok=False, dax="SUM(T[c])", reason="x")


from retail.dax_gen import _emit_base


def test_emit_base_sum_no_filter():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "sum",
         "source": {"table": "gold.fct_sales_rss", "column": "total_spent"}}
    )
    assert reason is None
    assert dax == "SUM('gold fct_sales_rss'[total_spent])"


def test_emit_base_count_rows_no_column():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.fct_sales_rss"}}
    )
    assert reason is None
    assert dax == "COUNTROWS('gold fct_sales_rss')"


def test_emit_base_with_filter_wraps_calculate():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.fct_sales_rss"},
         "filter": [{"column": "discount_applied", "op": "is_true"}]}
    )
    assert reason is None
    assert dax == (
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[discount_applied] = TRUE())"
    )


def test_emit_base_sum_without_column_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "sum",
         "source": {"table": "gold.fct_sales_rss"}}
    )
    assert dax is None
    assert "column" in reason


def test_emit_base_count_rows_with_column_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.fct_sales_rss", "column": "x"}}
    )
    assert dax is None
    assert "count_rows" in reason


def test_emit_base_non_gold_table_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "sum",
         "source": {"table": "silver.fct", "column": "c"}}
    )
    assert dax is None
    assert "gold" in reason


def test_emit_base_unknown_aggregation_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "median",
         "source": {"table": "gold.t", "column": "c"}}
    )
    assert dax is None
    assert "aggregation" in reason


def test_emit_base_unknown_filter_op_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.t"},
         "filter": [{"column": "c", "op": "is_weird"}]}
    )
    assert dax is None
    assert "op" in reason or "filter" in reason


from retail.dax_gen import _emit_ratio


def test_emit_ratio_inline_count_rows():
    dax, reason = _emit_ratio({
        "kind": "ratio",
        "numerator": {"aggregation": "count_rows",
                      "source": {"table": "gold.fct_sales_rss"},
                      "filter": [{"column": "discount_applied", "op": "is_true"}]},
        "denominator": {"aggregation": "count_rows",
                        "source": {"table": "gold.fct_sales_rss"},
                        "filter": [{"column": "discount_applied", "op": "is_not_null"}]},
    })
    assert reason is None
    assert dax == (
        "DIVIDE("
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[discount_applied] = TRUE()), "
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "NOT(ISBLANK('gold fct_sales_rss'[discount_applied]))))"
    )


def test_emit_ratio_refuses_bad_side():
    dax, reason = _emit_ratio({
        "kind": "ratio",
        "numerator": {"aggregation": "sum", "source": {"table": "gold.t"}},  # no column
        "denominator": {"aggregation": "count_rows", "source": {"table": "gold.t"}},
    })
    assert dax is None
    assert "column" in reason
