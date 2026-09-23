"""Second-layer scrub of finding text before it leaves the process.

Rules are expected never to echo a secret into a ``Finding`` (C1 and G6 redact
at source). This is the defence-in-depth layer for the surfaces that ship
finding text to a third party -- SARIF uploads and the governor MCP response --
so one rule that forgets the discipline does not leak through them.

It reuses the shipped ``SECRET_PATTERNS`` table (stdlib-only) so the shapes it
replaces cannot drift from what the pbi-mcp refusing chokepoint detects.
"""

from __future__ import annotations

from dataclasses import replace

from .core import Finding
from .pbi_mcp.scan import SECRET_PATTERNS

REDACTED = "<redacted>"


def _secret_spans(text: str) -> list[tuple[int, int]]:
    """Merged ``(start, end)`` spans matched by ANY pattern on the original text.

    Matching every pattern against the ORIGINAL text (rather than substituting
    pattern by pattern) matters: once a narrower pattern has replaced a URI's
    userinfo, the wider whole-URI pattern no longer sees a scheme and the host
    tail would survive. Taking the union of spans redacts the widest match.
    """
    spans = sorted(
        m.span() for _label, pattern in SECRET_PATTERNS for m in pattern.finditer(text)
    )
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def scrub_text(text: str) -> str:
    """``text`` with every secret-shaped span replaced by ``<redacted>``."""
    out: list[str] = []
    cursor = 0
    for start, end in _secret_spans(text):
        out.append(text[cursor:start] + REDACTED)
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def scrub_finding(finding: Finding) -> Finding:
    """A copy of ``finding`` whose message and locator are scrubbed."""
    message, locator = scrub_text(finding.message), scrub_text(finding.locator)
    if message == finding.message and locator == finding.locator:
        return finding
    return replace(finding, message=message, locator=locator)
