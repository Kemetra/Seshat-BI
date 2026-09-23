"""Scaffolded staging and fact columns are real, identifier-named silver columns."""

from __future__ import annotations

import pytest

from seshat.dbt.scaffold import model_plan
from tests.unit.dbt.test_dbt_scaffold import _FACT, _FULL_FACT_MAP, TABLE_ID, _source

pytestmark = pytest.mark.unit


def _fact(measures: list) -> dict:
    return {**_FULL_FACT_MAP["gold_star"]["fact"], "measures": measures}


def _with(columns: list, measures: list) -> dict:
    return {
        **_FULL_FACT_MAP,
        "columns": [*_FULL_FACT_MAP["columns"], *columns],
        "gold_star": {**_FULL_FACT_MAP["gold_star"], "fact": _fact(measures)},
    }


def test_kept_column_with_a_non_identifier_name_fails_closed() -> None:
    """A kept column staging cannot name is an error, never silently dropped."""
    broken = _with([{"source_name": "Total Spent", "decision": "keep"}], ["quantity"])
    with pytest.raises(model_plan.ScaffoldError, match="Total Spent"):
        model_plan.build_scaffold_plan(_source(broken), TABLE_ID, _FACT)


def test_fact_measure_with_a_non_identifier_name_fails_closed() -> None:
    broken = _with(
        [{"source_name": "Price Per Unit", "decision": "keep", "rename_to": "ppu"}],
        ["quantity", "Price Per Unit"],
    )
    with pytest.raises(model_plan.ScaffoldError, match="Price Per Unit"):
        model_plan.build_scaffold_plan(_source(broken), TABLE_ID, _FACT)


def test_fact_measure_naming_the_raw_bronze_column_of_a_renamed_row_fails() -> None:
    """Staging exposes the silver name; a fact column named after the renamed
    bronze column would select a column staging never produced."""
    columns = [
        {**row, "source_name": "qty"} if row["source_name"] == "Qty" else row
        for row in _FULL_FACT_MAP["columns"]
    ]
    broken = {
        **_FULL_FACT_MAP,
        "columns": columns,
        "gold_star": {**_FULL_FACT_MAP["gold_star"], "fact": _fact(["qty"])},
    }
    with pytest.raises(model_plan.ScaffoldError, match="quantity"):
        model_plan.build_scaffold_plan(_source(broken), TABLE_ID, _FACT)


def test_identifier_named_renamed_measure_still_scaffolds() -> None:
    plan = model_plan.build_scaffold_plan(_source(_FULL_FACT_MAP), TABLE_ID, _FACT)
    names = {column.name for column in plan.fact_model.columns}
    assert {"quantity", "total_spent"} <= names
