"""Human-readable rendering and exit-code policy for adoption results.

Rendering never collects a second data view: it reads only the normalized
assessment or scaffold result it is handed.
"""

from __future__ import annotations

from typing import Any


def _fact_lines(facts: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for fact in facts:
        locator = f" ({fact['artifact']})" if fact["artifact"] else ""
        lines.append(
            f"- [{fact['classification']}] {fact['subject']}: {fact['detail']}{locator}"
        )
    return lines


def _governance_lines(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return []
    lines = ["Governance findings:"]
    for finding in findings:
        lines.append(
            f"- [{finding['severity']}] {finding['rule_id']}: "
            f"{finding['message']} ({finding['locator']})"
        )
    return lines


def render_assessment_text(assessment: dict[str, Any]) -> str:
    """Render the normalized assessment without collecting a second data view."""
    lines = [
        f"PBIP adoption assessment: {assessment['target']['label']}",
        f"Coverage: {assessment['coverage']['status']}",
        "Facts:",
    ]
    lines.extend(_fact_lines(assessment["facts"]))
    lines.extend(_governance_lines(assessment["governance_findings"]))
    next_step = assessment["next_step"]
    lines.extend(["Next step:", f"- {next_step['action']}"])
    lines.extend(f"- blocker: {reason}" for reason in next_step["blocking_reasons"])
    lines.append(f"Assessment digest: {assessment['assessment_digest']}")
    return "\n".join(lines) + "\n"


def render_scaffold_result_text(result: dict[str, Any]) -> str:
    lines = [
        f"PBIP adoption scaffold: {result['outcome']}",
        f"Assessment digest: {result['assessment_digest'] or 'unavailable'}",
    ]
    lines.extend(f"Written: {path}" for path in result["written"])
    lines.extend(f"Blocker: {reason}" for reason in result["blocking_reasons"])
    lines.append(f"Next step: {result['next_step']['action']}")
    return "\n".join(lines) + "\n"


def assessment_exit_code(assessment: dict[str, Any]) -> int:
    if (
        assessment["next_step"]["kind"] == "terminal_stop"
        or assessment["next_step"]["blocking_reasons"]
    ):
        return 1
    return (
        1
        if any(fact["classification"] == "blocked" for fact in assessment["facts"])
        else 0
    )


def scaffold_exit_code(result: dict[str, Any]) -> int:
    return (
        0
        if result["outcome"] == "written"
        else 2
        if result["outcome"] == "input_defect"
        else 1
    )
