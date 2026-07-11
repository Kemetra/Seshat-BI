"""Fail-closed disclosure checks for generated public-facing artifacts."""

from __future__ import annotations

import re
from typing import Any

_SECRET_KEYS = frozenset(
    {"password", "passwd", "secret", "token", "api_key", "dsn", "connection_string"}
)
_PII_KEYS = frozenset(
    {"email", "phone", "ssn", "national_id", "customer_name", "full_name"}
)
_RAW_ARRAY_KEYS = frozenset(
    {"raw_values", "sample_values", "distinct_values", "source_rows", "raw_rows"}
)
_CONNECTION_RE = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mssql|sqlserver|snowflake)://", re.IGNORECASE
)
_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNIX_ABS_RE = re.compile(r"^/(?:home|Users|var|etc|opt|tmp)/")


def _finding(rule: str, locator: str, message: str) -> dict[str, str]:
    return {"rule": rule, "locator": locator, "message": message}


def _string_findings(key: str | None, value: str, locator: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if key in _SECRET_KEYS and value:
        findings.append(
            _finding(
                rule="secret_field", locator=locator, message="secret field is set"
            )
        )
    if _CONNECTION_RE.search(value):
        findings.append(
            _finding(
                rule="connection_string",
                locator=locator,
                message="connection string is not safe for disclosure",
            )
        )
    if _WINDOWS_ABS_RE.match(value) or _UNIX_ABS_RE.match(value):
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


def _walk(
    value: object, locator: str, key: str | None
) -> tuple[int, list[dict[str, str]]]:
    inspected = 1
    findings: list[dict[str, str]] = []
    if isinstance(value, str):
        findings.extend(_string_findings(key, value, locator))
    elif isinstance(value, dict):
        for child_key, child in value.items():
            child_locator = f"{locator}.{child_key}"
            count, child_findings = _walk(child, child_locator, str(child_key).lower())
            inspected += count
            findings.extend(child_findings)
    elif isinstance(value, list):
        if key in _RAW_ARRAY_KEYS and value:
            findings.append(
                _finding(
                    rule="raw_value_array",
                    locator=locator,
                    message="raw or sampled value array is not safe for disclosure",
                )
            )
        for index, child in enumerate(value):
            count, child_findings = _walk(child, f"{locator}[{index}]", key)
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
