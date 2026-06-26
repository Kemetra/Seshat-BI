"""Dollar-quote (`$$` / `$tag$`) handling across the three SQL strippers.

Audit finding #5 (2026-06-26): none of `tokenize_sql`, `strip_sql_comments`, or
`_strip_sql_noise` had a dollar-quote branch, so a PL/pgSQL function/procedure body
wrapped in `$$ ... $$` (or `$tag$ ... $tag$`) leaked verbatim into rule matching --
every `SELECT`, identifier, `--`, `;`, and `-1` inside the body was treated as live
SQL, corrupting S1/S3/S4b/S5/S6/S7/S8.

The fix shares ONE dollar-tag recognizer across all three functions; each keeps its
own output contract (placeholder token / blanked-but-line-preserving / collapsed
literal). These tests pin the recognizer grammar (the close-tag-matching trap, the
`$1`/`$2` positional-param non-opener, empty + named tags, unterminated fail-closed)
and the rule-level consequence (body contents must never reach S1-S8).
"""

from pathlib import Path

import pytest

from retail.core import RuleContext
from retail.rules.sql import (
    s1_snake_case_identifiers,
    s4b_guard_form,
    s6_gold_unknown_member,
    s8_date_dim_no_unknown_member,
)
from retail.sql import strip_sql_comments, tokenize_sql

pytestmark = pytest.mark.unit


def _ctx(tmp_path: Path, name: str, sql: str) -> RuleContext:
    dest_dir = tmp_path / "warehouse"
    dest_dir.mkdir(exist_ok=True)
    (dest_dir / name).write_text(sql, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(f"warehouse/{name}",))


# --- tokenize_sql -----------------------------------------------------------


def test_tokenize_drops_dollar_quoted_body() -> None:
    """A `$$ ... $$` body is data, not tokens -- inner words must not leak."""
    sql = (
        "CREATE FUNCTION gold.f() RETURNS int AS "
        "$$ SELECT raw_count FROM marts.x $$ LANGUAGE sql;"
    )
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    # tokens from the SIGNATURE survive; tokens from the BODY do not.
    assert "FUNCTION" in texts
    assert "LANGUAGE" in texts
    assert "raw_count" not in texts  # body identifier must not leak
    assert "marts" not in texts  # a stale-schema token inside a body must not leak


def test_tokenize_dollar_quote_close_tag_matching() -> None:
    """`$$ ... $tag$ ... $$` closes at the SECOND `$$`; the inner `$tag$` is body.

    The #1 implementation trap: a naive "next `$` run" or "next regex match" would
    close the span at the inner `$tag$`, leaking the trailing body as live SQL.
    """
    sql = (
        "SELECT a AS keep_before $$ body $weird$ still body $weird$ "
        "more body $$ keep_after FROM gold.t;"
    )
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "keep_before" in texts
    assert "keep_after" in texts  # we resumed AFTER the real closing $$
    assert "body" not in texts  # everything between the $$ pair is gone
    assert "weird" not in texts


def test_tokenize_named_dollar_tag_body_dropped() -> None:
    """Named tag `$body$ ... $body$` dropped; a different `$$` inside is body."""
    sql = "DO $body$ DECLARE leaked_ident int; SELECT $$ inner $$ ; $body$;"
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "DO" in texts
    assert "leaked_ident" not in texts
    assert "inner" not in texts


def test_tokenize_dollar_positional_param_is_not_a_dollar_quote() -> None:
    """`$1` / `$2` are positional params, NOT dollar-quote openers.

    The tag grammar `$([A-Za-z_][A-Za-z0-9_]*)?$` requires the char after the
    optional identifier to be `$`; `$1` is followed by a digit, so it must NOT open
    a span and swallow the rest of the statement.
    """
    sql = "SELECT keep_a, $1, keep_b, $2 FROM gold.t;"
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "keep_a" in texts
    assert "keep_b" in texts  # not swallowed by a phantom $1...$2 span
    assert "FROM" in texts
    assert "gold" in texts


def test_tokenize_dollar_inside_identifier_does_not_open_span() -> None:
    """A `$` ATTACHED to a preceding identifier char is identifier text, not a tag.

    PG's identifier-continuation class includes `$` (`a$b$c` is ONE ordinary
    identifier). Without this guard the `$b$` would open a phantom dollar-quote span
    and swallow the rest of the statement to EOF -- a regression vs the bare lexer
    (adversarial verification 2026-06-26, finding #1). The `$` opener is only honored
    when it is NOT glued to a preceding identifier-continuation char.
    """
    sql = "SELECT a$b$c FROM gold.x;"
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    # The trailing clause must NOT be swallowed.
    assert "FROM" in texts
    assert "gold" in texts
    assert "x" in texts


def test_tokenize_dollar_quote_at_string_start_still_opens() -> None:
    """A `$$...$$` at index 0 (no preceding char) must still open -- guards the i==0
    boundary so `text[i-1]` is never read as a negative wrap-around index."""
    sql = "$$ leaked_body $$ keep_after"
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "keep_after" in texts
    assert "leaked_body" not in texts  # the leading dollar body is still neutralized


def test_tokenize_adjacent_dollar_quotes_never_swallow_to_eof() -> None:
    """Back-to-back `$$a$$$$b$$` must never swallow the trailing clause to EOF.

    NOTE: `$$a$$$$b$$` (two dollar-quoted constants with no operator between them) is
    INVALID PostgreSQL (it needs `$$a$$ || $$b$$`), so it never appears in tracked
    SQL. The genuine safety property here is "no EOF-swallow": text after the run
    survives. The `$`-in-identifier guard leaves this strictly better than the bare
    lexer (baseline leaks both `a` and `b`; the guard neutralizes the first,
    properly-closed span). We assert the real invariant, not full PG fidelity.
    """
    texts = [t.text for t in tokenize_sql("before $$a$$$$b$$ after") if t.text]
    assert "before" in texts
    assert "after" in texts  # the real invariant: trailing clause not swallowed
    assert "a" not in texts  # the properly-closed first span IS neutralized


def test_tokenize_dollar_quote_inside_string_literal_is_not_opened() -> None:
    """A `$$` INSIDE a `'...'` string literal is data; the quote branch wins first."""
    sql = "SELECT '$$ not a quote $$' AS x, real_col FROM gold.t;"
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "real_col" in texts  # trailing code not eaten by a phantom dollar span
    assert "FROM" in texts


def test_tokenize_dollar_quote_inside_line_comment_is_not_opened() -> None:
    """A `$$` inside a `--` comment is data; the comment branch wins first."""
    sql = "SELECT keep_me; -- $$ comment never closes\nSELECT also_keep;"
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "keep_me" in texts
    assert "also_keep" in texts  # comment did not open a phantom dollar span


def test_tokenize_unterminated_dollar_quote_fails_closed_to_eof() -> None:
    """An unterminated `$$` consumes to EOF (like the quote/comment branches)."""
    sql = (
        "SELECT before_body $$ everything after is body and never closes SELECT leaked"
    )
    texts = [t.text for t in tokenize_sql(sql) if t.text]
    assert "before_body" in texts
    assert "leaked" not in texts


def test_tokenize_dollar_quote_preserves_line_numbers() -> None:
    """A multi-line `$$` body must not corrupt downstream line accounting."""
    sql = (
        "CREATE FUNCTION f() AS $$\nSELECT 1;\nSELECT 2;\n"
        "$$ LANGUAGE sql;\nSELECT keep_me;"
    )
    toks = [t for t in tokenize_sql(sql) if t.text]
    keep = [t for t in toks if t.text == "keep_me"]
    assert keep, toks
    assert keep[0].line == 5  # body spanned lines 1-4; keep_me is on line 5


# --- strip_sql_comments (S1's stripper) -------------------------------------


def test_strip_sql_comments_blanks_dollar_quoted_body() -> None:
    """A bad quoted identifier INSIDE a `$$` body must not survive for S1 to flag."""
    src = 'CREATE FUNCTION f() AS $$ SELECT "Bad Body Name" $$ LANGUAGE sql;\n'
    out = strip_sql_comments(src)
    assert '"Bad Body Name"' not in out  # body identifier neutralized


def test_strip_sql_comments_dollar_body_does_not_eat_trailing_code() -> None:
    """Text AFTER the closing `$$` (a real quoted identifier) must survive intact."""
    src = (
        "CREATE FUNCTION f() AS $$ body $$ LANGUAGE sql; "
        'CREATE TABLE silver."Bad Name" (x int);\n'
    )
    out = strip_sql_comments(src)
    assert '"Bad Name"' in out  # the real identifier after the body is preserved


# --- _strip_sql_noise (S6/S8's stripper) ------------------------------------


def test_strip_sql_noise_removes_minus_one_inside_dollar_body() -> None:
    """A literal `-1` inside a `$$` body must not reach the S6/S8 raw-text scan."""
    from retail.rules.sql import _strip_sql_noise

    src = "CREATE FUNCTION f() AS $$ VALUES (-1, 'x') $$ LANGUAGE sql;\n"
    out = _strip_sql_noise(src)
    assert "-1" not in out


def test_strip_sql_noise_dollar_body_preserves_line_count() -> None:
    """Newlines inside a stripped `$$` body are preserved for line accounting."""
    from retail.rules.sql import _strip_sql_noise

    src = "line1 $$\nbody2\nbody3\n$$ line4\n"
    out = _strip_sql_noise(src)
    assert out.count("\n") == src.count("\n")


# --- rule-level: body contents must not corrupt findings --------------------


def test_s1_ignores_bad_identifier_inside_dollar_body(tmp_path: Path) -> None:
    """S1 must not flag a non-snake_case quoted identifier living inside a `$$` body."""
    sql = (
        "CREATE OR REPLACE FUNCTION gold.f() RETURNS int AS $$\n"
        '  SELECT "Bad Body Identifier" FROM gold.t;\n'
        "$$ LANGUAGE sql;\n"
    )
    ctx = _ctx(tmp_path, "fn_body_ident.sql", sql)
    assert list(s1_snake_case_identifiers(ctx)) == []


def test_s4b_ignores_ddl_keywords_inside_dollar_body(tmp_path: Path) -> None:
    """A bare `CREATE`/`DROP` inside a `$$` function body is body text, not DDL.

    Before the fix, a `DROP TABLE` keyword sequence inside a PL/pgSQL body was
    tokenized as a real DDL verb and produced a spurious S4b finding.
    """
    sql = (
        "CREATE OR REPLACE FUNCTION gold.rebuild() RETURNS void AS $$\n"
        "BEGIN\n"
        "  DROP TABLE bronze.source;\n"  # body text, NOT a real bronze bare DROP
        "  CREATE TABLE gold.snapshot AS SELECT 1;\n"
        "END;\n"
        "$$ LANGUAGE plpgsql;\n"
    )
    ctx = _ctx(tmp_path, "fn_body_ddl.sql", sql)
    # The only real DDL is the guarded CREATE OR REPLACE FUNCTION -> no findings.
    assert list(s4b_guard_form(ctx)) == []


def test_s6_ignores_dim_create_inside_dollar_body(tmp_path: Path) -> None:
    """A `CREATE TABLE gold.dim_x` inside a `$$` body is body text, not a real dim.

    Before the fix, the body's `CREATE TABLE gold.dim_store` leaked into the raw-text
    scan and S6 demanded a -1 member for a dim that is never actually created.
    """
    sql = (
        "CREATE OR REPLACE FUNCTION gold.gen() RETURNS void AS $$\n"
        "  CREATE TABLE gold.dim_store (store_sk int);\n"
        "$$ LANGUAGE sql;\n"
    )
    ctx = _ctx(tmp_path, "fn_body_dim.sql", sql)
    assert list(s6_gold_unknown_member(ctx)) == []


def test_s8_ignores_date_dim_minus_one_inside_dollar_body(tmp_path: Path) -> None:
    """A date-dim `-1` member INSERT inside a `$$` body is body text, not a real insert.

    S8 is ERROR severity, so a body-leaked -1 date-member insert would WRONGLY block
    the build. The body must be neutralized before the S8 raw-text scan.
    """
    sql = (
        "CREATE OR REPLACE FUNCTION gold.seed() RETURNS void AS $$\n"
        "  INSERT INTO gold.dim_date (date_sk) VALUES (-1);\n"
        "$$ LANGUAGE sql;\n"
    )
    ctx = _ctx(tmp_path, "fn_body_date.sql", sql)
    assert list(s8_date_dim_no_unknown_member(ctx)) == []
