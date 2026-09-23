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

# The pattern table lives in the stdlib-only redaction leaf so the dbt and
# Dagster output surfaces scrub with exactly what this refusal scan detects.
from seshat.redaction_core import SECRET_PATTERNS  # noqa: E402

__all__ = [
    "SECRET_PATTERNS",
    "GeneratedSecretError",
    "refuse_if_secret_shaped",
    "scan_text",
]


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
