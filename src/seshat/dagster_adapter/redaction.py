"""Redaction for every surfaced Dagster-adapter string (spec 134, FR-008).

Anything the adapter prints, records as evidence, or raises passes through
here first. Scrubbed classes (Principle IX): URL DSNs, keyword-style
connection credentials (host/port/user/password/dbname), and the literal
values of secret-bearing environment variables -- ``DATABASE_URL``, the
credential subset of ``ANALYTICS_DB_*`` (host/name/user/password/account), and
anything with PASSWORD/SECRET/TOKEN in its name.

Secret ENV keys are an explicit POSITIVE set (#357): the ``ANALYTICS_DB_*``
config knobs (port/sslmode/engine/driver/trust) and any future config key are
non-secret by default, never an enumerated exclusion, so the value scan cannot
over-redact a fixed-vocabulary config word. Credential values are redacted at
any length; the tradeoff is that a database literally named a common word
(e.g. NAME=``gold``) has that word clobbered wherever it appears -- safe
direction (a dbname must never surface), a documented decision.
"""

from __future__ import annotations

import os
import re

from seshat.redaction_core import replace_fragments, uri_components

_DSN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"]+")
_KEYWORD_RE = re.compile(
    r"\b(host|hostaddr|port|user|username|password|passwd|dbname|pwd|uid)"
    r"\s*=\s*[^\s;'\"]+",
    re.IGNORECASE,
)
_SECRET_ENV_RE = re.compile(r"(PASSWORD|SECRET|TOKEN|_KEY$)", re.IGNORECASE)

# The ``ANALYTICS_DB_*`` keys whose VALUES are credentials (#357). This is a
# POSITIVE set: redact ONLY these, so every other key in the namespace -- the
# fixed-vocabulary config knobs (PORT/SSLMODE/ENGINE/ODBC_DRIVER/TRUST_CERT) AND
# any FUTURE ``ANALYTICS_DB_*`` config key -- is non-secret BY DEFAULT, with no
# enumerated exclusion list to keep in sync as `.env.example` grows. Mirrors
# ``seshat.dbt.redaction._SECRET_ENVIRONMENT_KEYS`` and the per-dialect
# ``_secret_keys`` in ``seshat.dialect`` (password/user/host/account/name).
#
# The set is derived from ALL ANALYTICS_DB_* keys the tool reads (see
# seshat.dialect / validate). Deliberately EXCLUDED as non-secret target/config
# labels, not credentials -- matching how dbt treats SESHAT_DBT_SCHEMA:
#   ANALYTICS_DB_ENGINE / _PORT / _SSLMODE / _ODBC_DRIVER / _TRUST_CERT (knobs)
#   ANALYTICS_DB_SCHEMA / _ROLE / _WAREHOUSE (Snowflake target/authz labels; none
#     appear in any dialect's _secret_keys).
# ACCOUNT (a Snowflake account identifier) IS redacted -- it is in
# _SNOWFLAKE_SECRET_KEYS: identifying infra, not a config word.
_SECRET_ANALYTICS_KEYS = frozenset(
    {
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_USER",
        "ANALYTICS_DB_PASSWORD",
        "ANALYTICS_DB_ACCOUNT",
    }
)


# A generic `_SECRET_ENV_RE`-matched key (e.g. `MY_DEPLOY_TOKEN`) can carry a
# tiny value (a flag `1`, a version `v2`) that is NOT a credential; replacing it
# globally would shred every matching digit/short token in the payload. The
# any-length policy the #357 decision approved applies to the KNOWN CREDENTIAL
# set only; generic regex-matched keys keep a small length floor (a real token
# is long) so a 1-char flag never becomes a redaction wildcard.
_GENERIC_SECRET_MIN_LEN = 4


def _secret_env_values() -> list[str]:
    # Two policies (#357):
    #  * a KNOWN credential -- the ANALYTICS secret set or DATABASE_URL -- is
    #    redacted at ANY non-empty length: a short host/user (`db`/`sa`) must not
    #    survive in a reformatted, non-key=value driver error. Correctness beats
    #    the (approved, documented) short-substring collision.
    #  * a GENERIC `_SECRET_ENV_RE`-matched key keeps a length floor, so a 1-char
    #    flag-style value never turns into a global redaction wildcard.
    values: list[str] = []
    for key, value in os.environ.items():
        if not value:
            continue
        if key == "DATABASE_URL" or key in _SECRET_ANALYTICS_KEYS:
            values.append(value)
        elif len(value) >= _GENERIC_SECRET_MIN_LEN and bool(_SECRET_ENV_RE.search(key)):
            values.append(value)
    # Longest first so substrings of longer secrets do not survive partially.
    return sorted(values, key=len, reverse=True)


def redact_text(text: str) -> str:
    """Return ``text`` with every credential-bearing fragment replaced."""
    if not text:
        return text
    # Exact secret VALUES first, then each URI component of a DSN-shaped secret
    # (host/user/password/dbname) so a reformatted, schemeless error is still
    # scrubbed, then the regex passes. Value-first mirrors dialect.py's documented
    # order: a regex-first pass can consume the leading token of a secret and leave
    # the tail (`abc;` of `abc;user=bob;xyz`) surviving the later value replace.
    secrets = _secret_env_values()
    out = replace_fragments(text, secrets, "[REDACTED-ENV]")
    out = replace_fragments(out, uri_components(secrets), "[REDACTED-ENV]")
    out = _DSN_RE.sub("[REDACTED-DSN]", out)
    out = _KEYWORD_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", out)
    return out


def redact_payload(payload: object) -> object:
    """Recursively redact every string inside a JSON-shaped payload.

    Dict KEYS are redacted too (mirrors ``seshat.dbt.redaction.sanitize``): a
    secret can surface as a mapping key, not only a value, and must not survive
    there."""
    if isinstance(payload, str):
        return redact_text(payload)
    if isinstance(payload, dict):
        return {
            redact_payload(key): redact_payload(value) for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(redact_payload(item) for item in payload)
    return payload
