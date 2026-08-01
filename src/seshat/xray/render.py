"""Render X-Ray audit and diff results: JSON payloads + ASCII text.

Pure functions -- the CLI command module owns printing and JSON dumping.
No numeric score exists in any payload (hard principle); summaries are
per-family COUNTS only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .audit import XrayFinding
from .diff import ModelChange

_FAMILIES = ("X0", "X1", "X2", "X3", "X4")
_BUCKETS = ("semantic", "cosmetic", "additive", "removed")


def audit_payload(
    findings: Iterable[XrayFinding],
    *,
    model: str,
    report_scanned: bool,
    blockers: tuple[Mapping[str, str], ...] = (),
) -> dict[str, object]:
    items = list(findings)
    return {
        "outcome": "blocked" if blockers else "completed",
        "model": model,
        "report_scanned": report_scanned,
        "findings": [
            {
                "finding_id": f.finding_id,
                "severity": f.severity,
                "message": f.message,
                "locator": f.locator,
                "fix_hint": f.fix_hint,
            }
            for f in items
        ],
        "summary": {
            fam: sum(1 for f in items if f.finding_id == fam) for fam in _FAMILIES
        },
        "blockers": [dict(b) for b in blockers],
    }


def diff_payload(
    changes: Iterable[ModelChange],
    *,
    base: str,
    blockers: tuple[Mapping[str, str], ...] = (),
) -> dict[str, object]:
    items = list(changes)
    return {
        "outcome": "blocked" if blockers else "completed",
        "base": base,
        "changes": [
            {
                "bucket": c.bucket,
                "kind": c.kind,
                "subject": c.subject,
                "sentence": c.sentence,
            }
            for c in items
        ],
        "summary": {b: sum(1 for c in items if c.bucket == b) for b in _BUCKETS},
        "blockers": [dict(b) for b in blockers],
    }


def render_text_audit(payload: Mapping[str, object]) -> str:
    lines = [f"X-Ray: {payload['model']} -- {payload['outcome']}"]
    if not payload["report_scanned"]:
        lines.append("note: no report scanned -- visual usage unknown")
    for f in payload["findings"]:  # type: ignore[union-attr]
        lines.append(
            f"[{f['severity']}] {f['finding_id']} {f['locator']}: {f['message']}"
        )
        lines.append(f"    fix: {f['fix_hint']}")
    summary = payload["summary"]
    lines.append(
        "summary: " + " ".join(f"{k}={summary[k]}" for k in _FAMILIES)  # type: ignore[index]
    )
    return "\n".join(lines)


def render_text_diff(payload: Mapping[str, object]) -> str:
    lines = [f"Model diff vs {payload['base']} -- {payload['outcome']}"]
    for c in payload["changes"]:  # type: ignore[union-attr]
        lines.append(f"[{c['bucket']}] {c['kind']} {c['subject']}: {c['sentence']}")
    summary = payload["summary"]
    lines.append(
        "summary: " + " ".join(f"{k}={summary[k]}" for k in _BUCKETS)  # type: ignore[index]
    )
    return "\n".join(lines)
