"""Read-only, DSN-safe table enumeration for Layer-A portfolio discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import unquote, urlsplit

from .dialect import Dialect, get_dialect
from .identifiers import validate_identifier

# The ANALYTICS_DB_* keys whose VALUES are credentials -- a POSITIVE set, mirroring
# ``seshat.dagster_adapter.redaction._SECRET_ANALYTICS_KEYS`` (#357). Redact ONLY
# these; every other ANALYTICS_DB_* key (the fixed-vocabulary config knobs ENGINE/
# PORT/SSLMODE/... and any future key) is non-secret BY DEFAULT. The old
# ``startswith("ANALYTICS_DB_")`` prefix-scan had no allowlist and over-redacted
# config words -- e.g. ENGINE=postgres shredded "postgresql" into "<redacted>ql".
_SECRET_ANALYTICS_KEYS = frozenset(
    {
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_USER",
        "ANALYTICS_DB_PASSWORD",
        "ANALYTICS_DB_ACCOUNT",
    }
)


@dataclass(frozen=True)
class PortfolioEnumeration:
    """All reachable tables, or one safe boundary error."""

    tables: tuple[str, ...] = ()
    error: str | None = None


def _safe_boundary_error(
    error: Exception,
    *,
    dialect: Dialect,
    config: object | None,
    env: Mapping[str, str],
) -> str:
    """Redact through the dialect and fail closed if the redactor itself fails."""
    redacted = _redact_error(error, dialect=dialect, config=config)
    return _scrub_environment_secrets(redacted, env)


def _redact_error(error: Exception, *, dialect: Dialect, config: object | None) -> str:
    if config is None:
        return str(error) or error.__class__.__name__
    try:
        return dialect.redact(error, config)
    except Exception:
        return "database metadata boundary failed (details redacted)"


def _replace_fragments(text: str, fragments: list[str]) -> str:
    for fragment in fragments:
        text = text.replace(fragment, "<redacted>")
    return text


def _scrub_environment_secrets(redacted: str, env: Mapping[str, str]) -> str:
    secrets = _database_secret_values(env)
    redacted = _replace_fragments(redacted, secrets)
    # Then each URI component of a DSN-shaped secret (host/user/password/dbname),
    # so a reformatted, schemeless error that names only the host/user -- neither
    # the verbatim DSN nor a `scheme://` present -- still gets its credentials
    # scrubbed (mirrors seshat.dbt.redaction._uri_values / the dagster redactor).
    redacted = _replace_fragments(redacted, _uri_components(secrets))
    if "@" in redacted or "://" in redacted:
        return "database metadata boundary failed (details redacted)"
    return redacted


def _database_secret_values(env: Mapping[str, str]) -> list[str]:
    secrets = {
        value
        for key, value in env.items()
        if value and (key == "DATABASE_URL" or key in _SECRET_ANALYTICS_KEYS)
    }
    return sorted(secrets, key=len, reverse=True)


def _uri_component_values(secret: str) -> tuple[str, ...]:
    parsed = urlsplit(secret)
    if not parsed.scheme or not parsed.netloc:
        return ()
    raw = (parsed.username, parsed.password, parsed.hostname, parsed.path.lstrip("/"))
    return tuple(
        component for value in raw if value for component in (value, unquote(value))
    )


def _uri_components(secrets: list[str]) -> list[str]:
    components = {
        component for secret in secrets for component in _uri_component_values(secret)
    }
    return sorted(components, key=len, reverse=True)


def enumerate_tables(
    schema: str,
    *,
    env: Mapping[str, str] | None = None,
) -> PortfolioEnumeration:
    """Enumerate every reachable base table/view in schema without sampling.

    This is the DB branch's only enumeration path. All config, driver, connection,
    and query failures return a safe error instead of raising across the boundary.
    """
    from seshat import cli

    safe_schema = validate_identifier(schema, context="portfolio schema")
    resolved_env = dict(os.environ if env is None else env)
    engine = resolved_env.get("ANALYTICS_DB_ENGINE") or "postgres"
    dialect = get_dialect(engine)
    config: object | None = None

    try:
        config = dialect.resolve_config(resolved_env)
        if config is None:
            return PortfolioEnumeration(
                error="no database connection configured; set DATABASE_URL or "
                "ANALYTICS_DB_* in the gitignored .env"
            )
        if not cli._ensure_driver():
            return PortfolioEnumeration(
                error="optional database driver unavailable; install the matching "
                "retail DB extra"
            )

        runner = cli._make_runner(config)
        placeholder = dialect.placeholder()
        sql = dialect.translate_params(
            "SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = {placeholder} "
            "AND table_type IN ('BASE TABLE', 'VIEW') ORDER BY table_name"
        )
        rows = runner.run(sql, (safe_schema,))
    except Exception as exc:
        return PortfolioEnumeration(
            error=_safe_boundary_error(
                exc, dialect=dialect, config=config, env=resolved_env
            )
        )

    return PortfolioEnumeration(tables=tuple(f"{safe_schema}.{row[0]}" for row in rows))
