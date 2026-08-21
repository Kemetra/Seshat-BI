"""The client-review scope (spec 140, US5, FR-140-018).

Least privilege, filtered SERVER-side. A client-side hide is not a boundary: the data
would still cross the wire, and anything on the wire is reachable.

Two properties this module keeps:

- only decisions in the explicitly selected scope are returned, and an absent scope is
  refused rather than defaulted to everything;
- no technical tool-approval control appears, because FR-140-013 keeps the technical
  and business models distinct and a reviewer must not be handed the wrong one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: What a reviewer may always do. Decline and clarification are never absent (US5
#: acceptance 3): a review surface that only offers "approve" is a consent funnel.
AVAILABLE_RESPONSES: tuple[str, ...] = (
    "approve",
    "decline",
    "request_clarification",
    "acknowledge",
)

#: Fields that must never reach a client-review payload. Technical approval state and
#: raw agent plumbing belong to the analyst surface.
_WITHHELD_FIELDS = frozenset(
    {
        "allow_permitted",
        "forbidden_reasons",
        "tool_approval",
        "request_id",
        "thread_id",
        "risk",
    }
)


@dataclass(frozen=True)
class ScopeRefused(Exception):
    """The review request cannot be served as asked."""

    status: int
    detail: str

    def __str__(self) -> str:  # pragma: no cover - message plumbing
        return self.detail


def _visible_decision(entry: dict[str, Any], scope: str) -> dict[str, Any]:
    """One decision, reduced to what a reviewer needs and allowed to see."""
    return {
        "id": entry.get("id"),
        "scope": scope,
        "question": entry.get("question", ""),
        "answer": entry.get("answer"),
        "state": entry.get("state", "pending_commit"),
        "signer": entry.get("approval", {}).get("approved_by"),
        "reviewed_scope": entry.get("approval", {}).get("reviewed_scope"),
    }


def review_for(*, scope: str | None, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """The review payload for one explicitly selected scope.

    `scope` is required. Defaulting an absent scope to "everything" would invert least
    privilege at exactly the moment a caller forgot to narrow it.
    """
    if not scope or not scope.strip():
        raise ScopeRefused(
            422,
            "an explicit scope is required; a review context is never widened to the "
            "whole workspace by default",
        )

    selected = [
        _visible_decision(entry, scope)
        for entry in decisions
        if entry.get("approval", {}).get("reviewed_scope") == scope
    ]
    payload = {
        "scope": scope,
        "decisions": selected,
        "available_responses": list(AVAILABLE_RESPONSES),
    }
    return _strip_withheld(payload)


def _strip_withheld(payload: Any) -> Any:
    """Remove withheld keys anywhere in the structure.

    Applied to the assembled payload rather than trusting each construction site: a
    future field added upstream is withheld by default instead of leaking until someone
    notices.
    """
    if isinstance(payload, dict):
        return {
            key: _strip_withheld(value)
            for key, value in payload.items()
            if key not in _WITHHELD_FIELDS
        }
    if isinstance(payload, list):
        return [_strip_withheld(item) for item in payload]
    return payload
