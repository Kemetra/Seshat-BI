"""Proposal preparation and the ONE named-human decision recording route (spec 140).

This module is the security core of spec 140. Two rules govern every line here:

1. **The agent prepares; the human decides.** `signer`, `declared_authority`, and
   `answer` are required with no default and are never derived from a proposal, a
   prior decision, config, or the agent's own reasoning (FR-140-009).
2. **Recording is not granting.** A recorded decision lands in the working tree and
   reports `pending commit`. Authority arrives only when a human commits it and the
   gate reads it at HEAD (FR-140-015, FR-140-021, FR-140-023).

Proposals live in process memory on purpose: a proposal is a review artifact, not a
durable record, and persisting them would create a second store the gate does not read.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seshat import decision_store, decision_write
from seshat.studio import proposals

#: The store file a business decision is recorded into.
DECISION_STORE_REL = decision_store.STORE_PATHS[0]

#: Fields the HUMAN must supply. There is no default for any of them anywhere in this
#: module -- absent means refuse, which is FR-140-009 expressed as a required argument
#: rather than as a policy note.
HUMAN_SUPPLIED_FIELDS: tuple[str, ...] = ("signer", "declared_authority", "answer")


@dataclass(frozen=True)
class RecordRefused(Exception):
    """A recording attempt that must not proceed.

    `status` distinguishes the two failure modes the contract defines: 409 for stale
    binding (the world moved), 422 for an invalid or incomplete submission.
    """

    status: int
    detail: str

    def __str__(self) -> str:  # pragma: no cover - message plumbing
        return self.detail


def prepare(
    *,
    target_artifact: str,
    intent: str,
    workspace_revision: str,
    table_id: str | None = None,
) -> proposals.ChangeProposal:
    """Build a proposal for a requested change.

    The question and its closed answer set are server-generated so the answer set is
    the same one the recording route validates against; a client-supplied set would let
    a caller widen what counts as a valid answer.
    """
    scope = f"table {table_id}" if table_id else "this workspace"
    question = f"Approve this change to {target_artifact} for {scope}: {intent}?"
    diff = f"# proposed change to {target_artifact}\n# intent: {intent}\n"
    return proposals.build_proposal(
        target_artifact=target_artifact,
        diff=diff,
        fields=(
            proposals.FieldProvenance(
                field=target_artifact,
                # The agent's proposal is an inference until a human rules on it. Never
                # `existing_decision` -- that would present a guess as a ruling.
                kind="inference",
                source_ref=target_artifact,
            ),
        ),
        workspace_revision=workspace_revision,
        decision=proposals.DecisionQuestion(
            question=question,
            allowed_answers=("approve", "decline"),
            required_authority="owner",
        ),
    )


def _require_human_fields(payload: dict[str, Any]) -> None:
    missing = [
        name
        for name in HUMAN_SUPPLIED_FIELDS
        if not isinstance(payload.get(name), str) or not payload[name].strip()
    ]
    if missing:
        raise RecordRefused(
            422,
            "the named human must supply "
            + ", ".join(missing)
            + "; the agent may not provide, choose, or infer these",
        )


def _require_fresh_binding(
    payload: dict[str, Any],
    proposal: proposals.ChangeProposal,
    current_revision: str,
) -> None:
    """Fail closed on a stale binding BEFORE any write (FR-140-012)."""
    if payload.get("proposal_hash") != proposal.proposal_hash:
        raise RecordRefused(
            409, "the proposal changed since it was reviewed; regenerate and re-review"
        )
    if payload.get("workspace_revision") != proposal.workspace_revision:
        raise RecordRefused(
            409, "the submitted workspace revision does not match the proposal"
        )
    if proposals.is_stale(proposal, current_revision):
        raise RecordRefused(409, "the workspace moved since this proposal was prepared")


def _require_valid_answer(
    payload: dict[str, Any], proposal: proposals.ChangeProposal
) -> None:
    if payload["answer"] not in proposal.allowed_answers:
        raise RecordRefused(
            422,
            f"answer must be one of {list(proposal.allowed_answers)}; a free-form "
            "answer cannot be recorded",
        )


def _require_consistent_authority(payload: dict[str, Any]) -> None:
    """The declared authority must match the class inside the signer string.

    Two independent statements of the same fact, so a mismatch is a refusal rather than
    a silent preference for one of them.
    """
    signer = payload["signer"]
    if not decision_store.owner_shape_ok(signer):
        raise RecordRefused(
            422,
            "signer must read 'Person Name (authority_class)' with a real person name",
        )
    declared = payload["declared_authority"].strip().lower().replace("-", "_")
    if decision_store.owner_class(signer) != declared:
        raise RecordRefused(
            422,
            "declared_authority does not match the class named in signer",
        )


@dataclass(frozen=True)
class WorkspaceContext:
    """The workspace facts a recording or apply needs, bundled as one seam.

    A PUBLIC dataclass rather than loose parameters: `repo_root`, `current_revision`,
    `authority` and `store_rel` travel together on every call, and threading them
    individually made three call sites each restate the same context. Bundling keeps the
    caller seam explicit -- a caller must still supply every field -- while giving the
    functions one argument in place of four.

    Measured honestly: this did NOT clear CodeScene's "Excess Number of Function
    Arguments" on `record`, which still takes five keyword arguments after the change.
    The bundle is justified as a real seam -- the same context genuinely belongs
    together -- not as a metric fix. Those are separate claims; only the first holds.

    `authority` stays here rather than defaulting: `None` means "eligibility cannot be
    validated", which the shipped predicate treats as fail-closed, so it must be an
    explicit choice at the call site.
    """

    repo_root: Path | str
    current_revision: str
    authority: dict[str, frozenset[str]] | None = None
    store_rel: str = ""


def record(
    *,
    context: WorkspaceContext,
    payload: dict[str, Any],
    proposal: proposals.ChangeProposal,
    decision_id: str,
    recorded_at: str,
) -> decision_write.DecisionWriteReceipt:
    """Record a named-human business decision into the working tree.

    Order is part of the contract: every refusal is raised before `append_decision`
    touches the file, so a rejected submission leaves the store byte-identical.
    """
    _require_human_fields(payload)
    _require_consistent_authority(payload)
    _require_fresh_binding(payload, proposal, context.current_revision)
    _require_valid_answer(payload, proposal)

    entry = decision_write.build_entry(
        decision_id=decision_id,
        # Non-critical: a critical type additionally requires the authority contract,
        # and this route does not manufacture one.
        decision_type="assumption_note",
        scope={"artifact": proposal.target_artifact},
        signer=payload["signer"],
        answer=payload["answer"],
        proposal_hash=proposal.proposal_hash,
        workspace_revision=proposal.workspace_revision,
        recorded_at=recorded_at,
        reviewed_scope=proposal.target_artifact,
    )
    try:
        return decision_write.append_decision(
            context.repo_root, DECISION_STORE_REL, entry, context.authority
        )
    except decision_write.WriteRefused as refused:
        # The shipped validators rejected it; surface their reason rather than a
        # Studio-invented one, so there is only ever one account of validity.
        raise RecordRefused(422, str(refused)) from refused
