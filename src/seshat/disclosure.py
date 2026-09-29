"""Fail-closed disclosure checks for generated public-facing artifacts."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "dsn",
        "connection_string",
        "database_url",
        "db_url",
        "connection_url",
        "access_token",
        "client_secret",
    }
)
# A key is ALSO secret when one of its word tokens is one of these (so
# `DB_PASSWORD`, `pg-pwd`, `client_secret_value` block) -- matched per token,
# never by substring, so `token_count` or `connection_status` stay clean.
_SECRET_KEY_TOKENS = frozenset({"password", "passwd", "pwd", "secret", "dsn"})
_PII_KEYS = frozenset(
    {"email", "phone", "ssn", "national_id", "customer_name", "full_name"}
)
_RAW_ARRAY_KEYS = frozenset(
    {"raw_values", "sample_values", "distinct_values", "source_rows", "raw_rows"}
)
# `scheme(+driver)?://` -- SQLAlchemy spellings such as `postgresql+psycopg2://`.
_CONNECTION_RE = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mssql|sqlserver|snowflake)(?:\+[a-z0-9_]+)?://",
    re.IGNORECASE,
)
# Libpq keyword conninfo (`host=h password=p`): a host= plus a credential key.
_CONNINFO_RE = re.compile(
    r"(?i)\b(?:host|hostaddr|server)\s*=\s*\S+.*\b(?:user|password|dbname)\s*=\s*\S"
)
# Unanchored, so a path embedded in an error string is caught too. The drive
# letter must not follow an alphanumeric (`http://` holds `p:/`).
_WINDOWS_ABS_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"(?<![^\s\"'(=])\\\\[^\\\s]+\\")
_UNIX_ABS_RE = re.compile(r"(?<![\w.:/-])/(?:home|Users|var|etc|opt|tmp|root|srv|mnt)/")


def _finding(rule: str, locator: str, message: str) -> dict[str, str]:
    return {"rule": rule, "locator": locator, "message": message}


def _is_secret_key(key: str | None) -> bool:
    if not key:
        return False
    if key in _SECRET_KEYS:
        return True
    return bool(_SECRET_KEY_TOKENS & set(re.split(r"[^a-z0-9]+", key)))


def _is_absolute_path(value: str) -> bool:
    return any(
        pattern.search(value) for pattern in (_WINDOWS_ABS_RE, _UNC_RE, _UNIX_ABS_RE)
    )


def _secret_shaped_findings(value: str, locator: str) -> list[dict[str, str]]:
    """The shipped SECRET_PATTERNS chokepoint, so this gate is never weaker."""
    from seshat.pbi_mcp.scan import scan_text

    return [
        _finding(
            rule="secret_shaped",
            locator=locator,
            message=f"value matches a secret-shaped pattern ({label})",
        )
        for label in scan_text(value)
    ]


def _string_findings(key: str | None, value: str, locator: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = _secret_shaped_findings(value, locator)
    if _is_secret_key(key) and value:
        findings.append(
            _finding(
                rule="secret_field", locator=locator, message="secret field is set"
            )
        )
    if _CONNECTION_RE.search(value) or _CONNINFO_RE.search(value):
        findings.append(
            _finding(
                rule="connection_string",
                locator=locator,
                message="connection string is not safe for disclosure",
            )
        )
    if _is_absolute_path(value):
        findings.append(
            _finding(
                rule="absolute_path",
                locator=locator,
                message="machine-local absolute path is not safe for disclosure",
            )
        )
    if key in _PII_KEYS and value:
        findings.append(
            _finding(
                rule="pii_value",
                locator=locator,
                message="possible PII value is not safe for disclosure",
            )
        )
    return findings


def _array_findings(
    key: str | None, value: list[object], locator: str
) -> list[dict[str, str]]:
    if key in _RAW_ARRAY_KEYS and value:
        return [
            _finding(
                rule="raw_value_array",
                locator=locator,
                message="raw or sampled value array is not safe for disclosure",
            )
        ]
    return []


def _child_items(
    value: object, locator: str, key: str | None
) -> list[tuple[str, str | None, object]]:
    """Normalize container children to ``(locator, key, child)`` triples."""
    if isinstance(value, dict):
        return [
            (f"{locator}.{child_key}", str(child_key).lower(), child)
            for child_key, child in value.items()
        ]
    if isinstance(value, list):
        return [
            (f"{locator}[{index}]", key, child) for index, child in enumerate(value)
        ]
    return []


def _walk(
    value: object, locator: str, key: str | None
) -> tuple[int, list[dict[str, str]]]:
    if isinstance(value, str):
        return 1, _string_findings(key, value, locator)
    inspected = 1
    findings = _array_findings(key, value, locator) if isinstance(value, list) else []
    for child_locator, child_key, child in _child_items(value, locator, key):
        count, child_findings = _walk(child, child_locator, child_key)
        inspected += count
        findings.extend(child_findings)
    return inspected, findings


def scan_disclosure(document: object) -> dict[str, Any]:
    inspected, findings = _walk(document, "$", None)
    return {
        "status": "blocked" if findings else "pass",
        "inspected_values": inspected,
        "findings": findings,
    }
