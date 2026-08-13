"""Deliver one decided approval back to the provider (T026).

**This module closes the round trip Phase 6 left open.** Until it existed, the relay
accepted a decision and burned its id while nothing sent it onward: real Codex raises
`item/*/requestApproval` as a JSON-RPC server request carrying an `id` and BLOCKS until
a response keyed to that id arrives (`tests/fixtures/codex_app_server/approvals.jsonl`),
so an accepted-but-undelivered decision left the turn hanging forever.

**Why this is its own module rather than a method on the bridge.** The write is one
frame and the guards around it are the same authority rules `approvals.py` already
owns; putting it behind an `AgentBridge` method would oblige every adapter -- including
`FakeAgentBridge`, which has no provider beneath it -- to implement a transport concern
it does not have. A free function taking anything with `send()` keeps the fake honest
and the seam testable without a subprocess.

**The refusals here are duplicated on purpose.** `PendingApprovals.decide` already
refuses an impermissible allow, and so does this function. That is not redundancy: the
ledger guards the DECISION and this guards the WIRE, and a future caller that writes a
frame without consulting the ledger must still be unable to send `approved` for a
scope readiness forbids. A boundary enforced at one layer only is a boundary that the
next refactor removes by accident.
"""

from __future__ import annotations

from typing import Any, Protocol

from seshat.studio.approvals import TECHNICAL, ApprovalEnvelope

__all__ = [
    "APPROVED",
    "DENIED",
    "DeliveryFailed",
    "DeliveryRefused",
    "FrameSink",
    "deliver_decision",
]

#: The provider's vocabulary, taken from the captured app-server exchange. Studio's own
#: HTTP edge speaks `allow_once`/`deny`; translating here rather than sharing one
#: spelling keeps a change to either side from silently corrupting the other.
APPROVED = "approved"
DENIED = "denied"


class FrameSink(Protocol):
    """Anything that can write one JSON-RPC frame to a provider.

    Structural rather than nominal so `CodexSession` satisfies it without importing
    this module, and so a test recorder satisfies it without a subprocess.
    """

    def send(self, frame: dict[str, Any]) -> None: ...


class DeliveryRefused(Exception):
    """The decision was never Studio's to deliver in that direction.

    Distinct from `DeliveryFailed`: this one means the frame must NOT be written, and
    retrying cannot help. `StaleApproval`'s wire-level counterpart.
    """


class DeliveryFailed(Exception):
    """The frame could not be written to a provider that was expected to receive it.

    Raised rather than swallowed so a caller cannot report a closed round trip on the
    strength of a write that never landed. Degrading silently here would recreate
    exactly the fail-open this module was written to remove.
    """


def deliver_decision(
    session: FrameSink, envelope: ApprovalEnvelope, *, allow: bool
) -> bool:
    """Answer the provider's approval request. True when a frame was written.

    Returns False -- rather than raising -- when the envelope carries no `request_id`.
    That is the fake bridge's normal case: an `approval_required` streamed as inert
    activity with no server request beneath it. The decision is still validly recorded;
    there is simply nobody waiting on it, and inventing an id to answer would be worse
    than answering nothing.

    An allow is refused unless the envelope permits one. A DENY is always permitted,
    including for `named_human`: refusing to *grant* a governance ruling is not the same
    as refusing to *answer* the provider, and a named-human request left unanswered
    blocks the turn just as hard as a technical one. Denying is the only move that both
    respects the authority split and releases Codex.
    """
    _refuse_impermissible(envelope, allow)
    if envelope.request_id is None:
        return False

    frame = {
        "jsonrpc": "2.0",
        "id": envelope.request_id,
        "result": {"decision": APPROVED if allow else DENIED},
    }
    try:
        session.send(frame)
    except Exception as failure:  # noqa: BLE001 -- every write failure must be audible
        raise DeliveryFailed(
            f"the decision for approval {envelope.approval_id!r} could not be "
            f"delivered to the provider ({failure})"
        ) from failure
    return True


def _refuse_impermissible(envelope: ApprovalEnvelope, allow: bool) -> None:
    """Raise unless this direction is one Studio may put on the wire.

    Only an ALLOW can be impermissible, and it is impermissible for exactly the two
    reasons `normalize_approval` already folded into `allow_permitted`: the authority
    was never technical, or readiness forbids the scope. Re-deriving them from the
    envelope's own fields keeps the message specific about which one applied.
    """
    if not allow or envelope.allow_permitted:
        return
    reason = (
        "; ".join(envelope.forbidden_reasons)
        if envelope.forbidden_reasons
        else f"its authority is {envelope.authority}, not {TECHNICAL}"
    )
    raise DeliveryRefused(
        f"approval {envelope.approval_id!r} may not be delivered as {APPROVED!r}: "
        f"{reason}"
    )
