"""Read-only gate readers for the Dagster orchestration adapter (spec 134).

The single implementation of the human-seam GO-signal read (research D4): the
orchestration package (``tower_bi_orchestration``) and the ``seshat dagster``
doctor both import THESE readers. The mirror itself is parsed by
``seshat.unresolved_mirror.parse_mirror`` -- the same parser the dbt Mapping
Ready gate uses -- so one committed human ruling has exactly one meaning for
every engine.

READ-ONLY BY CONTRACT (FR-005): this module exposes no write path. It parses
``mappings/<table>/unresolved-questions.md`` (the ``Gate status`` line + the
open-question rows) and ``mappings/<table>/readiness-status.yaml`` (the
``approvals[]`` entries + the ``publish_ready`` stage status) and returns
immutable views. Writing any of those fields is a named-human action recorded
by Core Authority -- never by adapter code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from seshat.gitstate import committed_text
from seshat.unresolved_mirror import parse_mirror

UNCOMMITTED = "UNCOMMITTED"


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
    publish_ready: str  # verbatim stage status, or "missing"

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


def _read_unresolved(repo_root: Path, table: str) -> tuple[str, int]:
    relative = f"mappings/{table}/unresolved-questions.md"
    if not (Path(repo_root) / relative).is_file():
        return "MISSING", 0
    text = committed_text(Path(repo_root), relative)
    if text is None:
        return UNCOMMITTED, 0
    state = parse_mirror(text)
    return state.gate_status, state.open_rows


def _approval_row(entry: object) -> Approval | None:
    """A named-human row: non-blank stage and owner plus an ISO ``at`` date."""
    if not isinstance(entry, dict):
        return None
    stage, owner, at = (entry.get(key) for key in ("stage", "owner", "at"))
    if not all(isinstance(value, str) and value.strip() for value in (stage, owner)):
        return None
    try:
        date.fromisoformat(str(at))
    except ValueError:
        return None
    return Approval(stage=str(stage), owner=str(owner).strip(), at=str(at))


def _publish_status(data: dict) -> str:
    stages = data.get("stages")
    publish = stages.get("publish_ready") if isinstance(stages, dict) else None
    if not isinstance(publish, dict):
        return "missing"
    return str(publish.get("status", "missing"))


def _read_readiness(repo_root: Path, table: str) -> tuple[tuple[Approval, ...], str]:
    relative = f"mappings/{table}/readiness-status.yaml"
    if not (Path(repo_root) / relative).is_file():
        return (), "missing"
    text = committed_text(Path(repo_root), relative)
    if text is None:
        return (), "uncommitted"
    import yaml  # lazy: keeps module import driver- and dependency-light

    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return (), "invalid"
    if not isinstance(data, dict):
        return (), "invalid"
    rows = data.get("approvals")
    candidates = rows if isinstance(rows, list) else []
    approvals = tuple(
        row for row in (_approval_row(entry) for entry in candidates) if row
    )
    return approvals, _publish_status(data)


def read_gate_state(repo_root: Path, table: str) -> GateState:
    """Read the COMMITTED gate state for ``table`` under ``repo_root``.

    Missing artifacts are reported as MISSING/missing -- never guessed, never
    treated as approval (fail-closed is the caller's duty on anything that is
    not an explicit CLEARED + zero open rows). A mirror that exists but is
    untracked or dirty against HEAD reads as UNCOMMITTED (#334): a
    worktree-only clearance never entered audit history and may disappear on
    checkout, so it must never permit the silver build. The same holds for
    ``readiness-status.yaml``: an untracked or dirty record yields NO approvals
    and ``publish_ready='uncommitted'``, and both files are parsed from their
    committed (HEAD) blob, never the worktree.
    """
    gate_status, open_rows = _read_unresolved(repo_root, table)
    approvals, publish_ready = _read_readiness(repo_root, table)
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
