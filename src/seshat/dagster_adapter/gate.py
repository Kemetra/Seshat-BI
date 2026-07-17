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
    gate_status: str  # "CLEARED" | "OPEN" | "MISSING" (or the verbatim token)
    open_rows: int
    approvals: tuple[Approval, ...]
    publish_ready: str  # verbatim stage status, or "missing"

    @property
    def silver_permitted(self) -> bool:
        """The ONLY GO signal for the silver build (Principle IV): a committed
        ``Gate status: CLEARED`` with zero open rows. Never computed from
        anything else; never writable from here."""
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


def _read_readiness(table_dir: Path) -> tuple[tuple[Approval, ...], str]:
    readiness = table_dir / "readiness-status.yaml"
    if not readiness.is_file():
        return (), "missing"
    import yaml  # lazy: keeps module import driver- and dependency-light

    data = yaml.safe_load(readiness.read_text(encoding="utf-8")) or {}
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
    """Read the committed gate state for ``table`` under ``repo_root``.

    Missing artifacts are reported as MISSING/missing -- never guessed, never
    treated as approval (fail-closed is the caller's duty on anything that is
    not an explicit CLEARED + zero open rows).
    """
    table_dir = Path(repo_root) / "mappings" / table
    gate_status, open_rows = _read_unresolved(table_dir)
    approvals, publish_ready = _read_readiness(table_dir)
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
