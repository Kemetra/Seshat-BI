"""Fabrication detector for dashboard pattern docs (spec 123, US3, FR-013).

A small, test-only scanner -- NOT a `retail check` rule, NOT shipped in
`src/seshat/` -- used by ``test_dashboard_patterns.py`` to prove that
``docs/patterns/dashboard/*.md`` stays GENERIC guidance and never fabricates a
concrete metric.

Detects two mechanically-catchable fabrication modes:

1. **DAX/formula syntax** -- a metric DEFINITION never belongs in a pattern
   doc (FR-013/FR-038: patterns own reusable guidance, metric contracts own
   metric meaning). Catches ``:=`` DAX assignment, a bare ``NAME = ...``
   formula line, and common DAX function calls (``SUM(``, ``CALCULATE(``,
   ``DIVIDE(``, ``AVERAGE(``, ``SUMX(``) plus a ``[Table]``/``[Column]``
   bracket reference.
2. **A concrete, named retail KPI** -- a representative denylist drawn from
   this repo's own `skills/retail-kpi-knowledge` vocabulary. There is no
   general algorithm for "this string names a specific metric"; the denylist
   targets the concrete fabrication mode this repo actually has (a named KPI
   standing in for a role), not a hypothetical universal detector.
"""

from __future__ import annotations

import re

_DAX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r":="),
    re.compile(r"\bSUM\s*\("),
    re.compile(r"\bCALCULATE\s*\("),
    re.compile(r"\bDIVIDE\s*\("),
    re.compile(r"\bAVERAGE\s*\("),
    re.compile(r"\bSUMX\s*\("),
    re.compile(r"\[[A-Za-z_][A-Za-z0-9_ ]*\]\s*\[[A-Za-z_][A-Za-z0-9_ ]*\]"),
)

# A named KPI standing in for a metric ROLE is the fabrication FR-013 forbids.
# Representative denylist (this repo's skills/retail-kpi-knowledge vocabulary),
# not an exhaustive universal list.
_NAMED_KPI_DENYLIST: tuple[str, ...] = (
    "net sales",
    "gross margin",
    "gmroi",
    "sell-through",
    "sell through",
    "days of supply",
    "days on hand",
    "average order value",
    "aov",
    "basket size",
    "same-store sales",
    "same store sales",
    "conversion rate",
    "inventory turnover",
)


def _dax_token_findings(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in _DAX_PATTERNS:
        m = pattern.search(text)
        if m:
            findings.append(f"DAX/formula token detected: {m.group(0)!r}")
    return findings


def _is_formula_assignment(stripped: str) -> bool:
    """A bare "<Name> = <expr>" assignment line (not "==", not YAML "key: value")."""
    return (
        "=" in stripped
        and "==" not in stripped
        and not stripped.startswith("#")
        and re.match(r"^[A-Za-z][A-Za-z0-9 _%]*\s=\s.+", stripped) is not None
    )


def _formula_assignment_findings(text: str) -> list[str]:
    return [
        f"formula-assignment line detected: {line.strip()!r}"
        for line in text.splitlines()
        if _is_formula_assignment(line.strip())
    ]


def _dax_findings(text: str) -> list[str]:
    return _dax_token_findings(text) + _formula_assignment_findings(text)


def _named_kpi_findings(text: str) -> list[str]:
    lowered = text.lower()
    return [
        f"named KPI '{kpi}' detected (role-level guidance only, FR-013)"
        for kpi in _NAMED_KPI_DENYLIST
        if kpi in lowered
    ]


def find_fabrications(text: str) -> list[str]:
    """Return every fabrication finding in ``text`` (empty == clean)."""
    return _dax_findings(text) + _named_kpi_findings(text)
