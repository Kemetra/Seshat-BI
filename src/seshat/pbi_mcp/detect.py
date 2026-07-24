"""Read-only environment detection for the Power BI MCP doctor (#450 slice 2).

Everything here is a local, no-network probe: which runtimes are on disk /
PATH, what mode the machine-local ``.mcp.json`` requests, whether a PBIP/TMDL
project exists, and what the committed per-table readiness records say about
``semantic_model_ready``. No MCP server is ever contacted; nothing is written.

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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Categorical state tokens (never a numeric score).
PRESENT = "present"
ABSENT = "absent"

CONFIG_ABSENT = "absent"
CONFIG_READ_ONLY = "read-only"
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
    semantic_model_ready: str  # pass | not-pass | missing
    semantic_ready_tables: tuple[str, ...]  # tables whose stage records pass
    publish_ready_approval: str  # recorded | absent


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


def _powerbi_server_args(servers: dict) -> list[list[str]]:
    """Args of every Power BI-shaped server entry, one list per server."""
    return [
        _server_args(entry)
        for name, entry in servers.items()
        if isinstance(entry, dict) and _is_powerbi_server(str(name), entry)
    ]


def _carries_forbidden_flag(per_server_args: list[list[str]]) -> bool:
    return any(_FORBIDDEN_FLAG in arg for args in per_server_args for arg in args)


def _requests_write_mode(per_server_args: list[list[str]]) -> bool:
    return any(arg in _WRITE_FLAGS for args in per_server_args for arg in args)


def _all_read_only(per_server_args: list[list[str]]) -> bool:
    return all(_READONLY_FLAG in args for args in per_server_args)


def _classify_servers(servers: dict) -> str:
    """Fold every Power BI server's args into one categorical verdict.

    Fail-closed ordering: the forbidden flag wins over everything; an explicit
    write flag -- or the mere ABSENCE of ``--readonly`` (the local server's
    documented default is write-enabled) -- reads as write mode.
    """
    relevant = _powerbi_server_args(servers)
    if not relevant:
        return CONFIG_ABSENT
    if _carries_forbidden_flag(relevant):
        return CONFIG_FORBIDDEN_FLAG
    if _requests_write_mode(relevant):
        return CONFIG_WRITE_MODE
    if _all_read_only(relevant):
        return CONFIG_READ_ONLY
    return CONFIG_WRITE_MODE


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


def detect_facts(
    repo_root: Path,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> DetectedFacts:
    """Collect every categorical fact the recommendation matrix consumes.

    ``which`` is injectable so tests never depend on the host PATH.
    """
    root = Path(repo_root)
    semantic, ready_tables, approval = read_semantic_readiness(root)
    return DetectedFacts(
        node_runtime=PRESENT if which("node") else ABSENT,
        vendored_runtime=(
            PRESENT if (root / VENDORED_RUNTIME_DIR).is_dir() else ABSENT
        ),
        mcp_config=classify_mcp_config(root / ".mcp.json"),
        pbip_project=PRESENT if _pbip_project_present(root) else ABSENT,
        semantic_model_ready=semantic,
        semantic_ready_tables=ready_tables,
        publish_ready_approval=approval,
    )
