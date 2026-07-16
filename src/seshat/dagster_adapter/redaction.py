"""Redaction for every surfaced Dagster-adapter string (spec 134, FR-008).

Anything the adapter prints, records as evidence, or raises passes through
here first. Scrubbed classes (Principle IX): URL DSNs, keyword-style
connection credentials (host/port/user/password/dbname), and the literal
values of secret-bearing environment variables (``DATABASE_URL``,
``ANALYTICS_DB_*``, anything with PASSWORD/SECRET/TOKEN in its name).
"""

from __future__ import annotations

import os
import re

_DSN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"]+")
_KEYWORD_RE = re.compile(
    r"\b(host|hostaddr|port|user|username|password|passwd|dbname)\s*=\s*[^\s;'\"]+",
    re.IGNORECASE,
)
_SECRET_ENV_RE = re.compile(r"(PASSWORD|SECRET|TOKEN|_KEY$)", re.IGNORECASE)


def _secret_env_values() -> list[str]:
    values: list[str] = []
    for key, value in os.environ.items():
        if len(value) < 4:
            continue
        if key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_") or _SECRET_ENV_RE.search(key):
            values.append(value)
    # Longest first so substrings of longer secrets do not survive partially.
    return sorted(values, key=len, reverse=True)


def redact_text(text: str) -> str:
    """Return ``text`` with every credential-bearing fragment replaced."""
    if not text:
        return text
    out = _DSN_RE.sub("[REDACTED-DSN]", text)
    out = _KEYWORD_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", out)
    for value in _secret_env_values():
        if value in out:
            out = out.replace(value, "[REDACTED-ENV]")
    return out


def redact_payload(payload: object) -> object:
    """Recursively redact every string inside a JSON-shaped payload."""
    if isinstance(payload, str):
        return redact_text(payload)
    if isinstance(payload, dict):
        return {key: redact_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(redact_payload(item) for item in payload)
    return payload
