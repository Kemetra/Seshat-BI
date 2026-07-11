"""Unit tests for the L3 semantic-check core (src/seshat/semantic.py)."""

from __future__ import annotations

import pytest

from seshat.core import Severity
from seshat.metric_drift import Verdict
from seshat.semantic import MeasurePair, run_semantic_pairs, verdict_to_finding

pytestmark = pytest.mark.unit

DEF_AVG = {
    "additive": False,
    "numerator": {"aggregation": "sum", "filter": []},
    "denominator": {
        "aggregation": "count_rows",
        "filter": [{"column": "total_spent", "op": "is_not_null"}],
    },
}
DAX_AVG = (
    "DIVIDE([TotalSales], CALCULATE([TransactionCount], NOT(ISBLANK("
    "'gold fct_sales_rss'[total_spent]))))"
)


def test_verdict_drift_maps_to_error_finding() -> None:
    f = verdict_to_finding("M", "path.tmdl:3", Verdict("drift", "wrong denominator"))
    assert f is not None
    assert f.severity is Severity.ERROR
    assert f.rule_id == "L3"
    assert "M" in f.message
    assert f.locator == "path.tmdl:3"


def test_verdict_escalate_maps_to_warning_finding() -> None:
    f = verdict_to_finding("M", "path.tmdl:3", Verdict("escalate", "unknown predicate"))
    assert f is not None
    assert f.severity is Severity.WARNING


def test_verdict_pass_maps_to_none() -> None:
    assert verdict_to_finding("M", "p:1", Verdict("pass", "ok")) is None


def test_verdict_skip_maps_to_none() -> None:
    assert verdict_to_finding("M", "p:1", Verdict("skip", "no definition")) is None


def test_run_pairs_clean_passes_exit_zero() -> None:
    pairs = [MeasurePair("AvgTransactionValue", DAX_AVG, "p.tmdl:1", DEF_AVG)]
    findings, exit_code = run_semantic_pairs(pairs)
    assert findings == []
    assert exit_code == 0


def test_run_pairs_drift_exits_one() -> None:
    buggy_def = {
        "additive": False,
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_not_null"}],
        },
    }
    pairs = [MeasurePair("AvgTransactionValue", DAX_AVG, "p.tmdl:1", buggy_def)]
    findings, exit_code = run_semantic_pairs(pairs)
    assert exit_code == 1
    # #17: assert rule_id and measure name are present, not just severity
    assert any(
        f.rule_id == "L3"
        and f.severity is Severity.ERROR
        and "AvgTransactionValue" in f.message
        for f in findings
    )


def test_run_pairs_escalate_warns_but_exits_zero() -> None:
    escalate_def = {
        "additive": False,
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    escalate_dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "LEN('gold fct_sales_rss'[total_spent]) <> 0))"
    )
    pairs = [MeasurePair("AvgTransactionValue", escalate_dax, "p.tmdl:1", escalate_def)]
    findings, exit_code = run_semantic_pairs(pairs)
    assert exit_code == 0  # WARNING does not fail the gate
    # #17: assert rule_id and measure name are present, not just severity
    assert any(
        f.rule_id == "L3"
        and f.severity is Severity.WARNING
        and "AvgTransactionValue" in f.message
        for f in findings
    )
