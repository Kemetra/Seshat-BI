import pytest

from seshat.sql import stale_schema_tokens, tokenize_sql

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


def test_tokenize_preserves_psql_meta_command_backslash() -> None:
    # #448 (Codex P1): a psql `\`-meta-command must keep its backslash so a rule can
    # tell the buffer-sending family (`\g`/`\gx`/`\gexec`) apart from an identifier.
    bs = chr(92)
    for cmd in (bs + "g", bs + "gx", bs + "gexec", bs + "set", bs + "d+"):
        toks = [t.text for t in tokenize_sql("SELECT 1 " + cmd) if t.text]
        assert cmd in toks, (cmd, toks)


def test_tokenize_g_meta_command_is_a_distinct_token_not_identifier_g() -> None:
    bs = chr(92)
    toks = [t.text for t in tokenize_sql("DROP TABLE bronze.x " + bs + "g") if t.text]
    assert toks[-1] == bs + "g"  # not a bare "g"


def test_tokenize_bare_trailing_backslash_is_skipped() -> None:
    # A lone backslash (EOL or `\` + non-command char) matches no meta-command and is
    # skipped, not emitted as a token. (Bare digits never tokenize -- leading-digit
    # is not a _WORD -- so use identifier tokens to isolate the backslash behavior.)
    bs = chr(92)
    assert [t.text for t in tokenize_sql("SELECT x " + bs) if t.text] == ["SELECT", "x"]
    assert [t.text for t in tokenize_sql("a " + bs + " b") if t.text] == ["a", "b"]
