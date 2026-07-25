"""Regression tests for issue #491 (date attributes always 'absent from gold_star').

`gap_detector._collect_gold` harvested nothing from `gold_star.date_dimension`
except its NAME, while the entity-dimension path ten lines earlier pushed each
dim's `attributes` into both token sets. So every date attribute (`year`,
`month`, `day`, ...) was reported absent no matter what the star contained --
and, worse, an APPROVED metric contract binding one false-blocked.

Resolution (owner-ruled): a date dimension's attributes are the RC15 generated
calendar set plus its declared surrogate key. That set is declared ONCE, in
``star_discovery``, so readers cannot each invent their own (issue #497).

Deliberately NOT done here: honoring a `date_dimension.attributes` key. No
consumer reads it -- `dbt/scaffold/model_plan.py:448-459` builds the date model
from `(surrogate, *_DATE_COLUMNS)` and never looks at `attributes` -- so
honoring it in this one reader would manufacture a fresh cross-surface
disagreement, which is the #487 defect.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _star(date_dim: str) -> dict:
    return {
        "gold_star": {
            "fact": {"name": "gold.fct_sales", "measures": ["net_sales"]},
            "dimensions": [
                {"name": "gold.dim_product", "attributes": ["category"]},
            ],
            "degenerate_dimensions": ["receipt_no"],
            "date_dimension": {
                "name": date_dim,
                "surrogate_key": "date_sk",
                "method": "generate_series",
                "contiguous": True,
            },
        }
    }


def _tokens(document: dict) -> tuple[set[str], set[str]]:
    from seshat.gap_detector import _collect_gold

    return _collect_gold(document)


# ---------------------------------------------------------------------------
# The reported symptom
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("attr", ["year", "month", "day", "quarter", "full_date"])
def test_generated_calendar_attributes_are_present_in_the_star(attr: str) -> None:
    """These are built by the RC15 generate_series calendar, so the star HAS them."""
    dims, cols = _tokens(_star("gold.dim_date_rss"))

    assert attr in dims, f"date attribute {attr!r} reported absent from gold_star"
    assert attr in cols, f"date attribute {attr!r} unavailable to metric binding"


def test_declared_surrogate_key_is_present() -> None:
    """`date_sk` is a real column of the date dimension."""
    dims, cols = _tokens(_star("gold.dim_date_rss"))

    assert "date_sk" in cols


def test_date_dimension_name_tokens_are_still_collected() -> None:
    """The pre-existing behavior must not regress."""
    dims, _ = _tokens(_star("gold.dim_date_rss"))

    assert "gold.dim_date_rss" in dims
    assert "dim_date_rss" in dims


def test_entity_dimension_and_degenerate_handling_unchanged() -> None:
    dims, cols = _tokens(_star("gold.dim_date_rss"))

    assert "category" in dims and "category" in cols
    assert "receipt_no" in dims and "receipt_no" in cols


def test_a_star_without_a_date_dimension_gains_no_calendar_tokens() -> None:
    """No date dimension declared -> the star genuinely has no date attributes."""
    document = _star("gold.dim_date_rss")
    del document["gold_star"]["date_dimension"]

    dims, cols = _tokens(document)

    assert "year" not in dims and "year" not in cols


def test_malformed_date_dimension_is_tolerated_without_inventing_columns() -> None:
    """A non-mapping date_dimension must not fabricate a calendar."""
    document = _star("gold.dim_date_rss")
    document["gold_star"]["date_dimension"] = "not-a-mapping"

    dims, cols = _tokens(document)

    assert "year" not in dims and "year" not in cols


# ---------------------------------------------------------------------------
# The more severe half: an APPROVED contract must not false-block
# ---------------------------------------------------------------------------


def test_approved_contract_binding_a_date_attribute_is_not_blocked() -> None:
    """An owner-approved contract binding `year` reported it absent from gold_star.

    That is the tool contradicting a recorded human approval, which is worse than
    a noisy dimension row.
    """
    from seshat.gap_detector import _missing_bound_columns

    _, cols = _tokens(_star("gold.dim_date_rss"))
    contract = {"columns": ["year", "month"]}

    missing = _missing_bound_columns(contract, {"gold_cols": cols})

    assert missing == [], f"approved contract false-blocked on {missing}"


def test_contract_binding_a_genuinely_absent_column_still_blocks() -> None:
    """The fix must not make the check fail OPEN -- that was the #487 defect."""
    from seshat.gap_detector import _missing_bound_columns

    _, cols = _tokens(_star("gold.dim_date_rss"))
    contract = {"columns": ["not_a_real_column"]}

    missing = _missing_bound_columns(contract, {"gold_cols": cols})

    assert missing == ["not_a_real_column"]


# ---------------------------------------------------------------------------
# One declared set (issue #497): readers must not each invent their own
# ---------------------------------------------------------------------------


def test_the_calendar_set_is_declared_once_and_shared() -> None:
    from seshat.gap_detector import _collect_gold  # noqa: F401
    from seshat.star_discovery import RC15_CALENDAR_ATTRIBUTES

    assert isinstance(RC15_CALENDAR_ATTRIBUTES, frozenset)
    assert {"full_date", "year", "quarter", "month", "day"} <= RC15_CALENDAR_ATTRIBUTES


def test_the_declared_set_matches_the_reference_migration_star() -> None:
    """Guard the constant against drifting from the star this repo actually builds.

    `warehouse/migrations/0004_*.sql` is the de-facto truth for what a Seshat date
    dimension contains; if that DDL changes, this constant must be revisited
    rather than silently disagreeing with it (issue #497).
    """
    import re

    from seshat.star_discovery import RC15_CALENDAR_ATTRIBUTES

    repo_root = Path(__file__).resolve().parents[2]
    ddl = next(repo_root.glob("warehouse/migrations/0004_*.sql")).read_text(
        encoding="utf-8"
    )
    block = re.search(
        r"create table\s+gold\.dim_date_rss\s*\((.*?)\);",
        ddl,
        re.IGNORECASE | re.DOTALL,
    )
    assert block, "could not locate the reference date-dimension DDL"

    declared = {
        m.group(1)
        for line in block.group(1).splitlines()
        if (m := re.match(r"\s*([a-z_][a-z0-9_]*)\s+[A-Za-z]", line))
    }
    # date_sk is the surrogate key, carried separately from the attribute set.
    declared.discard("date_sk")

    assert declared == set(RC15_CALENDAR_ATTRIBUTES), (
        "the declared calendar set and the reference migration DDL disagree: "
        f"only in DDL={sorted(declared - RC15_CALENDAR_ATTRIBUTES)}, "
        f"only in constant={sorted(set(RC15_CALENDAR_ATTRIBUTES) - declared)}"
    )
