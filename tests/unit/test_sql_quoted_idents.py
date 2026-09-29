"""Quoted SQL identifiers reach S2/S3/S4b/D8, and S4b is bounded per statement.

A double-quoted PostgreSQL identifier (``"bronze"``) is a NAME, not a string
literal. The tokenizer used to collapse it like ``'...'``, so the schema and zone
checks never saw it. Also covers the S4b statement bound, ``DROP SCHEMA <zone>``
and destructive DML (TRUNCATE / unfiltered DELETE) on bronze.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.dax import d8_gold_only_sourcing
from seshat.rules.sql import s2_medallion_schemas, s3_vw_prefix, s4b_guard_form
from seshat.sql import stale_schema_tokens, tokenize_sql

pytestmark = pytest.mark.unit


def _sql_ctx(tmp_path: Path, sql: str) -> RuleContext:
    rel = "warehouse/migrations/0001_x.sql"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(sql, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def _s4b(tmp_path: Path, sql: str) -> list[tuple[Severity, str]]:
    return [(f.severity, f.message) for f in s4b_guard_form(_sql_ctx(tmp_path, sql))]


def test_default_tokenizer_still_drops_quoted_spans() -> None:
    # Consumers that did not opt in (S5/S7/date-spine) keep the old stream.
    assert [t.text for t in tokenize_sql('SELECT "a" FROM t') if t.text] == [
        "SELECT",
        "FROM",
        "t",
    ]


def test_identifier_mode_keeps_the_name_with_escapes_collapsed() -> None:
    toks = tokenize_sql('SELECT "we""ird" FROM x', identifiers=True)
    assert [t.text for t in toks] == ["SELECT", '"we"ird"', "FROM", "x"]


def test_stale_schema_tokens_sees_quoted_schema() -> None:
    assert stale_schema_tokens('SELECT * FROM "raw"."orders"') == [("raw", 1)]
    assert stale_schema_tokens('SELECT * FROM "bronze"."sales"') == [("bronze", 1)]


def test_quoted_dot_is_not_a_qualifier() -> None:
    # A quoted identifier spelled "." must never act as the `.` punctuation.
    assert stale_schema_tokens('SELECT bronze "." FROM gold.t') == []


def test_s2_flags_quoted_raw_schema(tmp_path: Path) -> None:
    ctx = _sql_ctx(tmp_path, 'SELECT id FROM "raw"."orders";\n')
    findings = list(s2_medallion_schemas(ctx))
    assert [f.rule_id for f in findings] == ["S2"]


def test_d8_flags_escaped_quoted_bronze_in_native_query(tmp_path: Path) -> None:
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    tmdl = "\n".join(
        [
            "table T",
            "\tpartition T = m",
            "\t\tsource =",
            "\t\t\tlet",
            "\t\t\t\tSrc = PostgreSQL.Database(S, D),",
            '\t\t\t\tData = Value.NativeQuery(Src, "SELECT * FROM '
            '""bronze"".""sales""")',
            "\t\t\tin",
            "\t\t\t\tData",
            "",
        ]
    )
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True)
    dest.write_text(tmdl, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    findings = list(d8_gold_only_sourcing(ctx))
    assert findings and all(f.rule_id == "D8" for f in findings)
    assert "bronze" in findings[0].message


def test_s3_accepts_quoted_view_name(tmp_path: Path) -> None:
    ctx = _sql_ctx(tmp_path, 'CREATE VIEW gold."vw_sales" AS SELECT 1;\n')
    assert list(s3_vw_prefix(ctx)) == []


def test_s3_flags_quoted_view_name_without_prefix(tmp_path: Path) -> None:
    ctx = _sql_ctx(tmp_path, 'CREATE VIEW "gold"."sales" AS SELECT 1;\n')
    findings = list(s3_vw_prefix(ctx))
    assert len(findings) == 1
    assert "'sales'" in findings[0].message


def test_s4b_quoted_bronze_drop_is_an_error(tmp_path: Path) -> None:
    result = _s4b(tmp_path, 'DROP TABLE "bronze"."sales";\n')
    assert [sev for sev, _ in result] == [Severity.ERROR]


def test_s4b_guard_window_stops_at_the_statement_terminator(tmp_path: Path) -> None:
    result = _s4b(tmp_path, "DROP SCHEMA bronze; DROP TABLE IF EXISTS silver.x;\n")
    assert [sev for sev, _ in result] == [Severity.ERROR]


def test_s4b_drop_schema_bronze_cascade_is_an_error(tmp_path: Path) -> None:
    result = _s4b(tmp_path, "DROP SCHEMA bronze CASCADE;\n")
    assert [sev for sev, _ in result] == [Severity.ERROR]


def test_s4b_guarded_schema_create_still_passes(tmp_path: Path) -> None:
    assert _s4b(tmp_path, "CREATE SCHEMA IF NOT EXISTS bronze;\n") == []


def test_s4b_truncate_bronze_is_an_error(tmp_path: Path) -> None:
    result = _s4b(tmp_path, "TRUNCATE bronze.sales;\n")
    assert [sev for sev, _ in result] == [Severity.ERROR]
    assert "TRUNCATE" in result[0][1]


def test_s4b_unfiltered_delete_on_bronze_is_an_error(tmp_path: Path) -> None:
    result = _s4b(tmp_path, "DELETE FROM bronze.sales;\n")
    assert [sev for sev, _ in result] == [Severity.ERROR]


def test_s4b_dml_outside_bronze_and_filtered_delete_pass(tmp_path: Path) -> None:
    sql = (
        "TRUNCATE silver.x;\n"
        "DELETE FROM gold.y;\n"
        "DELETE FROM bronze.z WHERE loaded_at < now();\n"
        "GRANT DELETE ON bronze.z TO reader;\n"
    )
    assert _s4b(tmp_path, sql) == []


def test_s4b_on_delete_clause_inside_ddl_is_not_dml(tmp_path: Path) -> None:
    sql = (
        "BEGIN;\n"
        "CREATE TABLE silver.x (id int REFERENCES bronze.y ON DELETE CASCADE);\n"
        "COMMIT;\n"
    )
    assert _s4b(tmp_path, sql) == []
