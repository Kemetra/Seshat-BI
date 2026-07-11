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

from ..core import Finding, RuleContext, Severity, is_test_path
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


@register("G6", "No real host/value in committed PBIP parameters")
def check_pbip_param_no_real_value(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_param_files(ctx):
        text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        for lineno, line in enumerate(text.splitlines(), start=1):
            m = _PARAM_RE.search(line)
            if not m:
                continue
            # Only connection PARAMETERS, not every shared M expression.
            if "isparameterquery=true" not in m.group("meta").lower().replace(" ", ""):
                continue
            value = m.group("value")
            if _PLACEHOLDER_RE.search(value):
                continue  # placeholder form -> safe
            findings.append(
                Finding(
                    rule_id="G6",
                    severity=Severity.ERROR,
                    message=(
                        f"PBIP parameter {m.group('name')!r} has a real value "
                        f"({value!r}); a committed parameter must be the "
                        f"<placeholder> form -- real host/db are supplied at "
                        f"refresh (Desktop/gateway), never committed"
                    ),
                    locator=f"{rel}:{lineno}",
                )
            )
    return findings
