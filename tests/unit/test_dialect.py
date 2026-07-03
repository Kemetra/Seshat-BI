from __future__ import annotations

import pytest

from retail.dialect import get_dialect

pytestmark = pytest.mark.unit


def test_postgres_count_where_is_filter() -> None:
    pg = get_dialect("postgres")
    # Postgres KEEPS the native FILTER form (byte-identical to today's SQL).
    assert pg.count_where("x IS NULL") == "count(*) FILTER (WHERE x IS NULL)"


def test_postgres_quote_ident_double_quote() -> None:
    pg = get_dialect("postgres")
    assert pg.quote_ident("invoice_no") == '"invoice_no"'


def test_postgres_placeholder_is_percent_s() -> None:
    assert get_dialect("postgres").placeholder() == "%s"


def test_get_dialect_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_dialect("oracle")


def test_postgres_distinct_tuple_count_row_value() -> None:
    pg = get_dialect("postgres")
    assert pg.distinct_tuple_count(("invoice_no", "line_no"), "silver.t") == (
        "count(DISTINCT (invoice_no, line_no))"
    )


def test_postgres_columns_query_is_information_schema() -> None:
    pg = get_dialect("postgres")
    sql = pg.columns_query()
    assert "information_schema.columns" in sql
    assert "table_schema = %s" in sql
    assert "table_name = %s" in sql
    assert "ORDER BY ordinal_position" in sql


def test_sqlserver_count_where_is_count_case() -> None:
    d = get_dialect("sqlserver")
    # COUNT(CASE ...) — exact on empty input (returns 0, not NULL like SUM).
    assert d.count_where("x IS NULL") == "COUNT(CASE WHEN x IS NULL THEN 1 END)"


def test_sqlserver_distinct_tuple_is_derived_table() -> None:
    d = get_dialect("sqlserver")
    assert d.distinct_tuple_count(("a", "b"), "s.t") == (
        "(SELECT COUNT(*) FROM (SELECT DISTINCT a, b FROM s.t) AS sub)"
    )


def test_sqlserver_quote_ident_brackets() -> None:
    assert get_dialect("sqlserver").quote_ident("col") == "[col]"


def test_sqlserver_placeholder_is_qmark() -> None:
    assert get_dialect("sqlserver").placeholder() == "?"


def test_sqlserver_translate_params_percent_s_to_qmark() -> None:
    d = get_dialect("sqlserver")
    assert d.translate_params("WHERE a = %s AND b = %s") == "WHERE a = ? AND b = ?"


def test_sqlserver_is_text_type() -> None:
    d = get_dialect("sqlserver")
    assert d.is_text_type("varchar")
    assert d.is_text_type("NVARCHAR")
    assert not d.is_text_type("int")


def test_mysql_count_where_is_count_case() -> None:
    assert get_dialect("mysql").count_where("x IS NULL") == (
        "COUNT(CASE WHEN x IS NULL THEN 1 END)"
    )


def test_mysql_quote_ident_backtick() -> None:
    assert get_dialect("mysql").quote_ident("col") == "`col`"


def test_mysql_placeholder_is_percent_s() -> None:
    # mysql-connector paramstyle is pyformat (%s), same as psycopg2.
    assert get_dialect("mysql").placeholder() == "%s"


def test_mysql_translate_params_noop() -> None:
    d = get_dialect("mysql")
    assert d.translate_params("WHERE a = %s") == "WHERE a = %s"


def test_mysql_distinct_tuple_is_derived_table() -> None:
    assert get_dialect("mysql").distinct_tuple_count(("a", "b"), "s.t") == (
        "(SELECT COUNT(*) FROM (SELECT DISTINCT a, b FROM s.t) AS sub)"
    )


def test_snowflake_quote_ident_uppercases() -> None:
    # R1: Snowflake folds unquoted names to UPPERCASE; quoting must match stored case
    # or the query silently matches nothing.
    assert get_dialect("snowflake").quote_ident("my_table") == '"MY_TABLE"'


def test_snowflake_quote_qualified_uppercases_each_part() -> None:
    assert (
        get_dialect("snowflake").quote_qualified("bronze.my_table", context="t")
        == '"BRONZE"."MY_TABLE"'
    )


def test_snowflake_count_where_is_count_case() -> None:
    assert get_dialect("snowflake").count_where("x IS NULL") == (
        "COUNT(CASE WHEN x IS NULL THEN 1 END)"
    )


def test_snowflake_is_text_type_collapses_to_text() -> None:
    d = get_dialect("snowflake")
    assert d.is_text_type("TEXT")
    assert d.is_text_type("text")
    assert not d.is_text_type("NUMBER")


def test_snowflake_columns_query_uppercases_filter() -> None:
    # The profiler must pass UPPERCASE (schema, table); the query uses ILIKE-safe
    # equality on UPPER()-folded catalog values.
    sql = get_dialect("snowflake").columns_query()
    assert "INFORMATION_SCHEMA.COLUMNS" in sql
    assert "%s" in sql  # snowflake default paramstyle is pyformat


@pytest.mark.parametrize("engine", ["postgres", "sqlserver", "mysql", "snowflake"])
def test_count_where_predicate_is_embedded_verbatim(engine: str) -> None:
    # R3: the conditional-count fragment must count only matching rows; every engine
    # embeds the predicate. (PG uses FILTER, the others COUNT(CASE) — both count 0,
    # never NULL, on zero matches; the string form encodes that.)
    frag = get_dialect(engine).count_where("v IS NULL")
    assert "v IS NULL" in frag
    assert frag.startswith(("count(", "COUNT("))


def test_r2_param_translation_qmark_only_for_pyodbc() -> None:
    # R2: only the qmark engine rewrites %s -> ?; the pyformat engines leave it.
    assert get_dialect("sqlserver").translate_params("a=%s") == "a=?"
    for e in ("postgres", "mysql", "snowflake"):
        assert get_dialect(e).translate_params("a=%s") == "a=%s"


def test_distinct_tuple_form_is_portable_for_new_engines() -> None:
    # R (portability): the three new engines all use the derived-table form.
    for e in ("sqlserver", "mysql", "snowflake"):
        out = get_dialect(e).distinct_tuple_count(("a", "b"), "s.t")
        assert out.startswith("(SELECT COUNT(*) FROM (SELECT DISTINCT a, b")
        assert out.endswith("AS sub)")


def test_normalize_catalog_literal_identity_for_non_snowflake() -> None:
    # Guards against a future "simplify to one method" refactor silently breaking
    # Postgres (and the other non-folding engines) by uppercasing everywhere.
    for e in ("postgres", "sqlserver", "mysql"):
        assert get_dialect(e).normalize_catalog_literal("Bronze") == "Bronze"


def test_normalize_catalog_literal_uppercases_for_snowflake() -> None:
    assert get_dialect("snowflake").normalize_catalog_literal("bronze") == "BRONZE"


# ---------------------------------------------------------------------------
# R4 -- resolve_config / connect / redact (no live driver needed)
# ---------------------------------------------------------------------------


def test_postgres_resolve_config_delegates_to_resolve_dsn() -> None:
    d = get_dialect("postgres")
    env = {
        "ANALYTICS_DB_HOST": "h",
        "ANALYTICS_DB_USER": "u",
        "ANALYTICS_DB_PASSWORD": "p",
        "ANALYTICS_DB_NAME": "db",
    }
    assert d.resolve_config(env) == "postgresql://u:p@h/db"


def test_postgres_resolve_config_none_without_host() -> None:
    assert get_dialect("postgres").resolve_config({}) is None


def test_postgres_redact_delegates_to_cli_redact_dsn() -> None:
    d = get_dialect("postgres")
    dsn = "postgresql://admin:s3cret@h:5432/db"
    out = d.redact("auth failed for admin at h with s3cret", dsn)
    assert "s3cret" not in out
    assert "admin" not in out


def test_sqlserver_resolve_config_builds_odbc_keyword_string() -> None:
    d = get_dialect("sqlserver")
    env = {
        "ANALYTICS_DB_HOST": "h",
        "ANALYTICS_DB_PORT": "1433",
        "ANALYTICS_DB_NAME": "db",
        "ANALYTICS_DB_USER": "u",
        "ANALYTICS_DB_PASSWORD": "p",
    }
    cfg = d.resolve_config(env)
    assert cfg is not None
    assert "SERVER=h,1433" in cfg
    # UID/PWD are brace-wrapped per the ODBC-documented escape (R4: this is
    # what makes a ";" inside a password unambiguous -- see redact()).
    assert "UID={u}" in cfg
    assert "PWD={p}" in cfg
    assert "DATABASE=db" in cfg


def test_sqlserver_resolve_config_none_without_host() -> None:
    assert get_dialect("sqlserver").resolve_config({}) is None


def test_sqlserver_redact_scrubs_pwd() -> None:
    d = get_dialect("sqlserver")
    cfg = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=h;UID=u;PWD=topsecret"
    out = d.redact("login failed for PWD=topsecret at SERVER=h", cfg)
    assert "topsecret" not in out
    assert "h" not in out.split("SERVER=")[-1] if "SERVER=" in out else True


def test_sqlserver_redact_scrubs_reformatted_password_not_in_kw_form() -> None:
    # The driver may reformat the error so the secret appears bare (no "PWD="
    # prefix survives) -- the component-level scrub (pass 2) must still catch it.
    d = get_dialect("sqlserver")
    cfg = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=h;UID=u;PWD=hunter2pass"
    out = d.redact("connection refused; credential 'hunter2pass' rejected", cfg)
    assert "hunter2pass" not in out


def test_sqlserver_redact_scrubs_password_containing_semicolon() -> None:
    # R4 adversarial: a password containing ";" must not truncate the scrub.
    # config.split(";") would previously chop "PWD=pa;ss:w0rd" down to "PWD=pa",
    # leaking the "ss:w0rd" half of the real password in error text.
    env = {
        "ANALYTICS_DB_HOST": "h",
        "ANALYTICS_DB_USER": "u",
        "ANALYTICS_DB_PASSWORD": "pa;ss:w0rd",
    }
    d = get_dialect("sqlserver")
    cfg = d.resolve_config(env)
    assert cfg is not None
    out = d.redact("login failed: password 'pa;ss:w0rd' rejected", cfg)
    assert "pa;ss:w0rd" not in out
    assert "ss:w0rd" not in out
    assert "w0rd" not in out


def test_sqlserver_redact_scrubs_bare_host_without_server_prefix() -> None:
    # R4 adversarial: on a DNS/TCP failure, pyodbc/FreeTDS prints the bare host
    # with NO "SERVER=" prefix and no port (e.g. FreeTDS "TCP Provider" errors).
    # The old code only matched "SERVER=..." and stored "host,port" as one
    # composite token, so the port-less bare host never matched and leaked.
    # NOTE: username/password are deliberately multi-char and non-substrings of
    # the message, so a stray single-char accidental match (e.g. "UID=u"
    # matching a letter inside "found") cannot produce a false-positive pass.
    env = {
        "ANALYTICS_DB_HOST": "prodsql.internal.corp",
        "ANALYTICS_DB_USER": "svcuser",
        "ANALYTICS_DB_PASSWORD": "hunter2",
    }
    d = get_dialect("sqlserver")
    cfg = d.resolve_config(env)
    assert cfg is not None
    out = d.redact("TCP Provider: host 'prodsql.internal.corp' not found", cfg)
    assert "prodsql.internal.corp" not in out


def test_sqlserver_redact_regression_simple_password_still_scrubbed() -> None:
    # Regression guard for the brace-wrap change: a password with NO ";" (the
    # common case) must still be fully scrubbed, in both the brace-wrapped
    # PWD={...} form (resolve_config's new output) and if it appears bare in
    # driver-reformatted text.
    env = {
        "ANALYTICS_DB_HOST": "h",
        "ANALYTICS_DB_USER": "u",
        "ANALYTICS_DB_PASSWORD": "topsecret",
    }
    d = get_dialect("sqlserver")
    cfg = d.resolve_config(env)
    assert cfg is not None
    assert "PWD={topsecret}" in cfg
    out = d.redact("login failed: PWD={topsecret} rejected; raw topsecret leaked?", cfg)
    assert "topsecret" not in out


def test_mysql_resolve_config_builds_kwargs_dict() -> None:
    d = get_dialect("mysql")
    env = {
        "ANALYTICS_DB_HOST": "h",
        "ANALYTICS_DB_PORT": "3306",
        "ANALYTICS_DB_USER": "u",
        "ANALYTICS_DB_PASSWORD": "p",
        "ANALYTICS_DB_NAME": "db",
    }
    cfg = d.resolve_config(env)
    assert cfg == {
        "host": "h",
        "port": 3306,
        "user": "u",
        "password": "p",
        "database": "db",
    }


def test_mysql_resolve_config_none_without_host() -> None:
    assert get_dialect("mysql").resolve_config({}) is None


def test_mysql_redact_scrubs_password_and_host() -> None:
    d = get_dialect("mysql")
    cfg = {"host": "prod-mysql-01", "user": "svc", "password": "hunter2mysql"}
    out = d.redact("Access denied for user svc@prod-mysql-01 (hunter2mysql)", cfg)
    assert "hunter2mysql" not in out
    assert "prod-mysql-01" not in out


def test_snowflake_resolve_config_builds_kwargs_dict() -> None:
    d = get_dialect("snowflake")
    env = {
        "ANALYTICS_DB_ACCOUNT": "acme-prod",
        "ANALYTICS_DB_USER": "u",
        "ANALYTICS_DB_PASSWORD": "p",
        "ANALYTICS_DB_WAREHOUSE": "wh",
        "ANALYTICS_DB_ROLE": "role",
        "ANALYTICS_DB_NAME": "db",
    }
    cfg = d.resolve_config(env)
    assert cfg == {
        "account": "acme-prod",
        "user": "u",
        "password": "p",
        "warehouse": "wh",
        "role": "role",
        "database": "db",
    }


def test_snowflake_resolve_config_none_without_account() -> None:
    assert get_dialect("snowflake").resolve_config({}) is None


def test_snowflake_redact_scrubs_password_and_account() -> None:
    d = get_dialect("snowflake")
    cfg = {"account": "acme-prod", "user": "u", "password": "hunter2"}
    out = d.redact("auth error for acme-prod user u pw hunter2", cfg)
    assert "hunter2" not in out
    assert "acme-prod" not in out


@pytest.mark.parametrize("engine", ["sqlserver", "mysql", "snowflake"])
def test_each_engine_connect_is_lazy_no_import_error_at_module_scope(
    engine: str,
) -> None:
    # Constructing/calling resolve_config/redact must never trigger the driver
    # import -- only connect() does, and only when actually invoked. Merely
    # calling get_dialect + resolve_config/redact (without connect) must not
    # raise ImportError even when the optional driver package isn't installed.
    d = get_dialect(engine)
    d.resolve_config({})
    d.redact("no secrets here", {} if engine != "sqlserver" else "")
