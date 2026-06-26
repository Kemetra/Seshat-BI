"""TDD tests for the L3 contract<->DAX drift check (src/retail/metric_drift.py).

L3 of the layered DAX governance system: does a DIVIDE-based measure's DENOMINATOR
apply the filter the approved metric contract's structured `definition` declares? This
is the 50.37-vs-33.55 class -- a measure that is valid, best-practice-clean DAX yet
divides by the WRONG row-set.

Design invariants this suite locks in (from the design workflow + adversary red-team):
  * The CONTRACT's structured definition is the SOLE arbiter of direction -- never the
    DAX shape, never prose inference (the workflow's own scouts inverted 33.55/50.37 by
    reading prose; a deterministic filter-set comparison cannot be inference-inverted).
  * ESCALATE is the DEFAULT branch: a recognized predicate is compared; ANYTHING
    unrecognized escalates to a human. Never pass-on-uncertain (reopens the false
    negative), never drift-on-uncertain (the S8-over-broad false positive).
  * No bare-vs-wrapped verdict: AvgTransactionValue and DiscountedTransactionRate BOTH
    have a wrapped CALCULATE denominator; only the FILTER COLUMN differs. The
    discriminator is the filter-set, column-specific.

This module parses YAML (pyyaml, a dev/optional dep) and MUST live OUTSIDE the
`retail check` core import chain (the stdlib-only invariant) -- guarded separately.
"""

from __future__ import annotations

import pytest

from retail.metric_drift import Verdict, check_measure_drift

pytestmark = pytest.mark.unit

# The two ratio measures, VERBATIM from the committed TMDL (gold fct_sales_rss.tmdl).
# Both have a wrapped CALCULATE denominator; they differ only in the filter column --
# the adversary's "same-shape collision". A correct L3 passes BOTH.
DAX_DISCOUNTED = (
    "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] = "
    "TRUE()), CALCULATE([TransactionCount], NOT(ISBLANK('gold fct_sales_rss'"
    "[discount_applied]))))"
)
DAX_AVG = (
    "DIVIDE([TotalSales], CALCULATE([TransactionCount], NOT(ISBLANK("
    "'gold fct_sales_rss'[total_spent]))))"
)

# The APPROVED contract definitions (the ACTUAL truth: known-status / is_not_null).
# DiscountedTransactionRate: numerator filtered discount=TRUE, denominator known-status.
DEF_DISCOUNTED = {
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
# AvgTransactionValue: denominator = transactions with a non-null total_spent.
DEF_AVG = {
    "additive": False,
    "numerator": {"aggregation": "sum", "filter": []},
    "denominator": {
        "aggregation": "count_rows",
        "filter": [{"column": "total_spent", "op": "is_not_null"}],
    },
}


# --- GREEN: the shipped measures match their approved contracts -------------


def test_shipped_discounted_rate_passes() -> None:
    """The committed DiscountedTransactionRate DAX matches its known-status contract."""
    v = check_measure_drift(DAX_DISCOUNTED, DEF_DISCOUNTED)
    assert v.status == "pass", v


def test_shipped_avg_transaction_value_passes() -> None:
    """The committed AvgTransactionValue DAX matches its (total_spent) contract."""
    v = check_measure_drift(DAX_AVG, DEF_AVG)
    assert v.status == "pass", v


# --- RED (drift): wrong denominator caught ----------------------------------


def test_all_transactions_denominator_is_drift() -> None:
    """The ORIGINAL BUG: denominator = all transactions (bare [TransactionCount]).

    Contract says known-status (is_not_null), DAX denominator has NO filter -> drift.
    This is the exact 33.55-vs-50.37 regression the layer exists to catch.
    """
    buggy = (
        "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
        "= TRUE()), [TransactionCount])"
    )
    v = check_measure_drift(buggy, DEF_DISCOUNTED)
    assert v.status == "drift", v
    assert "denominator" in v.detail.lower()


def test_wrong_column_denominator_is_drift() -> None:
    """Adversary's wrong-column false-negative: AvgTransactionValue denominator
    filtered on discount_applied instead of total_spent -> drift (column-specific)."""
    wrong_col = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], NOT(ISBLANK("
        "'gold fct_sales_rss'[discount_applied]))))"
    )
    v = check_measure_drift(wrong_col, DEF_AVG)
    assert v.status == "drift", v


def test_empty_calculate_wrapper_normalizes_to_drift() -> None:
    """Adversary's no-op-wrapper evasion: DIVIDE(num, CALCULATE([TransactionCount]))
    -- a SYNTACTIC empty CALCULATE is semantically the bare all-transactions
    denominator, so it must still be caught as drift vs the known-status contract."""
    evasion = (
        "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
        "= TRUE()), CALCULATE([TransactionCount]))"
    )
    v = check_measure_drift(evasion, DEF_DISCOUNTED)
    assert v.status == "drift", v


# --- ESCALATE is the DEFAULT for anything unrecognized ----------------------


def test_unrecognized_predicate_escalates() -> None:
    """An unknown predicate spelling is NOT guessed -- it escalates to a human.

    `LEN(col) <> 0` is semantically is_not_null for text but needs type knowledge;
    it is intentionally NOT in the recognized whitelist -> escalate. (Note: the
    old `col <> BLANK()` example is now a RECOGNIZED spelling -- see
    test_is_not_null_via_ne_blank_passes.)
    """
    unknown = (
        "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
        "= TRUE()), CALCULATE([TransactionCount], "
        "LEN('gold fct_sales_rss'[discount_applied]) <> 0))"
    )
    v = check_measure_drift(unknown, DEF_DISCOUNTED)
    assert v.status == "escalate", v


# --- WIDENED predicate whitelist: 4 new recognized spellings -----------------


def test_is_not_null_via_ne_blank_passes() -> None:
    """`col <> BLANK()` is the recognized-equivalent of NOT(ISBLANK(col))."""
    dax = (
        "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
        "= TRUE()), CALCULATE([TransactionCount], "
        "'gold fct_sales_rss'[discount_applied] <> BLANK()))"
    )
    v = check_measure_drift(dax, DEF_DISCOUNTED)
    assert v.status == "pass", v


def test_is_not_null_via_isblank_eq_false_passes() -> None:
    """`ISBLANK(col) = FALSE()` is the recognized-equivalent of NOT(ISBLANK(col))."""
    dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "ISBLANK('gold fct_sales_rss'[total_spent]) = FALSE()))"
    )
    v = check_measure_drift(dax, DEF_AVG)
    assert v.status == "pass", v


def test_is_true_via_true_eq_col_passes() -> None:
    """`TRUE() = col` is the order-flipped recognized-equivalent of col = TRUE()."""
    contract = {
        "additive": False,
        "numerator": {"aggregation": "count_rows", "filter": []},
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_true"}],
        },
    }
    dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "TRUE() = 'gold fct_sales_rss'[discount_applied]))"
    )
    v = check_measure_drift(dax, contract)
    assert v.status == "pass", v


def test_is_true_via_ne_false_passes() -> None:
    """`col <> FALSE()` is the recognized-equivalent of col = TRUE()."""
    contract = {
        "additive": False,
        "numerator": {"aggregation": "count_rows", "filter": []},
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_true"}],
        },
    }
    dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "'gold fct_sales_rss'[discount_applied] <> FALSE()))"
    )
    v = check_measure_drift(dax, contract)
    assert v.status == "pass", v


def test_non_divide_measure_escalates() -> None:
    """A measure that is not a DIVIDE ratio cannot be filter-set-compared -> escalate
    (the contract carries a ratio definition; the DAX is not a ratio)."""
    not_a_ratio = "SUM('gold fct_sales_rss'[total_spent])"
    v = check_measure_drift(not_a_ratio, DEF_DISCOUNTED)
    assert v.status == "escalate", v


def test_unparseable_unbalanced_parens_escalates() -> None:
    """Malformed/unbalanced DAX is escalated, never crashes and never guesses."""
    broken = "DIVIDE(CALCULATE([TransactionCount], [x] = TRUE()"  # missing close
    v = check_measure_drift(broken, DEF_DISCOUNTED)
    assert v.status == "escalate", v


# --- additive measures escalate (filter-set logic does not apply) -----------


def test_additive_measure_escalates() -> None:
    """An additive measure's denominator filter-set logic does not apply -> escalate."""
    additive_def = {
        "additive": True,
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    v = check_measure_drift(DAX_AVG, additive_def)
    assert v.status == "escalate", v
    assert "additive" in v.detail.lower()


def test_missing_additive_flag_escalates() -> None:
    """A definition that omits `additive` is not-confirmed-ratio -> escalate."""
    no_flag_def = {
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    v = check_measure_drift(DAX_AVG, no_flag_def)
    assert v.status == "escalate", v


# --- backward compatibility: a contract with no definition block ------------


def test_contract_without_definition_block_skips() -> None:
    """A contract that has NOT adopted the structured `definition` block yet is
    SKIPPED (not failed) -- the 3 non-ratio contracts have no block."""
    v = check_measure_drift(DAX_DISCOUNTED, None)
    assert v.status == "skip", v


# --- the Verdict shape ------------------------------------------------------


def test_verdict_has_status_and_detail() -> None:
    v = check_measure_drift(DAX_DISCOUNTED, DEF_DISCOUNTED)
    assert isinstance(v, Verdict)
    assert v.status in ("pass", "drift", "escalate", "skip")
    assert isinstance(v.detail, str)


# --- stdlib-only invariant: metric_drift must stay OUT of the retail check core ----


def test_metric_drift_module_does_not_import_yaml_at_top_level() -> None:
    """`import yaml` must be LAZY (inside load_definition only), never at module scope.

    metric_drift parses YAML, but yaml is a dev/optional dep -- a top-level import would
    make it a hard dependency wherever the module is imported. Guard: no module-scope
    yaml import (a lazy `import yaml` inside a function body is allowed).
    """
    from pathlib import Path

    import retail.metric_drift as md

    src = Path(md.__file__).read_text(encoding="utf-8")
    # the only yaml import must be indented (inside a function), never at column 0
    for line in src.splitlines():
        if line.startswith("import yaml") or line.startswith("from yaml"):
            raise AssertionError(
                "metric_drift imports yaml at module scope (must be lazy)"
            )


def test_importing_retail_rules_does_not_pull_metric_drift() -> None:
    """The `retail check` core chain (retail.cli -> retail.rules) must NOT import
    metric_drift -- otherwise its (lazy) yaml dependency rides into the stdlib-only
    gate and a future maintainer could wire it into the registry, reopening the hole.

    Import retail.rules in a CLEAN subprocess and assert retail.metric_drift is absent
    from sys.modules (a subprocess so prior test imports don't pollute the check).
    """
    import subprocess
    import sys

    code = (
        "import sys; import retail.rules; "
        "assert 'retail.metric_drift' not in sys.modules, "
        "'retail.rules pulled metric_drift into the core import chain'; "
        "assert 'yaml' not in sys.modules, 'retail.rules pulled yaml'; "
        "print('clean')"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"core import chain is not clean:\n{r.stdout}\n{r.stderr}"
    assert "clean" in r.stdout
