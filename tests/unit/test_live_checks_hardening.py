"""Fail-closed edges in value-check, validate, the profile renderer and the
statistical compiler."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import main
from seshat.core import Severity
from seshat.dialect import get_dialect
from tests.unit.test_cli_value_check import _RATIO_CONTRACT, _write_contract

pytestmark = pytest.mark.unit


# --- L4 expected_value parsing --------------------------------------------


@pytest.mark.parametrize(
    ("value", "tolerance"),
    [("100", "Infinity"), ("100", "sNaN"), ("NaN", "0"), ("100", "-1")],
)
def test_non_finite_or_negative_expected_values_are_malformed(
    value: str, tolerance: str
) -> None:
    from seshat.value_proxy import parse_expected_value

    definition = {
        "expected_value": {
            "value": value,
            "tolerance_abs": tolerance,
            "aggregation": "count_rows",
        }
    }
    with pytest.raises(ValueError):
        parse_expected_value(definition, {"gold_table": "gold.f"})


# --- L4 ratio sides ---------------------------------------------------------


def _ratio(tmp_path: Path, contract: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    monkeypatch.setattr(
        "seshat.cli._make_runner",
        lambda _c, **_k: pytest.fail("a malformed ratio must not reach the DB"),
    )
    _write_contract(tmp_path, "Rate", contract)
    return main(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )


def test_a_ratio_side_that_is_not_count_rows_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    contract = _RATIO_CONTRACT.replace(
        "  numerator:\n    aggregation: count_rows",
        "  numerator:\n    aggregation: sum",
    )
    assert contract != _RATIO_CONTRACT

    assert _ratio(tmp_path, contract, monkeypatch) == 1
    assert "count_rows" in capsys.readouterr().err


def test_a_null_ratio_side_is_a_clean_error_not_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    block = (
        "  numerator:\n    aggregation: count_rows\n    filter:\n"
        "      - column: discount_applied\n        op: is_true\n"
    )
    contract = _RATIO_CONTRACT.replace(block, "  numerator: null\n")
    assert contract != _RATIO_CONTRACT

    assert _ratio(tmp_path, contract, monkeypatch) == 1
    assert "Traceback" not in capsys.readouterr().err


# --- boolean filter portability --------------------------------------------


def test_value_check_filters_are_portable_to_sql_server() -> None:
    from seshat.cli.commands.value_check import _filter_to_sql

    dialect = get_dialect("sqlserver")
    pred = _filter_to_sql([{"column": "c", "op": "is_true"}], dialect)

    assert pred == "[c] = 1"
    assert _filter_to_sql([], dialect) == "1 = 1"
    assert _filter_to_sql(
        [{"column": "c", "op": "is_true"}], get_dialect("postgres")
    ) == ('"c" = TRUE')


def test_report_boolean_filter_is_portable_to_sql_server() -> None:
    from seshat.report.observe import _predicate

    pred = _predicate(
        [{"column": "c", "op": "is_true"}], {"name": "X"}, get_dialect("sqlserver")
    )

    assert pred == "[c] = 1"
    assert "IS TRUE" not in pred


# --- validate: an empty result set is not zero defects ---------------------


class _Empty:
    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        return []


def test_empty_results_are_errors_for_date_coverage_and_orphans() -> None:
    from seshat.validate import (
        DateCoverageTarget,
        OrphanTarget,
        check_date_coverage,
        check_orphan_fks,
    )

    coverage = check_date_coverage(
        _Empty(),
        DateCoverageTarget(
            fact="gold.f", fact_date="d", date_dim="gold.dim_date", dim_date="d"
        ),
    )
    orphans = check_orphan_fks(
        _Empty(), OrphanTarget(fact="gold.f", fks=(("k", "gold.dim", "k"),))
    )

    assert [f.rule_id for f in coverage] == ["V-RC15"]
    assert [f.rule_id for f in orphans] == ["V-RC16"]
    assert all(f.severity is Severity.ERROR for f in coverage + orphans)
    assert all("no rows" in f.message for f in coverage + orphans)


# --- profile --file ---------------------------------------------------------


def test_a_bom_prefixed_csv_profiles_on_its_first_column(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    csv = tmp_path / "sales.csv"
    csv.write_text("id,name\n1,a\n2,b\n", encoding="utf-8-sig")

    assert main(["profile", "--file", str(csv), "--pk", "id"]) == 0
    out = capsys.readouterr().out
    assert "\ufeff" not in out
    assert "`id`" in out


def test_the_profile_label_is_the_file_name_not_a_local_path(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    csv = tmp_path / "sales.csv"
    csv.write_text("id,name\n1,a\n", encoding="utf-8")

    assert main(["profile", "--file", str(csv), "--pk", "id"]) == 0
    out = capsys.readouterr().out
    assert "profiled: `sales.csv`" in out
    assert str(tmp_path) not in out


@pytest.mark.parametrize("header", ["net|gross", "net`gross"])
def test_a_header_that_breaks_the_markdown_table_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture, header: str
) -> None:
    csv = tmp_path / "x.csv"
    csv.write_text(f"id,{header}\n1,2\n", encoding="utf-8")

    assert main(["profile", "--file", str(csv), "--pk", "id"]) == 1
    assert "header" in capsys.readouterr().err


# --- statistical compiler ---------------------------------------------------


def test_joined_queries_qualify_every_main_table_column() -> None:
    from seshat.statistical.providers.base import (
        Aggregate,
        DataRequest,
        Filter,
        Join,
    )
    from seshat.statistical.query import compile_select

    request = DataRequest(
        table="gold.fct_sales",
        columns=("store_id", "net_amount"),
        logical_types=("category", "number"),
        roles={"response": "net_amount"},
        filters=(Filter("store_id", "is_not_null", None),),
        aggregates=(Aggregate("net_amount", "sum", "net_amount"),),
        group_by=("store_id",),
        joins=(Join("gold.dim_store", "store_id", "store_id", "many_to_one"),),
        privacy_floor=5,
    )

    sql = compile_select(request, get_dialect("postgres")).sql

    main_col = '"gold"."fct_sales"."store_id"'
    assert f"GROUP BY {main_col}" in sql
    assert f"WHERE {main_col} IS NOT NULL" in sql
    assert 'SUM("gold"."fct_sales"."net_amount")' in sql
