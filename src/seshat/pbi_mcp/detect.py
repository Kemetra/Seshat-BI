"""Read-only environment detection for the Power BI MCP doctor (#450 slice 2).

Everything here is a local, no-network probe: which runtimes are on disk /
PATH, what mode the machine-local ``.mcp.json`` requests, whether a PBIP/TMDL
project exists, and what the committed per-table readiness records say about
``semantic_model_ready`` and ``dashboard_ready``. No MCP server is ever
contacted; nothing is written.

The readiness read mirrors the ``seshat.dagster_adapter.gate`` reader style
(read-only by contract, missing artifacts reported as ``missing``, never
guessed). It reads the WORKTREE files -- sufficient for a read-only advisory.
The slice-5 mutation gate (owner-ADR-gated, NOT implemented here) must
additionally require the committed state via ``gitstate.is_tracked_and_clean``
per the #334 lesson: an uncommitted gate artifact is never a GO signal.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

# Categorical state tokens (never a numeric score).
PRESENT = "present"
ABSENT = "absent"

CONFIG_ABSENT = "absent"
CONFIG_READ_ONLY = "read-only"
# Remote-HTTP-only configuration: the published endpoint queries
# already-published models and exposes no write switch, so it has no
# ``--readonly`` argument to carry. Classified separately from a local stdio
# read-only config rather than mistaken for write mode (#477).
CONFIG_QUERY_ONLY = "query-only"
CONFIG_WRITE_MODE = "write-mode"
CONFIG_FORBIDDEN_FLAG = "forbidden-flag"
CONFIG_UNPARSEABLE = "unparseable"

READINESS_PASS = "pass"
READINESS_NOT_PASS = "not-pass"
READINESS_MISSING = "missing"

APPROVAL_RECORDED = "recorded"
APPROVAL_ABSENT = "absent"

VENDORED_RUNTIME_DIR = "tools/powerbi-modeling-mcp"

# Flags in the machine-local .mcp.json (Microsoft's documented spellings plus
# the misspelling this repo once shipped; both count as write mode).
_FORBIDDEN_FLAG = "--skipconfirmation"
_WRITE_FLAGS = ("--readwrite", "--read-write")
_READONLY_FLAG = "--readonly"


@dataclass(frozen=True)
class DetectedFacts:
    """Immutable categorical facts about the local environment."""

    node_runtime: str  # present | absent
    vendored_runtime: str  # present | absent
    mcp_config: str  # absent | read-only | write-mode | forbidden-flag | unparseable
    pbip_project: str  # present | absent
    target: str | None  # exact governed table selected by the caller
    semantic_model_ready: str  # pass | not-pass | missing
    semantic_ready_tables: tuple[str, ...]  # tables whose stage records pass
    target_semantic_model_ready: str  # pass | not-pass | missing for exact target
    dashboard_ready: str  # pass | not-pass | missing for the exact target
    dashboard_ready_tables: tuple[str, ...]  # target when it records pass
    dashboard_design_approval: str  # recorded | absent for exact target
    publish_ready_approval: str  # recorded | absent
    official_report_skills: tuple[str, ...]  # compatible discovered target names


def _is_powerbi_server(name: str, entry: dict) -> bool:
    """Only Power BI-shaped servers are classified -- an unrelated MCP server
    in the same .mcp.json (a docs server, say) must not flip the verdict."""
    blob = " ".join(
        (name, str(entry.get("command", "")), str(entry.get("url", "")))
    ).lower()
    return "powerbi" in blob or "pbi" in blob


def _server_args(entry: dict) -> list[str]:
    args = entry.get("args")
    if not isinstance(args, list):
        return []
    return [str(arg).lower() for arg in args]


def _powerbi_servers(servers: dict) -> list[dict]:
    """Every Power BI-shaped server entry."""
    return [
        entry
        for name, entry in servers.items()
        if isinstance(entry, dict) and _is_powerbi_server(str(name), entry)
    ]


def _powerbi_server_args(servers: dict) -> list[list[str]]:
    """Args of every Power BI-shaped server entry, one list per server."""
    return [_server_args(entry) for entry in _powerbi_servers(servers)]


def _is_local_server(entry: dict) -> bool:
    """A stdio server this machine launches -- it takes the ``--readonly`` flag."""
    return bool(entry.get("command"))


def _is_remote_server(entry: dict) -> bool:
    """A remote HTTP server -- addressed by URL, with no local flags at all."""
    return bool(entry.get("url")) or str(entry.get("type", "")).lower() == "http"


def _carries_forbidden_flag(per_server_args: list[list[str]]) -> bool:
    return any(_FORBIDDEN_FLAG in arg for args in per_server_args for arg in args)


def _is_write_flag(arg: str) -> bool:
    """Whether one argument requests write mode.

    Matches the bare flag and its ``=value`` form. The value form matters
    because an exact membership test reads ``--readwrite=true`` as *not* write
    mode -- harmless while nothing could be invoked in write mode (slices 2-4),
    a fail-open once slice 5 makes it reachable.

    The split is on ``=`` rather than a substring test so that a longer flag
    which merely starts with the same letters (``--readwrite-dry-run``) is not
    swept up as a write request.
    """
    return arg.split("=", 1)[0] in _WRITE_FLAGS


def _requests_write_mode(per_server_args: list[list[str]]) -> bool:
    return any(_is_write_flag(arg) for args in per_server_args for arg in args)


def _all_read_only(per_server_args: list[list[str]]) -> bool:
    return all(_READONLY_FLAG in args for args in per_server_args)


def _classify_servers(servers: dict) -> str:
    """Fold every Power BI server entry into one categorical verdict.

    Fail-closed ordering: the forbidden flag wins over everything, then an
    explicit write flag anywhere.

    After that the verdict is per TRANSPORT SHAPE (#477), because the
    ``--readonly`` rule only applies where the flag exists:

    - local stdio (``command``): the documented default is write-enabled, so
      the mere ABSENCE of ``--readonly`` reads as write mode;
    - remote HTTP (``url`` / ``type: http``): query-only by construction, with
      no local flag to carry -- requiring ``--readonly`` here rejected the
      repo's own generated remote/both configurations;
    - any other shape: unidentifiable transport, so not provably read-only.
    """
    relevant = _powerbi_servers(servers)
    if not relevant:
        return CONFIG_ABSENT
    flagged = _flag_verdict([_server_args(entry) for entry in relevant])
    return flagged if flagged is not None else _transport_verdict(relevant)


def _flag_verdict(every_arg_list: list[list[str]]) -> str | None:
    """The verdicts a FLAG forces regardless of transport shape, or None."""
    if _carries_forbidden_flag(every_arg_list):
        return CONFIG_FORBIDDEN_FLAG
    if _requests_write_mode(every_arg_list):
        return CONFIG_WRITE_MODE
    return None


def _transport_verdict(relevant: list[dict]) -> str:
    """The shape-driven verdict once no flag has forced one."""
    local = [entry for entry in relevant if _is_local_server(entry)]
    remote = [
        entry
        for entry in relevant
        if not _is_local_server(entry) and _is_remote_server(entry)
    ]
    if len(local) + len(remote) != len(relevant):
        return CONFIG_WRITE_MODE  # unidentifiable transport: never assume safe
    if not local:
        return CONFIG_QUERY_ONLY
    if _all_read_only([_server_args(entry) for entry in local]):
        return CONFIG_READ_ONLY
    return CONFIG_WRITE_MODE


def classify_invocation_argv(argv: Sequence[str]) -> str:
    """Classify one INVOCATION's argv through the same flag matcher as config.

    Spec 149 (F016 slice 5). Until write mode became reachable, the only place a
    bypass flag could appear was the machine-local ``.mcp.json``, so
    :func:`classify_mcp_config` was the whole story. An invocation can now carry
    the flag too, and it must be judged by the SAME rule -- hence this delegates
    to :func:`_flag_verdict` rather than owning a second matcher. One rule, one
    enforcement path.

    Args are lowercased first, mirroring what :func:`_server_args` does for the
    config path; without it an argv-only case bypass (``--SkipConfirmation``)
    would exist that the config path does not have.

    Returns ``CONFIG_FORBIDDEN_FLAG``, ``CONFIG_WRITE_MODE``, or
    ``CONFIG_READ_ONLY``. Read-only is the resting state: an invocation naming no
    mode resolves to read-only, so write mode is never reached by omission
    (FR-001).
    """
    lowered = [str(arg).lower() for arg in argv]
    forced = _flag_verdict([lowered])
    return forced if forced is not None else CONFIG_READ_ONLY


def classify_mcp_config(path: Path) -> str:
    """Classify the machine-local ``.mcp.json`` at ``path`` (read-only)."""
    if not path.is_file():
        return CONFIG_ABSENT
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeDecodeError):
        return CONFIG_UNPARSEABLE
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return CONFIG_UNPARSEABLE
    return _classify_servers(servers)


def _pbip_marker_at(root: Path, depth: str) -> bool:
    """A ``*.pbip`` pointer file or a ``*.SemanticModel`` DIRECTORY at one
    glob depth."""
    if next(root.glob(f"{depth}*.pbip"), None) is not None:
        return True
    return any(hit.is_dir() for hit in root.glob(f"{depth}*.SemanticModel"))


def _pbip_project_present(root: Path) -> bool:
    """A PBIP marker within three levels of the root (bounded probe -- never
    a full-tree walk)."""
    return any(_pbip_marker_at(root, depth) for depth in ("", "*/", "*/*/"))


def _stage_status(data: dict, stage: str) -> str:
    stages = data.get("stages") or {}
    entry = stages.get(stage) if isinstance(stages, dict) else None
    if isinstance(entry, dict):
        return str(entry.get("status", READINESS_MISSING))
    return READINESS_MISSING


def _has_publish_approval(data: dict) -> bool:
    approvals = data.get("approvals") or []
    return any(
        isinstance(entry, dict) and str(entry.get("stage", "")) == "publish_ready"
        for entry in approvals
    )


def _load_readiness_record(record: Path) -> dict | None:
    """Parse one readiness record; ``None`` means unreadable/mis-shaped --
    treated as not-pass by the caller, never as pass."""
    import yaml  # lazy: mirrors the gate reader's dependency-light discipline

    try:
        data = yaml.safe_load(record.read_text(encoding="utf-8-sig")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _fold_readiness_records(
    records: list[Path],
) -> tuple[tuple[str, ...], str]:
    """Fold parsed records into (semantic-ready tables, publish approval)."""
    ready: list[str] = []
    approval = APPROVAL_ABSENT
    for record in records:
        data = _load_readiness_record(record)
        if data is None:
            continue
        if _stage_status(data, "semantic_model_ready") == "pass":
            ready.append(record.parent.name)
        if _has_publish_approval(data):
            approval = APPROVAL_RECORDED
    return tuple(ready), approval


def read_stage_readiness(repo_root: Path, stage: str) -> tuple[str, tuple[str, ...]]:
    """Summarize one stage across committed per-table readiness records.

    A pass is copied verbatim from a record. Missing or malformed records never
    become a pass; no aggregate confidence or inferred state is produced.
    """
    mappings = Path(repo_root) / "mappings"
    if not mappings.is_dir():
        return READINESS_MISSING, ()
    records = sorted(mappings.glob("*/readiness-status.yaml"))
    if not records:
        return READINESS_MISSING, ()
    ready = tuple(
        record.parent.name
        for record in records
        if (data := _load_readiness_record(record)) is not None
        and _stage_status(data, stage) == READINESS_PASS
    )
    return (READINESS_PASS if ready else READINESS_NOT_PASS), ready


def read_semantic_readiness(repo_root: Path) -> tuple[str, tuple[str, ...], str]:
    """Read every ``mappings/<table>/readiness-status.yaml`` and summarize.

    Returns ``(semantic_model_ready, semantic_ready_tables, publish_approval)``
    where the first element is ``pass`` only when at least one table RECORDS a
    ``semantic_model_ready`` pass verbatim, ``missing`` when no readiness
    record exists at all, and ``not-pass`` otherwise -- never inferred, never
    guessed (fail-closed).
    """
    mappings = Path(repo_root) / "mappings"
    if not mappings.is_dir():
        return READINESS_MISSING, (), APPROVAL_ABSENT
    records = sorted(mappings.glob("*/readiness-status.yaml"))
    if not records:
        return READINESS_MISSING, (), APPROVAL_ABSENT
    ready, approval = _fold_readiness_records(records)
    status = READINESS_PASS if ready else READINESS_NOT_PASS
    return status, ready, approval


def read_table_readiness(repo_root: Path, table: str) -> str:
    """``semantic_model_ready`` for ONE table: pass | not-pass | missing.

    Deliberately exact (#477): the record must live at
    ``mappings/<table>/readiness-status.yaml``. A declared target naming no such
    record is ``missing`` -- never resolved by fuzzy match, and never satisfied
    by some OTHER table's pass. Readiness is a property of a table, so a
    target-scoped question must be answered from the target's own record.
    """
    return read_table_stage(repo_root, table, "semantic_model_ready")


def _valid_table_name(table: str) -> bool:
    return bool(table) and table not in {".", ".."} and Path(table).name == table


def read_table_stage(repo_root: Path, table: str, stage: str) -> str:
    """Read one exact table/stage without traversal or fuzzy matching."""
    if not _valid_table_name(table):
        return READINESS_NOT_PASS
    record = Path(repo_root) / "mappings" / table / "readiness-status.yaml"
    if not record.is_file():
        return READINESS_MISSING
    data = _load_readiness_record(record)
    if data is None:
        return READINESS_NOT_PASS
    if _stage_status(data, stage) == READINESS_PASS:
        return READINESS_PASS
    return READINESS_NOT_PASS


def read_table_approval(repo_root: Path, table: str, stage: str) -> str:
    """Read one complete named-human approval from the exact table record."""

    if not _valid_table_name(table):
        return APPROVAL_ABSENT
    record = Path(repo_root) / "mappings" / table / "readiness-status.yaml"
    if not record.is_file():
        return APPROVAL_ABSENT
    data = _load_readiness_record(record)
    if data is None:
        return APPROVAL_ABSENT
    approvals = data.get("approvals")
    if not isinstance(approvals, list):
        return APPROVAL_ABSENT
    for entry in approvals:
        if not isinstance(entry, dict) or entry.get("stage") != stage:
            continue
        if all(
            isinstance(entry.get(field), str) and entry[field].strip()
            for field in ("owner", "at", "note")
        ):
            return APPROVAL_RECORDED
    return APPROVAL_ABSENT


def detect_facts(
    repo_root: Path,
    *,
    which: Callable[[str], str | None] = shutil.which,
    target: str | None = None,
) -> DetectedFacts:
    """Collect every categorical fact the recommendation matrix consumes.

    ``which`` is injectable so tests never depend on the host PATH.
    """
    root = Path(repo_root)
    semantic, ready_tables, approval = read_semantic_readiness(root)
    dashboard, dashboard_tables = read_stage_readiness(root, "dashboard_ready")
    target_semantic = READINESS_MISSING
    design_approval = APPROVAL_ABSENT
    if target is not None:
        target_semantic = read_table_stage(root, target, "semantic_model_ready")
        dashboard = read_table_stage(root, target, "dashboard_ready")
        dashboard_tables = (target,) if dashboard == READINESS_PASS else ()
        design_approval = read_table_approval(root, target, "dashboard_ready")
    return DetectedFacts(
        node_runtime=PRESENT if which("node") else ABSENT,
        vendored_runtime=(
            PRESENT if (root / VENDORED_RUNTIME_DIR).is_dir() else ABSENT
        ),
        mcp_config=classify_mcp_config(root / ".mcp.json"),
        pbip_project=PRESENT if _pbip_project_present(root) else ABSENT,
        target=target,
        semantic_model_ready=semantic,
        semantic_ready_tables=ready_tables,
        target_semantic_model_ready=target_semantic,
        dashboard_ready=dashboard,
        dashboard_ready_tables=dashboard_tables,
        dashboard_design_approval=design_approval,
        publish_ready_approval=approval,
        official_report_skills=(),
    )
