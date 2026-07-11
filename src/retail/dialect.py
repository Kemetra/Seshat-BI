"""Per-engine SQL dialect seam for the read-only profile + validate surface.

The QueryRunner Protocol answers "how do I execute"; a Dialect answers "how do I
phrase it" -- identifier quoting, param placeholder, and the handful of SQL
fragments the profile/validate/value_proxy modules build. Adding an engine means
adding a Dialect, not editing the check logic.

PostgresDialect emits BYTE-IDENTICAL SQL to the repo's original hardcoded strings
(FILTER, row-value DISTINCT) so the existing suite stays a true regression oracle;
the other dialects use portable/native forms verified per engine.

DRIVER-FREE: every concrete connect() lazy-imports its driver INSIDE the method,
never at module scope, so importing this module opens nothing (B3 enforces it).
"""

from __future__ import annotations

import re
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
    def columns_query(self) -> str: ...
    def normalize_catalog_literal(self, value: str) -> str: ...

    # R4 -- resolve_config/connect/redact. The config shape differs by engine
    # (a DSN/ODBC keyword string for Postgres/SQL-Server, a kwargs dict for
    # MySQL/Snowflake), hence the union return/param types. This is a
    # documentation-level Protocol declaration -- it records the seam's
    # contract explicitly (previously undeclared on Protocol, so a caller
    # holding a `Dialect`-typed value had no static signature for these three
    # methods at all) rather than a hardened type-checker gate: no mypy/
    # pyright is configured in this repo, and even under one, the concrete
    # classes accept a narrower/single param type than this Protocol's union,
    # which a strict checker would flag as its own (separate, pre-existing-
    # pattern) contravariance note rather than something this change resolves.
    def resolve_config(self, env: dict[str, str]) -> str | dict[str, object] | None: ...
    def connect(self, config: str | dict[str, object]) -> object: ...
    def redact(self, message: object, config: str | dict[str, object]) -> str: ...


# Postgres text types (information_schema.data_type), from profile.py today.
_PG_TEXT_TYPES = frozenset(
    {"text", "character varying", "varchar", "character", "char", "name", '"char"'}
)


class PostgresDialect:
    name = "postgres"

    def resolve_config(self, env: dict[str, str]) -> str | None:
        """Resolve a Postgres DSN from env. Delegates to the existing resolver
        UNCHANGED so the Postgres path stays byte-identical to today."""
        from .validate import resolve_dsn

        return resolve_dsn(env)

    def connect(self, config: str) -> object:
        """Build a real (lazy psycopg2) QueryRunner over a DSN."""
        from .validate import make_psycopg2_runner

        return make_psycopg2_runner(config)

    def redact(self, message: object, config: str) -> str:
        """Scrub the DSN and its components out of an error message."""
        from .cli import _redact_dsn

        return _redact_dsn(message, config)

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

    def columns_query(self) -> str:
        return (
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position"
        )

    def normalize_catalog_literal(self, value: str) -> str:
        return value


class _CursorRunner:
    """Shared QueryRunner over a DB-API connection: cursor-per-call, no
    transaction management beyond what the caller's connect() already set
    (autocommit). Module scope is safe here -- this class touches no driver,
    it only wraps whatever connection object a dialect's lazy connect already
    produced (B1/B3: importing this module still opens nothing)."""

    def __init__(self, conn: object) -> None:
        self._conn = conn

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return list(cur.fetchall())


class _LazyDriverDialect:
    """Template-method base for the three "kwargs/DSN + lazy driver" dialects
    (SqlServer, MySQL, Snowflake). ``connect()`` is identical in shape across
    all three -- open a connection, wrap it in a cursor-per-call runner -- so
    it lives here once; each subclass supplies only its driver-specific
    ``_raw_connect`` (the lazy import + the actual ``.connect(...)`` call,
    which differs in call convention: positional config for pyodbc, **kwargs
    for mysql.connector/snowflake.connector)."""

    def _raw_connect(self, config: object) -> object:
        raise NotImplementedError

    def connect(self, config: object) -> object:
        conn = self._raw_connect(config)
        return _CursorRunner(conn)

    def count_where(self, predicate: str) -> str:
        return f"COUNT(CASE WHEN {predicate} THEN 1 END)"

    def distinct_tuple_count(
        self, cols: tuple[str, ...], table: str, where: str | None = None
    ) -> str:
        joined = ", ".join(cols)
        w = f" WHERE {where}" if where else ""
        return (
            f"(SELECT COUNT(*) FROM (SELECT DISTINCT {joined} FROM {table}{w}) AS sub)"
        )


class _DictConfigDialect(_LazyDriverDialect):
    """Shared ``resolve_config()``/``redact()`` for dialects whose resolved
    config is a flat kwargs dict (MySQL, Snowflake), both driven by per-engine
    CLASS DATA -- a subclass adds an engine by declaring data, not by copying
    a near-identical method body:

    - ``_anchor``: required (env_key, config_key); when its env var is absent,
      resolve_config returns None instead of a half-built dict, so the
      caller's "no connection configured" error path is reused verbatim.
    - ``_optional``: ordered (env_key, config_key) copies, taken only when the
      env var is truthy; the order fixes each engine's dict order.
    - ``_int_keys``: env keys whose value is int()-coerced (e.g. PORT).
    - ``_secret_keys``: dict keys whose values ``redact`` scrubs from error
      text. No longest-first ordering is needed here: unlike SqlServer's DSN
      string there is no token parsing -- each dict value is looked up and
      replaced independently, in the subclass-declared key order."""

    _secret_keys: tuple[str, ...] = ()
    _anchor: tuple[str, str] = ("", "")
    _optional: tuple[tuple[str, str], ...] = ()
    _int_keys: frozenset[str] = frozenset()

    # Build the connector kwargs dict from ANALYTICS_DB_* env vars per this
    # engine's class data (see the class docstring).
    def resolve_config(self, env: dict[str, str]) -> dict[str, object] | None:
        anchor_env, anchor_key = self._anchor
        anchor_val = env.get(anchor_env)
        if not anchor_val:
            return None
        config: dict[str, object] = {anchor_key: anchor_val}
        for env_key, config_key in self._optional:
            value = env.get(env_key)
            if value:
                config[config_key] = int(value) if env_key in self._int_keys else value
        return config

    def redact(self, message: object, config: dict[str, object]) -> str:
        text = str(message)
        for key in self._secret_keys:
            value = (config or {}).get(key)
            if value:
                text = text.replace(str(value), "<redacted>")
        return text


_MSSQL_TEXT_TYPES = frozenset({"varchar", "nvarchar", "char", "nchar", "text", "ntext"})


class SqlServerDialect(_LazyDriverDialect):
    name = "sqlserver"

    # Build an ODBC connection keyword string from ANALYTICS_DB_* env vars.
    #
    # Returns None (no host configured) rather than a half-built string, so
    # the caller's "no connection configured" error path is reused verbatim.
    #
    # UID/PWD values are brace-wrapped (ODBC's documented escaping form,
    # `KEYWORD={value}`) so an embedded `;` stays unambiguous to both the
    # driver and `redact()`, and a literal `}` inside a value is DOUBLED
    # (`}}`) per full ODBC brace-escaping -- without these, such a password
    # would both build a malformed connection string pyodbc's ODBC parser
    # cannot round-trip AND fail to scrub fully from error text.
    # `_parse_tokens` / `_scan_braced_value` parse these exact rules back (R4).
    def resolve_config(self, env: dict[str, str]) -> str | None:
        driver = env.get("ANALYTICS_DB_ODBC_DRIVER") or "ODBC Driver 18 for SQL Server"
        host = env.get("ANALYTICS_DB_HOST")
        if not host:
            return None
        port = env.get("ANALYTICS_DB_PORT", "1433")
        parts = [f"DRIVER={{{driver}}}", f"SERVER={host},{port}"]
        if env.get("ANALYTICS_DB_NAME"):
            parts.append(f"DATABASE={env['ANALYTICS_DB_NAME']}")
        if env.get("ANALYTICS_DB_USER"):
            parts.append("UID={" + env["ANALYTICS_DB_USER"].replace("}", "}}") + "}")
        if env.get("ANALYTICS_DB_PASSWORD"):
            parts.append(
                "PWD={" + env["ANALYTICS_DB_PASSWORD"].replace("}", "}}") + "}"
            )
        parts.append("Encrypt=yes")
        if env.get("ANALYTICS_DB_TRUST_CERT", "").lower() in ("1", "true", "yes"):
            parts.append("TrustServerCertificate=yes")
        return ";".join(parts)

    def _raw_connect(self, config: str) -> object:
        """Connect via pyodbc (lazy import). Read-only posture: use a
        SELECT-only DB user; autocommit avoids holding an open transaction."""
        import pyodbc  # lazy: only on a real live run

        return pyodbc.connect(config, autocommit=True)

    # Scrub PWD/UID/SERVER/DATABASE values from an error message.
    #
    # Two passes, mirroring `_redact_dsn`'s component-level scrub for
    # psycopg2, and ORDER MATTERS -- the authoritative pass runs first:
    #
    # 1. `_scrub_component_values`: re-derive each secret VALUE from the
    #    config (via `_parse_tokens`, so a brace-wrapped value with an
    #    embedded `;` is never truncated the way a naive `split(";")` would
    #    be) and replace it verbatim wherever it appears. This is what
    #    catches the driver reformatting the error into its own text, e.g.
    #    FreeTDS "TCP Provider: host 'X' not found" -- no "SERVER=" and no
    #    port anywhere in the message.
    # 2. `_scrub_kw_value_backstop`: a best-effort `KW=value` regex pass,
    #    defence-in-depth only.
    #
    # Regex-first would leak: a password itself containing a literal
    # `KEYWORD=` (e.g. `secret;DATABASE=x`) would get rewritten mid-value by
    # the regex, so the later verbatim whole-value replace would no longer
    # match and the password prefix (`secret`) would survive. Running the
    # exact-value replace first scrubs the whole credential intact.
    def redact(self, message: object, config: str) -> str:
        text = str(message)
        text = self._scrub_component_values(text, config or "")
        text = self._scrub_kw_value_backstop(text)
        return text

    # Non-secret boolean flags; see _token_secret_values for the yes/no skip.
    _BOOLEAN_KEYWORDS = ("ENCRYPT", "TRUSTSERVERCERTIFICATE")

    # The secret value(s) a single (KEYWORD, value) token contributes to the
    # scrub set -- empty when the token carries no secret.
    #
    # A `SERVER=host,port` token contributes BOTH the full value and the bare
    # host, since the driver may print the host alone with no port and no
    # prefix. A `_BOOLEAN_KEYWORDS` flag equal to "yes"/"no" contributes
    # nothing (avoids over-redacting non-secret flags); that skip is scoped
    # to those keywords ONLY, never to the value text -- a credential that
    # happens to literally equal "yes"/"no" is still a credential and must be
    # scrubbed (security over cosmetic over-redaction).
    @classmethod
    def _token_secret_values(cls, kw: str, val: str) -> tuple[str, ...]:
        if not val:
            return ()
        if kw in cls._BOOLEAN_KEYWORDS and val.lower() in ("yes", "no"):
            return ()
        if kw == "SERVER":
            host = val.rsplit(",", 1)[0]
            return (val, host) if host else (val,)
        return (val,)

    # Pass 1 of `redact`: replace every parsed secret value verbatim,
    # longest-first so a short value (e.g. a username that is a substring of
    # the host) cannot pre-empt a longer overlapping match, matching
    # `_redact_dsn`'s discipline.
    @classmethod
    def _scrub_component_values(cls, text: str, config: str) -> str:
        secrets: set[str] = set()
        for kw, val in cls._parse_tokens(config):
            secrets.update(cls._token_secret_values(kw, val))

        for secret in sorted(secrets, key=len, reverse=True):
            text = text.replace(secret, "<redacted>")
        return text

    # Pass 2 of `redact`: KW=value regex on the message, covering brace and
    # bare forms (stops at a following `;` OR `}`).
    @staticmethod
    def _scrub_kw_value_backstop(text: str) -> str:
        for kw in ("PWD", "UID"):
            # Brace form first (value may legitimately contain ';'), then bare.
            text = re.sub(rf"({kw}=)\{{[^}}]*\}}", r"\1<redacted>", text)
            text = re.sub(rf"({kw}=)[^;]*", r"\1<redacted>", text)
        for kw in ("SERVER", "DATABASE"):
            text = re.sub(rf"({kw}=)[^;]*", r"\1<redacted>", text)
        return text

    # Scan a brace-quoted value starting just AFTER its opening `{`; return
    # the unescaped value (`}}` -> `}`) and the index just past the
    # terminating single `}`. ODBC brace-quoting is NON-NESTABLE: an interior
    # `{` is a plain literal, a doubled `}}` is a literal `}`, and the first
    # `}` not followed by another terminates.
    @staticmethod
    def _scan_braced_value(config: str, start: int) -> tuple[str, int]:
        n = len(config)
        chars: list[str] = []
        j = start
        while j < n:
            if config[j] != "}":
                chars.append(config[j])
                j += 1
                continue
            if j + 1 < n and config[j + 1] == "}":
                chars.append("}")
                j += 2
                continue
            j += 1  # consume the terminating brace
            break
        return "".join(chars), j

    # True when the segment starting here is NOT a `KEYWORD=value` token: no
    # `=` at all (sep == -1), or the next `;` arrives before the next `=`.
    # Named to keep the `_parse_tokens` loop flat.
    @staticmethod
    def _segment_is_not_keyword_pair(sep: int, semi: int) -> bool:
        return sep == -1 or (semi != -1 and semi < sep)

    # Parse the single `KEYWORD=value` token at index `i` into
    # (keyword, value, next_i), where next_i is where the following token
    # begins. The caller has already established, via
    # `_segment_is_not_keyword_pair`, that a `=` precedes the next `;`; a
    # brace-wrapped value is scanned as ONE unit (`_scan_braced_value`) so an
    # embedded literal `;` does not truncate it.
    @classmethod
    def _parse_one_token(cls, config: str, i: int) -> tuple[str, str, int]:
        n = len(config)
        sep = config.find("=", i)
        semi = config.find(";", i)
        kw = config[i:sep].strip().upper()
        val_start = sep + 1

        if val_start < n and config[val_start] == "{":
            value, j = cls._scan_braced_value(config, val_start + 1)
            # After the closing brace, skip to just past the next ';'.
            next_semi = config.find(";", j)
            return kw, value, (next_semi + 1 if next_semi != -1 else n)

        # Bare (unbraced) value: terminated by ';' or end-of-string.
        end = semi if semi != -1 else n
        return kw, config[val_start:end], end + 1

    # Split an ODBC keyword string into (KEYWORD, value) pairs, splitting on
    # `;` only OUTSIDE a brace-wrapped value -- that is the whole point of
    # the ODBC brace-escape (see `_parse_one_token` for the scan).
    @classmethod
    def _parse_tokens(cls, config: str) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        i = 0
        n = len(config)
        while i < n:
            sep = config.find("=", i)
            semi = config.find(";", i)
            if cls._segment_is_not_keyword_pair(sep, semi):
                # Skip past this non-token segment (up to the next ';', or end).
                i = semi + 1 if semi != -1 else n
                continue
            kw, value, i = cls._parse_one_token(config, i)
            pairs.append((kw, value))
        return pairs

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

    def normalize_catalog_literal(self, value: str) -> str:
        return value


_MYSQL_TEXT_TYPES = frozenset(
    {"char", "varchar", "tinytext", "text", "mediumtext", "longtext"}
)


_MYSQL_SECRET_KEYS = ("password", "user", "host")


class MySqlDialect(_DictConfigDialect):
    name = "mysql"
    _secret_keys = _MYSQL_SECRET_KEYS

    # mysql.connector kwargs dict: PORT is int-coerced (the connector expects
    # an int port). resolve_config is inherited from _DictConfigDialect.
    _anchor = ("ANALYTICS_DB_HOST", "host")
    _optional = (
        ("ANALYTICS_DB_PORT", "port"),
        ("ANALYTICS_DB_USER", "user"),
        ("ANALYTICS_DB_PASSWORD", "password"),
        ("ANALYTICS_DB_NAME", "database"),
    )
    _int_keys = frozenset({"ANALYTICS_DB_PORT"})

    def _raw_connect(self, config: dict[str, object]) -> object:
        """Connect via mysql.connector (lazy import), read-only-posture autocommit."""
        import mysql.connector  # lazy: only on a real live run

        return mysql.connector.connect(autocommit=True, **config)

    def quote_ident(self, name: str, *, context: str = "identifier") -> str:
        return f"`{validate_identifier(name, context=context)}`"

    def quote_qualified(
        self, name: str, *, context: str, min_parts: int = 1, max_parts: int = 2
    ) -> str:
        validated = validate_qualified_identifier(
            name, context=context, min_parts=min_parts, max_parts=max_parts
        )
        return ".".join(f"`{p}`" for p in validated.split("."))

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

    def normalize_catalog_literal(self, value: str) -> str:
        return value


_SNOWFLAKE_SECRET_KEYS = ("password", "user", "account", "token", "host")


class SnowflakeDialect(_DictConfigDialect):
    name = "snowflake"
    _secret_keys = _SNOWFLAKE_SECRET_KEYS

    # snowflake.connector kwargs dict (all values are strings).
    # resolve_config is inherited from _DictConfigDialect.
    _anchor = ("ANALYTICS_DB_ACCOUNT", "account")
    _optional = (
        ("ANALYTICS_DB_USER", "user"),
        ("ANALYTICS_DB_PASSWORD", "password"),
        ("ANALYTICS_DB_WAREHOUSE", "warehouse"),
        ("ANALYTICS_DB_ROLE", "role"),
        ("ANALYTICS_DB_NAME", "database"),
        ("ANALYTICS_DB_SCHEMA", "schema"),
    )

    def _raw_connect(self, config: dict[str, object]) -> object:
        """Connect via snowflake.connector (lazy import), autocommit posture."""
        import snowflake.connector  # lazy: only on a real live run

        return snowflake.connector.connect(autocommit=True, **config)

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

    def normalize_catalog_literal(self, value: str) -> str:
        return value.upper()


_DIALECTS: dict[str, type] = {
    "postgres": PostgresDialect,
    "sqlserver": SqlServerDialect,
    "mysql": MySqlDialect,
    "snowflake": SnowflakeDialect,
}


def get_dialect(name: str) -> Dialect:
    """Return the Dialect for ``name`` (postgres|sqlserver|mysql|snowflake)."""
    try:
        return _DIALECTS[name]()
    except KeyError:
        raise ValueError(
            f"unknown DB engine {name!r}; expected one of {sorted(_DIALECTS)}"
        ) from None
