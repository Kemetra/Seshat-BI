"""Agent-facing next-action document (Seshat Agent-Driven v0.1).

``retail next --format agent`` / repo-level ``retail next --format json`` answer
the guarded-agent questions in ONE stable document: what stage is this project
in, what evidence exists, what is blocked, what is the next allowed action, what
is forbidden, and where must the agent stop.

This module is a COMPOSITION, not a second source of truth:

  - the per-table decision (next action / blocked / approval required /
    terminal pass / input defect) is ``seshat.run_next.build_run_next_response``
    (spec 080), reused verbatim;
  - the recorded evidence/status projection is
    ``seshat.status_surface.build_status_projection`` (spec 109), reused
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

from seshat.run_next import (
    _STAGE_ORDER,
    build_run_next_response,
)
from seshat.status_surface import build_status_projection

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
    "python -m seshat.cli check --repo .",
    "python -m seshat.cli status --repo . --format json",
    "python -m seshat.cli next --repo . --format json",
)

_VALIDATION_EXTRAS_BY_STAGE: dict[str, tuple[str, ...]] = {
    "gold_ready": (
        "python -m seshat.cli validate --source-map "
        "mappings/<table>/source-map.yaml  # needs the db extra + a DSN; "
        "without them, report the deferred state -- never fake a pass",
    ),
    "semantic_model_ready": ("python -m seshat.cli semantic-check --repo .",),
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
    "run `seshat scaffold-source <table>` to write the blank source profile "
    "and readiness-status.yaml, then fill the source profile and record "
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
    return "Repair the readiness-status.yaml input defect before any pipeline work."


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


def _summaries(
    triples: list[tuple[dict[str, Any] | None, dict[str, Any], str]],
) -> list[dict]:
    return [
        {
            "table": response["table"],
            "source_path": source_path,
            "outcome": response["outcome"],
            "stage": response["stage"],
        }
        for _entry, response, source_path in triples
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


def _dir_name(source_path: str) -> str:
    """The ``mappings/<dir>/`` directory name -- the identity
    ``build_run_next_response`` always resolves via its direct candidate path,
    even when the file records no string ``table`` field."""
    return source_path.rsplit("/", 2)[-2]


def _unprojected_status_paths(root: Path, entries: list[dict[str, Any]]) -> list[str]:
    """Committed readiness-status files the best-effort projection SKIPPED
    (unreadable / unparseable / non-mapping). They must still surface -- as
    ``input_defect``, never as an absent table -- or a broken committed file
    would silently read as a fresh journey."""
    projected = {entry["source_path"] for entry in entries}
    mappings_dir = root / "mappings"
    if not mappings_dir.is_dir():
        return []
    return [
        path.relative_to(root).as_posix()
        for path in sorted(mappings_dir.glob("*/readiness-status.yaml"))
        if path.relative_to(root).as_posix() not in projected
    ]


def _all_triples(
    root: Path, entries: list[dict[str, Any]]
) -> list[tuple[dict[str, Any] | None, dict[str, Any], str]]:
    """One ``(projection entry, run-next response, source path)`` triple per
    committed readiness-status file, including files the projection skipped
    (entry ``None``; their run-next outcome is ``input_defect``)."""
    triples: list[tuple[dict[str, Any] | None, dict[str, Any], str]] = [
        (
            entry,
            build_run_next_response(root, _dir_name(entry["source_path"])),
            entry["source_path"],
        )
        for entry in entries
    ]
    for source_path in _unprojected_status_paths(root, entries):
        triples.append(
            (
                None,
                build_run_next_response(root, _dir_name(source_path)),
                source_path,
            )
        )
    return triples


def _resolved_source_path(root: Path, table: str) -> str | None:
    """The repo-relative path of the readiness file run-next itself resolves
    for ``table`` (its ``_find_status_data`` matches dir name / recorded
    table / source_id -- reused, not re-derived)."""
    from seshat.run_next import _find_status_data

    status_path, _data, _error = _find_status_data(root, table)
    if status_path is None:
        return None
    return status_path.relative_to(root).as_posix()


def _entry_by_source_path(
    entries: list[dict[str, Any]], source_path: str | None
) -> dict[str, Any] | None:
    if source_path is None:
        return None
    return next((e for e in entries if e["source_path"] == source_path), None)


def _entry_by_name(
    entries: list[dict[str, Any]], names: set[str | None]
) -> dict[str, Any] | None:
    return next(
        (e for e in entries if {e.get("table"), _dir_name(e["source_path"])} & names),
        None,
    )


def _entry_matching(
    root: Path,
    entries: list[dict[str, Any]],
    table: str,
    response: dict[str, Any],
) -> dict[str, Any] | None:
    """Find the projection entry behind a --table response: authoritatively by
    the source path of the file run-next resolved, else by name."""
    by_path = _entry_by_source_path(entries, _resolved_source_path(root, table))
    if by_path is not None:
        return by_path
    return _entry_by_name(entries, {response.get("table"), table})


def build_table_next_document(repo_root: Path | str, table: str) -> dict[str, Any]:
    """Single-table next-action document WITHOUT the portfolio summaries.

    Same composed shape as :func:`build_agent_next_document`, but it reads
    only this table's readiness file (one run-next response) instead of
    re-projecting every table -- O(1) file reads, which keeps portfolio-wide
    consumers (the shared readiness projection, spec 120) linear instead of
    quadratic. ``tables`` is empty and the entry-derived fields
    (``readiness_state``/``evidence``) degrade conservatively; callers that
    need those use the full document."""
    return _compose(build_run_next_response(Path(repo_root), table), None, [])


def build_agent_next_document(
    repo_root: Path | str, table: str | None = None
) -> dict[str, Any]:
    """Build the agent-facing next-action document for ``repo_root``.

    With ``table``, the document focuses that table (missing file degrades to
    the conservative Source Ready start, exactly as ``build_run_next_response``
    does). Without it, the focus is the table with the most urgent run-next
    outcome -- a malformed committed readiness file first, then the earliest
    incomplete stage (ties broken by source path, so the answer is
    deterministic); a repo with no readiness files at all produces the
    conservative evidence-first document. Read-only in every path.
    """
    root = Path(repo_root)
    projection = build_status_projection(root)
    entries: list[dict[str, Any]] = projection["tables"]
    triples = _all_triples(root, entries)

    if table is not None:
        response = build_run_next_response(root, table)
        entry = _entry_matching(root, entries, table, response)
        return _compose(response, entry, _summaries(triples))

    if not triples:
        return _fresh_repo_document()

    focus_entry, focus_response, _ = min(
        triples, key=lambda triple: (_rank(triple[1]), triple[2])
    )
    return _compose(focus_response, focus_entry, _summaries(triples))
