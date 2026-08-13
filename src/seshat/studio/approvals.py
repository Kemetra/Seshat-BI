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
from typing import Any, Sequence

__all__ = [
    "NAMED_HUMAN",
    "TECHNICAL",
    "ApprovalEnvelope",
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
