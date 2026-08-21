"""Applying a reviewed proposal, bound to its exact scope (spec 140, US4).

Two refusals carry this module. An apply is refused unless its governing decision is
**authoritative** -- committed and readable at HEAD, not merely written (US4 acceptance
5) -- and it can never touch more than the reviewed proposal named (FR-140-014).

The scope is derived from the stored proposal, never taken from the request. A caller
who could supply the scope could widen it, which would make the reviewed diff a
suggestion rather than a boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from seshat import decision_write
from seshat.studio import proposals

#: Said on every receipt. A static gate proves the artifact is well-formed; it cannot
#: prove the numbers are right or that a live source agrees (FR-140-016).
STATIC_LABEL = (
    "static checks passed -- necessary, not sufficient: this is not semantic or live "
    "correctness"
)

#: The repository's existing marker for "no live evidence yet" (FR-140-017). Never a
#: fabricated pass.
PENDING_LIVE = "[PENDING LIVE PROFILE] no DSN configured, so nothing was verified live"


@dataclass(frozen=True)
class ApplyRefused(Exception):
    """An apply that must not proceed."""

    status: int
    detail: str

    def __str__(self) -> str:  # pragma: no cover - message plumbing
        return self.detail


@dataclass(frozen=True)
class ApplyReceipt:
    """What was applied and how it was verified.

    Deliberately carries no readiness field. Readiness is recomputed from artifacts and
    gates at HEAD (FR-140-015); a receipt that also claimed a stage would be a second,
    weaker account of the same fact.
    """

    proposal_hash: str
    applied_paths: tuple[str, ...]
    verification: dict[str, str]
    remaining_blockers: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict:
        return {
            "proposal_hash": self.proposal_hash,
            "applied_paths": list(self.applied_paths),
            "verification": dict(self.verification),
            "remaining_blockers": list(self.remaining_blockers),
        }


def _require_authoritative_decision(
    committed: Any, proposal: proposals.ChangeProposal, store_rel: str
) -> None:
    """The governing decision must be visible AT HEAD, not just written.

    A `pending commit` decision is exactly the state this refuses: the file on disk
    holds it, but nothing a human ratified does.
    """
    at_head = decision_write.decisions_at_head(committed, store_rel)
    bound = [
        entry
        for entry in at_head
        if entry.get("approval", {}).get("evidence")
        == f"proposal:{proposal.proposal_hash}"
    ]
    if not bound:
        raise ApplyRefused(
            422,
            "no committed decision authorizes this proposal; a recorded decision is "
            "pending commit until a human commits it, and pending commit is not "
            "authority",
        )


def _require_reviewed_scope(
    payload: dict[str, Any], proposal: proposals.ChangeProposal
) -> tuple[str, ...]:
    """The applied set is the proposal's target, and nothing the caller adds."""
    requested = payload.get("extra_paths") or []
    if requested:
        raise ApplyRefused(
            422,
            "the apply scope is fixed by the reviewed proposal; paths outside that "
            f"scope were requested: {sorted(str(item) for item in requested)}",
        )
    return (proposal.target_artifact,)


def apply_proposal(
    *,
    committed: Any,
    proposal: proposals.ChangeProposal,
    payload: dict[str, Any],
    current_revision: str,
    store_rel: str,
    live_available: bool = False,
) -> ApplyReceipt:
    """Apply exactly the reviewed proposal, refusing anything wider or unauthorized.

    Order is part of the contract: staleness, then authority, then scope. Each refusal
    happens before anything is applied.
    """
    if proposals.is_stale(proposal, current_revision):
        raise ApplyRefused(
            409, "the workspace moved since this proposal was reviewed; re-review it"
        )
    _require_authoritative_decision(committed, proposal, store_rel)
    applied = _require_reviewed_scope(payload, proposal)

    verification = {"static": STATIC_LABEL}
    # No DSN => say so. Synthesising a live result would be the fabricated pass
    # FR-140-017 forbids.
    verification["live"] = "live checks passed" if live_available else PENDING_LIVE

    return ApplyReceipt(
        proposal_hash=proposal.proposal_hash,
        applied_paths=applied,
        verification=verification,
        remaining_blockers=() if live_available else ("live verification pending",),
    )
