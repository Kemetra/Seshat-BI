"""Agent-facing next-action document (Seshat Agent-Driven v0.1).

``retail next --format agent`` / repo-level ``retail next --format json`` answer
the guarded-agent questions in ONE stable document: what stage is this project
in, what evidence exists, what is blocked, what is the next allowed action, what
is forbidden, and where must the agent stop.

This module is a COMPOSITION, not a second source of truth:

  - the per-table decision (next action / blocked / approval required /
    terminal pass / input defect) is ``retail.run_next.build_run_next_response``
    (spec 080), reused verbatim;
  - the recorded evidence/status projection is
    ``retail.status_surface.build_status_projection`` (spec 109), reused
    verbatim;
  - the gate ordering is the seven-stage spine already fixed in
    ``run_next._STAGE_ORDER``.

Contract (same posture as both parents): read-only -- no writes, no DB, no
network; deterministic -- same committed state, byte-identical document; never
a numeric readiness value -- only the four categorical statuses plus named
evidence/blocker strings (hard rule #9, Principle V). When evidence is missing
the document degrades to the conservative evidence-first action (start at
Source Ready), never a fabricated stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from retail.run_next import (
    _STAGE_ORDER,
    build_run_next_response,
)
from retail.status_surface import build_status_projection

_STAGE_TITLES: dict[str, str] = {
    "source_ready": "Source Ready (Stage 1)",
    "mapping_ready": "Mapping Ready (Stage 2)",
    "silver_ready": "Silver Ready (Stage 3)",
    "gold_ready": "Gold Ready (Stage 4)",
    "semantic_model_ready": "Semantic Model Ready (Stage 5)",
    "dashboard_ready": "Dashboard Ready (Stage 6)",
    "publish_ready": "Publish Ready (Stage 7)",
}

# One sentence per gate, in spine order: work forbidden until that gate passes.
_GATE_RULES: tuple[tuple[str, str], ...] = (
    (
        "mapping_ready",
        "No silver work (no silver.* SQL) before Mapping Ready passes.",
    ),
    (
        "silver_ready",
        "No gold work (no gold star/mart SQL) before Silver Ready passes.",
    ),
    (
        "gold_ready",
        "No semantic-model work before Gold Ready (live-validated) passes.",
    ),
    (
        "semantic_model_ready",
        "No dashboard work before Semantic Model Ready "
        "(approved metric contracts) passes.",
    ),
    (
        "dashboard_ready",
        "No publish/handoff work before Dashboard Ready passes.",
    ),
    (
        "publish_ready",
        "No live publish before Publish Ready passes; publish execution is "
        "the deferred F016 adapter.",
    ),
)

# Invariants that hold at every stage, including terminal pass.
_ALWAYS_FORBIDDEN: tuple[str, ...] = (
    "Never self-grant an approval; approvals are named-human actions.",
    "Never fabricate readiness; readiness is status + evidence + blockers, "
    "never a number.",
    "Never run the Power BI execution adapter (F016) from this surface.",
)

_BASE_VALIDATION_COMMANDS: tuple[str, ...] = (
    "python -m retail.cli check --repo .",
    "python -m retail.cli status --repo . --format json",
    "python -m retail.cli next --repo . --format json",
)

_VALIDATION_EXTRAS_BY_STAGE: dict[str, tuple[str, ...]] = {
    "gold_ready": (
        "python -m retail.cli validate --source-map "
        "mappings/<table>/source-map.yaml  # needs the db extra + a DSN; "
        "without them, report the deferred state -- never fake a pass",
    ),
    "semantic_model_ready": ("python -m retail.cli semantic-check --repo .",),
}

_STOP_POINT_BY_STAGE: dict[str, str] = {
    "source_ready": (
        "Stop once the read-only source profile and readiness-status.yaml are "
        "recorded; mapping review is a human gate."
    ),
    "mapping_ready": (
        "Stop at the mapping gate: source-map.yaml must be reviewed and "
        "approved by a named human before any silver SQL."
    ),
    "silver_ready": (
        "Stop after authoring the silver migration SQL; do not execute it and "
        "do not begin gold work before Silver Ready passes."
    ),
    "gold_ready": (
        "Stop after authoring the gold SQL and preparing live-validate "
        "evidence; Gold Ready passes only on live validation."
    ),
    "semantic_model_ready": (
        "Stop at the metric-contract gate: the metric owner approves the "
        "contracts before any dashboard work."
    ),
    "dashboard_ready": (
        "Stop at the design-review gate: governance approves the dashboard "
        "design before publish preparation."
    ),
    "publish_ready": (
        "Stop before any publish: assemble the handoff pack only; live "
        "publish is the deferred F016 execution adapter."
    ),
}

_TERMINAL_STOP_POINT = (
    "All seven stages pass. Live publish stays with the deferred F016 "
    "execution adapter; nothing further from this surface."
)

_FRESH_NEXT_ACTION = (
    "No readiness evidence found under mappings/. Begin at Source Ready: "
    "onboard one table with a read-only source profile and record "
    "mappings/<table>/readiness-status.yaml before any warehouse or "
    "dashboard work."
)


def _stage_index(stage: str | None) -> int:
    """Spine position for ranking; terminal (``None``) sorts last."""
    if stage is None:
        return len(_STAGE_ORDER)
    return _STAGE_ORDER.index(stage)


def _forbidden_scope(stage: str | None, outcome: str) -> list[str]:
    """Every gate at or after the current stage is still closed; the
    invariants hold always. Deterministic given (stage, outcome)."""
    if outcome == "terminal_pass" or stage is None:
        gates: list[str] = []
    else:
        current = _stage_index(stage)
        gates = [
            sentence
            for gate_stage, sentence in _GATE_RULES
            if _stage_index(gate_stage) >= current
        ]
    return gates + list(_ALWAYS_FORBIDDEN)


def _validation_commands(stage: str | None) -> list[str]:
    commands = list(_BASE_VALIDATION_COMMANDS)
    commands.extend(_VALIDATION_EXTRAS_BY_STAGE.get(stage or "", ()))
    return commands


def _stop_point(response: dict[str, Any]) -> str:
    outcome = response["outcome"]
    stage = response["stage"]
    if outcome == "terminal_pass":
        return _TERMINAL_STOP_POINT
    if outcome == "stop_blocked":
        return (
            "Stopped now: resolve or escalate the recorded blocking_reasons; "
            "do not work around the block."
        )
    if outcome == "approval_required":
        authority = response.get("required_authority") or "named human"
        return (
            f"Stopped now: a named-human approval ({authority}) for stage "
            f"{stage!r} is required before any further stage work."
        )
    if outcome == "input_defect":
        return (
            "Stopped now: repair the malformed readiness-status.yaml before "
            "any pipeline work."
        )
    return _STOP_POINT_BY_STAGE.get(stage or "", _STOP_POINT_BY_STAGE["source_ready"])


def _next_allowed_action(response: dict[str, Any]) -> str:
    outcome = response["outcome"]
    stage = response["stage"]
    if outcome == "next_action":
        return str(response.get("action_text") or "")
    if outcome == "stop_blocked":
        return (
            f"STOP -- stage {stage!r} is blocked; resolve the recorded "
            "blocking_reasons before any other pipeline work."
        )
    if outcome == "approval_required":
        authority = response.get("required_authority") or "named human"
        return (
            f"STOP -- obtain the named-human approval ({authority}) for "
            f"stage {stage!r}; never self-grant it."
        )
    if outcome == "terminal_pass":
        return "No pipeline action: all seven readiness stages pass for this table."
    return (
        "Repair the readiness-status.yaml input defect before any pipeline work."
    )


def _readiness_state(
    response: dict[str, Any], entry: dict[str, Any] | None
) -> str | None:
    """The RECORDED four-status of the current stage, read from the same
    committed projection -- never derived. ``input_defect`` has no honest
    state, so it projects as ``None``."""
    outcome = response["outcome"]
    if outcome == "terminal_pass":
        return "pass"
    if outcome == "input_defect":
        return None
    stage = response["stage"]
    if entry is not None and stage is not None:
        block = entry.get("stages", {}).get(stage)
        if isinstance(block, dict) and isinstance(block.get("status"), str):
            return block["status"]
    # No readiness file (or stage block unreadable): the conservative,
    # non-fabricated state is the journey's start.
    return "blocked" if outcome == "stop_blocked" else "not_started"


def _evidence(entry: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Every recorded stage, verbatim from the committed projection, in spine
    order -- items are the readiness file's own evidence strings."""
    if entry is None:
        return []
    stages = entry.get("stages", {})
    return [
        {
            "stage": name,
            "status": stages[name]["status"],
            "items": list(stages[name]["evidence"]),
        }
        for name in _STAGE_ORDER
        if name in stages
    ]


def _summaries(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict]:
    return [
        {
            "table": response["table"],
            "source_path": entry["source_path"],
            "outcome": response["outcome"],
            "stage": response["stage"],
        }
        for entry, response in pairs
    ]


def _rank(response: dict[str, Any]) -> int:
    """Focus ranking: a malformed file is the most urgent, then the earliest
    incomplete stage; a fully-passed table sorts last."""
    if response["outcome"] == "input_defect":
        return -1
    return _stage_index(response["stage"])


def _compose(
    response: dict[str, Any],
    entry: dict[str, Any] | None,
    summaries: list[dict],
) -> dict[str, Any]:
    stage = response["stage"]
    outcome = response["outcome"]
    return {
        "current_stage": stage,
        "readiness_state": _readiness_state(response, entry),
        "evidence": _evidence(entry),
        "blocking_reasons": list(response.get("blocking_reasons", [])),
        "next_allowed_action": _next_allowed_action(response),
        "forbidden_scope": _forbidden_scope(stage, outcome),
        "validation_commands": _validation_commands(stage),
        "stop_point": _stop_point(response),
        "table": response["table"],
        "outcome": outcome,
        "required_authority": response.get("required_authority"),
        "caveats": list(response.get("caveats", [])),
        "tables": summaries,
        "read_only_proof": True,
    }


def _fresh_repo_document() -> dict[str, Any]:
    """No committed readiness evidence at all: the conservative,
    evidence-first answer -- never a fabricated stage or state."""
    return {
        "current_stage": "source_ready",
        "readiness_state": "not_started",
        "evidence": [],
        "blocking_reasons": [],
        "next_allowed_action": _FRESH_NEXT_ACTION,
        "forbidden_scope": _forbidden_scope("source_ready", "next_action"),
        "validation_commands": _validation_commands("source_ready"),
        "stop_point": _STOP_POINT_BY_STAGE["source_ready"],
        "table": None,
        "outcome": "next_action",
        "required_authority": None,
        "caveats": [],
        "tables": [],
        "read_only_proof": True,
    }


def _entry_for(
    entries: list[dict[str, Any]], response: dict[str, Any]
) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("table") == response.get("table"):
            return entry
    return None


def build_agent_next_document(
    repo_root: Path | str, table: str | None = None
) -> dict[str, Any]:
    """Build the agent-facing next-action document for ``repo_root``.

    With ``table``, the document focuses that table (missing file degrades to
    the conservative Source Ready start, exactly as ``build_run_next_response``
    does). Without it, the focus is the table with the most urgent run-next
    outcome (ties broken by source path, so the answer is deterministic); an
    empty repo produces the conservative evidence-first document. Read-only in
    every path.
    """
    root = Path(repo_root)
    projection = build_status_projection(root)
    entries: list[dict[str, Any]] = projection["tables"]

    if table is not None:
        response = build_run_next_response(root, table)
        pairs = [(e, build_run_next_response(root, e["table"])) for e in entries]
        return _compose(response, _entry_for(entries, response), _summaries(pairs))

    if not entries:
        return _fresh_repo_document()

    pairs = [(e, build_run_next_response(root, e["table"])) for e in entries]
    focus_entry, focus_response = min(
        pairs, key=lambda pair: (_rank(pair[1]), pair[0]["source_path"])
    )
    return _compose(focus_response, focus_entry, _summaries(pairs))
