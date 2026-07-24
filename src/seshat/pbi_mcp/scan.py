"""Secret / literal-connection refusal scan for generated pbi-mcp output.

Mirrors the C1/C2 committed-secret shapes (``seshat.rules.git_meta``) and the
bundle-export patterns (``scripts/export_agent_bundles.py``) so anything this
family GENERATES is held to the same bar as anything the repo COMMITS: a
would-be credential, tenant/app GUID, connection literal, managed-DB endpoint,
or user-local path in generated text is a refusal, never a warning.

Findings name the PATTERN only -- the matched value is never echoed
(Principle IX). Several pattern literals below are assembled from parts so
this source file cannot itself trip the C2 scanner it mirrors (the same
discipline ``git_meta.py`` documents for its own patterns).
"""

from __future__ import annotations

import re

# Assembled from parts: the two ODBC credential keywords must never appear in
# this source directly followed by their delimiter (see module docstring).
_ODBC_KEYS = "PW" + "D|UI" + "D"
_PG_SCHEME = "postgres" + "(?:ql)?" + ":" + "//"
_DO_SUFFIX = ".db." + "ondigitalocean" + ".com"

# label -> pattern. Every VALUE class excludes ``<`` so a documented
# ``<placeholder>`` token never matches; only a real literal value can.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|api[_ -]?key|access[_ -]?token"
            r"|client[_ -]?secret|accountkey)\s*[=:]\s*[^\s<>{}$]+"
        ),
    ),
    (
        "credential-bearing URL",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:<>]+:[^\s/@<>]+@", re.IGNORECASE),
    ),
    (
        "database connection URL",
        re.compile(
            "(?i)\\b(?:" + _PG_SCHEME + r"|mysql://|mssql://|sqlserver://"
            r"|snowflake://)[^\s<>]+"
        ),
    ),
    (
        "managed-database endpoint",
        re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,253}" + re.escape(_DO_SUFFIX)),
    ),
    (
        "managed-database cluster slug",
        re.compile(r"\bdb-[a-z]{2,}-[a-z]{2,}\d-\d{3,}\b"),
    ),
    (
        "ODBC credential keyword",
        re.compile(r"\b(?:" + _ODBC_KEYS + r")=[^;\s{}<>/]+"),
    ),
    (
        "Windows user path",
        re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s<>]+"),
    ),
    (
        "macOS user path",
        re.compile(r"/Users/[^/\s<>]+/"),
    ),
    (
        # A raw GUID in GENERATED config/guidance text is a tenant, app, or
        # workspace id -- the templates use <tenant-id>-style placeholders, so
        # a matching literal means real environment data leaked in.
        "GUID (tenant/app/workspace id)",
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
            r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
    ),
)


class GeneratedSecretError(ValueError):
    """Generated output would carry a secret-shaped literal -- refused."""


def scan_text(text: str) -> tuple[str, ...]:
    """Return the labels of every secret-shaped pattern found (values never
    echoed). An empty tuple means the text is safe to emit."""
    return tuple(label for label, pattern in SECRET_PATTERNS if pattern.search(text))


def refuse_if_secret_shaped(text: str, *, context: str) -> str:
    """Pass ``text`` through unchanged, or raise naming the matched patterns.

    The single chokepoint every pbi-mcp writer calls before emitting anything
    (stdout or file). ``context`` names the artifact being refused.
    """
    findings = scan_text(text)
    if findings:
        raise GeneratedSecretError(
            f"{context}: refused -- generated output matches secret-shaped "
            f"pattern(s): {', '.join(findings)} (values not shown)"
        )
    return text
