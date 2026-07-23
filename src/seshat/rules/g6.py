"""G6 -- no real host/value in committed PBIP connection parameters.

Power BI Desktop's "Edit Parameters -> save" bakes the REAL parameter values
(host, database) into the tracked ``expressions.tmdl`` every time. C2 already
flags a committed DigitalOcean endpoint, but the leak is host-agnostic: any real
value in a committed parameter is a leak. G6 fails closed on ANY non-placeholder
value in a PBIP M parameter (``IsParameterQuery=true``), so the recurring leak is
blocked at the gate for any host/provider.

Convention (docs/powerbi-connection.md): a committed parameter value MUST be the
``<placeholder>`` form (angle-bracketed). The real value is supplied at refresh by
Desktop/the gateway and lives only in machine-local state, never in git.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path, read_tracked_text
from ..registry import register

# A PBIP M parameter line:
#   expression <Name> = "<value>" meta [ ... IsParameterQuery=true ... ]
# Capture the parameter name and its quoted default value. Only lines whose meta
# marks IsParameterQuery=true are connection parameters G6 governs.
_PARAM_RE = re.compile(
    r'expression\s+(?P<name>\S+)\s*=\s*"(?P<value>[^"]*)"\s*meta\s*\[(?P<meta>[^\]]*)\]'
)

# A placeholder value is angle-bracketed: "<your-db-host>", "<your-database>:5432".
# Anything containing a "<...>" token is treated as a placeholder (the committed,
# safe form). A value with no angle-bracket token is a real value -> leak.
_PLACEHOLDER_RE = re.compile(r"<[^>]+>")


def _iter_param_files(ctx: RuleContext) -> list[str]:
    # Scan committed PBIP semantic-model expression files. Skip test fixtures
    # (they deliberately carry real-looking values to exercise G6), same exemption
    # as the other PBIP/TMDL file-scanning rules.
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(".SemanticModel/definition/expressions.tmdl")
        and not is_test_path(p)
    ]


def _g6_finding_for_line(rel: str, lineno: int, line: str) -> Finding | None:
    """The G6 finding for one line, or ``None`` when the line is safe.

    Flags only a connection PARAMETER (``IsParameterQuery=true``) whose value is
    NOT the ``<placeholder>`` form -- a real host/db committed into a parameter.
    """
    m = _PARAM_RE.search(line)
    if m is None:
        return None
    # Only connection PARAMETERS, not every shared M expression.
    if "isparameterquery=true" not in m.group("meta").lower().replace(" ", ""):
        return None
    value = m.group("value")
    if _PLACEHOLDER_RE.search(value):
        return None  # placeholder form -> safe
    return Finding(
        rule_id="G6",
        severity=Severity.ERROR,
        message=(
            f"PBIP parameter {m.group('name')!r} has a real value ({value!r}); "
            f"a committed parameter must be the <placeholder> form -- real "
            f"host/db are supplied at refresh (Desktop/gateway), never committed"
        ),
        locator=f"{rel}:{lineno}",
    )


def _g6_findings_for_text(rel: str, text: str) -> list[Finding]:
    """Every G6 finding in one parameter file's text (one per leaking line)."""
    return [
        finding
        for lineno, line in enumerate(text.splitlines(), start=1)
        if (finding := _g6_finding_for_line(rel, lineno, line)) is not None
    ]


@register("G6", "No real host/value in committed PBIP parameters")
def check_pbip_param_no_real_value(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_param_files(ctx):
        # A tracked-but-deleted-on-disk parameter file (#430) has no content to
        # scan for a leaked value; skip it rather than crash. This is a content
        # scan, not a presence check.
        text = read_tracked_text(ctx.repo_root / rel, encoding="utf-8-sig")
        if text is not None:
            findings.extend(_g6_findings_for_text(rel, text))
    return findings
