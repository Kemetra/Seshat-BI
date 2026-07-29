"""Readiness diff -- what changed in committed readiness state between two revisions.

`seshat status` answers "where is this table NOW"; `seshat impact-map` answers
"what does THIS approved decision touch". Neither answers the reviewer's question
on a pull request: **did readiness move, and did anything go backwards?**

This module owns the comparison MATH only. It takes two already-parsed
``{table -> readiness-status document}`` maps and returns a categorical diff. It
never runs git, opens a database, or makes a network call -- the revision-reading
layer is a separate seam (mirroring ``profile.py``'s QueryRunner and
``file_profile.py``'s FrameReader), which is what keeps this testable without a
repo fixture and keeps the core stdlib-only.

Hard invariants (mirroring ``status_surface`` / ``blocker_explainer``):
  - Read-only and derived: it reports what committed state SAYS changed. It
    grants no approval, advances no stage, and writes nothing.
  - Never a numeric score: a change is categorical and ``has_regression`` is a
    BOOLEAN derived from the status/stage lattices -- never a severity number,
    never summed or averaged across stages (hard rule #9, Principle V).
  - Regression is asymmetric ON PURPOSE: ``pass -> blocked`` regresses;
    ``blocked -> pass`` is ordinary forward progress. Collapsing that asymmetry
    would make the surface useless as a review signal.
  - A LOST APPROVAL is a regression. An approval disappearing means the evidence
    a stage rested on is gone; reporting it as a neutral edit would let a
    reviewer merge away a named-human signature without noticing.
  - Best-effort: a malformed committed document contributes nothing rather than
    aborting the diff, so one bad table cannot blind a reviewer to every other.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The seven-stage spine and the status vocabulary are owned by `run_next`; import
# them rather than adding another copy (`agent_next` imports the same names). The
# ordered status tuple below is the PROGRESS order the set cannot express -- a
# test pins it against `_STATUS_VALUES` so the two cannot drift.
from .run_next import _STAGE_ORDER

# Statuses in progress order (docs/readiness/readiness-model.md). The index
# answers only the boolean "did this go backwards".
_STATUS_PROGRESS: tuple[str, ...] = ("not_started", "blocked", "warning", "pass")


def _progress_of(status: str | None) -> int | None:
    """Progress index of ``status``, or ``None`` when it is not a known status.

    An unknown or missing status yields ``None`` so the caller reports the change
    WITHOUT claiming a direction -- guessing a rank for an unrecognized value
    would fabricate a regression verdict out of a malformed file.
    """
    if status not in _STATUS_PROGRESS:
        return None
    return _STATUS_PROGRESS.index(status)


def _stage_index(stage: str | None) -> int | None:
    """Position of ``stage`` in the seven-stage spine, or ``None`` if unrecognized."""
    if stage not in _STAGE_ORDER:
        return None
    return _STAGE_ORDER.index(stage)


@dataclass(frozen=True)
class StageChange:
    """One stage's status moving between the two revisions."""

    table: str
    stage: str
    base_status: str | None
    head_status: str | None
    is_regression: bool


@dataclass(frozen=True)
class CurrentStageChange:
    """A table's ``current_stage`` moving between the two revisions."""

    table: str
    base_stage: str | None
    head_stage: str | None
    is_regression: bool


@dataclass(frozen=True)
class ApprovalChange:
    """One recorded named-human approval appearing or disappearing."""

    table: str
    stage: str | None
    owner: str | None
    at: str | None


@dataclass(frozen=True)
class ReadinessDiff:
    """The categorical difference between two committed readiness snapshots."""

    tables_added: tuple[str, ...] = ()
    tables_removed: tuple[str, ...] = ()
    stage_changes: tuple[StageChange, ...] = ()
    current_stage_changes: tuple[CurrentStageChange, ...] = ()
    blockers_added: tuple[tuple[str, str, str], ...] = ()
    blockers_removed: tuple[tuple[str, str, str], ...] = ()
    approvals_added: tuple[ApprovalChange, ...] = ()
    approvals_removed: tuple[ApprovalChange, ...] = ()

    @property
    def has_regression(self) -> bool:
        """True when a stage regressed, a table moved back, or an approval was lost.

        A boolean, deliberately: the reviewer's question is "is something wrong
        here", and a count or score would invite ranking severity the committed
        state cannot support.
        """
        return (
            any(change.is_regression for change in self.stage_changes)
            or any(move.is_regression for move in self.current_stage_changes)
            or bool(self.approvals_removed)
        )

    @property
    def is_empty(self) -> bool:
        """True when nothing changed at all."""
        return not (
            self.tables_added
            or self.tables_removed
            or self.stage_changes
            or self.current_stage_changes
            or self.blockers_added
            or self.blockers_removed
            or self.approvals_added
            or self.approvals_removed
        )


def _as_document(document: object) -> dict:
    """``document`` when it is a mapping, else an empty one (best-effort)."""
    return document if isinstance(document, dict) else {}


def _stage_blocks(document: object) -> dict[str, dict]:
    """``{stage -> block}`` from one readiness document, tolerating malformed input."""
    stages = _as_document(document).get("stages")
    if not isinstance(stages, dict):
        return {}
    return {
        name: (block if isinstance(block, dict) else {})
        for name, block in stages.items()
        if isinstance(name, str)
    }


def _status_of(block: dict) -> str | None:
    status = block.get("status")
    return status if isinstance(status, str) else None


def _blockers_of(block: dict) -> tuple[str, ...]:
    reasons = block.get("blocking_reasons")
    if not isinstance(reasons, list):
        return ()
    return tuple(reason for reason in reasons if isinstance(reason, str))


def _approvals_of(document: object) -> dict[tuple, dict]:
    """``{identity -> approval}`` for one document.

    Identity is (stage, owner, at, note): re-signing the same stage on a later
    date is a NEW approval, and must not silently look like the old one.
    """
    approvals = _as_document(document).get("approvals")
    if not isinstance(approvals, list):
        return {}
    identified: dict[tuple, dict] = {}
    for entry in approvals:
        if not isinstance(entry, dict):
            continue
        identity = (
            entry.get("stage"),
            entry.get("owner"),
            entry.get("at"),
            entry.get("note"),
        )
        identified[identity] = entry
    return identified


def _approval_change(table: str, entry: dict) -> ApprovalChange:
    def _text(key: str) -> str | None:
        value = entry.get(key)
        return value if isinstance(value, str) else None

    return ApprovalChange(
        table=table, stage=_text("stage"), owner=_text("owner"), at=_text("at")
    )


def _current_stage_of(document: object) -> str | None:
    stage = _as_document(document).get("current_stage")
    return stage if isinstance(stage, str) else None


def _current_move(
    table: str, base_doc: object, head_doc: object
) -> CurrentStageChange | None:
    """The table's ``current_stage`` move, or ``None`` when it did not move."""
    base_stage = _current_stage_of(base_doc)
    head_stage = _current_stage_of(head_doc)
    if base_stage == head_stage:
        return None
    before = _stage_index(base_stage)
    after = _stage_index(head_stage)
    return CurrentStageChange(
        table=table,
        base_stage=base_stage,
        head_stage=head_stage,
        is_regression=(before is not None and after is not None and after < before),
    )


def _stage_change(
    table: str,
    stage: str,
    before_status: str | None,
    after_status: str | None,
) -> StageChange | None:
    """One stage's status change, or ``None`` when the status is unchanged."""
    if before_status == after_status:
        return None
    before_rank = _progress_of(before_status)
    after_rank = _progress_of(after_status)
    return StageChange(
        table=table,
        stage=stage,
        base_status=before_status,
        head_status=after_status,
        is_regression=(
            before_rank is not None
            and after_rank is not None
            and after_rank < before_rank
        ),
    )


def _blocker_deltas(
    table: str, stage: str, before_block: dict, after_block: dict
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """``(added, removed)`` blocking reasons for one stage, sorted."""
    before = set(_blockers_of(before_block))
    after = set(_blockers_of(after_block))
    return (
        [(table, stage, reason) for reason in sorted(after - before)],
        [(table, stage, reason) for reason in sorted(before - after)],
    )


def _identity_sort_key(identity: tuple) -> tuple:
    """Deterministic ordering for approval identities that may hold non-strings."""
    return tuple(map(str, identity))


def _approval_deltas(
    table: str, base_doc: object, head_doc: object
) -> tuple[list[ApprovalChange], list[ApprovalChange]]:
    """``(added, removed)`` recorded approvals for one table, sorted."""
    base_approvals = _approvals_of(base_doc)
    head_approvals = _approvals_of(head_doc)
    added = [
        _approval_change(table, head_approvals[identity])
        for identity in sorted(
            set(head_approvals) - set(base_approvals), key=_identity_sort_key
        )
    ]
    removed = [
        _approval_change(table, base_approvals[identity])
        for identity in sorted(
            set(base_approvals) - set(head_approvals), key=_identity_sort_key
        )
    ]
    return added, removed


@dataclass
class _Accumulator:
    """Per-table findings collected across the walk, in encounter order."""

    stage_changes: list[StageChange] = field(default_factory=list)
    current_moves: list[CurrentStageChange] = field(default_factory=list)
    blockers_added: list[tuple[str, str, str]] = field(default_factory=list)
    blockers_removed: list[tuple[str, str, str]] = field(default_factory=list)
    approvals_added: list[ApprovalChange] = field(default_factory=list)
    approvals_removed: list[ApprovalChange] = field(default_factory=list)


def _collect_table(
    acc: _Accumulator, table: str, base_doc: object, head_doc: object
) -> None:
    """Fold one table's changes into ``acc``. Stages walked in sorted order."""
    move = _current_move(table, base_doc, head_doc)
    if move is not None:
        acc.current_moves.append(move)

    base_blocks = _stage_blocks(base_doc)
    head_blocks = _stage_blocks(head_doc)
    for stage in sorted(set(base_blocks) | set(head_blocks)):
        before_block = base_blocks.get(stage, {})
        after_block = head_blocks.get(stage, {})
        change = _stage_change(
            table,
            stage,
            _status_of(before_block) if stage in base_blocks else None,
            _status_of(after_block) if stage in head_blocks else None,
        )
        if change is not None:
            acc.stage_changes.append(change)
        added, removed = _blocker_deltas(table, stage, before_block, after_block)
        acc.blockers_added.extend(added)
        acc.blockers_removed.extend(removed)

    approvals_added, approvals_removed = _approval_deltas(table, base_doc, head_doc)
    acc.approvals_added.extend(approvals_added)
    acc.approvals_removed.extend(approvals_removed)


def diff_readiness(base: dict[str, object], head: dict[str, object]) -> ReadinessDiff:
    """Compare two ``{table -> readiness document}`` maps.

    Every collection is walked in sorted order so the output is deterministic --
    a diff a reviewer cannot re-derive byte-for-byte is not evidence.
    """
    acc = _Accumulator()
    for table in sorted(set(base) | set(head)):
        _collect_table(acc, table, base.get(table), head.get(table))

    return ReadinessDiff(
        tables_added=tuple(sorted(set(head) - set(base))),
        tables_removed=tuple(sorted(set(base) - set(head))),
        stage_changes=tuple(acc.stage_changes),
        current_stage_changes=tuple(acc.current_moves),
        blockers_added=tuple(acc.blockers_added),
        blockers_removed=tuple(acc.blockers_removed),
        approvals_added=tuple(acc.approvals_added),
        approvals_removed=tuple(acc.approvals_removed),
    )
