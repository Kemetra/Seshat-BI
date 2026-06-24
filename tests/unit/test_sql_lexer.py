import pytest

from retail.sql import stale_schema_tokens, tokenize_sql

pytestmark = pytest.mark.unit


def test_tokenize_tracks_line_numbers() -> None:
    toks = tokenize_sql("CREATE SCHEMA gold;\nSELECT 1;")
    texts = [(t.text, t.line) for t in toks if t.text]
    assert ("CREATE", 1) in texts
    assert ("gold", 1) in texts
    assert ("SELECT", 2) in texts


def test_tokenize_strips_line_comment() -> None:
    toks = tokenize_sql("SELECT 1; -- CREATE SCHEMA raw\n")
    assert all(t.text != "raw" for t in toks)


def test_tokenize_strips_string_literal_contents() -> None:
    toks = tokenize_sql("SELECT 'CREATE SCHEMA raw' AS note;")
    assert all(t.text != "raw" for t in toks)


def test_stale_schema_passes_snake_case_column() -> None:
    # "raw_amount" is a single identifier; \braw\b does NOT match it.
    assert stale_schema_tokens("SELECT raw_amount FROM gold.sales;") == []


def test_stale_schema_flags_create_schema_raw() -> None:
    hits = stale_schema_tokens("CREATE SCHEMA raw;")
    assert hits == [("raw", 1)]


def test_stale_schema_flags_qualifier_and_from() -> None:
    hits = stale_schema_tokens("SELECT * FROM marts.orders;")
    assert ("marts", 1) in hits
