"""Immutable change proposals (spec 140, US2, FR-140-005..008).

A proposal binds a reviewed change to the exact content and workspace revision it was
prepared from. That binding is what lets a later decision be refused when either moves:
without it a human could sign one thing while a different thing gets applied.

Frozen by construction. Any change produces a NEW proposal with a new hash, which
invalidates the prior approval (FR-140-008) rather than silently re-scoping it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

#: Closed vocabulary (FR-140-006). `inference` and `default` are the two kinds that must
#: never be presentable as `existing_decision` -- that would show a guess as a ruling.
PROVENANCE_KINDS: tuple[str, ...] = (
    "discovered_fact",
    "existing_decision",
    "default",
    "inference",
    "new_human_judgment",
)


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    """Where one proposed field's value came from."""

    field: str
    kind: str
    source_ref: str
    author: str | None = None
    recorded_at: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in PROVENANCE_KINDS:
            raise ValueError(
                f"unknown provenance kind {self.kind!r}; expected one of "
                f"{PROVENANCE_KINDS}"
            )

    def as_dict(self) -> dict:
        return {
            "field": self.field,
            "kind": self.kind,
            "source_ref": self.source_ref,
            "author": self.author,
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True)
class ChangeProposal:
    """One immutable proposed change, bound to a hash and a workspace revision."""

    proposal_id: str
    proposal_hash: str
    workspace_revision: str
    target_artifact: str
    diff: str
    question: str
    allowed_answers: tuple[str, ...]
    required_authority: str
    fields: tuple[FieldProvenance, ...] = ()
    validation: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "workspace_revision": self.workspace_revision,
            "target_artifact": self.target_artifact,
            "diff": self.diff,
            "question": self.question,
            "allowed_answers": list(self.allowed_answers),
            "required_authority": self.required_authority,
            "fields": [item.as_dict() for item in self.fields],
            "validation": list(self.validation),
        }


def _canonical_hash(payload: dict) -> str:
    """Content-addressed digest. Sorted keys and tight separators so an identical
    proposal re-prepared later hashes identically -- otherwise every refresh would
    read as stale."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_proposal(
    *,
    target_artifact: str,
    diff: str,
    fields: tuple[FieldProvenance, ...],
    workspace_revision: str,
    question: str,
    allowed_answers: tuple[str, ...],
    required_authority: str,
    validation: tuple[str, ...] = (),
) -> ChangeProposal:
    """Prepare a proposal. The agent prepares; it does not decide.

    `allowed_answers` is a closed set on purpose: it is what makes FR-140-009
    checkable, since an answer outside the set is refused rather than interpreted.
    """
    digest = _canonical_hash(
        {
            "target": target_artifact,
            "diff": diff,
            "revision": workspace_revision,
            "question": question,
            "answers": list(allowed_answers),
            "authority": required_authority,
        }
    )
    return ChangeProposal(
        proposal_id=digest[:12],
        proposal_hash=digest,
        workspace_revision=workspace_revision,
        target_artifact=target_artifact,
        diff=diff,
        question=question,
        allowed_answers=tuple(allowed_answers),
        required_authority=required_authority,
        fields=tuple(fields),
        validation=tuple(validation),
    )


def is_stale(proposal: ChangeProposal, current_revision: str) -> bool:
    """True once the workspace moved away from what the proposal was prepared from."""
    return proposal.workspace_revision != current_revision
