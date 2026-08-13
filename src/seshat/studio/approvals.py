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


def normalize_approval(
    event: dict[str, Any], forbidden_scope: Sequence[str]
) -> ApprovalEnvelope:
    """Turn a provider `approval_required` payload into a decision envelope.

    `allow_permitted` is True only when BOTH hold: the authority is technical, and
    readiness forbids nothing. Two independent reasons to refuse, evaluated before any
    control is exposed (FR-018).
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
        self._live[envelope.approval_id] = envelope

    def envelope(self, approval_id: str) -> ApprovalEnvelope | None:
        """The live envelope, or None if it is unknown or already decided.

        Read-only: lets a caller distinguish "impermissible" (403) from "not awaiting a
        decision" (409) without consuming the id to find out.
        """
        return self._live.get(approval_id)

    def decide(self, approval_id: str, allow: bool) -> str:
        if approval_id in self._decided:
            raise StaleApproval(
                f"approval {approval_id!r} was already decided "
                f"({self._decided[approval_id]})"
            )
        envelope = self._live.get(approval_id)
        if envelope is None:
            raise StaleApproval(f"approval {approval_id!r} is not awaiting a decision")
        if allow and not envelope.allow_permitted:
            raise StaleApproval(
                f"approval {approval_id!r} may not be allowed here: "
                + "; ".join(envelope.forbidden_reasons or (envelope.authority,))
            )
        outcome = "allowed" if allow else "denied"
        self._decided[approval_id] = outcome
        del self._live[approval_id]
        return outcome
