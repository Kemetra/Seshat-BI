"""Human and JSON scenario-matrix renderers (spec 120, US7, FR-040).

Both renderings are scenario-level and categorical. Neither computes an
aggregate score, percentage, rank, or winner -- an incomplete-disclosure run
renders as ``incomplete`` with the missing items, never as a result.
"""

from __future__ import annotations

from typing import Any

from .model import Observation
from .runner import missing_disclosure


def _comparison(entry: dict[str, Any]) -> str:
    observation = Observation(
        scenario_id=str(entry.get("scenario_id")),
        expected_behavior=str(entry.get("expected_behavior")),
        observed_behavior=str(entry.get("observed_behavior")),
    )
    return observation.comparison


def render_report_document(document: dict[str, Any]) -> dict[str, Any]:
    """The stable machine rendering: run disclosure + per-scenario rows."""
    missing = missing_disclosure(document)
    if missing:
        return {
            "schema_version": "1.0",
            "state": "incomplete",
            "missing_disclosure": missing,
            "rows": [],
        }
    rows = [
        {
            "scenario_id": entry.get("scenario_id"),
            "expected_behavior": entry.get("expected_behavior"),
            "observed_behavior": entry.get("observed_behavior"),
            "comparison": _comparison(entry),
            "evidence": entry.get("evidence", []),
            "variation_note": entry.get("variation_note"),
        }
        for entry in document["observations"]
    ]
    return {
        "schema_version": "1.0",
        "state": "rendered",
        "run_id": document.get("run_id"),
        "participant": document.get("participant"),
        "repetitions": document.get("repetitions"),
        "instructions_digest": document.get("instructions_digest"),
        "rows": rows,
    }


def render_report_text(document: dict[str, Any]) -> str:
    report = render_report_document(document)
    if report["state"] == "incomplete":
        lines = ["benchmark run: INCOMPLETE -- missing disclosure:"]
        lines += [f"  - {item}" for item in report["missing_disclosure"]]
        lines.append("An incomplete run is not a comparable result (FR-041).")
        return "\n".join(lines)
    participant = report["participant"]
    lines = [
        f"benchmark run: {report['run_id']}",
        f"participant: {participant.get('name')} ({participant.get('kind')})",
        f"repetitions: {report['repetitions']}",
        "",
    ]
    for row in report["rows"]:
        lines.append(
            f"[{row['comparison']}] {row['scenario_id']}: "
            f"expected {row['expected_behavior']}, "
            f"observed {row['observed_behavior']}"
        )
        for evidence in row["evidence"]:
            lines.append(f"    evidence: {evidence}")
        if row["variation_note"]:
            lines.append(f"    variation: {row['variation_note']}")
    lines.append("")
    lines.append(
        "Categorical scenario outcomes only; no aggregate score, rank, or winner."
    )
    return "\n".join(lines)
