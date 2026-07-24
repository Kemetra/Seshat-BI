"""Read-only MCP preflight: capability discovery + target validation (#450, slice 4).

Asks an MCP server -- through a :class:`McpTransport` Protocol whose REAL
implementation is deliberately absent -- for its identity and tool list, then
validates a declared target against an explicit allowlist. The shipped
transport (:class:`MissingRuntimeTransport`) reports "runtime not present --
preflight skipped" gracefully; tests exercise the logic through an in-memory
fake. Nothing here mutates any artifact, ever.

Fail-closed ordering (issue #450 section 8, step 3):

1. the machine-local ``.mcp.json`` must not request write mode, and
   ``--skipconfirmation`` anywhere in it is a hard refusal;
2. ``semantic_model_ready`` must record a pass (the gate-reader style read
   from ``mappings/*/readiness-status.yaml``) -- otherwise the preflight is
   blocked NAMING the gate and the server is never contacted;
3. only then is the transport asked to describe itself; an unsupported
   protocol version or a missing required capability is a blocker naming it
   verbatim (F032 posture: unknown is never compatible).

The result can be written -- only under the explicit ``--write-artifact``
flag -- to ``.seshat/powerbi-mcp-preflight.json``: a derived-evidence-only
advisory with NO score. This artifact is the smoke-test evidence SHAPE the
adapter-compatibility matrix's F016 row references; producing it attests
nothing (a named owner does that).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .detect import (
    CONFIG_FORBIDDEN_FLAG,
    CONFIG_UNPARSEABLE,
    CONFIG_WRITE_MODE,
    READINESS_PASS,
    classify_mcp_config,
    read_semantic_readiness,
)
from .scan import refuse_if_secret_shaped

SCHEMA_VERSION = 1
ARTIFACT_RELPATH = ".seshat/powerbi-mcp-preflight.json"

STATUS_OK = "ok"
STATUS_BLOCKED = "blocked"
STATUS_SKIPPED = "skipped"

# Model Context Protocol revisions this preflight has been written against.
# Anything else is UNKNOWN, and unknown is never compatible (F032) -- the
# blocker names the version verbatim so a human can extend this tuple after
# a reviewed compatibility pass, never silently.
SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = ("2025-03-26", "2025-06-18")

GENERATED_NOTE = (
    "derived evidence only -- no score, no approval, no readiness effect; "
    "a named owner attests compatibility, this artifact never does"
)

_RUNTIME_ABSENT_MESSAGE = (
    "official Power BI MCP runtime not present -- preflight skipped "
    "(install Node.js 20+ / vendor tools/powerbi-modeling-mcp/, then re-run)"
)


class RuntimeUnavailable(RuntimeError):
    """The MCP runtime is not installed/reachable -- a graceful skip."""


@dataclass(frozen=True)
class ServerDescription:
    """What an MCP server says about itself during initialization."""

    name: str
    version: str  # echoed verbatim for the record; never compared numerically
    protocol_version: str
    tools: tuple[str, ...]


class McpTransport(Protocol):
    """The one seam to a real MCP runtime. Read-only by construction: the
    Protocol exposes discovery only -- there is no call/execute member, so a
    conforming transport cannot be asked to run a tool from here."""

    def describe(self) -> ServerDescription: ...


class MissingRuntimeTransport:
    """The shipped default: no real MCP runtime is wired in slices 2-4."""

    def describe(self) -> ServerDescription:
        raise RuntimeUnavailable(_RUNTIME_ABSENT_MESSAGE)


@dataclass(frozen=True)
class PreflightBlocker:
    """One categorical blocker -- id + plain-language detail, no score."""

    id: str
    detail: str


@dataclass(frozen=True)
class PreflightResult:
    """Immutable outcome of one read-only preflight."""

    status: str  # ok | blocked | skipped
    mode: str  # always "read-only" -- slices 2-4 have no other mode
    server: ServerDescription | None
    tools_present: tuple[str, ...]
    tools_missing: tuple[str, ...]
    target: str | None
    target_allowlisted: bool | None  # None = no target declared
    blockers: tuple[PreflightBlocker, ...]
    notes: tuple[str, ...]


def _config_blockers(repo_root: Path) -> list[PreflightBlocker]:
    state = classify_mcp_config(Path(repo_root) / ".mcp.json")
    if state == CONFIG_FORBIDDEN_FLAG:
        return [
            PreflightBlocker(
                id="PBIMCP-CONF-01",
                detail=(
                    ".mcp.json carries --skipconfirmation -- forbidden in "
                    "every mode; hard refusal, nothing was contacted"
                ),
            )
        ]
    if state == CONFIG_WRITE_MODE:
        return [
            PreflightBlocker(
                id="PBIMCP-CONF-02",
                detail=(
                    ".mcp.json requests write mode -- this preflight asserts "
                    "read-only and refuses; set --readonly"
                ),
            )
        ]
    if state == CONFIG_UNPARSEABLE:
        return [
            PreflightBlocker(
                id="PBIMCP-CONF-03",
                detail=(
                    ".mcp.json is unparseable -- fail-closed; fix or "
                    "regenerate it (seshat pbi-mcp generate-config)"
                ),
            )
        ]
    return []


def _readiness_blockers(repo_root: Path) -> list[PreflightBlocker]:
    status, _tables, _approval = read_semantic_readiness(Path(repo_root))
    if status == READINESS_PASS:
        return []
    return [
        PreflightBlocker(
            id="PBIMCP-GATE-01",
            detail=(
                f"semantic_model_ready gate is '{status}' -- no table "
                "records a pass, so the preflight is blocked fail-closed "
                "(the gate, not this tool, decides)"
            ),
        )
    ]


def _capability_blockers(
    server: ServerDescription,
    required_tools: tuple[str, ...],
    supported_protocol_versions: tuple[str, ...],
) -> tuple[list[PreflightBlocker], tuple[str, ...], tuple[str, ...]]:
    blockers: list[PreflightBlocker] = []
    if server.protocol_version not in supported_protocol_versions:
        blockers.append(
            PreflightBlocker(
                id="PBIMCP-VER-01",
                detail=(
                    f"unsupported protocol version '{server.protocol_version}'"
                    " -- unknown is never compatible (F032); a human extends "
                    "the supported set after a reviewed compatibility pass"
                ),
            )
        )
    if not server.tools:
        blockers.append(
            PreflightBlocker(
                id="PBIMCP-CAP-02",
                detail="server reported no capabilities -- nothing to validate",
            )
        )
    present = tuple(tool for tool in required_tools if tool in server.tools)
    missing = tuple(tool for tool in required_tools if tool not in server.tools)
    for tool in missing:
        blockers.append(
            PreflightBlocker(
                id="PBIMCP-CAP-01",
                detail=f"required capability '{tool}' not offered by the server",
            )
        )
    return blockers, present, missing


def _target_blockers(
    target: str | None, target_allowlist: tuple[str, ...]
) -> tuple[list[PreflightBlocker], bool | None]:
    if target is None:
        return [], None
    if not target_allowlist:
        return [
            PreflightBlocker(
                id="PBIMCP-TGT-02",
                detail=(
                    "a target was declared but no allowlist is defined -- "
                    "no mutation-adjacent validation without an explicit, "
                    "reviewed allowlist"
                ),
            )
        ], False
    if target not in target_allowlist:
        return [
            PreflightBlocker(
                id="PBIMCP-TGT-01",
                detail=f"declared target '{target}' is not on the allowlist",
            )
        ], False
    return [], True


def run_preflight(
    repo_root: Path,
    transport: McpTransport,
    *,
    target: str | None = None,
    target_allowlist: tuple[str, ...] = (),
    required_tools: tuple[str, ...] = (),
    supported_protocol_versions: tuple[str, ...] = SUPPORTED_PROTOCOL_VERSIONS,
) -> PreflightResult:
    """Run the read-only preflight; see the module docstring for the order."""
    blockers = _config_blockers(repo_root) + _readiness_blockers(repo_root)
    if blockers:
        # Fail-closed BEFORE any contact: a config that demands write mode or
        # a not-passed gate means the server is never even described.
        return PreflightResult(
            status=STATUS_BLOCKED,
            mode="read-only",
            server=None,
            tools_present=(),
            tools_missing=(),
            target=target,
            target_allowlisted=None,
            blockers=tuple(blockers),
            notes=("server not contacted -- blocked before discovery",),
        )
    try:
        server = transport.describe()
    except RuntimeUnavailable as absence:
        return PreflightResult(
            status=STATUS_SKIPPED,
            mode="read-only",
            server=None,
            tools_present=(),
            tools_missing=(),
            target=target,
            target_allowlisted=None,
            blockers=(),
            notes=(str(absence),),
        )
    cap_blockers, present, missing = _capability_blockers(
        server, required_tools, supported_protocol_versions
    )
    tgt_blockers, allowlisted = _target_blockers(target, target_allowlist)
    all_blockers = tuple(cap_blockers + tgt_blockers)
    return PreflightResult(
        status=STATUS_BLOCKED if all_blockers else STATUS_OK,
        mode="read-only",
        server=server,
        tools_present=present,
        tools_missing=missing,
        target=target,
        target_allowlisted=allowlisted,
        blockers=all_blockers,
        notes=(),
    )


def render_result_json(result: PreflightResult, generated_at: str) -> str:
    """Deterministic, ASCII-only JSON rendering of one preflight result."""
    server = None
    if result.server is not None:
        server = {
            "name": result.server.name,
            "version": result.server.version,
            "protocol_version": result.server.protocol_version,
            "tools": list(result.server.tools),
        }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact": "powerbi-mcp-preflight",
        "authority": "derived-evidence-only",
        "readiness_effect": "none; named-human approval required",
        "generated_at": generated_at,
        "generated_note": GENERATED_NOTE,
        "mode": result.mode,
        "status": result.status,
        "server": server,
        "tools_present": list(result.tools_present),
        "tools_missing": list(result.tools_missing),
        "target": {
            "declared": result.target,
            "allowlisted": result.target_allowlisted,
        },
        "blockers": [
            {"id": blocker.id, "detail": blocker.detail} for blocker in result.blockers
        ],
        "notes": list(result.notes),
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write_artifact(
    repo_root: Path,
    result: PreflightResult,
    *,
    generated_at: str | None = None,
) -> Path:
    """Write the preflight record (latest run replaces the previous one --
    stale smoke evidence is worse than none). Only ever called under the
    explicit ``--write-artifact`` flag; scanned before writing."""
    stamp = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = render_result_json(result, stamp)
    refuse_if_secret_shaped(text, context=ARTIFACT_RELPATH)
    target = Path(repo_root) / ARTIFACT_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return target
