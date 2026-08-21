"""The investigation journey's evidence view (spec 140, US1).

A view over the shipped projection, not a new source of truth: every member of
`EvidenceBundle` is an existing `projection` type. That is deliberate -- US1 must not
be able to disagree with the readiness the gate computes.

The one derived value is `pending_live`, and how it is derived matters. A stage with no
evidence means "no evidence" (an input defect); a stage awaiting a live profile means
"pending". Deriving pending-live from emptiness would launder missing data into an
expected-pending state, so it is read from the projection's own live-state signal
instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from seshat.studio import projection

#: The `EvidenceRef.live_state` value the projection uses for "not verified against a
#: live source". Mirrored from `projection._LIVE_PENDING` (private there) and pinned by
#: `test_a_pending_live_stage_is_reported_pending`, which fails if it drifts.
PENDING_LIVE_STATE = "pending_live_profile"

#: The marker the rest of Seshat already uses. It reaches a stage two ways: as an
#: evidence `live_state`, and as text inside a blocking reason (which is how a source
#: stage awaiting a DSN is actually recorded). Both count.
PENDING_LIVE_MARKER = "[PENDING LIVE PROFILE]"


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """One table's evidence, grouped for the investigation view."""

    table_id: str
    stages: tuple[projection.StageState, ...]
    evidence: tuple[projection.EvidenceRef, ...]
    defects: tuple[projection.InputDefect, ...]
    pending_live: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "table_id": self.table_id,
            "stages": [stage.as_dict() for stage in self.stages],
            "evidence": [ref.as_dict() for ref in self.evidence],
            "defects": [defect.as_dict() for defect in self.defects],
            "pending_live": list(self.pending_live),
        }


def _stage_is_pending_live(stage: projection.StageState) -> bool:
    """True when this stage is awaiting a live profile.

    Two signals, because the projection records the boundary both ways:
      - an evidence reference whose `live_state` is the pending value;
      - a blocking reason whose message carries the pending-live marker.
    Emptiness is NOT a signal -- that is a defect, handled separately.
    """
    if any(ref.live_state == PENDING_LIVE_STATE for ref in stage.evidence):
        return True
    return any(
        PENDING_LIVE_MARKER in reason.message for reason in stage.blocking_reasons
    )


def bundle_for(snapshot: projection.WorkspaceSnapshot, table_id: str) -> EvidenceBundle:
    """Group one table's committed evidence, defects, and pending-live boundaries.

    Raises `KeyError` for an unknown table rather than returning an empty bundle: an
    empty bundle would read as "this table is fine", which is the empty-success state
    US1 exists to prevent.
    """
    journey = next(
        (table for table in snapshot.tables if table.table_id == table_id), None
    )
    if journey is None:
        raise KeyError(table_id)

    return EvidenceBundle(
        table_id=table_id,
        stages=journey.stages,
        evidence=tuple(ref for stage in journey.stages for ref in stage.evidence),
        # `WorkspaceSnapshot.input_defects` -- InputDefect carries no table_id, so
        # defects cannot be narrowed by identity. Carrying them all is the honest
        # option; dropping one because it cannot be attributed would hide a defect.
        defects=snapshot.input_defects,
        pending_live=tuple(
            stage.stage for stage in journey.stages if _stage_is_pending_live(stage)
        ),
    )
