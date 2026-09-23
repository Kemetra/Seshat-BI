"""`retail next` handler: run-next readiness surface + agent document.

Two read-only surfaces share this verb:

  - with ``--table`` and ``--format text|json``: the original per-table
    run-next response (spec 080), unchanged;
  - with ``--format agent``, or without ``--table``: the agent-facing
    next-action document (``seshat.agent_next``) -- stable keys
    ``current_stage`` / ``readiness_state`` / ``evidence`` /
    ``blocking_reasons`` / ``next_allowed_action`` / ``forbidden_scope`` /
    ``validation_commands`` / ``stop_point``, plus the two informational
    guidance keys ``source_map_shape_signpost`` (issue #488) and
    ``orchestration_checkpoint`` (issue #489).

The two guidance keys are rendered AFTER ``stop_point`` and are explicitly
labelled informational: they never gate, so they must never read like the
next allowed action or a blocking reason.
"""

from __future__ import annotations

import argparse
import json

from seshat.cli.commands.next_guidance_render import guidance_lines


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
    lines += guidance_lines(document)
    for caveat in document.get("caveats", []):
        lines.append(f"caveat: {caveat.get('kind')}: {caveat.get('detail')}")
    for entry in document.get("tables", []):
        lines.append(
            f"tables: {entry['table']} outcome={entry['outcome']} "
            f"stage={entry['stage']}"
        )
    lines.append("read_only_proof: true")
    return "\n".join(lines)


#: ``--exit-code`` mapping (audit F153). Opt-in: the default stays exit 0.
_EXIT_BY_OUTCOME: dict[str, int] = {
    "next_action": 0,
    "terminal_pass": 0,
    "stop_blocked": 3,
    "approval_required": 3,
    "input_defect": 2,
}
_EXIT_STOP = 3


def _exit_status(args: argparse.Namespace, outcome: object, *, stopped: bool) -> int:
    """0 unless ``--exit-code``; then STOP -> 3, input defect -> 2.

    ``stopped`` carries the document's own STOP signal: a live-validation STOP
    is phrased while ``outcome`` stays ``next_action``/``terminal_pass``, so the
    outcome alone would let it exit 0. An unknown outcome never exits 0.
    """
    if not getattr(args, "exit_code", False):
        return 0
    code = _EXIT_BY_OUTCOME.get(str(outcome), _EXIT_STOP)
    return _EXIT_STOP if code == 0 and stopped else code


def _document_stopped(document: dict) -> bool:
    return document.get("readiness_state") == "blocked" or str(
        document.get("next_allowed_action") or ""
    ).startswith("STOP")


def next_main(args: argparse.Namespace) -> int:
    from seshat.run_next import build_run_next_response

    output_format = getattr(args, "output_format", "text")
    table = getattr(args, "table", None)

    if output_format == "agent" or table is None:
        from seshat.agent_next import build_agent_next_document

        document = build_agent_next_document(args.repo, table)
        if output_format == "json":
            print(json.dumps(document, indent=2))
        else:
            print(_render_agent_text(document))
        return _exit_status(
            args, document.get("outcome"), stopped=_document_stopped(document)
        )

    response = build_run_next_response(args.repo, table)
    if output_format == "json":
        print(json.dumps(response, indent=2))
    else:
        print(_render_text(response))
    stopped = str(response.get("action_text") or "").startswith("STOP")
    return _exit_status(args, response.get("outcome"), stopped=stopped)
