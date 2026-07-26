"""Read-only run-next readiness surface (spec 080).

This module answers one question for one table: what is the single next allowed
readiness action, or why is the table stopped? It writes nothing, opens no DB
connection, makes no network call, and never grants an approval.

Reads, stated precisely (widened by #485/A2, and the no-DB/no-network contract
above is UNCHANGED by that widening):

  * ``mappings/<table>/readiness-status.yaml`` -- the readiness state, as always;
  * ``mappings/<table>/db-provenance.json`` -- the machine-written, server-echoed
    live-DB identity record, when one exists (see ``seshat.db_provenance``);
  * the process environment and the workspace `.env`, to resolve the configured
    DSN *as a string* via the explicitly driver-free ``validate.resolve_dsn``.

The third of those is configuration, not a live system: nothing here connects to
a database or opens a socket. It happens only when a provenance record exists,
which is no committed table today.
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
    """Stages satisfied by a shape-valid approval -- one shared definition.

    Delegates to ``readiness_status.approval_is_shape_valid`` so this surface
    cannot drift from the gate rule or from the approval inbox (issue #487).
    """
    from seshat.rules.readiness_status import approval_is_shape_valid

    if not isinstance(approvals, list):
        return set()
    return {item.get("stage") for item in approvals if approval_is_shape_valid(item)}


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


# Stages whose `pass` evidence asserts that objects EXIST IN A SPECIFIC DATABASE
# ("migration applied to ..."). Deliberately narrow: source/mapping are profile
# and decision work, and semantic-model/dashboard evidence is files on disk, so
# none of those makes a database-dependent claim worth qualifying here.
_LIVE_MATERIALIZATION_STAGES: frozenset[str] = frozenset({"silver_ready", "gold_ready"})
_PROVENANCE_CAVEAT_KIND = "unverified_db_provenance"

# Every kind the A2 provenance check can emit. Used to enforce "at most one
# provenance caveat per table" across all three non-blocking verdicts -- checking
# only the legacy kind would let a `verified` and an `unverified` caveat coexist.
_PROVENANCE_KINDS: frozenset[str] = frozenset(
    {
        _PROVENANCE_CAVEAT_KIND,
        "db_provenance_verified",
        "db_provenance_not_comparable",
    }
)


def _provenance_caveat(stage_name: str) -> dict[str, str]:
    """Interim #485 signal: this surface cannot tell WHICH database earned this.

    `readiness-status.yaml` records no structured live-DB identity -- database
    names appear only as prose inside `evidence[]` -- and this module reads no
    DSN and opens no connection by contract. So a table whose silver/gold
    evidence was earned against one database still reports `pass` verbatim after
    the configured DSN is repointed at another (issue #485).

    A caveat, never a blocker: no committed record carries provenance today, so
    enforcing it would fail every table at once. It states the limit rather than
    implying a correlation that did not happen. The real fix is to capture the
    identity mechanically at connect time -- see
    docs/superpowers/specs/2026-07-25-live-db-provenance-design.md (option A2).
    """
    return {
        "kind": _PROVENANCE_CAVEAT_KIND,
        "detail": (
            f"stage {stage_name!r} is pass, but its evidence records no "
            "machine-checkable database identity, so it cannot be correlated "
            "with the currently configured connection; confirm this evidence "
            "was earned against the database you are now pointed at"
        ),
    }


def _first_live_pass_stage(stages: object) -> str | None:
    """The FIRST live-materialization stage recorded ``pass``, or ``None``.

    At most one stage, because one caveat per table reads as a fact about the
    table while one per stage reads as noise.
    """
    if not isinstance(stages, dict):
        return None
    for stage_name in _STAGE_ORDER:
        if stage_name not in _LIVE_MATERIALIZATION_STAGES:
            continue
        block = stages.get(stage_name)
        if isinstance(block, dict) and block.get("status") == "pass":
            return stage_name
    return None


def provenance_caveat_for_stages(
    stages: object,
    repo_root: Path | str | None = None,
    table_dir: str | None = None,
) -> dict[str, str] | None:
    """The #485 provenance caveat for a projected `stages` mapping, or ``None``.

    ONE wording per condition, shared with every surface that reports it --
    `next` (via ``_add_provenance_caveat``) and the human-readable
    `status --format text` render. Two surfaces drifting into two sentences for
    one condition is exactly #487's failure mode, so both resolve through here.

    ``repo_root`` / ``table_dir`` are OPTIONAL. Given both, this returns the A2
    verdict for the table: the ``unverified_db_provenance`` caveat when no record
    exists (the legacy path), a ``db_provenance_verified`` caveat when the
    recorded identity matches the configured connection, a
    ``db_provenance_not_comparable`` caveat when a record exists but cannot be
    compared, and the named ``stale_evidence_wrong_database`` blocker text on a
    MISMATCH. Omitting them yields the legacy caveat unconditionally, which is
    what a caller with no directory context can honestly say.

    `status --format json` deliberately carries none of this: that projection is
    verbatim-only by contract (``status_surface`` docstring) and its schema
    (``schemas/agent-status.schema.json``) is closed, so a DERIVED field has no
    honest home there. The text render is where a human reads the qualification.
    """
    stage_name = _first_live_pass_stage(stages)
    if stage_name is None:
        return None
    if repo_root is None or not table_dir:
        return _provenance_caveat(stage_name)
    from seshat import db_provenance
    from seshat.db_provenance_reader import provenance_verdict

    verdict, detail = provenance_verdict(repo_root, table_dir)
    if verdict == "mismatch":
        assert detail is not None
        return {"kind": db_provenance.BLOCKER_ID, "detail": detail}
    return _provenance_caveat_for_verdict(stage_name, verdict, detail)


def _provenance_verdict(context: dict[str, Any]) -> tuple[str, str | None]:
    """The A2 provenance verdict for this table, computed at most ONCE.

    Memoized on the context because the verdict is a property of the TABLE (one
    record, one configured DSN), not of a stage, and recomputing it per stage
    would re-read the same file and the same `.env` for every live stage.

    ``("absent", None)`` when the table has no record -- every committed table
    today -- so the common path costs one failed ``open`` and no `.env` work.
    """
    cached = context.get("provenance_verdict")
    if cached is not None:
        return cached
    root, table_dir = context.get("repo_root"), context.get("table_dir")
    if root is None or not table_dir:
        verdict: tuple[str, str | None] = ("absent", None)
    else:
        from seshat.db_provenance_reader import provenance_verdict

        verdict = provenance_verdict(root, table_dir)
    context["provenance_verdict"] = verdict
    return verdict


def _add_provenance_caveat(
    caveats: list[dict[str, str]], stage_name: str, context: dict[str, Any]
) -> dict[str, Any] | None:
    """Qualify a live-materialization `pass` by its A2 provenance verdict.

    Returns a ``stop_blocked`` response when the recorded identity DISAGREES with
    the configured connection, and ``None`` otherwise (the caller continues). At
    most one provenance caveat per table: one reads as a fact about the table,
    one per stage reads as noise.

    The four verdicts, per ruling R7:

      * ``absent``       -> the shipped option-B caveat, exactly as before. Never
        a blocker: no committed record carries provenance, so gating on absence
        would fail every table at once (the legacy path).
      * ``match``        -> the option-B caveat DROPS and a ``verified`` caveat
        states that the check ran and agreed. Silence would be indistinguishable
        from "not checked", which is the ambiguity A2 exists to remove.
      * ``mismatch``     -> DOWNGRADE with the named ``stale_evidence_wrong_database``
        blocker. Never a fabricated pass and never a silent pass.
      * ``uncomparable`` -> a record exists but could not be compared. Reported as
        a caveat, never as agreement -- and never as a blocker either, because
        failing to READ configuration is not evidence that the database is wrong.
    """
    if stage_name not in _LIVE_MATERIALIZATION_STAGES:
        return None
    verdict, detail = _provenance_verdict(context)
    if verdict == "mismatch":
        # A downgrade, not a caveat: this is the one A2 condition that must stop a
        # reader, so it takes the same shape as any other blocked stage.
        assert detail is not None
        return _response(
            context["table"],
            "stop_blocked",
            stage_name,
            {"blocking_reasons": [detail], "caveats": list(caveats)},
        )
    if any(c.get("kind") in _PROVENANCE_KINDS for c in caveats):
        return None
    caveats.append(_provenance_caveat_for_verdict(stage_name, verdict, detail))
    return None


def _provenance_caveat_for_verdict(
    stage_name: str, verdict: str, detail: str | None
) -> dict[str, str]:
    """The caveat for a non-mismatch provenance verdict."""
    from seshat import db_provenance_reader

    if verdict == "match":
        return db_provenance_reader.verified_caveat(stage_name)
    if verdict == "uncomparable" and detail is not None:
        return db_provenance_reader.uncomparable_caveat(detail)
    return _provenance_caveat(stage_name)


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
    downgrade = _add_provenance_caveat(caveats, stage_name, context)
    if downgrade is not None:
        # The recorded database disagrees with the configured one: stop here
        # rather than walking on to later stages whose pass rests on the same
        # (now-unclaimable) live evidence.
        return downgrade
    if not _approval_missing(stage_name, block, context["approved"]):
        return None
    from seshat.rules.readiness_status import APPROVAL_SHAPE_HINT

    authority = _authority_for(stage_name)
    # Without action_text the default `next --table X` text surface printed no
    # guidance line at all -- the reporter's quoted advice only ever appeared
    # under --format agent (issue #487).
    return _response(
        context["table"],
        "approval_required",
        stage_name,
        {
            "required_authority": authority,
            "action_text": (
                f"STOP -- obtain the named-human approval ({authority}) for "
                f"stage {stage_name!r}; never self-grant it. Once that human "
                f"has decided, {APPROVAL_SHAPE_HINT}."
            ),
            "caveats": caveats,
        },
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


def _build_from_data(
    table: str,
    data: dict[str, Any],
    repo_root: Path | None = None,
    table_dir: str | None = None,
) -> dict[str, Any]:
    """Decide the next action from one parsed readiness document.

    ``repo_root`` / ``table_dir`` locate the table's ``mappings/<table>/`` so the
    A2 provenance record can be read (#485). Both are optional and default to
    ``None``, which yields the ``absent`` verdict -- i.e. exactly the behavior
    before A2 -- so a caller that has no directory context still gets a correct
    answer rather than an error.
    """
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
        "repo_root": repo_root,
        "table_dir": table_dir,
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
    status_path, data, error = _find_status_data(root, table)
    if error is not None:
        return _input_defect(table, None, error)
    if data is None:
        return _response(
            table,
            "next_action",
            "source_ready",
            {"action_text": _NO_STATUS_FILE_ACTION},
        )
    # The provenance record is a SIBLING of the readiness file, so its directory
    # is the one actually found -- never re-derived from `table`, which may be a
    # schema-qualified name or an alias that resolved via `_matching_status_data`.
    table_dir = status_path.parent.name if status_path is not None else None
    return _build_from_data(table, data, root, table_dir)
