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


_MSSQL_TEXT_TYPES = frozenset({"varchar", "nvarchar", "char", "nchar", "text", "ntext"})


class SqlServerDialect:
    name = "sqlserver"

    def resolve_config(self, env: dict[str, str]) -> str | None:
        """Build an ODBC connection keyword string from ANALYTICS_DB_* env vars.

        Returns None (no host configured) rather than a half-built string, so
        the caller's "no connection configured" error path is reused verbatim.

        UID/PWD values are brace-wrapped (ODBC's documented escaping form,
        `KEYWORD={value}`) so a `;` inside a password/username is unambiguous
        both to the driver and to `redact()` -- without bracing, a `;` inside
        the value is indistinguishable from the next `KEYWORD=` separator and
        `config.split(";")` truncates the value (R4).

        A literal `}` inside the value is escaped by DOUBLING it (`}}`) before
        wrapping, per full ODBC brace-escaping rules -- a brace-quoted value
        starts after the opening `{` and ends at the first `}` that is NOT
        doubled; a `{` inside the value is just a literal character (bracing
        is not nestable). Without doubling, a password containing `}` would
        both (a) build a malformed connection string pyodbc's ODBC parser
        cannot round-trip, and (b) fail to fully scrub in `redact()` via
        `_parse_tokens`, which now parses these exact rules (R4).
        """
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

    def connect(self, config: str) -> object:
        """Connect via pyodbc (lazy import). Read-only posture: use a
        SELECT-only DB user; autocommit avoids holding an open transaction."""
        import pyodbc  # lazy: only on a real live run

        conn = pyodbc.connect(config, autocommit=True)

        class _Runner:
            def run(self, sql: str, params: tuple = ()) -> list[tuple]:
                cur = conn.cursor()
                cur.execute(sql, params)
                return list(cur.fetchall())

        return _Runner()

    def redact(self, message: object, config: str) -> str:
        """Scrub PWD/UID/SERVER/DATABASE values from an error message.

        A naive `config.split(";")` is ambiguous: a `;` INSIDE a password (or
        any value) is indistinguishable from the separator between keywords,
        so a plain split silently truncates the value at the first embedded
        `;`. resolve_config now brace-wraps PWD/UID (`KEY={value}`, the ODBC-
        documented escape), which makes those two values unambiguous; this
        method parses brace-wrapped tokens as a single unit instead of
        splitting on every `;` blindly.

        Two passes, mirroring `_redact_dsn`'s component-level scrub for
        psycopg2. ORDER MATTERS: (1) the AUTHORITATIVE component-level pass
        runs FIRST -- it re-derives each secret VALUE from the config string
        (unwrapping braces, and splitting SERVER on the LAST `,` to isolate the
        bare host) and replaces it verbatim wherever it appears; this is what
        catches the driver reformatting the error into its own text (e.g.
        FreeTDS "TCP Provider: host 'X' not found", which never contains
        "SERVER=" or the port at all). Component values are scrubbed
        longest-first so a short value (e.g. a username that is a substring of
        the host) cannot pre-empt a longer overlapping match, matching
        `_redact_dsn`'s discipline. (2) a best-effort `KW=value` regex pass
        runs SECOND as a defence-in-depth backstop (covers brace and bare
        forms, stops at a following `;` OR `}`).

        The component pass MUST precede the regex pass: if a password itself
        contains a literal `KEYWORD=` (e.g. `secret;DATABASE=x`), a regex-first
        order would rewrite the `DATABASE=x` fragment INSIDE the password text,
        so the later verbatim whole-value replace no longer matches and the
        password prefix (`secret`) leaks. Running the exact-value replace first
        scrubs the whole credential before the regex can mangle it.
        """
        text = str(message)

        # Pass 1 (authoritative): exact-value component scrub, longest-first.
        # The yes/no skip is scoped to the BOOLEAN keywords only (Encrypt,
        # TrustServerCertificate) -- it exists to avoid over-redacting those
        # non-secret flags. It must NOT apply keyword-agnostically: a PWD/UID/
        # DATABASE/SERVER value that happens to literally equal "yes"/"no"
        # is still a real credential and must be scrubbed (security over
        # cosmetic over-redaction).
        _BOOLEAN_KEYWORDS = ("ENCRYPT", "TRUSTSERVERCERTIFICATE")
        secrets: set[str] = set()
        for kw, val in self._parse_tokens(config or ""):
            if not val:
                continue
            if kw in _BOOLEAN_KEYWORDS and val.lower() in ("yes", "no"):
                continue
            if kw == "SERVER":
                # SERVER=host,port -- scrub the bare host independently, since
                # the driver may print it alone with no port and no prefix.
                host = val.rsplit(",", 1)[0]
                if host:
                    secrets.add(host)
                secrets.add(val)
            else:
                secrets.add(val)

        for secret in sorted(secrets, key=len, reverse=True):
            text = text.replace(secret, "<redacted>")

        # Pass 2 (defence-in-depth backstop): KW=value regex on the message.
        for kw in ("PWD", "UID"):
            # Brace form first (value may legitimately contain ';'), then bare.
            text = re.sub(rf"({kw}=)\{{[^}}]*\}}", r"\1<redacted>", text)
            text = re.sub(rf"({kw}=)[^;]*", r"\1<redacted>", text)
        for kw in ("SERVER", "DATABASE"):
            text = re.sub(rf"({kw}=)[^;]*", r"\1<redacted>", text)
        return text

    @staticmethod
    def _parse_tokens(config: str) -> list[tuple[str, str]]:
        """Split an ODBC keyword string into (KEYWORD, value) pairs.

        Unlike a naive ``config.split(";")``, this splits on ``;`` only
        OUTSIDE of a brace-wrapped value (``KEY={...}``) -- a brace-wrapped
        value may legitimately contain a literal ``;`` (that is the whole
        point of the ODBC brace-escape), and a blind split truncates it.

        ODBC brace-quoting is NON-NESTABLE, so this is a char-scan, not
        depth-counting: once a value opens with ``{``, an interior ``{`` is
        just a literal character; a doubled ``}}`` is a literal ``}`` (part
        of the value); the first SINGLE ``}`` (not followed by another ``}``)
        terminates the value. The returned value is unescaped (``}}`` -> ``}``).
        """
        pairs: list[tuple[str, str]] = []
        i = 0
        n = len(config)
        while i < n:
            # Find the end of this token's KEYWORD= prefix (up to '=' or ';').
            sep = config.find("=", i)
            semi = config.find(";", i)
            if sep == -1 or (semi != -1 and semi < sep):
                # No '=' before the next ';' (or no '=' at all) -- not a
                # KEYWORD=value token; skip past this segment.
                i = semi + 1 if semi != -1 else n
                continue

            kw = config[i:sep].strip().upper()
            val_start = sep + 1

            if val_start < n and config[val_start] == "{":
                # Brace-quoted value: scan for the terminating single '}'.
                chars: list[str] = []
                j = val_start + 1
                while j < n:
                    if config[j] == "}":
                        if j + 1 < n and config[j + 1] == "}":
                            chars.append("}")
                            j += 2
                            continue
                        j += 1  # consume the terminating brace
                        break
                    chars.append(config[j])
                    j += 1
                pairs.append((kw, "".join(chars)))
                # After the closing brace, skip to just past the next ';'.
                next_semi = config.find(";", j)
                i = next_semi + 1 if next_semi != -1 else n
            else:
                # Bare (unbraced) value: terminated by ';' or end-of-string.
                end = semi if semi != -1 else n
                pairs.append((kw, config[val_start:end]))
                i = end + 1
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


class MySqlDialect:
    name = "mysql"

    def resolve_config(self, env: dict[str, str]) -> dict[str, object] | None:
        """Build a mysql.connector kwargs dict from ANALYTICS_DB_* env vars."""
        host = env.get("ANALYTICS_DB_HOST")
        if not host:
            return None
        config: dict[str, object] = {"host": host}
        port = env.get("ANALYTICS_DB_PORT")
        if port:
            config["port"] = int(port)
        if env.get("ANALYTICS_DB_USER"):
            config["user"] = env["ANALYTICS_DB_USER"]
        if env.get("ANALYTICS_DB_PASSWORD"):
            config["password"] = env["ANALYTICS_DB_PASSWORD"]
        if env.get("ANALYTICS_DB_NAME"):
            config["database"] = env["ANALYTICS_DB_NAME"]
        return config

    def connect(self, config: dict[str, object]) -> object:
        """Connect via mysql.connector (lazy import), read-only-posture autocommit."""
        import mysql.connector  # lazy: only on a real live run

        conn = mysql.connector.connect(autocommit=True, **config)

        class _Runner:
            def run(self, sql: str, params: tuple = ()) -> list[tuple]:
                cur = conn.cursor()
                cur.execute(sql, params)
                return list(cur.fetchall())

        return _Runner()

    def redact(self, message: object, config: dict[str, object]) -> str:
        """Scrub each secret config value (password/user/host) from a message."""
        text = str(message)
        for key in _MYSQL_SECRET_KEYS:
            value = (config or {}).get(key)
            if value:
                text = text.replace(str(value), "<redacted>")
        return text

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
        return (
            f"(SELECT COUNT(*) FROM (SELECT DISTINCT {joined} FROM {table}{w}) AS sub)"
        )

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


class SnowflakeDialect:
    name = "snowflake"

    def resolve_config(self, env: dict[str, str]) -> dict[str, object] | None:
        """Build a snowflake.connector kwargs dict from ANALYTICS_DB_* env vars."""
        account = env.get("ANALYTICS_DB_ACCOUNT")
        if not account:
            return None
        config: dict[str, object] = {"account": account}
        if env.get("ANALYTICS_DB_USER"):
            config["user"] = env["ANALYTICS_DB_USER"]
        if env.get("ANALYTICS_DB_PASSWORD"):
            config["password"] = env["ANALYTICS_DB_PASSWORD"]
        if env.get("ANALYTICS_DB_WAREHOUSE"):
            config["warehouse"] = env["ANALYTICS_DB_WAREHOUSE"]
        if env.get("ANALYTICS_DB_ROLE"):
            config["role"] = env["ANALYTICS_DB_ROLE"]
        if env.get("ANALYTICS_DB_NAME"):
            config["database"] = env["ANALYTICS_DB_NAME"]
        if env.get("ANALYTICS_DB_SCHEMA"):
            config["schema"] = env["ANALYTICS_DB_SCHEMA"]
        return config

    def connect(self, config: dict[str, object]) -> object:
        """Connect via snowflake.connector (lazy import), autocommit posture."""
        import snowflake.connector  # lazy: only on a real live run

        conn = snowflake.connector.connect(autocommit=True, **config)

        class _Runner:
            def run(self, sql: str, params: tuple = ()) -> list[tuple]:
                cur = conn.cursor()
                cur.execute(sql, params)
                return list(cur.fetchall())

        return _Runner()

    def redact(self, message: object, config: dict[str, object]) -> str:
        """Scrub each secret config value (password/user/account/token/host)."""
        text = str(message)
        for key in _SNOWFLAKE_SECRET_KEYS:
            value = (config or {}).get(key)
            if value:
                text = text.replace(str(value), "<redacted>")
        return text

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
        return (
            f"(SELECT COUNT(*) FROM (SELECT DISTINCT {joined} FROM {table}{w}) AS sub)"
        )

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
