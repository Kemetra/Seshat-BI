# Multi-Engine DB Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the read-only profile + validate seam connect to SQL Server, MySQL, and Snowflake (in addition to the default Postgres) via a thin `Dialect` abstraction over the existing `QueryRunner` Protocol.

**Architecture:** A new `src/seshat/dialect.py` holds a `Dialect` Protocol + four concrete dialects. `PostgresDialect` emits **today's exact SQL** (so the 897-test suite stays a true regression oracle); the three new dialects emit portable/native forms. The three DB modules (`profile.py`, `validate.py`, `value_proxy.py`) stop hardcoding Postgres SQL and route fragment-building through a dialect. Drivers are lazy optional extras. The work ends at a Principle III ratify ledger — no merge to `main`.

**Tech Stack:** Python 3.13, stdlib-only static core, pytest (unit), `ast`-based governance rules. New optional drivers: pyodbc (SQL Server), mysql-connector-python (MySQL), snowflake-connector-python (Snowflake). psycopg2 unchanged (Postgres, default).

## Global Constraints

- **Driver-free import path:** no module-scope import of any DB driver in any `src/seshat/*.py`. Every driver import is LAZY, inside the `connect()` method that uses it. (Enforced by B1/B3; extended in this plan.)
- **Static core stays `dependencies = []`:** new drivers are OPTIONAL extras, never added to `dev`. CI installs none of them; the suite passing proves the seam is driver-free.
- **`PostgresDialect` is behavior-preserving:** it emits byte-identical SQL to today's hardcoded strings. The existing 897 tests MUST stay green after every consumer refactor task.
- **Identifier validation is mandatory at every boundary:** splitting validation (shared) from quoting (Dialect) MUST NOT drop the validate step. Every dynamic identifier is validated (raises `ValueError` BEFORE any SQL is built) then quoted. This is a SQL-injection boundary.
- **Secrets only in gitignored `.env`:** no real host/user/password/account in any tracked file (Principle IX / C2). Connection configs resolve from `ANALYTICS_DB_*` env vars.
- **Engine selection has ONE authority:** `ANALYTICS_DB_ENGINE` (default `postgres`). No URL-scheme fallback.
- **Governance stop:** the terminal task drafts the Principle III amendment + a ratify ledger and STOPS. The agent never edits `.specify/memory/constitution.md` to ratify, never merges to `main`, never emits a numeric confidence score.
- **Test marker:** every new test module starts with `pytestmark = pytest.mark.unit`.
- **Run tests with:** `python -m pytest tests/unit/<file> -v` (repo uses `pythonpath = ["src", "."]`; `--cov` is on by default via `addopts`).

---

## File Structure

| File | Responsibility | New/Modified |
|---|---|---|
| `src/seshat/dialect.py` | `Dialect` Protocol + `PostgresDialect`, `SqlServerDialect`, `MySqlDialect`, `SnowflakeDialect`; `get_dialect(name)` factory | **Create** |
| `tests/unit/test_dialect.py` | String-assertion tests for every dialect's fragment builders + the 4 silent-failure risks | **Create** |
| `src/seshat/profile.py` | Route SQL through a dialect (was hardcoded PG) | Modify |
| `src/seshat/validate.py` | Route SQL + connect + resolve-config through a dialect | Modify |
| `src/seshat/value_proxy.py` | Route aggregate SQL through a dialect | Modify |
| `src/seshat/cli.py` | `_make_runner`/`_ensure_driver`/`_redact_dsn` become engine-aware | Modify |
| `src/seshat/rules/never_execute.py` | Add `mysql`/`snowflake` to `_FORBIDDEN_ROOTS` | Modify |
| `src/seshat/rules/live_surface_boundary.py` | Add `src/seshat/dialect.py` to `_LIVE_SURFACE` | Modify |
| `src/seshat/rules/git_meta.py` | Extend C2 secret-scan to ODBC/Snowflake/MySQL connection shapes | Modify |
| `pyproject.toml` | Add `mssql`, `mysql`, `snowflake` optional extras | Modify |
| `.env.example` | Add `ANALYTICS_DB_ENGINE` + per-engine keys (empty values) | Modify |
| `docs/superpowers/specs/2026-07-03-multi-engine-db-support-design.md` | Fix the "byte-identical" line to state PG keeps FILTER/row-value | Modify |
| `.specify/memory/` amendment draft + ratify ledger | Governance artifact | **Create (STOP)** |

**Sequencing rationale (advisor-directed):** make the code *dialect-shaped* and prove it green (Tasks 1–5) BEFORE adding any new engine (Tasks 6–8). This isolates extraction bugs (provable against the 897) from new-dialect bugs (unprovable in CI). Guards + packaging (Tasks 9–11) then governance (Task 12).

---

## Task 1: `Dialect` Protocol + `PostgresDialect` (purely additive)

**Files:**
- Create: `src/seshat/dialect.py`
- Test: `tests/unit/test_dialect.py`

**Interfaces:**
- Produces:
  - `class Dialect(Protocol)` with methods:
    - `name: str` (class attribute)
    - `quote_ident(self, name: str, *, context: str = "identifier") -> str`
    - `quote_qualified(self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2) -> str`
    - `count_where(self, predicate: str) -> str` — returns a `COUNT/SUM(...)` fragment for `predicate`
    - `distinct_tuple_count(self, cols: tuple[str, ...], table: str, where: str | None = None) -> str` — full scalar subquery
    - `columns_query(self) -> tuple[str, tuple[str, ...] | None]` — `(sql, param_placeholders_note)`; returns SQL using this dialect's placeholder for `(schema, table)`
    - `is_text_type(self, data_type: str) -> bool`
    - `placeholder(self) -> str`
    - `translate_params(self, sql: str) -> str` — rewrite canonical `%s` SQL into this dialect's paramstyle
  - `def get_dialect(name: str) -> Dialect` — maps `postgres|sqlserver|mysql|snowflake` → instance; raises `ValueError` on unknown.
- Consumes: `retail.identifiers.validate_identifier`, `validate_qualified_identifier` (validation only; quoting is dialect-local).

- [ ] **Step 1: Write the failing test (PostgresDialect emits today's exact SQL)**

```python
# tests/unit/test_dialect.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dialect.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retail.dialect'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/seshat/dialect.py
"""Per-engine SQL dialect seam for the read-only profile + validate surface.

The QueryRunner Protocol answers "how do I execute"; a Dialect answers "how do I
phrase it" -- identifier quoting, param placeholder, and the handful of SQL
fragments the profile/validate/value_proxy modules build. Adding an engine means
adding a Dialect, not editing the check logic.

PostgresDialect emits BYTE-IDENTICAL SQL to the repo's original hardcoded strings
(FILTER, row-value DISTINCT) so the existing suite stays a true regression oracle;
the three new dialects use portable/native forms verified per engine.

DRIVER-FREE: every concrete connect() lazy-imports its driver INSIDE the method,
never at module scope, so importing this module opens nothing (B3 enforces it).
"""

from __future__ import annotations

from typing import Protocol

from .identifiers import validate_identifier, validate_qualified_identifier


class Dialect(Protocol):
    name: str

    def quote_ident(self, name: str, *, context: str = "identifier") -> str: ...
    def quote_qualified(
        self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2
    ) -> str: ...
    def count_where(self, predicate: str) -> str: ...
    def distinct_tuple_count(
        self, cols: tuple[str, ...], table: str, where: str | None = None
    ) -> str: ...
    def is_text_type(self, data_type: str) -> bool: ...
    def placeholder(self) -> str: ...
    def translate_params(self, sql: str) -> str: ...


# Postgres text types (information_schema.data_type), from profile.py today.
_PG_TEXT_TYPES = frozenset(
    {"text", "character varying", "varchar", "character", "char", "name", '"char"'}
)


class PostgresDialect:
    name = "postgres"

    def quote_ident(self, name: str, *, context: str = "identifier") -> str:
        return f'"{validate_identifier(name, context=context)}"'

    def quote_qualified(
        self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2
    ) -> str:
        validated = validate_qualified_identifier(
            name, context=context, min_parts=min_parts, max_parts=max_parts
        )
        return ".".join(f'"{p}"' for p in validated.split("."))

    def count_where(self, predicate: str) -> str:
        return f"count(*) FILTER (WHERE {predicate})"

    def distinct_tuple_count(
        self, cols: tuple[str, ...], table: str, where: str | None = None
    ) -> str:
        # Postgres keeps its native row-value form (byte-identical to today).
        joined = ", ".join(cols)
        return f"count(DISTINCT ({joined}))"

    def is_text_type(self, data_type: str) -> bool:
        return data_type.lower() in _PG_TEXT_TYPES

    def placeholder(self) -> str:
        return "%s"

    def translate_params(self, sql: str) -> str:
        return sql  # canonical style IS %s; no rewrite for Postgres


_DIALECTS: dict[str, type] = {"postgres": PostgresDialect}


def get_dialect(name: str) -> Dialect:
    """Return the Dialect for ``name`` (postgres|sqlserver|mysql|snowflake)."""
    try:
        return _DIALECTS[name]()
    except KeyError:
        raise ValueError(
            f"unknown DB engine {name!r}; expected one of {sorted(_DIALECTS)}"
        ) from None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dialect.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dialect.py tests/unit/test_dialect.py
git commit -m "feat: add Dialect Protocol + PostgresDialect (additive, PG SQL unchanged)"
```

---

## Task 2: PostgresDialect `distinct_tuple_count` full-subquery variant + `columns_query`

**Files:**
- Modify: `src/seshat/dialect.py`
- Test: `tests/unit/test_dialect.py`

**Interfaces:**
- Note: Postgres `distinct_tuple_count` stays the row-value `count(DISTINCT (a, b))` scalar (byte-identical). `columns_query()` returns the exact SELECT `profile.py` uses today (`information_schema.columns … WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position`).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dialect.py::test_postgres_columns_query_is_information_schema -v`
Expected: FAIL with `AttributeError: 'PostgresDialect' object has no attribute 'columns_query'`

- [ ] **Step 3: Write minimal implementation**

Add to `PostgresDialect` (and to the `Dialect` Protocol, adjust `columns_query` return type to `str`):

```python
    def columns_query(self) -> str:
        return (
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position"
        )
```

Update the Protocol signature to `def columns_query(self) -> str: ...` (drop the earlier tuple note — a plain SQL string with `%s` placeholders is simpler and the profiler already passes `(schema, name)` params).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dialect.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dialect.py tests/unit/test_dialect.py
git commit -m "feat: PostgresDialect columns_query + distinct_tuple_count (PG-exact)"
```

---

## Task 3: Refactor `profile.py` to route through a dialect (897 stay green)

**Files:**
- Modify: `src/seshat/profile.py`
- Test: `tests/unit/test_profile.py` (existing — must stay green), `tests/unit/test_dialect.py`

**Interfaces:**
- Consumes: `get_dialect`, `PostgresDialect` from Task 1–2.
- Produces: `profile(runner, table, candidate_pk, *, dialect: Dialect | None = None)` — `dialect` defaults to `get_dialect("postgres")` so all existing callers are unchanged.

**This is the riskiest task — isolate it. The existing `test_profile.py` is the oracle.**

- [ ] **Step 1: Confirm the current oracle is green**

Run: `python -m pytest tests/unit/test_profile.py -v`
Expected: PASS (baseline before touching profile.py)

- [ ] **Step 2: Refactor `profile.py` to build SQL via a dialect, defaulting to Postgres**

Replace the module-level `_TEXT_TYPES` usage and the three hardcoded SQL builders with dialect calls. Key edits:

```python
# profile.py — add import + default dialect
from .dialect import Dialect, get_dialect

# _discover_columns: use dialect.columns_query() (identical PG SQL)
def _discover_columns(
    runner: QueryRunner, table: str, dialect: Dialect
) -> tuple[tuple[str, str], ...]:
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "public", table
    rows = runner.run(dialect.columns_query(), (schema, name))
    return tuple((r[0], (r[1] if len(r) > 1 else "text")) for r in rows)


def profile(
    runner: QueryRunner,
    table: str,
    candidate_pk: tuple[str, ...],
    *,
    dialect: Dialect | None = None,
) -> ProfileResult:
    dialect = dialect or get_dialect("postgres")
    table = _safe_identifier(table)
    columns = _discover_columns(runner, table, dialect)
    row_rows = runner.run(f"SELECT count(*) FROM {table}")
    row_count = row_rows[0][0] if row_rows else 0

    col_profiles: list[ColumnProfile] = []
    for col_name, data_type in columns:
        col = _safe_identifier(col_name)
        if dialect.is_text_type(data_type):
            missing_frag = dialect.count_where(f"trim({col}) = '' OR {col} IS NULL")
            stat = runner.run(
                f"SELECT {missing_frag}, count(DISTINCT trim({col})) FROM {table}"
            )
        else:
            missing_frag = dialect.count_where(f"{col} IS NULL")
            stat = runner.run(
                f"SELECT {missing_frag}, count(DISTINCT {col}) FROM {table}"
            )
        # ... rest unchanged ...
```

For the PK proof, replace the null-predicate FILTER with `dialect.count_where(null_pred)` and keep `count(DISTINCT ({pk_cols}))` as-is for the PG default (it maps to `dialect.distinct_tuple_count` in the new dialects, but PG's is byte-identical so the string is unchanged).

Keep `_safe_identifier` (the injection guard) exactly as-is — it is the mandatory validation boundary.

- [ ] **Step 3: Run the profile oracle + dialect tests**

Run: `python -m pytest tests/unit/test_profile.py tests/unit/test_dialect.py -v`
Expected: PASS (test_profile.py unchanged — proves PG SQL is byte-identical; the `FakeRunner` returns rows by call order, so identical call count/order + identical SQL = green)

- [ ] **Step 4: Run the FULL suite to confirm no regression**

Run: `python -m pytest tests/unit -q --no-cov`
Expected: PASS (897 passed, 1 skipped) — same as baseline

- [ ] **Step 5: Commit**

```bash
git add src/seshat/profile.py
git commit -m "refactor: route profile.py SQL through a dialect (PG default, 897 green)"
```

---

## Task 4: Refactor `validate.py` to route through a dialect

**Files:**
- Modify: `src/seshat/validate.py`
- Test: `tests/unit/test_validate.py`, `tests/unit/test_live_surface_boundary.py` (both must stay green)

**Interfaces:**
- Consumes: `get_dialect`, `Dialect`.
- Produces: each `check_*` gains an optional `dialect: Dialect | None = None` param (defaults to Postgres); `run_live_checks(runner, targets, *, dialect=None)`. `make_psycopg2_runner` stays (it is the PG connect); a new `connect(engine, config)` indirection is added in Task 6/cli.

- [ ] **Step 1: Confirm the oracle is green**

Run: `python -m pytest tests/unit/test_validate.py -v`
Expected: PASS (baseline)

- [ ] **Step 2: Refactor the four checks to build SQL via the dialect**

In `check_pk_uniqueness`, replace the hardcoded `count(DISTINCT ({pk}))` + `count(*) FILTER (WHERE {null_pred})` with `dialect.distinct_tuple_count(...)` (PG-exact) and `dialect.count_where(null_pred)`. Replace `_sql_identifier`/`_sql_table` internals to delegate quoting to `dialect.quote_ident`/`dialect.quote_qualified` while KEEPING the `quote_identifier`/`quote_qualified_identifier` validation call (validation stays; quoting moves). Default `dialect = get_dialect("postgres")` at the top of each check.

The generated PG SQL must be byte-identical: `test_validate.py` asserts substrings like `'FROM "silver"."sales_c086"'` and `'"invoice_no"'` — these survive because `PostgresDialect.quote_qualified` produces `"silver"."sales_c086"` and `count(*) FILTER (WHERE ...)` is unchanged.

- [ ] **Step 3: Run validate oracle + boundary guard**

Run: `python -m pytest tests/unit/test_validate.py tests/unit/test_live_surface_boundary.py -v`
Expected: PASS

- [ ] **Step 4: Run FULL suite**

Run: `python -m pytest tests/unit -q --no-cov`
Expected: PASS (897 passed, 1 skipped)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/validate.py
git commit -m "refactor: route validate.py checks through a dialect (PG default, green)"
```

---

## Task 5: Refactor `value_proxy.py` to route through a dialect

**Files:**
- Modify: `src/seshat/value_proxy.py`
- Test: `tests/unit/test_value_proxy.py`

**Interfaces:**
- Consumes: `Dialect`, `get_dialect`.
- Produces: `_aggregate_sql(expected, dialect)`, `check_expected_value(runner, name, expected, *, dialect=None)` (default Postgres).

- [ ] **Step 1: Confirm oracle green**

Run: `python -m pytest tests/unit/test_value_proxy.py -v`
Expected: PASS (baseline)

- [ ] **Step 2: Refactor `_aggregate_sql` and the count helper to use the dialect**

Replace `quote_qualified_identifier`/`quote_identifier` calls with `dialect.quote_qualified`/`dialect.quote_ident` (validation preserved inside them). The `_AGG_SQL` template `"distinct_count": "count(DISTINCT {col})"` stays for PG. Thread `dialect` through `_check_single`/`_check_ratio`/`_count`.

- [ ] **Step 3: Run oracle**

Run: `python -m pytest tests/unit/test_value_proxy.py -v`
Expected: PASS

- [ ] **Step 4: Run FULL suite**

Run: `python -m pytest tests/unit -q --no-cov`
Expected: PASS (897 passed, 1 skipped)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/value_proxy.py
git commit -m "refactor: route value_proxy.py aggregate SQL through a dialect (green)"
```

---

## Task 6: `SqlServerDialect` (T-SQL, pyodbc) — the fragments

**Files:**
- Modify: `src/seshat/dialect.py`
- Test: `tests/unit/test_dialect.py`

**Interfaces:**
- Produces: `SqlServerDialect` registered under `"sqlserver"` in `_DIALECTS`.

- [ ] **Step 1: Write the failing tests (recon-verified T-SQL forms)**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/test_dialect.py -k sqlserver -v`
Expected: FAIL (`ValueError: unknown DB engine 'sqlserver'`)

- [ ] **Step 3: Implement `SqlServerDialect`**

```python
_MSSQL_TEXT_TYPES = frozenset(
    {"varchar", "nvarchar", "char", "nchar", "text", "ntext"}
)


class SqlServerDialect:
    name = "sqlserver"

    def quote_ident(self, name: str, *, context: str = "identifier") -> str:
        v = validate_identifier(name, context=context)
        return f"[{v}]"

    def quote_qualified(
        self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2
    ) -> str:
        validated = validate_qualified_identifier(
            name, context=context, min_parts=min_parts, max_parts=max_parts
        )
        return ".".join(f"[{p}]" for p in validated.split("."))

    def count_where(self, predicate: str) -> str:
        return f"COUNT(CASE WHEN {predicate} THEN 1 END)"

    def distinct_tuple_count(
        self, cols: tuple[str, ...], table: str, where: str | None = None
    ) -> str:
        joined = ", ".join(cols)
        w = f" WHERE {where}" if where else ""
        return f"(SELECT COUNT(*) FROM (SELECT DISTINCT {joined} FROM {table}{w}) AS sub)"

    def is_text_type(self, data_type: str) -> bool:
        return data_type.lower() in _MSSQL_TEXT_TYPES

    def placeholder(self) -> str:
        return "?"

    def translate_params(self, sql: str) -> str:
        return sql.replace("%s", "?")

    def columns_query(self) -> str:
        # INFORMATION_SCHEMA columns are UPPERCASE-labelled; alias to lowercase so
        # callers read r[0]/r[1] identically across engines. Uses ? placeholders.
        return (
            "SELECT COLUMN_NAME AS column_name, DATA_TYPE AS data_type "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION"
        )
```

Register: `_DIALECTS["sqlserver"] = SqlServerDialect`.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/unit/test_dialect.py -k sqlserver -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dialect.py tests/unit/test_dialect.py
git commit -m "feat: SqlServerDialect T-SQL fragments (COUNT(CASE), brackets, qmark)"
```

---

## Task 7: `MySqlDialect` — the fragments

**Files:**
- Modify: `src/seshat/dialect.py`
- Test: `tests/unit/test_dialect.py`

**Interfaces:**
- Produces: `MySqlDialect` under `"mysql"`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/test_dialect.py -k mysql -v`
Expected: FAIL (`ValueError: unknown DB engine 'mysql'`)

- [ ] **Step 3: Implement `MySqlDialect`**

```python
_MYSQL_TEXT_TYPES = frozenset(
    {"char", "varchar", "tinytext", "text", "mediumtext", "longtext"}
)


class MySqlDialect:
    name = "mysql"

    def quote_ident(self, name: str, *, context: str = "identifier") -> str:
        return f"`{validate_identifier(name, context=context)}`"

    def quote_qualified(
        self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2
    ) -> str:
        validated = validate_qualified_identifier(
            name, context=context, min_parts=min_parts, max_parts=max_parts
        )
        return ".".join(f"`{p}`" for p in validated.split("."))

    def count_where(self, predicate: str) -> str:
        return f"COUNT(CASE WHEN {predicate} THEN 1 END)"

    def distinct_tuple_count(
        self, cols: tuple[str, ...], table: str, where: str | None = None
    ) -> str:
        joined = ", ".join(cols)
        w = f" WHERE {where}" if where else ""
        return f"(SELECT COUNT(*) FROM (SELECT DISTINCT {joined} FROM {table}{w}) AS sub)"

    def is_text_type(self, data_type: str) -> bool:
        return data_type.lower() in _MYSQL_TEXT_TYPES

    def placeholder(self) -> str:
        return "%s"

    def translate_params(self, sql: str) -> str:
        return sql  # pyformat, same as canonical

    def columns_query(self) -> str:
        return (
            "SELECT COLUMN_NAME AS column_name, DATA_TYPE AS data_type "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION"
        )
```

Register: `_DIALECTS["mysql"] = MySqlDialect`.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/unit/test_dialect.py -k mysql -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dialect.py tests/unit/test_dialect.py
git commit -m "feat: MySqlDialect fragments (COUNT(CASE), backticks, pyformat)"
```

---

## Task 8: `SnowflakeDialect` — the fragments + folding rule (R1)

**Files:**
- Modify: `src/seshat/dialect.py`
- Test: `tests/unit/test_dialect.py`

**Interfaces:**
- Produces: `SnowflakeDialect` under `"snowflake"`. Its `quote_ident`/`quote_qualified` UPPERCASE the identifier before quoting (Snowflake stores unquoted names uppercase; `"my_table"` would silently match nothing — R1). `columns_query` filters on UPPERCASE literals and the profiler passes uppercased `(schema, table)`.

- [ ] **Step 1: Write the failing tests (folding is the R1 silent-failure guard)**

```python
def test_snowflake_quote_ident_uppercases() -> None:
    # R1: Snowflake folds unquoted names to UPPERCASE; quoting must match stored case
    # or the query silently matches nothing.
    assert get_dialect("snowflake").quote_ident("my_table") == '"MY_TABLE"'


def test_snowflake_quote_qualified_uppercases_each_part() -> None:
    assert get_dialect("snowflake").quote_qualified(
        "bronze.my_table", context="t"
    ) == '"BRONZE"."MY_TABLE"'


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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/test_dialect.py -k snowflake -v`
Expected: FAIL (`ValueError: unknown DB engine 'snowflake'`)

- [ ] **Step 3: Implement `SnowflakeDialect`**

```python
class SnowflakeDialect:
    name = "snowflake"

    def quote_ident(self, name: str, *, context: str = "identifier") -> str:
        # Validate the RAW name, then fold to Snowflake's stored (upper) case (R1).
        v = validate_identifier(name, context=context)
        return f'"{v.upper()}"'

    def quote_qualified(
        self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2
    ) -> str:
        validated = validate_qualified_identifier(
            name, context=context, min_parts=min_parts, max_parts=max_parts
        )
        return ".".join(f'"{p.upper()}"' for p in validated.split("."))

    def count_where(self, predicate: str) -> str:
        return f"COUNT(CASE WHEN {predicate} THEN 1 END)"

    def distinct_tuple_count(
        self, cols: tuple[str, ...], table: str, where: str | None = None
    ) -> str:
        joined = ", ".join(cols)
        w = f" WHERE {where}" if where else ""
        return f"(SELECT COUNT(*) FROM (SELECT DISTINCT {joined} FROM {table}{w}) AS sub)"

    def is_text_type(self, data_type: str) -> bool:
        # Snowflake collapses VARCHAR/STRING/CHAR/... to DATA_TYPE = 'TEXT'.
        return data_type.upper() == "TEXT"

    def placeholder(self) -> str:
        return "%s"  # default pyformat

    def translate_params(self, sql: str) -> str:
        return sql

    def columns_query(self) -> str:
        # UPPER()-fold catalog names so a caller's uppercased literal matches; the
        # profiler must uppercase the (schema, table) params for Snowflake (R1).
        return (
            "SELECT COLUMN_NAME AS column_name, DATA_TYPE AS data_type "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE UPPER(TABLE_SCHEMA) = %s AND UPPER(TABLE_NAME) = %s "
            "ORDER BY ORDINAL_POSITION"
        )
```

Register: `_DIALECTS["snowflake"] = SnowflakeDialect`.

Also: in `profile.py._discover_columns`, when `dialect.name == "snowflake"`, uppercase the `(schema, name)` params passed to `columns_query`. Add a small `dialect.normalize_catalog_literal(s: str) -> str` hook (returns `s.upper()` for Snowflake, `s` otherwise) so the profiler stays dialect-agnostic.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/unit/test_dialect.py -k snowflake -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dialect.py tests/unit/test_dialect.py src/seshat/profile.py
git commit -m "feat: SnowflakeDialect + R1 folding normalization (uppercase idents)"
```

---

## Task 9: The four silent-failure regression tests (R1–R4)

**Files:**
- Test: `tests/unit/test_dialect.py`

**Interfaces:** consumes all four dialects.

- [ ] **Step 1: Write the R2/R3 tests (R1 covered in Task 8; R4 in Task 11)**

```python
import pytest


@pytest.mark.parametrize("engine", ["postgres", "sqlserver", "mysql", "snowflake"])
def test_count_where_predicate_is_embedded_verbatim(engine) -> None:
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
```

- [ ] **Step 2: Run to verify (should PASS — the dialects already implement these)**

Run: `python -m pytest tests/unit/test_dialect.py -v`
Expected: PASS (all dialect tests)

- [ ] **Step 3: (no impl needed — these lock in existing behavior)**

- [ ] **Step 4: Run FULL suite**

Run: `python -m pytest tests/unit -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_dialect.py
git commit -m "test: lock in R1-R3 silent-failure regressions across all four dialects"
```

---

## Task 10: Extend B1/B3 guards for the new drivers + `dialect.py`

**Files:**
- Modify: `src/seshat/rules/never_execute.py`, `src/seshat/rules/live_surface_boundary.py`
- Test: `tests/unit/test_never_execute.py`, `tests/unit/test_live_surface_boundary.py`

**Interfaces:** none exported; these are governance-rule edits.

- [ ] **Step 1: Write the failing tests**

```python
# test_never_execute.py — add:
def test_snowflake_and_mysql_connector_are_forbidden_roots() -> None:
    from retail.rules.never_execute import _FORBIDDEN_ROOTS
    assert "snowflake" in _FORBIDDEN_ROOTS
    assert "mysql" in _FORBIDDEN_ROOTS


# test_live_surface_boundary.py — add:
def test_dialect_module_is_a_live_surface() -> None:
    from retail.rules.live_surface_boundary import _LIVE_SURFACE
    assert "src/seshat/dialect.py" in _LIVE_SURFACE
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/test_never_execute.py::test_snowflake_and_mysql_connector_are_forbidden_roots tests/unit/test_live_surface_boundary.py::test_dialect_module_is_a_live_surface -v`
Expected: FAIL (`AssertionError`)

- [ ] **Step 3: Add the roots + the live-surface member**

In `never_execute.py`, add to `_FORBIDDEN_ROOTS`: `"mysql"` (covers `mysql.connector`), `"snowflake"` (covers `snowflake.connector`). (`pyodbc`, `pymysql` already present.)

In `live_surface_boundary.py`, add `"src/seshat/dialect.py"` to `_LIVE_SURFACE`.

- [ ] **Step 4: Run to verify pass + the disjointness wiring test**

Run: `python -m pytest tests/unit/test_never_execute.py tests/unit/test_live_surface_boundary.py -v`
Expected: PASS (including `test_live_surface_set_is_disjoint_from_b1_governed`)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/rules/never_execute.py src/seshat/rules/live_surface_boundary.py tests/unit/test_never_execute.py tests/unit/test_live_surface_boundary.py
git commit -m "feat: B1/B3 guard the new drivers (mysql/snowflake) + dialect.py live-surface"
```

---

## Task 11: Engine-aware connect, config resolution, redaction (R4) + C2 extension + packaging

**Files:**
- Modify: `src/seshat/dialect.py` (add per-engine `connect`, `resolve_config`, `redact`), `src/seshat/cli.py` (engine-aware `_make_runner`/`_ensure_driver`/`_redact_dsn`), `src/seshat/rules/git_meta.py` (C2), `pyproject.toml`, `.env.example`
- Test: `tests/unit/test_dialect.py`, `tests/unit/test_git_meta.py`, `tests/unit/test_cli_context.py`

**Interfaces:**
- Produces: `Dialect.connect(config) -> QueryRunner` (lazy driver import inside), `Dialect.resolve_config(env) -> dict | str`, `Dialect.redact(message, config) -> str`; `cli` reads `ANALYTICS_DB_ENGINE` to pick the dialect.

- [ ] **Step 1: Write the failing redaction + C2 tests**

```python
# test_dialect.py — R4 redaction (no live driver needed)
def test_sqlserver_redact_scrubs_pwd() -> None:
    d = get_dialect("sqlserver")
    cfg = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=h;UID=u;PWD=topsecret"
    out = d.redact("login failed for PWD=topsecret at SERVER=h", cfg)
    assert "topsecret" not in out
    assert "h" not in out.split("SERVER=")[-1] if "SERVER=" in out else True


def test_snowflake_redact_scrubs_password_and_account() -> None:
    d = get_dialect("snowflake")
    cfg = {"account": "acme-prod", "user": "u", "password": "hunter2"}
    out = d.redact("auth error for acme-prod user u pw hunter2", cfg)
    assert "hunter2" not in out
    assert "acme-prod" not in out
```

```python
# test_git_meta.py — C2 must now catch an ODBC keyword string with a password
def test_c2_flags_odbc_password_string(tmp_path) -> None:
    from retail.rules.git_meta import _scan_line_for_secret  # helper added in Task 11
    hit = _scan_line_for_secret("DRIVER={ODBC Driver 18 for SQL Server};PWD=realpw;")
    assert hit is True


def test_c2_ignores_placeholder_odbc(tmp_path) -> None:
    from retail.rules.git_meta import _scan_line_for_secret
    assert _scan_line_for_secret("DRIVER={...};PWD=<your-password>;") is False
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/test_dialect.py -k redact tests/unit/test_git_meta.py -k odbc -v`
Expected: FAIL

- [ ] **Step 3: Implement connect/resolve_config/redact + C2 patterns + packaging**

Per dialect, add (drivers imported LAZILY inside `connect`):

```python
# PostgresDialect (unchanged behavior — delegates to existing make_psycopg2_runner)
    def resolve_config(self, env):
        from .validate import resolve_dsn
        return resolve_dsn(env)  # a DSN string

    def connect(self, config):
        from .validate import make_psycopg2_runner
        return make_psycopg2_runner(config)

    def redact(self, message, config):
        from .cli import _redact_dsn
        return _redact_dsn(message, config)
```

```python
# SqlServerDialect
    def resolve_config(self, env):
        driver = env.get("ANALYTICS_DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
        host = env.get("ANALYTICS_DB_HOST")
        if not host:
            return None
        port = env.get("ANALYTICS_DB_PORT", "1433")
        parts = [f"DRIVER={{{driver}}}", f"SERVER={host},{port}"]
        if env.get("ANALYTICS_DB_NAME"):
            parts.append(f"DATABASE={env['ANALYTICS_DB_NAME']}")
        if env.get("ANALYTICS_DB_USER"):
            parts.append(f"UID={env['ANALYTICS_DB_USER']}")
        if env.get("ANALYTICS_DB_PASSWORD"):
            parts.append(f"PWD={env['ANALYTICS_DB_PASSWORD']}")
        parts.append("Encrypt=yes")
        if env.get("ANALYTICS_DB_TRUST_CERT", "").lower() in ("1", "true", "yes"):
            parts.append("TrustServerCertificate=yes")
        return ";".join(parts)

    def connect(self, config):
        import pyodbc  # lazy
        conn = pyodbc.connect(config, autocommit=True)  # read-only posture: SELECT-only user

        class _Runner:
            def run(self, sql, params=()):
                cur = conn.cursor()
                cur.execute(sql, params)
                return list(cur.fetchall())
        return _Runner()

    def redact(self, message, config):
        text = str(message)
        for kw in ("PWD", "UID", "SERVER", "DATABASE"):
            # scrub the value after KW= up to the next ;
            import re
            text = re.sub(rf"({kw}=)[^;]*", r"\1<redacted>", text)
        # also scrub each raw value in case the driver reformatted the error
        for token in config.split(";"):
            if "=" in token:
                _, val = token.split("=", 1)
                if val and val not in ("yes", "no"):
                    text = text.replace(val, "<redacted>")
        return text
```

MySQL/Snowflake `resolve_config` return a **dict** of `connect()` kwargs (host/port/user/password/db for MySQL; account/user/password/warehouse/role/database/schema for Snowflake), `connect` lazy-imports `mysql.connector` / `snowflake.connector` with `autocommit=True`, and `redact` scrubs each secret value (`password`, `token`, `account`, `host`, `user`) from the message.

In `cli.py`: `_run_validate`/the profile handler read `engine = os.environ.get("ANALYTICS_DB_ENGINE", "postgres")`, `dialect = get_dialect(engine)`, `config = dialect.resolve_config(env)`, `runner = dialect.connect(config)`, and on error `print(dialect.redact(exc, config))`. Keep `_ensure_driver` generalized to try the engine's driver import. **Preserve the existing Postgres path exactly** (engine unset → postgres → identical behavior).

In `git_meta.py`: factor the line scan into `_scan_line_for_secret(line: str) -> bool` and add patterns: `PWD=` / `UID=` in an ODBC-shaped string (with a non-placeholder value), a `mysql://…@` URI (extend `CONN_URI_RE` or add `MYSQL_URI_RE`), and a Snowflake account+password kwargs shape. Reuse the existing `<...>`-placeholder exemption (a value wrapped in `<…>` is a documented placeholder, not a secret). Keep `docs/superpowers/` excluded (that is why the design doc's `PWD=secret` example is allowed).

In `pyproject.toml`, add:

```toml
mssql     = ["pyodbc>=5.0"]
mysql     = ["mysql-connector-python>=9.0"]
snowflake = ["snowflake-connector-python>=3.0"]
```

In `.env.example`, add (empty values): `ANALYTICS_DB_ENGINE=`, `ANALYTICS_DB_ACCOUNT=`, `ANALYTICS_DB_ODBC_DRIVER=`, `ANALYTICS_DB_TRUST_CERT=`, `ANALYTICS_DB_WAREHOUSE=`, `ANALYTICS_DB_ROLE=`. **Note:** if C2 requires `.env.example` to be empty for `REQUIRED_ENV_KEYS`, confirm any new key added there is empty-valued.

- [ ] **Step 4: Run the redaction + C2 tests + FULL suite**

Run: `python -m pytest tests/unit/test_dialect.py tests/unit/test_git_meta.py tests/unit/test_cli_context.py -v`
Then: `python -m pytest tests/unit -q --no-cov`
Expected: PASS (897 + new tests; the Postgres path unchanged)

- [ ] **Step 5: Run the static gate end-to-end**

Run: `python -m seshat.cli check` (or `retail check`)
Expected: exit 0, rule count unchanged (no new rule added; B1/B3/C2 edits are within existing rules)

- [ ] **Step 6: Commit**

```bash
git add src/seshat/dialect.py src/seshat/cli.py src/seshat/rules/git_meta.py pyproject.toml .env.example tests/unit/
git commit -m "feat: engine-aware connect/config/redaction (R4), C2 multi-shape scan, extras"
```

---

## Task 12: Governance — draft the Principle III amendment + ratify ledger, then STOP

**Files:**
- Modify: `docs/superpowers/specs/2026-07-03-multi-engine-db-support-design.md` (fix the "byte-identical" line)
- Create: a ratify-ledger note (e.g. `docs/superpowers/specs/2026-07-03-multi-engine-ratify-ledger.md`) + a proposed `speckit-constitution` amendment DRAFT (NOT applied to `.specify/memory/constitution.md`)

**Interfaces:** none — this is the human handoff.

- [ ] **Step 1: Fix the spec's byte-identical line**

In the design spec, change the "PostgresDialect extracted verbatim" wording to: *"PostgresDialect emits byte-identical SQL to today's strings — it KEEPS the native `FILTER` and row-value `DISTINCT` forms (it is NOT rewritten to the portable forms); only the three new dialects use the portable/native forms."* (Aligns spec with the implemented decision.)

- [ ] **Step 2: Write the ratify ledger**

Create the ledger naming: the decision (widen Principle III to allow the read-only seam on 3 more engines), the exact proposed amended Principle III text (from the design spec §9), the required human owner, the evidence (all tests green, `retail check` exit 0, driver-free guards extended, C2 now multi-shape), and the explicit note that **changing what C2 catches is governance-adjacent** and is part of what is being ratified.

- [ ] **Step 3: Verify the full suite + gate one final time**

Run: `python -m pytest tests/unit -q --no-cov && python -m seshat.cli check`
Expected: all tests pass; `retail check` exit 0.

- [ ] **Step 4: Commit the governance artifacts**

```bash
git add docs/superpowers/specs/
git commit -m "docs: multi-engine ratify ledger + Principle III amendment draft (STOP)"
```

- [ ] **Step 5: STOP — open a PR, do not merge**

Push the branch and open a PR describing the change and the pending ratification. **Do NOT** edit `.specify/memory/constitution.md`, mark any readiness stage `pass`, or merge to `main`. Present the ratify ledger to the user/named owner. The Principle-V ratification is theirs alone.

---

## Self-Review

**1. Spec coverage:**
- §2 Dialect seam → Tasks 1–2, 6–8. ✅
- §3 recon-verified fragments (COUNT(CASE), derived-table distinct, per-engine quote/param, is_text_type) → Tasks 6–8. ✅
- §4 R1 folding → Task 8; R2 param translation → Tasks 6/9; R3 empty-input count → Tasks 6–9 (COUNT(CASE) form); R4 redaction + C2 → Task 11. ✅
- §5 one engine authority (`ANALYTICS_DB_ENGINE`) → Task 11. ✅
- §6 data flow → Task 11. ✅
- §7 optional extras → Task 11. ✅
- §8 backward-compat (897 green) → Tasks 3–5 gates; driver-free guard → Task 10. ✅
- §9 governance stop → Task 12. ✅

**2. Placeholder scan:** No TBD/TODO. Every code step shows code; every run step shows the command + expected output. ✅

**3. Type consistency:** `Dialect` method names are identical across Protocol + all four concrete classes (`quote_ident`, `quote_qualified`, `count_where`, `distinct_tuple_count`, `is_text_type`, `placeholder`, `translate_params`, `columns_query`, and the Task-11 additions `resolve_config`/`connect`/`redact`, plus the Task-8 `normalize_catalog_literal`). `get_dialect(name)` factory used consistently. `profile`/`check_*`/`check_expected_value` all gain `*, dialect: Dialect | None = None` defaulting to Postgres. ✅

**Note added during review:** `columns_query` was defined in Task 2 (Postgres) and each new dialect (Tasks 6–8) must also implement it — added to those tasks' code. `normalize_catalog_literal` (Task 8) must exist on ALL dialects (identity for non-Snowflake) — implementers add a default to the Protocol/base; a one-line `return s` on the other three.
