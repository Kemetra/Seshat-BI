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

from seshat import decision_store, decision_write
from seshat.studio import decision_routes, proposals

#: Said on every receipt. Apply writes nothing yet and runs no rule, so the only true
#: static statement is that no check ran. Claiming "static checks passed" here was a
#: verdict nothing computed. Even a real pass would be necessary, not sufficient: a
#: static gate cannot prove the numbers are right or that a live source agrees
#: (FR-140-016).
STATIC_LABEL = (
    "not run: no static check was executed for this apply (a static pass would be "
    "necessary, not sufficient -- never semantic or live correctness)"
)

#: Said on every receipt until apply really writes. `applied_paths` stays empty
#: rather than naming a target nothing touched.
NOT_EXECUTED = (
    "not executed: the authorized, in-scope proposal was verified, but apply writes "
    "no files yet"
)

#: The one answer that authorizes an apply. A decline also carries the proposal's
#: evidence string, so evidence alone can never be the test.
_AUTHORIZING_ANSWER = "approve"

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


def authorizes(
    entry: dict[str, Any], authority: dict[str, frozenset[str]] | None
) -> bool:
    """True only for an approving, approved entry the shipped predicate accepts.

    Public so Operations history labels a committed entry by the SAME test rather
    than calling everything committed "authoritative".
    """
    return (
        entry.get("answer") == _AUTHORIZING_ANSWER
        and entry.get("status") == "approved"
        and decision_store.approval_is_valid(entry, authority)[0]
    )


def _require_authoritative_decision(
    committed: Any,
    proposal: proposals.ChangeProposal,
    context: "decision_routes.WorkspaceContext",
) -> None:
    """The governing decision must be visible AT HEAD, valid, and an approval.

    A `pending commit` decision is exactly the state this refuses: the file on disk
    holds it, but nothing a human ratified does. So is a committed DECLINE, and so is
    a hand-written stub that merely repeats the evidence string. More than one bound
    entry is refused too: an approve followed by a decline is not an authorization.
    """
    at_head = decision_write.decisions_at_head(committed, context.store_rel)
    bound = [
        entry
        for entry in at_head
        if entry.get("approval", {}).get("evidence")
        == f"proposal:{proposal.proposal_hash}"
    ]
    if len(bound) == 1 and authorizes(bound[0], context.authority):
        return
    raise ApplyRefused(
        422,
        "no committed decision authorizes this proposal; a recorded decision is "
        "pending commit until a human commits it, pending commit is not authority, "
        "and only exactly one committed, valid 'approve' ruling authorizes an apply",
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
    context: "decision_routes.WorkspaceContext",
    live_available: bool = False,
) -> ApplyReceipt:
    """Apply exactly the reviewed proposal, refusing anything wider or unauthorized.

    Order is part of the contract: staleness, then authority, then scope. Each refusal
    happens before anything is applied.
    """
    if proposals.is_stale(proposal, context.current_revision):
        raise ApplyRefused(
            409, "the workspace moved since this proposal was reviewed; re-review it"
        )
    _require_authoritative_decision(committed, proposal, context)
    _require_reviewed_scope(payload, proposal)

    verification = {"apply": NOT_EXECUTED, "static": STATIC_LABEL}
    # No DSN => say so. Synthesising a live result would be the fabricated pass
    # FR-140-017 forbids.
    verification["live"] = "live checks passed" if live_available else PENDING_LIVE

    return ApplyReceipt(
        proposal_hash=proposal.proposal_hash,
        applied_paths=(),
        verification=verification,
        remaining_blockers=() if live_available else ("live verification pending",),
    )
