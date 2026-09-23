"""Read-only gate readers for the Dagster orchestration adapter (spec 134).

The single implementation of the human-seam GO-signal read (research D4): the
orchestration package (``tower_bi_orchestration``) and the ``seshat dagster``
doctor both import THESE readers, so there is exactly one parser for the most
safety-critical artifacts in the flow.

READ-ONLY BY CONTRACT (FR-005): this module exposes no write path. It parses
``mappings/<table>/unresolved-questions.md`` (the ``Gate status`` line + the
open-question rows) and ``mappings/<table>/readiness-status.yaml`` (the
``approvals[]`` entries + the ``publish_ready`` stage status) and returns
immutable views. Writing any of those fields is a named-human action recorded
by Core Authority -- never by adapter code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from seshat.gitstate import committed_text, is_tracked_and_clean

# Both committed phrasings are real: the retail_store_sales instance writes a
# bold bullet (`- **Gate status:** \`CLEARED\``); the demo_sample_orders
# instance writes a heading (`## Gate status: CLEARED`). Read either; anything
# else stays MISSING (fail-closed).
_GATE_STATUS_RE = re.compile(
    r"(?:\*\*Gate status:\*\*|^#{1,6}\s*Gate status:)\s*`?([A-Za-z]+)`?",
    re.MULTILINE,
)
# An open-question table row: `| Q<n> | ... |`. The Status column carries
# `answered` when resolved; anything else counts as open.
_QUESTION_ROW_RE = re.compile(r"^\|\s*Q\d+\s*\|", re.MULTILINE)


@dataclass(frozen=True)
class Approval:
    """One named-human sign-off row from ``approvals[]`` -- read verbatim."""

    stage: str
    owner: str
    at: str


@dataclass(frozen=True)
class GateState:
    """The committed gate state for one table -- an immutable read-only view."""

    table: str
    # "CLEARED" | "OPEN" | "MISSING" | "UNCOMMITTED" (or the verbatim token).
    # UNCOMMITTED means the mirror exists in the worktree but is untracked or
    # carries uncommitted edits -- never a GO signal (#334).
    gate_status: str
    open_rows: int
    approvals: tuple[Approval, ...]
    # Verbatim COMMITTED stage status, or "missing" / "uncommitted" /
    # "unreadable" (never "pass" unless HEAD records it).
    publish_ready: str

    @property
    def silver_permitted(self) -> bool:
        """The ONLY GO signal for the silver build (Principle IV): a COMMITTED
        ``Gate status: CLEARED`` with zero open rows (an uncommitted mirror
        reads as UNCOMMITTED, #334). Never computed from anything else; never
        writable from here."""
        return self.gate_status == "CLEARED" and self.open_rows == 0

    def approval_for(self, stage: str) -> Approval | None:
        """The committed approval for ``stage``, or None (the caller HALTS)."""
        for approval in self.approvals:
            if approval.stage == stage:
                return approval
        return None


def _read_unresolved(table_dir: Path) -> tuple[str, int]:
    unresolved = table_dir / "unresolved-questions.md"
    if not unresolved.is_file():
        return "MISSING", 0
    text = unresolved.read_text(encoding="utf-8")
    match = _GATE_STATUS_RE.search(text)
    gate_status = match.group(1).upper() if match else "MISSING"
    # A question row is open unless its Status cell is EXACTLY the token
    # `answered` -- substring matching would count "unanswered" as resolved
    # (review finding).
    open_rows = 0
    for line in text.splitlines():
        if not _QUESTION_ROW_RE.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        status_cell = cells[5] if len(cells) > 5 else ""
        if status_cell.strip("`").strip() != "answered":
            open_rows += 1
    return gate_status, open_rows


def _committed_readiness(repo_root: Path, table: str) -> dict | str:
    """The COMMITTED readiness mapping, or the verbatim reason there is none.

    Read through ``committed_text`` (tracked AND clean against HEAD), never the
    worktree: ``approval_for`` is documented as the COMMITTED approval, and a
    worktree read would let an uncommitted, agent-added ``approvals[]`` row
    look committed -- a second approval-trust path. A malformed record is a
    reason, not an exception out of the reader.
    """
    relative = f"mappings/{table}/readiness-status.yaml"
    if not (Path(repo_root) / relative).is_file():
        return "missing"
    text = committed_text(Path(repo_root), relative)
    if text is None:
        return "uncommitted"
    import yaml  # lazy: keeps module import driver- and dependency-light

    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return "unreadable"
    return data if isinstance(data, dict) else "unreadable"


def _read_readiness(repo_root: Path, table: str) -> tuple[tuple[Approval, ...], str]:
    data = _committed_readiness(repo_root, table)
    if isinstance(data, str):
        return (), data
    approvals = tuple(
        Approval(
            stage=str(entry.get("stage", "")),
            owner=str(entry.get("owner", "")),
            at=str(entry.get("at", "")),
        )
        for entry in data.get("approvals") or []
        if isinstance(entry, dict)
    )
    stages = data.get("stages") or {}
    publish = stages.get("publish_ready") or {}
    publish_ready = (
        str(publish.get("status", "missing"))
        if isinstance(publish, dict)
        else "missing"
    )
    return approvals, publish_ready


def read_gate_state(repo_root: Path, table: str) -> GateState:
    """Read the COMMITTED gate state for ``table`` under ``repo_root``.

    Missing artifacts are reported as MISSING/missing -- never guessed, never
    treated as approval (fail-closed is the caller's duty on anything that is
    not an explicit CLEARED + zero open rows). A mirror that exists but is
    untracked or dirty against HEAD reads as UNCOMMITTED (#334): a
    worktree-only clearance never entered audit history and may disappear on
    checkout, so it must never permit the silver build.
    """
    table_dir = Path(repo_root) / "mappings" / table
    gate_status, open_rows = _read_unresolved(table_dir)
    if gate_status != "MISSING" and not is_tracked_and_clean(
        Path(repo_root), f"mappings/{table}/unresolved-questions.md"
    ):
        gate_status = "UNCOMMITTED"
    approvals, publish_ready = _read_readiness(Path(repo_root), table)
    return GateState(
        table=table,
        gate_status=gate_status,
        open_rows=open_rows,
        approvals=approvals,
        publish_ready=publish_ready,
    )


def list_mapped_tables(repo_root: Path) -> list[str]:
    """Tables with a committed ``source-map.yaml`` under ``mappings/`` (sorted)."""
    mappings = Path(repo_root) / "mappings"
    if not mappings.is_dir():
        return []
    return sorted(
        entry.name
        for entry in mappings.iterdir()
        if entry.is_dir() and (entry / "source-map.yaml").is_file()
    )
