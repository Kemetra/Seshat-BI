"""Prove the report's compiled SQL against a real Postgres (spec: report live figures).

Every other test of :mod:`seshat.report.observe` injects a fake runner, which proves
the compilation rules and proves none of the SQL. A statement can be shaped exactly
right and still be rejected by the engine, or return a column order the reader
misreads -- neither is visible to a fake.

Requires the ``livetest`` extra + a running Docker daemon; otherwise import-skips /
fixture-skips honestly, never silently passing.
"""

from decimal import Decimal

import pytest

pytest.importorskip("testcontainers")  # collection-skip when livetest extra absent

from seshat import validate  # noqa: E402
from seshat.report.observe import FigureRequest, compile_query, observe  # noqa: E402

pytestmark = pytest.mark.live_db

# Seeded gold.fct_order_line: net_amount 20.00 + 15.50 + 30.00 = 65.50 over 3 rows.
_SEEDED_TOTAL = Decimal("65.50")
_SEEDED_ROWS = 3

_SUM = {
    "name": "NetSales",
    "binds_to": {"gold_table": "gold.fct_order_line", "columns": ["net_amount"]},
    "definition": {"kind": "base", "aggregation": "sum", "filter": []},
}

_COUNT = {
    "name": "OrderLineCount",
    "binds_to": {"gold_table": "gold.fct_order_line", "columns": ["order_line_id"]},
    "definition": {"kind": "base", "aggregation": "count_rows", "filter": []},
}

# sum over a filtered count -- the AvgTransactionValue shape, which is the one the
# fakes cannot prove is valid SQL because it mixes aggregate forms in one row.
_AVERAGE = {
    "name": "AvgLineValue",
    "binds_to": {"gold_table": "gold.fct_order_line", "columns": ["net_amount"]},
    "definition": {
        "numerator": {"aggregation": "sum", "filter": []},
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "net_amount", "op": "is_not_null"}],
        },
    },
}


def _observe(dsn: str, contract: dict, unit_kind: str) -> Decimal | None:
    runner = validate.make_psycopg2_runner(dsn)
    request = FigureRequest(
        visual_id="v1", contract_id=contract["name"], unit_kind=unit_kind, label=None
    )
    return observe(runner, [request], {contract["name"]: contract})[0]["value"]


@pytest.mark.seed("seed_value_check.sql")
def test_a_summed_contract_returns_the_seeded_total(live_db_container):
    """Penny-exact, and a Decimal rather than a float."""
    value = _observe(live_db_container.dsn, _SUM, "currency")
    assert value == _SEEDED_TOTAL
    assert isinstance(value, Decimal)


@pytest.mark.seed("seed_value_check.sql")
def test_a_row_count_contract_returns_the_seeded_row_count(live_db_container):
    assert _observe(live_db_container.dsn, _COUNT, "count") == Decimal(_SEEDED_ROWS)


@pytest.mark.seed("seed_value_check.sql")
def test_a_mixed_aggregate_ratio_is_valid_sql_and_divides_the_right_way_round(
    live_db_container,
):
    """The column order matters and a fake cannot check it.

    65.50 / 3 is 21.83...; 3 / 65.50 is 0.045. Both are numbers, and only one is the
    average line value, so this asserts the sides did not swap.
    """
    value = _observe(live_db_container.dsn, _AVERAGE, "ratio")
    assert value == _SEEDED_TOTAL / Decimal(_SEEDED_ROWS)
    assert value > Decimal(1)


@pytest.mark.seed("seed_value_check.sql")
def test_an_empty_table_yields_pending_rather_than_zero(live_db_container):
    """`sum` over no rows is SQL NULL, not 0. Rendering it as 0 would state that the
    business took nothing, which is a different claim from having no data."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    runner.run("DELETE FROM gold.fct_order_line")
    assert _observe(live_db_container.dsn, _SUM, "currency") is None


@pytest.mark.seed("seed_value_check.sql")
def test_the_engine_accepts_every_shipped_contract(live_db_container):
    """Each shipped contract's statement, run against a table with the same shape.

    Executed for acceptance rather than for its value: a statement the engine
    rejects is a figure that can never go live, and only a real engine can say.
    """
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    for contract in (_SUM, _COUNT, _AVERAGE):
        rows = runner.run(compile_query(contract).sql)
        assert rows and rows[0], f"{contract['name']} returned no row"
