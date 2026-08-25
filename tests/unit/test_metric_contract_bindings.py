from __future__ import annotations

from copy import deepcopy

import pytest

from seshat.metric_contract_bindings import definition_binding_errors


def _two_table_contract() -> dict[str, object]:
    return {
        "binds_to": {
            "gold_table": "gold.fct_actuals",
            "columns": ["amount", "is_posted"],
            "pii_sensitive": False,
        },
        "compares_to": {
            "gold_table": "gold.fct_targets",
            "columns": ["amount", "is_active"],
            "pii_sensitive": False,
        },
        "definition": {
            "kind": "ratio",
            "numerator": {
                "aggregation": "sum",
                "source": {"table": "gold.fct_actuals", "column": "amount"},
                "filter": [{"column": "is_posted", "op": "is_true"}],
            },
            "denominator": {
                "aggregation": "sum",
                "source": {"table": "gold.fct_targets", "column": "amount"},
                "filter": [{"column": "is_active", "op": "is_true"}],
            },
        },
    }


def _one_table_ratio() -> dict[str, object]:
    return {
        "kind": "ratio",
        "numerator": {
            "aggregation": "count_rows",
            "source": {"table": "gold.fct_orders"},
        },
        "denominator": {
            "aggregation": "count_rows",
            "source": {"table": "gold.fct_orders"},
        },
    }


def test_two_table_ratio_bindings_are_coherent() -> None:
    assert definition_binding_errors(_two_table_contract()) == ()


def test_count_rows_uses_filter_columns_but_not_a_source_column() -> None:
    contract = _two_table_contract()
    numerator = contract["definition"]["numerator"]
    numerator["aggregation"] = "count_rows"
    numerator["source"] = {"table": "gold.fct_actuals"}

    assert definition_binding_errors(contract) == ()


def test_missing_compares_to_is_refused() -> None:
    contract = _two_table_contract()
    del contract["compares_to"]

    assert definition_binding_errors(contract) == (
        "two-table ratio requires compares_to",
    )


def test_definition_tables_must_match_their_governed_bindings() -> None:
    contract = _two_table_contract()
    contract["definition"]["denominator"]["source"]["table"] = "gold.fct_plan"

    assert definition_binding_errors(contract) == (
        "denominator source table must equal compares_to.gold_table",
    )


def test_definition_source_table_rejects_surrounding_whitespace() -> None:
    contract = _two_table_contract()
    contract["definition"]["numerator"]["source"]["table"] = " gold.fct_actuals"

    assert definition_binding_errors(contract) == (
        "numerator source.table must be a non-empty gold.* string",
    )


def test_every_used_column_must_be_declared_by_its_binding() -> None:
    contract = _two_table_contract()
    contract["compares_to"]["columns"] = ["amount"]

    assert definition_binding_errors(contract) == (
        "denominator column 'is_active' is absent from compares_to.columns",
    )


@pytest.mark.parametrize("binding_name", ("binds_to", "compares_to"))
@pytest.mark.parametrize(
    "gold_table", ("silver.fct_values", "gold.", " gold.fct_values")
)
def test_two_table_bindings_require_gold_tables(
    binding_name: str, gold_table: str
) -> None:
    contract = _two_table_contract()
    contract[binding_name]["gold_table"] = gold_table

    assert definition_binding_errors(contract) == (
        f"{binding_name}.gold_table must be a non-empty gold.* string",
    )


@pytest.mark.parametrize("binding_name", ("binds_to", "compares_to"))
@pytest.mark.parametrize("columns", ([], ["amount", 7], "amount"))
def test_two_table_bindings_require_non_empty_string_columns(
    binding_name: str, columns: object
) -> None:
    contract = _two_table_contract()
    contract[binding_name]["columns"] = columns

    assert definition_binding_errors(contract) == (
        f"{binding_name}.columns must be a non-empty list of strings",
    )


@pytest.mark.parametrize("binding_name", ("binds_to", "compares_to"))
def test_two_table_binding_pii_flags_must_be_boolean(binding_name: str) -> None:
    contract = _two_table_contract()
    contract[binding_name]["pii_sensitive"] = "false"

    assert definition_binding_errors(contract) == (
        f"{binding_name}.pii_sensitive must be boolean",
    )


def test_malformed_side_columns_are_refused_without_raising() -> None:
    contract = _two_table_contract()
    contract["definition"]["numerator"]["filter"] = [
        {"column": ["is_posted"], "op": "is_true"}
    ]

    assert definition_binding_errors(contract) == (
        "numerator filter columns must be non-empty strings",
    )


@pytest.mark.parametrize(
    ("field", "expected"),
    (
        (
            "source",
            "numerator source.column must not contain surrounding whitespace",
        ),
        (
            "filter",
            "numerator filter column must not contain surrounding whitespace",
        ),
    ),
)
def test_definition_columns_reject_surrounding_whitespace(
    field: str, expected: str
) -> None:
    contract = _two_table_contract()
    numerator = contract["definition"]["numerator"]
    if field == "source":
        numerator["source"]["column"] = " amount "
    else:
        numerator["filter"][0]["column"] = " is_posted "

    assert definition_binding_errors(contract) == (expected,)


def test_unhashable_filter_operator_is_refused_without_raising() -> None:
    contract = _two_table_contract()
    contract["definition"]["numerator"]["filter"][0]["op"] = ["is_true"]

    assert definition_binding_errors(contract) == (
        "numerator filter op must be a supported string",
    )


def test_compares_to_requires_a_ratio_definition() -> None:
    contract = _two_table_contract()
    contract["definition"] = {
        "kind": "base",
        "aggregation": "sum",
        "source": {"table": "gold.fct_actuals", "column": "amount"},
    }

    assert definition_binding_errors(contract) == (
        "compares_to requires a ratio numerator and denominator",
    )


def test_one_table_contract_is_unchanged() -> None:
    assert definition_binding_errors({"definition": _one_table_ratio()}) == ()


def test_validation_does_not_mutate_the_contract() -> None:
    contract = _two_table_contract()
    before = deepcopy(contract)

    definition_binding_errors(contract)

    assert contract == before
