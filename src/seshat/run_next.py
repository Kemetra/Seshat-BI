"""Read-only run-next readiness surface (spec 080).

This module answers one question for one table: what is the single next allowed
readiness action, or why is the table stopped? It reads only
``mappings/<table>/readiness-status.yaml`` state, writes nothing, opens no DB
connection, and never grants an approval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_STAGE_ORDER: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
_STATUS_VALUES: frozenset[str] = frozenset(
    {"not_started", "blocked", "warning", "pass"}
)
_APPROVAL_REQUIRED: frozenset[str] = frozenset(
    {"mapping_ready", "semantic_model_ready", "dashboard_ready", "publish_ready"}
)
_FILE_SOURCE_KINDS: frozenset[str] = frozenset({"csv", "tsv", "excel"})

_AUTHORITY_BY_STAGE: dict[str, str] = {
    "source_ready": "data_owner",
    "mapping_ready": "analyst",
    "semantic_model_ready": "metric_owner",
    "dashboard_ready": "governance",
    "publish_ready": "data_owner",
}

# The action shown when NO readiness file exists at all -- an unstarted journey.
# Kept distinct from the source_ready action below: emitting "No readiness file
# found" for a file that IS present is inaccurate (#374).
_NO_STATUS_FILE_ACTION = "No readiness file found; start onboarding at Source Ready."

_ACTION_BY_STAGE: dict[str, str] = {
    "source_ready": (
        "Begin Source Ready (Stage 1) -- fill the read-only source profile, then "
        "submit the mapping for review."
    ),
    "mapping_ready": "Begin Mapping Ready (Stage 2) -- the source-mapping gate.",
    "silver_ready": (
        "Begin Silver Ready (Stage 3) -- author the silver migration strictly "
        "from the approved source map."
    ),
    "gold_ready": (
        "Begin Gold Ready (Stage 4) -- author the gold star and prepare live "
        "retail validate evidence."
    ),
    "semantic_model_ready": (
        "Begin Semantic Model Ready (Stage 5) -- build the governed semantic "
        "model against approved metric contracts."
    ),
    "dashboard_ready": (
        "Begin Dashboard Ready (Stage 6) -- design the dashboard against the "
        "approved contracts."
    ),
    "publish_ready": (
        "Begin Publish Ready (Stage 7) -- assemble and review the BI handoff "
        "pack; do not publish from this surface."
    ),
}


def _response(
    table: str,
    outcome: str,
    stage: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = details or {}
    return {
        "table": table,
        "outcome": outcome,
        "stage": stage,
        "action_text": payload.get("action_text"),
        "blocking_reasons": payload.get("blocking_reasons", []),
        "required_authority": payload.get("required_authority"),
        "caveats": payload.get("caveats", []),
        "read_only_proof": True,
    }


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _valid_owner(owner: object) -> bool:
    """Use RS1's named-human approval shape so run-next agrees with the gate."""
    from seshat.rules.readiness_status import _owner_is_valid

    return _owner_is_valid(owner)


def _source_kind(stage_block: object) -> str | None:
    from seshat.rules.readiness_status import _source_kind

    return _source_kind(stage_block)


def _approved_stages(approvals: object) -> set[str]:
    if not isinstance(approvals, list):
        return set()
    return {
        item.get("stage")
        for item in approvals
        if isinstance(item, dict)
        and isinstance(item.get("stage"), str)
        and _valid_owner(item.get("owner"))
    }


def _table_candidate_names(table: str) -> list[str]:
    normalized = table.strip().replace("\\", "/").strip("/")
    names = [normalized, normalized.rsplit(".", 1)[-1]]
    unique: list[str] = []
    for name in names:
        if _candidate_needs_append(name, unique):
            unique.append(name)
    return unique


def _candidate_needs_append(name: str, existing: list[str]) -> bool:
    if not name:
        return False
    if "/" in name:
        return False
    return name not in existing


def _status_path_candidates(root: Path, table: str) -> list[Path]:
    return [
        root / "mappings" / name / "readiness-status.yaml"
        for name in _table_candidate_names(table)
    ]


def _load_yaml_mapping(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    import yaml

    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"could not read readiness status: {exc}"
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, f"readiness status is not valid YAML: {exc}"
    if not isinstance(data, dict):
        return None, "readiness status must be a mapping"
    return data, None


def _find_status_data(
    root: Path, table: str
) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    direct = _direct_status_data(root, table)
    if direct[0] is not None:
        return direct

    mappings_dir = root / "mappings"
    if not mappings_dir.is_dir():
        return None, None, None
    return _matching_status_data(mappings_dir, table)


def _direct_status_data(
    root: Path, table: str
) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    for candidate in _status_path_candidates(root, table):
        if candidate.is_file():
            data, error = _load_yaml_mapping(candidate)
            return candidate, data, error
    return None, None, None


def _status_names(status_path: Path, data: dict[str, Any]) -> set[str]:
    return {
        status_path.parent.name,
        str(data.get("table") or ""),
        str(data.get("source_id") or ""),
    }


def _matches_status_identity(
    status_path: Path,
    data: dict[str, Any] | None,
    error: str | None,
    table: str,
) -> bool:
    if error is not None:
        return False
    if data is None:
        return False
    return table in _status_names(status_path, data)


def _matching_status_data(
    mappings_dir: Path, table: str
) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
        data, error = _load_yaml_mapping(status_path)
        if _matches_status_identity(status_path, data, error, table):
            return status_path, data, None
    return None, None, None


def _input_defect(table: str, stage: str | None, detail: str) -> dict[str, Any]:
    return _response(
        table,
        "input_defect",
        stage,
        {"caveats": [{"kind": "input_defect", "detail": detail}]},
    )


def _stage_block(
    stages: dict[str, object], stage_name: str, table: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    block = stages.get(stage_name)
    if block is None:
        return None, _input_defect(
            table, stage_name, f"stage {stage_name!r} is missing"
        )
    if not isinstance(block, dict):
        return None, _input_defect(
            table, stage_name, f"stage {stage_name!r} must be a mapping"
        )
    status = block.get("status")
    if status not in _STATUS_VALUES:
        return None, _input_defect(
            table,
            stage_name,
            f"stage {stage_name!r} has invalid status {status!r}",
        )
    return block, None


def _add_disagreement_caveat(
    response: dict[str, Any], stored_next_action: object
) -> dict[str, Any]:
    if response["outcome"] != "next_action":
        return response
    if not isinstance(stored_next_action, str) or not stored_next_action.strip():
        return response
    computed = str(response.get("action_text") or "")
    if stored_next_action.strip().lower() == computed.strip().lower():
        return response
    response["caveats"].append(
        {
            "kind": "next_action_disagreement",
            "detail": (
                "stored next_action differs from computed action; "
                f"stored={stored_next_action!r}; computed={computed!r}"
            ),
        }
    )
    return response


def _add_dual_blocked_caveat(
    response: dict[str, Any], blocked_stages: list[str]
) -> dict[str, Any]:
    later = [stage for stage in blocked_stages if stage != response["stage"]]
    if response["outcome"] == "stop_blocked" and later:
        response["caveats"].append(
            {
                "kind": "dual_blocked",
                "detail": f"later blocked stage(s) also present: {', '.join(later)}",
            }
        )
    return response


def _stage_requires_source_approval(stage_name: str, block: dict[str, Any]) -> bool:
    return stage_name == "source_ready" and _source_kind(block) in _FILE_SOURCE_KINDS


def _approval_required_for_stage(stage_name: str, block: dict[str, Any]) -> bool:
    return stage_name in _APPROVAL_REQUIRED or _stage_requires_source_approval(
        stage_name, block
    )


def _authority_for(stage_name: str) -> str:
    return _AUTHORITY_BY_STAGE.get(stage_name, "data_owner")


def _response_table(table: str, data: dict[str, Any]) -> str:
    response_table = data.get("table")
    if isinstance(response_table, str) and response_table:
        return response_table
    return table


def _evidence_caveat(stage_name: str, block: dict[str, Any]) -> dict[str, str] | None:
    if _as_str_list(block.get("evidence")):
        return None
    return {
        "kind": "pass_without_evidence",
        "detail": f"stage {stage_name!r} is pass but evidence[] is empty",
    }


def _warning_caveat(stage_name: str) -> dict[str, str]:
    return {
        "kind": "warning_carried_forward",
        "detail": f"stage {stage_name!r} is warning",
    }


def _blocked_response(
    table: str, stage_name: str, block: dict[str, Any], stages: dict[str, object]
) -> dict[str, Any]:
    response = _response(
        table,
        "stop_blocked",
        stage_name,
        {"blocking_reasons": _as_str_list(block.get("blocking_reasons"))},
    )
    return _add_dual_blocked_caveat(response, _all_blocked_stages(stages))


def _next_action_response(
    context: dict[str, Any],
    stage_name: str,
    status: object,
) -> dict[str, Any]:
    caveats = context["caveats"]
    if status == "warning":
        caveats.append(_warning_caveat(stage_name))
    response = _response(
        context["table"],
        "next_action",
        stage_name,
        {"action_text": _ACTION_BY_STAGE[stage_name], "caveats": caveats},
    )
    return _add_disagreement_caveat(response, context["stored_next_action"])


def _approval_missing(
    stage_name: str, block: dict[str, Any], approved: set[str]
) -> bool:
    return (
        _approval_required_for_stage(stage_name, block) and stage_name not in approved
    )


def _pass_stage_result(
    context: dict[str, Any],
    stage_name: str,
    block: dict[str, Any],
) -> dict[str, Any] | None:
    caveats = context["caveats"]
    caveat = _evidence_caveat(stage_name, block)
    if caveat is not None:
        caveats.append(caveat)
    if not _approval_missing(stage_name, block, context["approved"]):
        return None
    return _response(
        context["table"],
        "approval_required",
        stage_name,
        {"required_authority": _authority_for(stage_name), "caveats": caveats},
    )


def _stage_decision(
    context: dict[str, Any],
    stage_name: str,
    block: dict[str, Any],
) -> dict[str, Any] | None:
    status = block["status"]
    if status == "blocked":
        return _blocked_response(context["table"], stage_name, block, context["stages"])
    if status in {"not_started", "warning"}:
        return _next_action_response(context, stage_name, status)
    return _pass_stage_result(context, stage_name, block)


def _build_from_data(table: str, data: dict[str, Any]) -> dict[str, Any]:
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return _input_defect(
            table, None, "readiness status must contain a 'stages' mapping"
        )

    response_table = _response_table(table, data)
    context = {
        "table": response_table,
        "stages": stages,
        "approved": _approved_stages(data.get("approvals")),
        "caveats": [],
        "stored_next_action": data.get("next_action"),
    }

    for stage_name in _STAGE_ORDER:
        block, defect = _stage_block(stages, stage_name, response_table)
        if defect is not None:
            return defect
        assert block is not None
        result = _stage_decision(
            context,
            stage_name=stage_name,
            block=block,
        )
        if result is not None:
            return result

    return _response(
        response_table, "terminal_pass", None, {"caveats": context["caveats"]}
    )


def _all_blocked_stages(stages: dict[str, object]) -> list[str]:
    blocked: list[str] = []
    for stage_name in _STAGE_ORDER:
        block = stages.get(stage_name)
        if isinstance(block, dict) and block.get("status") == "blocked":
            blocked.append(stage_name)
    return blocked


def build_run_next_response(repo_root: Path | str, table: str) -> dict[str, Any]:
    """Return the run-next answer for one table.

    Missing files are handled as an unstarted Source Ready journey. Malformed
    files produce ``input_defect`` instead of raising. The function performs no
    writes and has no live-system dependency.
    """
    root = Path(repo_root)
    _, data, error = _find_status_data(root, table)
    if error is not None:
        return _input_defect(table, None, error)
    if data is None:
        return _response(
            table,
            "next_action",
            "source_ready",
            {"action_text": _NO_STATUS_FILE_ACTION},
        )
    return _build_from_data(table, data)
