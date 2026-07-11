"""`retail next` handler: run-next readiness surface + agent document.

Two read-only surfaces share this verb:

  - with ``--table`` and ``--format text|json``: the original per-table
    run-next response (spec 080), unchanged;
  - with ``--format agent``, or without ``--table``: the agent-facing
    next-action document (``retail.agent_next``) -- stable keys
    ``current_stage`` / ``readiness_state`` / ``evidence`` /
    ``blocking_reasons`` / ``next_allowed_action`` / ``forbidden_scope`` /
    ``validation_commands`` / ``stop_point``.
"""

from __future__ import annotations

import argparse
import json


def _render_text(response: dict) -> str:
    lines = [
        f"table: {response['table']}",
        f"outcome: {response['outcome']}",
        f"stage: {response['stage']}",
    ]
    if response.get("action_text"):
        lines.append(f"action: {response['action_text']}")
    for reason in response.get("blocking_reasons", []):
        lines.append(f"blocking_reason: {reason}")
    if response.get("required_authority"):
        lines.append(f"required_authority: {response['required_authority']}")
    for caveat in response.get("caveats", []):
        lines.append(f"caveat: {caveat.get('kind')}: {caveat.get('detail')}")
    lines.append("read_only_proof: true")
    return "\n".join(lines)


def _agent_list_lines(label: str, items: list) -> list[str]:
    lines = [f"{label}:"]
    if not items:
        lines.append("  (none)")
    for item in items:
        lines.append(f"  - {item}")
    return lines


def _agent_evidence_lines(evidence: list[dict]) -> list[str]:
    lines = ["evidence:"]
    if not evidence:
        lines.append("  (none recorded)")
    for stage in evidence:
        lines.append(f"  {stage['stage']}: {stage['status']}")
        for item in stage["items"]:
            lines.append(f"    - {item}")
    return lines


def _render_agent_text(document: dict) -> str:
    """Deterministic line-oriented rendering of the agent document -- the same
    facts as ``--format json``, ordered for an agent reading top to bottom."""
    lines = [
        "SESHAT NEXT -- guarded next-action surface (read-only)",
        f"table: {document['table']}",
        f"current_stage: {document['current_stage']}",
        f"readiness_state: {document['readiness_state']}",
        f"outcome: {document['outcome']}",
    ]
    lines += _agent_evidence_lines(document["evidence"])
    lines += _agent_list_lines("blocking_reasons", document["blocking_reasons"])
    lines.append(f"next_allowed_action: {document['next_allowed_action']}")
    lines += _agent_list_lines("forbidden_scope", document["forbidden_scope"])
    lines += _agent_list_lines("validation_commands", document["validation_commands"])
    lines.append(f"stop_point: {document['stop_point']}")
    for caveat in document.get("caveats", []):
        lines.append(f"caveat: {caveat.get('kind')}: {caveat.get('detail')}")
    for entry in document.get("tables", []):
        lines.append(
            f"tables: {entry['table']} outcome={entry['outcome']} "
            f"stage={entry['stage']}"
        )
    lines.append("read_only_proof: true")
    return "\n".join(lines)


def next_main(args: argparse.Namespace) -> int:
    from retail.run_next import build_run_next_response

    output_format = getattr(args, "output_format", "text")
    table = getattr(args, "table", None)

    if output_format == "agent" or table is None:
        from retail.agent_next import build_agent_next_document

        document = build_agent_next_document(args.repo, table)
        if output_format == "json":
            print(json.dumps(document, indent=2))
        else:
            print(_render_agent_text(document))
        return 0

    response = build_run_next_response(args.repo, table)
    if output_format == "json":
        print(json.dumps(response, indent=2))
    else:
        print(_render_text(response))
    return 0
