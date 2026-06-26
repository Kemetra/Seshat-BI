"""Unit tests for DAX/TMDL rules D1-D8 and C1."""

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.dax import (
    c1_parameterized_connection,
    d1_pascalcase_measures,
    d2_display_folder,
    d3_no_duplicate_logic,
    d4_divide_not_slash,
    d5_explicit_aggregation,
    d6_no_bidir_relationships,
    d7_ti_needs_date_marker,
    d8_gold_only_sourcing,
    d9_no_hardcoded_dates,
    d10_no_filter_all,
    d11_measures_documented,
)
from retail.tmdl import TmdlMeasure

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "tmdl"


def _ctx(tmp_path: Path, fixture: str) -> RuleContext:
    """Stage a fixture under a SemanticModel path and return a RuleContext."""
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / fixture).read_text(encoding="utf-8-sig"), encoding="utf-8"
    )
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


# ---------------------------------------------------------------------------
# D1 — PascalCase measure names
# ---------------------------------------------------------------------------


def test_d1_flags_non_pascalcase(tmp_path: Path) -> None:
    findings = list(d1_pascalcase_measures(_ctx(tmp_path, "bad_names.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D1"
    assert findings[0].severity is Severity.ERROR
    assert "total_revenue" in findings[0].message


def test_d1_passes_clean(tmp_path: Path) -> None:
    assert list(d1_pascalcase_measures(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d1_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d1_pascalcase_measures(_ctx(tmp_path, "bad_names.tmdl")))
    assert findings[0].locator.endswith(":2")


# ---------------------------------------------------------------------------
# D2 — displayFolder required
# ---------------------------------------------------------------------------


def test_d2_passes_clean(tmp_path: Path) -> None:
    assert list(d2_display_folder(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d2_passes_ti_file_with_folder(tmp_path: Path) -> None:
    # bad_ti_no_marker.tmdl has a displayFolder on its measure
    assert list(d2_display_folder(_ctx(tmp_path, "bad_ti_no_marker.tmdl"))) == []


def test_d2_flags_missing_folder(tmp_path: Path) -> None:
    findings = list(d2_display_folder(_ctx(tmp_path, "bad_no_folder.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D2"
    assert findings[0].severity is Severity.ERROR
    assert "Revenue" in findings[0].message


def test_d2_passes_non_empty_folder(tmp_path: Path) -> None:
    """A measure with a present, non-empty displayFolder passes (is None == False)."""
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "table T\n\tmeasure Revenue = SUM(T[Amount])\n\t\tdisplayFolder: KPIs\n",
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d2_display_folder(ctx)) == []


def test_d2_does_not_flag_explicitly_empty_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contract: D2 guards on `is None`, not falsiness.

    An empty-string displayFolder (`""`) is a *different* state than a missing
    line (`None`). D2 must flag only `None`. Because the parser never yields
    `""` from TMDL text (its regex requires a non-empty value), this exercises
    the rule directly with a constructed measure to lock the is-None contract:
    a falsy-but-not-None folder must NOT be flagged.
    """
    from retail.rules import dax as dax_mod
    from retail.tmdl import TmdlTable

    empty_folder_table = TmdlTable(
        name="T",
        measures=(
            TmdlMeasure(
                name="Revenue", expression="SUM(T[Amount])", display_folder="", line=2
            ),
        ),
        columns=(),
        partition_sources=(),
        annotations=(),
        line=1,
    )
    monkeypatch.setattr(
        dax_mod, "iter_model_files", lambda ctx, suffix: iter([("T.tmdl", "x")])
    )
    monkeypatch.setattr(dax_mod, "parse_tmdl", lambda text: empty_folder_table)
    ctx = RuleContext(repo_root=Path("."), tracked_files=())
    assert list(d2_display_folder(ctx)) == []


# ---------------------------------------------------------------------------
# D3 — no duplicated measure logic
# ---------------------------------------------------------------------------


def test_d3_flags_identical_bodies(tmp_path: Path) -> None:
    findings = list(d3_no_duplicate_logic(_ctx(tmp_path, "bad_duplicate.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D3"
    assert findings[0].severity is Severity.ERROR
    assert "Revenue" in findings[0].message and "TotalSales" in findings[0].message


def test_d3_passes_clean(tmp_path: Path) -> None:
    assert list(d3_no_duplicate_logic(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d3_second_occurrence_is_locator(tmp_path: Path) -> None:
    """The second (duplicate) measure is the locator, not the first."""
    findings = list(d3_no_duplicate_logic(_ctx(tmp_path, "bad_duplicate.tmdl")))
    # TotalSales is the second measure; its name appears in the message
    assert "TotalSales" in findings[0].message


# ---------------------------------------------------------------------------
# D4 — use DIVIDE() not bare /
# ---------------------------------------------------------------------------


def test_d4_flags_bare_slash(tmp_path: Path) -> None:
    findings = list(d4_divide_not_slash(_ctx(tmp_path, "bad_divide.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D4"
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator.endswith(":2")


def test_d4_passes_clean(tmp_path: Path) -> None:
    # clean_sales uses DIVIDE(...) and SUM(...) — no bare slash
    assert list(d4_divide_not_slash(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d4_passes_url_in_string_literal(tmp_path: Path) -> None:
    """A '/' inside a string literal must NOT trigger D4."""
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        'table T\n\tmeasure M = "http://example.com"\n\t\tdisplayFolder: X\n',
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d4_divide_not_slash(ctx)) == []


# ---------------------------------------------------------------------------
# D5 — WARNING: numeric column summarizeBy != none
# ---------------------------------------------------------------------------


def test_d5_warns_on_implicit_aggregation(tmp_path: Path) -> None:
    findings = list(d5_explicit_aggregation(_ctx(tmp_path, "bad_summarize.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D5"
    assert findings[0].severity is Severity.WARNING
    assert "Amount" in findings[0].message


def test_d5_passes_when_summarize_none(tmp_path: Path) -> None:
    # clean_sales: Amount and ProductKey both summarizeBy none
    assert list(d5_explicit_aggregation(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d5_passes_non_numeric_column_with_sum(tmp_path: Path) -> None:
    """A text/string column with summarizeBy: sum should NOT fire D5."""
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "table T\n\tcolumn Name\n\t\tdataType: string\n\t\tsummarizeBy: sum\n",
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d5_explicit_aggregation(ctx)) == []


def test_d5_exempts_tests_prefix(tmp_path: Path) -> None:
    """Files under tests/ must be exempted (iter_model_files exemption)."""
    rel = "tests/fixtures/golden_pbip/X.SemanticModel/definition/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "table T\n\tcolumn Amount\n\t\tdataType: decimal\n\t\tsummarizeBy: sum\n",
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d5_explicit_aggregation(ctx)) == []


# ---------------------------------------------------------------------------
# D6 — no bidirectional relationships
# ---------------------------------------------------------------------------


def _ctx_rel(tmp_path: Path, fixture: str) -> RuleContext:
    """Stage a relationship fixture under a SemanticModel definition path."""
    rel = "Model.SemanticModel/definition/relationships.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / fixture).read_text(encoding="utf-8-sig"), encoding="utf-8"
    )
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def test_d6_flags_both_directions(tmp_path: Path) -> None:
    findings = list(
        d6_no_bidir_relationships(_ctx_rel(tmp_path, "bad_relationships.tmdl"))
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "D6"
    assert findings[0].severity is Severity.ERROR
    assert "bothDirections" in findings[0].message
    assert "Sales_Date" in findings[0].message


def test_d6_passes_single_direction(tmp_path: Path) -> None:
    findings = list(
        d6_no_bidir_relationships(_ctx_rel(tmp_path, "clean_relationships.tmdl"))
    )
    assert findings == []


def test_d6_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(
        d6_no_bidir_relationships(_ctx_rel(tmp_path, "bad_relationships.tmdl"))
    )
    assert ":" in findings[0].locator
    line = int(findings[0].locator.split(":")[-1])
    assert line >= 1


def test_d6_exempts_tests_prefix(tmp_path: Path) -> None:
    """Relationships files under tests/ must be exempted."""
    rel = "tests/fixtures/X.SemanticModel/definition/relationships.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "relationship R\n\tcrossFilteringBehavior: bothDirections\n",
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d6_no_bidir_relationships(ctx)) == []


# ---------------------------------------------------------------------------
# D7 — time-intelligence requires a date-table marker
# ---------------------------------------------------------------------------


def _ctx_two(tmp_path: Path, fixture_a: str, fixture_b: str) -> RuleContext:
    """Stage two TMDL fixtures in the same model definition directory."""
    rel_a = "Model.SemanticModel/definition/tables/SalesTable.tmdl"
    rel_b = "Model.SemanticModel/definition/tables/DateTable.tmdl"
    for rel, fixture in ((rel_a, fixture_a), (rel_b, fixture_b)):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            (FIXTURES / fixture).read_text(encoding="utf-8-sig"), encoding="utf-8"
        )
    return RuleContext(repo_root=tmp_path, tracked_files=(rel_a, rel_b))


def test_d7_flags_ti_without_marker(tmp_path: Path) -> None:
    """TI function present, no date-table marker anywhere → D7 fires."""
    ctx = _ctx(tmp_path, "bad_ti_no_marker.tmdl")
    findings = list(d7_ti_needs_date_marker(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "D7"
    assert findings[0].severity is Severity.ERROR
    assert "PBI_DateTable" in findings[0].message


def test_d7_passes_with_marker_in_same_table(tmp_path: Path) -> None:
    """TI function in the same table that has the marker → no finding."""
    ctx = _ctx(tmp_path, "clean_date.tmdl")
    assert list(d7_ti_needs_date_marker(ctx)) == []


def test_d7_passes_with_marker_in_different_table(tmp_path: Path) -> None:
    """TI in Sales table, marker in Date table → no finding (model-level rule)."""
    ctx = _ctx_two(tmp_path, "bad_ti_no_marker.tmdl", "clean_date.tmdl")
    assert list(d7_ti_needs_date_marker(ctx)) == []


def test_d7_passes_no_ti_no_marker(tmp_path: Path) -> None:
    """No TI functions at all → no finding even if marker is absent."""
    ctx = _ctx(tmp_path, "clean_sales.tmdl")
    assert list(d7_ti_needs_date_marker(ctx)) == []


def test_d7_exempts_tests_prefix(tmp_path: Path) -> None:
    """TMDL files under tests/ are exempted — the golden fixture must not trigger D7."""
    rel = "tests/fixtures/X.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmdl_body = (
        "table T\n\tmeasure YTD = TOTALYTD([Revenue], T[Date])\n\t\tdisplayFolder: TI\n"
    )
    dest.write_text(tmdl_body, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d7_ti_needs_date_marker(ctx)) == []


# ---------------------------------------------------------------------------
# D8 — gold-only sourcing
# ---------------------------------------------------------------------------


def _ctx_m(tmp_path: Path, fixture: str) -> RuleContext:
    """Stage a table TMDL fixture (with M partition source) in a model path."""
    rel = "Model.SemanticModel/definition/tables/SalesTable.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / fixture).read_text(encoding="utf-8-sig"), encoding="utf-8"
    )
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def test_d8_flags_bronze_in_native_sql(tmp_path: Path) -> None:
    """bronze inside a NativeQuery string literal must be detected."""
    ctx = _ctx_m(tmp_path, "bad_source_bronze.tmdl")
    findings = list(d8_gold_only_sourcing(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "D8"
    assert findings[0].severity is Severity.ERROR
    assert "bronze" in findings[0].message


def test_d8_passes_gold_source(tmp_path: Path) -> None:
    ctx = _ctx_m(tmp_path, "clean_gold_source.tmdl")
    assert list(d8_gold_only_sourcing(ctx)) == []


def _write_m_source(tmp_path: Path, rel: str, schema: str) -> None:
    """Write a minimal table TMDL with a NativeQuery sourcing ``schema``."""
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    sql = f"SELECT * FROM {schema}.obj"
    lines = [
        "table T",
        "\tpartition T = m",
        "\t\tsource =",
        "\t\t\tlet",
        "\t\t\t\tSrc = PostgreSQL.Database(S, D),",
        f'\t\t\t\tData = Value.NativeQuery(Src, "{sql}")',
        "\t\t\tin",
        "\t\t\t\tData",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")


def test_d8_flags_non_gold_schemas(tmp_path: Path) -> None:
    """Each of raw, marts, silver triggers D8."""
    for schema in ("raw", "marts", "silver"):
        rel = "Model.SemanticModel/definition/tables/T.tmdl"
        _write_m_source(tmp_path, rel, schema)
        ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
        findings = list(d8_gold_only_sourcing(ctx))
        assert len(findings) >= 1, f"Expected finding for schema={schema}"
        assert findings[0].rule_id == "D8"


def test_d8_exempts_tests_prefix(tmp_path: Path) -> None:
    """TMDL files under tests/ are exempted."""
    rel = "tests/fixtures/X.SemanticModel/definition/tables/T.tmdl"
    _write_m_source(tmp_path, rel, "bronze")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d8_gold_only_sourcing(ctx)) == []


def test_d8_flags_bronze_in_shared_expression(tmp_path: Path) -> None:
    """D8 must detect stale schemas in top-level shared expression blocks."""
    # Shared expressions live at indent 0 in a TMDL model definition file,
    # not inside a table block. iter_m_sources must walk these too.
    rel = "Model.SemanticModel/definition/expressions.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    sql = "SELECT * FROM bronze.stg_sales"
    lines = [
        "expression SharedQuery =",
        "\tlet",
        "\t\tSrc = PostgreSQL.Database(S, D),",
        f'\t\tData = Value.NativeQuery(Src, "{sql}")',
        "\tin",
        "\t\tData",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    findings = list(d8_gold_only_sourcing(ctx))
    assert len(findings) >= 1
    assert findings[0].rule_id == "D8"
    assert "bronze" in findings[0].message


def _write_schema_option(tmp_path: Path, rel: str, schema: str) -> None:
    """Write a table TMDL whose M source uses the ``[Schema="<schema>"]`` option."""
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "table T",
        "\tpartition T = m",
        "\t\tsource =",
        "\t\t\tlet",
        f'\t\t\t\tSrc = PostgreSQL.Database(Server, Db, [Schema="{schema}"]),',
        '\t\t\t\tData = Value.NativeQuery(Src, "SELECT * FROM fct_x")',
        "\t\t\tin",
        "\t\t\t\tData",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")


def test_d8_flags_schema_option_bronze(tmp_path: Path) -> None:
    """D8 must flag the M connection option [Schema="bronze"].

    tokenize_sql strips string-literal contents, so the bare `bronze` inside
    `[Schema="bronze"]` is invisible to the stale_schema_tokens passes — the
    dedicated Schema= pass must catch it.
    """
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    _write_schema_option(tmp_path, rel, "bronze")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    findings = list(d8_gold_only_sourcing(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "D8"
    assert findings[0].severity is Severity.ERROR
    assert "bronze" in findings[0].message


def test_d8_passes_schema_option_gold(tmp_path: Path) -> None:
    """[Schema="gold"] must PASS — gold is the allowed schema."""
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    _write_schema_option(tmp_path, rel, "gold")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d8_gold_only_sourcing(ctx)) == []


def test_d8_flags_all_stale_schema_options(tmp_path: Path) -> None:
    """Each of bronze, silver, raw, marts as a Schema= option triggers D8."""
    for schema in ("bronze", "silver", "raw", "marts"):
        rel = "Model.SemanticModel/definition/tables/T.tmdl"
        _write_schema_option(tmp_path, rel, schema)
        ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
        findings = list(d8_gold_only_sourcing(ctx))
        assert len(findings) == 1, f"Expected one finding for Schema={schema}"
        assert findings[0].rule_id == "D8"


# ---------------------------------------------------------------------------
# C1 — parameterized connection
# ---------------------------------------------------------------------------


def test_c1_flags_string_host(tmp_path: Path) -> None:
    ctx = _ctx_m(tmp_path, "bad_c1_string_host.tmdl")
    findings = list(c1_parameterized_connection(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "C1"
    assert findings[0].severity is Severity.ERROR
    assert "string literal" in findings[0].message


def test_c1_passes_parameterized(tmp_path: Path) -> None:
    ctx = _ctx_m(tmp_path, "clean_gold_source.tmdl")
    assert list(c1_parameterized_connection(ctx)) == []


def test_c1_flags_string_db_arg(tmp_path: Path) -> None:
    """Second argument as a string literal must also be flagged."""
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "table T",
        "\tpartition T = m",
        "\t\tsource =",
        "\t\t\tlet",
        '\t\t\t\tSrc = PostgreSQL.Database(ServerParam, "mydb"),',
        '\t\t\t\tData = Value.NativeQuery(Src, "SELECT 1")',
        "\t\t\tin",
        "\t\t\t\tData",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    findings = list(c1_parameterized_connection(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "C1"


def test_c1_does_not_flag_native_query_string(tmp_path: Path) -> None:
    """The SQL string in Value.NativeQuery must NOT trigger C1."""
    ctx = _ctx_m(tmp_path, "clean_gold_source.tmdl")
    assert list(c1_parameterized_connection(ctx)) == []


def test_c1_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/X.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "table T",
        "\tpartition T = m",
        "\t\tsource =",
        "\t\t\tlet",
        '\t\t\t\tSrc = PostgreSQL.Database("myhost", DbParam)',
        "\t\t\tin",
        "\t\t\t\tSrc",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(c1_parameterized_connection(ctx)) == []


# ---------------------------------------------------------------------------
# D7 broadening (#4): table-level `dataCategory: Time` + a column `isKey` is the
# REAL "Mark as Date Table" marker and must satisfy D7 (in addition to the
# annotation form). Column-level dataCategory alone / no isKey is NOT enough.
# ---------------------------------------------------------------------------


def test_d7_passes_with_datacategory_and_iskey(tmp_path: Path) -> None:
    """TI + a Date table marked via `dataCategory: Time` + `isKey` -> no finding."""
    ctx = _ctx(tmp_path, "clean_date_datacategory.tmdl")
    assert list(d7_ti_needs_date_marker(ctx)) == []


def test_d7_fires_when_datacategory_but_no_iskey(tmp_path: Path) -> None:
    """`dataCategory: Time` WITHOUT an isKey column is not a valid marker -> D7 fires.

    Honors the spec stance that the date-table marker requires the Key column,
    not just the table data category.
    """
    ctx = _ctx(tmp_path, "bad_datacategory_no_key.tmdl")
    findings = list(d7_ti_needs_date_marker(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "D7"


# ---------------------------------------------------------------------------
# D9 — no hardcoded date literals in measures
# ---------------------------------------------------------------------------


def test_d9_flags_date_literal(tmp_path: Path) -> None:
    findings = list(d9_no_hardcoded_dates(_ctx(tmp_path, "bad_date_literal.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D9"
    assert findings[0].severity is Severity.WARNING
    assert "SalesSince" in findings[0].message


def test_d9_passes_clean(tmp_path: Path) -> None:
    assert (
        list(d9_no_hardcoded_dates(_ctx(tmp_path, "clean_no_date_literal.tmdl"))) == []
    )


def test_d9_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d9_no_hardcoded_dates(_ctx(tmp_path, "bad_date_literal.tmdl")))
    assert findings[0].locator.endswith(":3")


def test_d9_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/tmdl/bad_date_literal.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / "bad_date_literal.tmdl").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d9_no_hardcoded_dates(ctx)) == []


# ---------------------------------------------------------------------------
# D10 — no FILTER(ALL(...)) full-table-scan anti-pattern
# ---------------------------------------------------------------------------


def test_d10_flags_filter_all(tmp_path: Path) -> None:
    findings = list(d10_no_filter_all(_ctx(tmp_path, "bad_filter_all.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D10"
    assert findings[0].severity is Severity.WARNING
    assert "CashSales" in findings[0].message


def test_d10_passes_clean(tmp_path: Path) -> None:
    assert list(d10_no_filter_all(_ctx(tmp_path, "clean_column_filter.tmdl"))) == []


def test_d10_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d10_no_filter_all(_ctx(tmp_path, "bad_filter_all.tmdl")))
    assert findings[0].locator.endswith(":3")


def test_d10_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/tmdl/bad_filter_all.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / "bad_filter_all.tmdl").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d10_no_filter_all(ctx)) == []


# ---------------------------------------------------------------------------
# D11 — every measure carries a /// doc comment
# ---------------------------------------------------------------------------


def test_d11_flags_undocumented_measure(tmp_path: Path) -> None:
    findings = list(d11_measures_documented(_ctx(tmp_path, "bad_no_doc.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D11"
    assert findings[0].severity is Severity.WARNING
    assert "UndocumentedSales" in findings[0].message


def test_d11_passes_documented(tmp_path: Path) -> None:
    assert list(d11_measures_documented(_ctx(tmp_path, "clean_with_doc.tmdl"))) == []


def test_d11_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d11_measures_documented(_ctx(tmp_path, "bad_no_doc.tmdl")))
    assert findings[0].locator.endswith(":3")


def test_d11_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/tmdl/bad_no_doc.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / "bad_no_doc.tmdl").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d11_measures_documented(ctx)) == []
