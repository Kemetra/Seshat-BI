"""One redaction chain for every live-DB CLI boundary error.

``validate``, ``profile``, ``value-check``, ``drift`` and ``report --from-gold``
each print a driver exception when a connection or query fails. Before this
module each site printed ``dialect.redact(exc, config)`` alone. That is layer
ONE: it scrubs values derived from the configured DSN, and so it misses what the
driver learns elsewhere -- a host or user from ``pg_service.conf`` / ``PGHOST``,
a resolved IP address, a user path the driver names, a tenant GUID -- and the
dict-config engines scrubbed only a few keys.

:func:`boundary_error_text` applies every layer, in order:

1. the engine's own ``dialect.redact`` (DSN / ODBC / kwargs components);
2. span-based ``key=value`` redaction (``connection_env``), so a credential
   keyword's whole value goes, not a fragment of it;
3. the configured and ambient connection VALUES (config plus the ``PG*`` and
   ``ANALYTICS_DB_*`` secret variables), replaced only at alphanumeric
   boundaries so a short value cannot shred unrelated words;
4. the connection-context shapes drivers print (``server at "..."``,
   ``user '...'@'...'``, ``database "..."``, IP literals, libpq's
   ``missing "=" after "..."``);
5. ``scrub_secret_shaped`` -- the shipped SECRET_PATTERNS table (layer two).

If any layer raises, the whole message is withheld: under-redaction while
formatting an error is worse than a terse message.
"""

from __future__ import annotations

import os
import re

_TOKEN = "<redacted>"
_WITHHELD = "database boundary failure (details redacted)"

# Ambient variables whose VALUES are connection secrets. libpq reads the PG*
# ones even when the configured DSN does not mention them.
_SECRET_ENV_KEYS = (
    "PGHOST",
    "PGHOSTADDR",
    "PGUSER",
    "PGPASSWORD",
    "PGDATABASE",
    "PGSERVICE",
    "ANALYTICS_DB_HOST",
    "ANALYTICS_DB_NAME",
    "ANALYTICS_DB_USER",
    "ANALYTICS_DB_PASSWORD",
    "ANALYTICS_DB_ACCOUNT",
    "ANALYTICS_DB_WAREHOUSE",
)

# Kwargs-config keys (MySQL / Snowflake) whose values identify or unlock a target.
_SECRET_CONFIG_KEYS = (
    "password",
    "user",
    "host",
    "account",
    "token",
    "database",
    "warehouse",
)

_QUOTED = r"""(["'])[^"'\r\n]*\3"""
_CONTEXT_SHAPES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?i)\b(server\s+at|server\s+on|host\s+name|hostname|host|for\s+user"
            r"|user|role|database|warehouse|account)(\s+)" + _QUOTED
        ),
        rf"\1\2\3{_TOKEN}\3",
    ),
    (re.compile(r"""(["'])@(["'])[^"'\r\n]*\2"""), rf"\1@\2{_TOKEN}\2"),
    (re.compile(r'(?i)(missing\s+"="\s+after\s+)"[^"\r\n]*"'), rf'\1"{_TOKEN}"'),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), _TOKEN),
    (
        re.compile(r"\((?=[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*:)[0-9A-Fa-f:.%]+\)"),
        f"({_TOKEN})",
    ),
)


def boundary_error_text(dialect: object, exc: object, config: object) -> str:
    """The fully redacted text of one DB-boundary exception (see module doc)."""
    try:
        text = dialect.redact(exc, config)  # type: ignore[attr-defined]
        return _scrub_layers(str(text) or exc.__class__.__name__, config)
    except Exception:  # noqa: BLE001 -- never under-redact while formatting
        return _WITHHELD


def _scrub_layers(text: str, config: object) -> str:
    from seshat.connection_env import _scrub_connection_values
    from seshat.pbi_mcp_adapter.evidence import scrub_secret_shaped
    from seshat.redaction_core import replace_bounded

    text = _scrub_connection_values(text)
    text = replace_bounded(text, _secret_values(config), _TOKEN)
    for pattern, replacement in _CONTEXT_SHAPES:
        text = pattern.sub(replacement, text)
    scrubbed, _labels = scrub_secret_shaped(text)
    return scrubbed


def _secret_values(config: object) -> list[str]:
    """Every configured or ambient connection value, longest first."""
    values = {os.environ.get(key, "") for key in _SECRET_ENV_KEYS}
    values.update(_config_values(config))
    return sorted((v for v in values if v and v.strip()), key=len, reverse=True)


def _config_values(config: object) -> set[str]:
    """The secret values carried by one resolved config, whatever its shape."""
    if isinstance(config, dict):
        return {str(config[k]) for k in _SECRET_CONFIG_KEYS if config.get(k)}
    if not isinstance(config, str) or not config:
        return set()
    from seshat.redaction_core import conninfo_password_words, uri_components

    return {*uri_components([config]), *conninfo_password_words(config)}
