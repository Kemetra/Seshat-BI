"""Normalization for provider approval requests (T025).

**The authority split is the whole point of this module.** A provider asks for one
thing -- permission to act -- but Seshat recognizes two different authorities, and
only one of them is Studio's to grant. A `technical` approval is permission to run a
command; a `named_human` approval is a governance ruling, which FR-021/FR-022 place
outside Studio entirely. Both arrive as `approval_required`, so if the split is not
made HERE it is not made at all.

**Unknown authority degrades to `named_human`, never to `technical`.** An
unrecognized value means this build does not understand what is being asked, and the
safe reading of "I do not understand this request" is "I may not grant it."

**Forbidden scope is passed IN, not computed here.** The single source of that
judgment is `agent_next.build_table_next_document()`. Taking it as a parameter keeps
this module pure -- and pure is what lets the T024 cases run without a repo, a
database, or a server.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from seshat.agent_next import build_table_next_document

__all__ = [
    "NAMED_HUMAN",
    "TECHNICAL",
    "ApprovalEnvelope",
    "PendingApprovals",
    "StaleApproval",
    "forbidden_scope_for",
    "normalize_approval",
]

#: Studio may expose an allow control for this authority.
TECHNICAL = "technical"

#: A governance ruling. Studio prepares a summary and offers NO allow control.
NAMED_HUMAN = "named_human"

#: Stand-in for a display field the provider omitted. An explicit word beats an
#: empty string, which renders as a blank panel the analyst cannot interpret.
_UNKNOWN = "unknown"

#: How many decided approval ids stay remembered. Bounded because FR-035 forbids a
#: database, so this dict IS the store; large enough that a browser retrying a decision
#: still reads "already decided" rather than the weaker "unknown approval".
_DECIDED_RETENTION = 512

#: How many UNDECIDED approvals stay decidable at once. An approval legitimately
#: outlives its turn (see `register`), so nothing else would ever evict these.
_LIVE_RETENTION = 256


@dataclass(frozen=True)
class ApprovalEnvelope:
    """One normalized approval request.

    Frozen: a decision already taken must not be editable by a later caller.
    """

    approval_id: str
    authority: str
    allow_permitted: bool
    forbidden_reasons: tuple[str, ...]
    action: str
    target: str
    reason: str
    scope: str
    risk: str
    #: The thread this approval was raised on. The contract addresses the relay
    #: thread-scoped, so a decision arriving under a DIFFERENT thread's URL is a
    #: mismatch to refuse rather than an id to look up globally.
    thread_id: str | None = None
    #: The JSON-RPC `id` of the provider's `requestApproval` server request, when one
    #: is waiting. The provider correlates the response by THIS value and blocks until
    #: it arrives, so an envelope that drops it can be decided but never answered.
    #:
    #: `None` is a legitimate state, not a defect: `FakeAgentBridge` streams
    #: `approval_required` with no provider request beneath it, and Phase 4's inert
    #: activity events are exactly that. Delivery reports "nothing to answer" for those
    #: rather than inventing an id.
    request_id: object | None = None


def normalize_approval(
    event: dict[str, Any],
    forbidden_scope: Sequence[str],
    *,
    thread_id: str | None = None,
    request_id: object | None = None,
) -> ApprovalEnvelope:
    """Turn a provider `approval_required` payload into a decision envelope.

    `allow_permitted` is True only when BOTH hold: the authority is technical, and
    readiness forbids nothing. Two independent reasons to refuse, evaluated before any
    control is exposed (FR-018).

    `request_id` is the provider's JSON-RPC correlation id, passed IN for the same
    reason `forbidden_scope` is: it belongs to the transport, and taking it as a
    parameter keeps this module free of any protocol import.
    """
    raw_authority = event.get("required_authority")
    authority = TECHNICAL if raw_authority == TECHNICAL else NAMED_HUMAN
    reasons = tuple(forbidden_scope)
    return ApprovalEnvelope(
        approval_id=str(event.get("approval_id", _UNKNOWN)),
        authority=authority,
        allow_permitted=authority == TECHNICAL and not reasons,
        forbidden_reasons=reasons,
        action=str(event.get("action", _UNKNOWN)),
        target=str(event.get("target", _UNKNOWN)),
        reason=str(event.get("reason", _UNKNOWN)),
        scope=str(event.get("scope", _UNKNOWN)),
        risk=str(event.get("risk", _UNKNOWN)),
        thread_id=thread_id,
        request_id=request_id,
    )


def forbidden_scope_for(repo_root: Path | str, table: str | None) -> tuple[str, ...]:
    """The readiness gate's forbidden-scope sentences for one table.

    **Fails CLOSED.** A lookup that raises, or a turn with no table in scope, returns
    a refusal sentence rather than an empty tuple -- because an empty tuple is how
    this module says "readiness forbids nothing", which would hand out an allow
    control on the strength of a crash. Reporting the error while continuing to refuse
    is the required posture.
    """
    if table is None:
        return (
            "No table is in scope for this turn, so its readiness gate could not be "
            "read; a technical allow is refused until one is named.",
        )
    try:
        document = build_table_next_document(repo_root, table)
    except Exception as failure:  # noqa: BLE001 -- any failure must refuse, not permit
        return (
            f"The readiness gate for {table!r} could not be read ({failure}); "
            "a technical allow is refused until it can be.",
        )
    return tuple(document.get("forbidden_scope", ()))


class StaleApproval(Exception):
    """The decision does not correspond to a live, allowable approval request."""


class PendingApprovals:
    """Approvals awaiting a decision, each decidable exactly once.

    **Burning the id on ANY decision -- allow or deny -- is deliberate.** If only
    allows consumed the id, a denied request could be re-submitted as an allow, which
    turns "deny" into "ask again until it works". SC-005's allow-once is really
    decide-once.

    **`allow=True` on a non-allowable envelope raises rather than degrading to a
    deny.** Silently recording a deny would tell the caller their allow was
    processed. The refusal has to be audible.
    """

    def __init__(self) -> None:
        self._live: dict[str, ApprovalEnvelope] = {}
        self._decided: dict[str, str] = {}

    def register(self, envelope: ApprovalEnvelope) -> None:
        """Make one approval decidable, evicting the oldest if the ledger is full.

        Bounded by COUNT rather than by turn lifetime: Phase 4 streams an
        `approval_required` as inert activity beside a `turn_completed` in the same
        turn, so an approval outliving its turn is the normal case, not a leak. Memory
        is the only store FR-035 allows, so something must cap it -- and evicting the
        OLDEST keeps the approval an analyst is most likely looking at right now.
        """
        self._live[envelope.approval_id] = envelope
        while len(self._live) > _LIVE_RETENTION:
            oldest = next(iter(self._live))
            del self._live[oldest]

    def envelope(self, approval_id: str) -> ApprovalEnvelope | None:
        """The live envelope, or None if it is unknown or already decided.

        Read-only: lets a caller distinguish "impermissible" (403) from "not awaiting a
        decision" (409) without consuming the id to find out.
        """
        return self._live.get(approval_id)

    def decide(
        self, approval_id: str, allow: bool, *, thread_id: str | None = None
    ) -> str:
        """Record one decision, or raise `StaleApproval`.

        Reads as its four refusals then its one effect. Each guard is its own method so
        the reason for a refusal has a name, and so this one stays a list of questions
        rather than a nest of conditions.
        """
        envelope = self._claim(approval_id, thread_id)
        self._refuse_impermissible_allow(envelope, allow)
        outcome = "allowed" if allow else "denied"
        self._decided[approval_id] = outcome
        del self._live[approval_id]
        self._evict_if_needed()
        return outcome

    def _claim(self, approval_id: str, thread_id: str | None) -> ApprovalEnvelope:
        """The live envelope for this id on this thread, or raise.

        Three ways an id fails to name a decidable approval -- already decided, never
        registered, or registered on a different thread -- and all three raise
        `StaleApproval`, because to the caller they are one fact: not yours to decide.
        """
        if approval_id in self._decided:
            raise StaleApproval(
                f"approval {approval_id!r} was already decided "
                f"({self._decided[approval_id]})"
            )
        envelope = self._live.get(approval_id)
        if envelope is None:
            raise StaleApproval(f"approval {approval_id!r} is not awaiting a decision")
        if self._belongs_to_another_thread(envelope, thread_id):
            raise StaleApproval(
                f"approval {approval_id!r} was not raised on thread {thread_id!r}"
            )
        return envelope

    @staticmethod
    def _belongs_to_another_thread(
        envelope: ApprovalEnvelope, thread_id: str | None
    ) -> bool:
        """True only when both sides name a thread and the two disagree.

        Either side being `None` means nobody asserted a scope, which is not the same as
        asserting a conflicting one -- so it is not a mismatch to refuse.
        """
        if thread_id is None or envelope.thread_id is None:
            return False
        return thread_id != envelope.thread_id

    @staticmethod
    def _refuse_impermissible_allow(envelope: ApprovalEnvelope, allow: bool) -> None:
        """Raise if this allow was never Studio's to grant.

        Raises rather than degrading to a deny: silently recording a deny would tell the
        caller their allow was processed. The refusal has to be audible.
        """
        if allow and not envelope.allow_permitted:
            raise StaleApproval(
                f"approval {envelope.approval_id!r} may not be allowed here: "
                + "; ".join(envelope.forbidden_reasons or (envelope.authority,))
            )

    def abandon_thread(self, thread_id: str) -> int:
        """Drop every live approval raised on a thread that is over.

        Called when a turn finishes, fails, or is reaped. Without this, an approval
        whose turn no longer exists stays decidable and an allow returns 204 for work
        nothing will ever run -- and `_live` grows for the process lifetime, which
        FR-035 (no database) makes a real bound rather than a theoretical one.
        """
        doomed = [
            approval_id
            for approval_id, envelope in self._live.items()
            if envelope.thread_id == thread_id
        ]
        for approval_id in doomed:
            del self._live[approval_id]
        return len(doomed)

    def _evict_if_needed(self) -> None:
        """Keep the decided-id ledger bounded, oldest first.

        The ids must be remembered long enough to tell "already decided" from
        "unknown" -- collapsing those two would let a replay read as a fresh request.
        Bounded because memory is the only store available.
        """
        while len(self._decided) > _DECIDED_RETENTION:
            oldest = next(iter(self._decided))
            del self._decided[oldest]
