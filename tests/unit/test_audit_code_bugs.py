"""Regression tests for the LOW-severity code-bug findings in the external audit
(Report #1, 2026-06-26): #29 D8 M-string escape, #30 D9 1-or-2-digit ISO date,
#33 L3 trailing-`;`. (#28 cli return-vs-exit lives in test_cli_context.py.)
"""

from __future__ import annotations

import pytest

from seshat.metric_drift import check_measure_drift
from seshat.rules.dax import (
    _DATE_LITERAL,
    _M_STRING_LITERAL,
    _extract_m_string_bodies,
)

# A known drift case verbatim from test_metric_drift.py (denominator = all
# transactions, contract says known-status -> drift) and its approved contract.
_DEF_DISCOUNTED = {
    "additive": False,
    "numerator": {
        "aggregation": "count_rows",
        "filter": [{"column": "discount_applied", "op": "is_true"}],
    },
    "denominator": {
        "aggregation": "count_rows",
        "filter": [{"column": "discount_applied", "op": "is_not_null"}],
    },
}
_DRIFT_DAX = (
    "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
    "= TRUE()), [TransactionCount])"
)

pytestmark = pytest.mark.unit


# --- #30: D9 ISO-date regex must match 1-or-2-digit month/day ----------------


def test_d9_date_literal_matches_single_digit_month_and_day() -> None:
    """`2024-1-1` is a hardcoded date literal too; the ISO branch required two
    digits each (`\\d{4}-\\d{2}-\\d{2}`) and silently missed it (audit #30)."""
    assert _DATE_LITERAL.search("2024-1-1") is not None
    assert _DATE_LITERAL.search("2024-01-01") is not None  # still matches 2-digit
    assert _DATE_LITERAL.search("2024-12-9") is not None


def test_d9_date_literal_does_not_match_plain_arithmetic() -> None:
    """The widened branch must not start matching non-date `n-n-n` token runs that
    are not 4-digit-year-led (guard against over-broadening)."""
    # a 2- or 3-digit lead is not a year; must not match as an ISO date.
    assert _DATE_LITERAL.search("12-1-1") is None
    assert _DATE_LITERAL.search("999-1-1") is None


# --- #29: D8 M-string regex must respect the M `""` escape -------------------


def test_d8_m_string_literal_spans_escaped_double_quote() -> None:
    """In M, a doubled `""` is an escaped quote INSIDE one string literal.

    `"a""b"` is the single literal `a"b`, not `"a"` + `b` + `"`. The old
    `"([^"]*)"` split it at the inner quote, so schema tokens after an escaped
    quote could leak past D8's scan (audit #29).
    """
    m = _M_STRING_LITERAL.search('"a""b"')
    assert m is not None
    # The whole literal (including the escaped inner quotes) is one match.
    assert m.group(0) == '"a""b"'
    # And the extracted body is the true value `a"b`, with the escape collapsed.
    assert _extract_m_string_bodies('"a""b"') == ['a"b']


def test_d8_m_string_two_separate_literals_still_split() -> None:
    """Two genuinely separate literals must still be two bodies (no over-merge)."""
    assert _extract_m_string_bodies('"first" + "second"') == ["first", "second"]


# --- #33: L3 _outer_call must tolerate a trailing `;` ------------------------


def test_l3_accepts_trailing_semicolon_on_calculate_wrapper() -> None:
    """A measure body with a trailing `;` must still be drift-checked, not bypassed.

    `_outer_call` required the closing `)` to be the LAST char, so a non-standard
    trailing `;` (or whitespace) made the whole wrapper unrecognized -> the drift
    check silently no-op'd (audit #33).
    """
    # Same known-drift body as test_all_transactions_denominator_is_drift, but
    # with a trailing `;`. Drift must still be detected, not silently bypassed.
    v_clean = check_measure_drift(_DRIFT_DAX, _DEF_DISCOUNTED)
    assert v_clean.status == "drift", ("baseline must drift", v_clean)

    v_semi = check_measure_drift(_DRIFT_DAX + ";", _DEF_DISCOUNTED)
    assert v_semi.status == "drift", ("trailing ; must not bypass drift", v_semi)
