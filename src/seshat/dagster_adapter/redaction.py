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
    r"\b(host|hostaddr|port|user|username|password|passwd|dbname|pwd|uid)"
    r"\s*=\s*[^\s;'\"]+",
    re.IGNORECASE,
)
_SECRET_ENV_RE = re.compile(r"(PASSWORD|SECRET|TOKEN|_KEY$)", re.IGNORECASE)

# ``ANALYTICS_DB_*`` keys whose VALUES are non-secret config from `.env.example`
# (a port number, an sslmode word, an engine name, a driver name, a boolean
# trust flag). Redacting these as if they were credentials corrupts legitimate
# output -- e.g. the literal "require" / "25060" / "true" would be replaced
# wherever it appears -- since #348 now loads `.env` into the process env these
# commands redact against. Excluded by key so the blunt value-replacement never
# sees a fixed-vocabulary config value (Codex P2). HOST / NAME / USER / PASSWORD
# / ACCOUNT stay redacted (a host / account is identifying infra, not a boolean).
_NON_SECRET_ANALYTICS_KEYS = frozenset(
    {
        "ANALYTICS_DB_PORT",
        "ANALYTICS_DB_SSLMODE",
        "ANALYTICS_DB_ENGINE",
        "ANALYTICS_DB_ODBC_DRIVER",
        "ANALYTICS_DB_TRUST_CERT",
    }
)


def _secret_env_values() -> list[str]:
    values: list[str] = []
    values.extend(
        value
        for key, value in os.environ.items()
        if len(value) >= 4 and _is_secret_key(key)
    )
    # Longest first so substrings of longer secrets do not survive partially.
    return sorted(values, key=len, reverse=True)


def _is_secret_key(key: str) -> bool:
    if key in _NON_SECRET_ANALYTICS_KEYS:
        return False  # fixed-vocabulary config, never a credential value
    if key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_"):
        return True
    return bool(_SECRET_ENV_RE.search(key))


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
