"""Read-only, DSN-safe table enumeration for Layer-A portfolio discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .dialect import Dialect, get_dialect
from .identifiers import validate_identifier


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
    if config is not None:
        try:
            redacted = dialect.redact(error, config)
        except Exception:
            redacted = "database metadata boundary failed (details redacted)"
    else:
        redacted = str(error) or error.__class__.__name__

    secrets = {
        value
        for key, value in env.items()
        if value and (key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_"))
    }
    for secret in sorted(secrets, key=len, reverse=True):
        redacted = redacted.replace(secret, "<redacted>")
    if any(part in redacted for part in ("@", "://")):
        return "database metadata boundary failed (details redacted)"
    return redacted


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
