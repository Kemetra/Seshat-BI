from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.sql import (
    s1_snake_case_identifiers,
    s2_medallion_schemas,
    s3_vw_prefix,
    s4a_migration_numbering,
    s4b_guard_form,
)

pytestmark = pytest.mark.unit

# Canonical fixture content lives in flat tracked files (read-only source); each
# test stages copies into its own tmp_path so tests never write into the real
# repo tree and never depend on a file another test wrote.
FIXTURES = Path(__file__).parent.parent / "fixtures" / "sql"


def _stage(tmp_path: Path, name: str) -> str:
    """Copy fixture `name` into tmp_path/warehouse/ and return its rel path."""
    src = FIXTURES / name
    dest_dir = tmp_path / "warehouse"
    dest_dir.mkdir(exist_ok=True)
    (dest_dir / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return f"warehouse/{name}"


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


def test_s1_passes_snake_case(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s1_s2.sql"))
    assert list(s1_snake_case_identifiers(ctx)) == []


def test_s1_flags_quoted_caps(tmp_path: Path) -> None:
    # #46: fixture has exactly 2 violations: "Sale Items" and "Item Id"
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s1_quoted_caps.sql"))
    findings = list(s1_snake_case_identifiers(ctx))
    assert len(findings) == 2, (
        f"expected 2 S1 findings, got {len(findings)}: {findings}"
    )
    assert all(f.rule_id == "S1" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    messages = " ".join(f.message for f in findings)
    assert "Sale Items" in messages
    assert "Item Id" in messages


def _stage_text(tmp_path: Path, name: str, sql: str) -> str:
    dest_dir = tmp_path / "warehouse"
    dest_dir.mkdir(exist_ok=True)
    (dest_dir / name).write_text(sql, encoding="utf-8")
    return f"warehouse/{name}"


def test_s1_ignores_quoted_text_in_comments(tmp_path: Path) -> None:
    """S1 must not flag a double-quoted phrase inside a SQL COMMENT.

    Regression guard (2026-06-25 defect): a comment like
    `-- ... the dirty Kaggle "retail store sales" CSV` tripped S1 because the rule
    scanned raw lines with the _QUOTED regex and never stripped comments (unlike
    S3/S5/S6/S7, which route through the comment-aware lexer). A double-quoted
    spaced phrase in a comment is prose, not a PG identifier.
    """
    sql = (
        "-- Build silver.retail_store_sales from the dirty Kaggle "
        '"retail store sales" CSV.\n'
        '/* block comment with a "Bad Quoted Name" inside */\n'
        "CREATE TABLE silver.retail_store_sales (transaction_id text);\n"
    )
    ctx = _ctx(tmp_path, _stage_text(tmp_path, "comment_quotes.sql", sql))
    assert list(s1_snake_case_identifiers(ctx)) == []


def test_s1_still_flags_real_quoted_identifier_after_comment_fix(
    tmp_path: Path,
) -> None:
    """The comment fix must NOT blind S1 to a real bad quoted identifier in code."""
    sql = (
        '-- a comment mentioning "ignored phrase"\n'
        'CREATE TABLE silver."Bad Name" (x int);\n'
    )
    ctx = _ctx(tmp_path, _stage_text(tmp_path, "real_bad_ident.sql", sql))
    findings = list(s1_snake_case_identifiers(ctx))
    assert findings, "S1 must still catch the real quoted non-snake_case identifier"
    assert any("Bad Name" in f.message for f in findings)
    assert all("ignored phrase" not in f.message for f in findings)


def test_strip_sql_noise_comment_marker_inside_string_is_data() -> None:
    """`_strip_sql_noise` (S6/S8's stripper) must not treat a comment marker inside
    a string literal as a comment (audit #10 regression guard).

    The stripper collapses string CONTENTS to '' anyway, so a `--`/`/* */` inside a
    string never reaches the rule scan -- and, crucially, the `-1`/code AFTER the
    string is preserved. (The `''` escape is cosmetically mis-split into `''''` but
    span parity is even, so no S6/S8 VERDICT changes -- see the §A deferral note in
    rules/sql.py. These cases lock in the behavior that is correct today.)
    """
    from seshat.rules.sql import _strip_sql_noise

    # A `--` and `/* */` inside string literals must not eat the trailing `-1`.
    assert "-1" in _strip_sql_noise("SELECT '-- x', -1 AS y;")
    assert "-1" in _strip_sql_noise("SELECT 'a /* b */ c', -1;")
    # A `''` escape keeps the trailing code intact (cosmetic mis-split only).
    out = _strip_sql_noise("INSERT INTO gold.dim_x VALUES ('it''s', -1);")
    assert "-1" in out
    assert "FROM" not in out  # nothing spuriously swallowed/exposed


def test_strip_sql_comments_preserves_double_dash_inside_string_literal() -> None:
    """`--` inside a '...' string literal is DATA, not a comment marker.

    Regression guard (2026-06-25 Codex PR review): strip_sql_comments tracked no
    quote state, so a `'--'` literal opened a phantom comment span that blanked the
    rest of the line -- hiding any real bad quoted identifier after it. The literal
    body may be collapsed, but text AFTER the closing quote must survive intact.
    """
    from seshat.sql import strip_sql_comments

    src = "SELECT '--' AS x, silver.\"Bad Name\" AS y;\n"
    out = strip_sql_comments(src)
    # the real quoted identifier after the literal must NOT be blanked away
    assert '"Bad Name"' in out
    assert out.endswith("AS y;\n")  # nothing after the literal was eaten as a comment


def test_strip_sql_comments_double_dash_inside_quoted_identifier() -> None:
    """A `--` inside a "..." quoted identifier is also not a comment start."""
    from seshat.sql import strip_sql_comments

    src = 'CREATE TABLE silver."has--dashes" (x int); -- trailing comment\n'
    out = strip_sql_comments(src)
    assert '"has--dashes"' in out  # the identifier (incl. its --) is preserved
    assert "trailing comment" not in out  # the real trailing comment IS stripped


def test_s1_flags_bad_identifier_after_double_dash_string_literal(
    tmp_path: Path,
) -> None:
    """S1 must still flag a bad quoted identifier sitting after a `'--'` literal.

    The user-visible half of the strip_sql_comments quote-state defect: before the
    fix, S1 saw the literal's `--` as a comment and never reached `"Bad Name"`.
    """
    sql = "SELECT '--' AS x, silver.\"Bad Name\" AS y;\n"
    ctx = _ctx(tmp_path, _stage_text(tmp_path, "dash_in_literal.sql", sql))
    findings = list(s1_snake_case_identifiers(ctx))
    assert findings, "S1 must catch the bad identifier after a '--' string literal"
    assert any("Bad Name" in f.message for f in findings)


def test_s2_passes_raw_amount_column(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s1_s2.sql"))
    assert list(s2_medallion_schemas(ctx)) == []


def test_s2_flags_create_schema_raw(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s2_create_schema_raw.sql"))
    findings = list(s2_medallion_schemas(ctx))
    assert len(findings) >= 1
    assert any("raw" in f.message for f in findings)
    assert all(f.rule_id == "S2" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


def test_s2_exempts_warehouse_readme(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "warehouse/README.md")  # not a .sql -> never scanned
    assert list(s2_medallion_schemas(ctx)) == []


def test_s3_passes_prefixed_views(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s3_vw.sql"))
    assert list(s3_vw_prefix(ctx)) == []


def test_s3_flags_unprefixed_view(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s3_no_prefix.sql"))
    findings = list(s3_vw_prefix(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "S3"
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator == "warehouse/fail_s3_no_prefix.sql:1"


def test_s4a_passes_contiguous_unique(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path,
        "warehouse/migrations/0001_init.sql",
        "warehouse/migrations/0002_add_sales.sql",
    )
    assert list(s4a_migration_numbering(ctx)) == []


def test_s4a_flags_bad_name(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "warehouse/migrations/1_init.sql")
    findings = list(s4a_migration_numbering(ctx))
    assert any(f.rule_id == "S4a" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(":" not in f.locator.rsplit(".sql", 1)[-1] for f in findings)


def test_s4a_flags_gap(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path,
        "warehouse/migrations/0001_init.sql",
        "warehouse/migrations/0003_skip.sql",
    )
    findings = list(s4a_migration_numbering(ctx))
    assert any("gap" in f.message or "contiguous" in f.message for f in findings)


def test_s4a_flags_duplicate(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path,
        "warehouse/migrations/0001_init.sql",
        "warehouse/migrations/0001_again.sql",
    )
    findings = list(s4a_migration_numbering(ctx))
    assert any("duplicate" in f.message for f in findings)


def test_s4b_passes_guarded_forms(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s4b_guarded.sql"))
    assert list(s4b_guard_form(ctx)) == []


def test_s4b_warns_on_bare_create_and_alter(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s4b_bare.sql"))
    findings = list(s4b_guard_form(ctx))
    assert len(findings) == 2
    assert all(f.rule_id == "S4b" for f in findings)
    assert all(f.severity is Severity.WARNING for f in findings)
    assert {f.locator for f in findings} == {
        "warehouse/fail_s4b_bare.sql:1",
        "warehouse/fail_s4b_bare.sql:2",
    }


# --- audit fixes (2026-06-26): S4b false-negative / false-positive ----------


def test_s4b_bare_start_is_not_a_transaction(tmp_path: Path) -> None:
    """`START` alone (e.g. CREATE SEQUENCE ... START WITH 1) must NOT open a txn.

    Audit finding: `START` unconditionally set in_txn=True, silently suppressing
    later bare-DDL findings. Only `START TRANSACTION` is a real transaction start.
    A bare CREATE after a `START WITH` sequence must still WARN.
    """
    sql = "CREATE SEQUENCE gold.s START WITH 1;\nCREATE TABLE gold.t (id int);\n"
    ctx = _ctx(tmp_path, _stage_text(tmp_path, "fail_s4b_start_seq.sql", sql))
    findings = list(s4b_guard_form(ctx))
    # The bare CREATE TABLE on line 2 must still be flagged (not suppressed by START).
    assert any(f.rule_id == "S4b" and f.locator.endswith(":2") for f in findings), (
        findings
    )


def test_s4b_start_transaction_still_opens_txn(tmp_path: Path) -> None:
    """`START TRANSACTION` still opens a txn so silver/gold bare DDL inside passes."""
    sql = "START TRANSACTION;\nCREATE TABLE gold.t (id int);\nCOMMIT;\n"
    ctx = _ctx(tmp_path, _stage_text(tmp_path, "pass_s4b_start_txn.sql", sql))
    findings = list(s4b_guard_form(ctx))
    # Inside a real transaction, the bare CREATE is acceptable -> no WARNING for line 2.
    assert not any(f.locator.endswith(":2") for f in findings), findings


def test_sql_rules_exempt_tests_path_files(tmp_path: Path) -> None:
    """#48: S1-S4b must NOT flag SQL files under tests/ (non-warehouse exemption).

    iter_sql_files() only yields files starting with `warehouse/`; a tests/ path
    is never forwarded to any S rule. Each violation below WOULD fire if the file
    were under warehouse/ -- verifying each assertion is load-bearing:
      S1 -- "Sale Items", "Item Id" (quoted non-snake_case identifiers)
      S2 -- CREATE SCHEMA raw (stale schema token)
      S3 -- CREATE VIEW gold.bad_view (missing vw_ prefix)
      S4b -- bare CREATE TABLE gold.t (no IF NOT EXISTS / BEGIN guard)
    """
    bad_sql = (
        "CREATE SCHEMA raw;\n"
        "CREATE VIEW gold.bad_view AS SELECT 1;\n"
        'CREATE TABLE gold."Sale Items" (\n'
        '    "Item Id" BIGINT\n'
        ");\n"
    )
    tests_dir = tmp_path / "tests" / "fixtures"
    tests_dir.mkdir(parents=True)
    (tests_dir / "bad.sql").write_text(bad_sql, encoding="utf-8")
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=("tests/fixtures/bad.sql",),
    )
    assert list(s1_snake_case_identifiers(ctx)) == [], "S1 must skip tests/ paths"
    assert list(s2_medallion_schemas(ctx)) == [], "S2 must skip tests/ paths"
    assert list(s3_vw_prefix(ctx)) == [], "S3 must skip tests/ paths"
    assert list(s4b_guard_form(ctx)) == [], "S4b must skip tests/ paths"


def test_s4b_create_or_replace_function_is_guarded(tmp_path: Path) -> None:
    """`CREATE OR REPLACE FUNCTION` is a guarded form -> no false-positive WARNING.

    Audit finding: _is_guarded only matched `OR REPLACE VIEW`, so every stored
    function/procedure migration fired a spurious finding.
    """
    sql = (
        "CREATE OR REPLACE FUNCTION gold.f() RETURNS int AS 'select 1' LANGUAGE sql;\n"
    )
    ctx = _ctx(tmp_path, _stage_text(tmp_path, "pass_s4b_or_replace_fn.sql", sql))
    findings = list(s4b_guard_form(ctx))
    assert findings == [], findings
