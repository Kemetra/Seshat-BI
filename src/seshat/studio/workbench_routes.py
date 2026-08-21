"""Route registration for the spec-140 governed workbench.

Extracted from `app.py` because six routes plus their helpers pushed
`_register_routes` to a cyclomatic complexity of 26 and the module past its
lines-of-code threshold. This is a real boundary rather than a line-count dodge: every
route here belongs to spec 140, they share the proposal registry and the
committed-vs-working-tree distinction, and none of them existed before the workbench.

The two reads of decision state live side by side on purpose. `apply` must read HEAD --
the gate's view, the only authority -- while `review` deliberately shows the working
tree so a reviewer sees pending work. Keeping both in one file makes that difference
reviewable at a glance; it is the whole security model of this feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Request

from seshat import gitutil
from seshat.studio import apply as apply_module
from seshat.studio import decision_routes, evidence, proposals, review_scope


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _json_body(request: Request) -> dict[str, Any]:
    """The request body as a mapping; a non-mapping becomes an empty one.

    Returning {} rather than raising lets each route's own field checks produce the
    contracted 422 with a useful message instead of a framework-shaped error.
    """
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _proposal_id_for(app: FastAPI, proposal_hash: Any) -> str:
    """The prepared proposal whose hash matches, or "" when none does.

    Looking a proposal up BY HASH is deliberate: if a caller could name an id and
    separately submit a hash, the two could disagree and the binding the human reviewed
    would not be the one enforced.
    """
    if not isinstance(proposal_hash, str):
        return ""
    for identifier, proposal in app.state.workbench_proposals.items():
        if proposal.proposal_hash == proposal_hash:
            return identifier
    return ""


class _CommittedReader:
    """Reads a path as it stands at HEAD -- the gate's view, and the only authority."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def file_at_head(self, relative: str) -> str | None:
        result = gitutil.run_subprocess(
            # The SHARED hardening tuple, never a local re-listing: naming
            # core.fsmonitor alone leaves hooksPath and protocol.ext live on a tree
            # this process did not author.
            ["git", *gitutil.GIT_HARDENING, "show", f"HEAD:{relative}"],
            cwd=self._root,
            # run_subprocess sets stdin and timeout but NOT capture_output. Without
            # this, stdout is empty and EVERY committed decision looks absent.
            capture_output=True,
            text=True,
        )
        if getattr(result, "returncode", 1) != 0:
            return None
        return getattr(result, "stdout", "") or None


def _working_tree_decisions(root: Path, relative: str) -> list[dict[str, Any]]:
    """Decisions in the WORKING TREE -- the review view, never authority.

    A missing or malformed file yields [] rather than raising: an unreadable store is
    "nothing to review", and the store's own loader is what reports it as a defect.
    """
    path = root.joinpath(*relative.split("/"))
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(document, dict):
        return []
    entries = document.get("decisions") or []
    return [item for item in entries if isinstance(item, dict)]


@dataclass(frozen=True)
class Deps:
    """The three app-level seams every workbench handler needs.

    Bundled so a handler can be a module-level function instead of a closure. That
    is what lets `register` stay branch-free: the complexity lives in the handler
    that owns it, where it can be read and tested on its own.
    """

    app: Any
    problem: Any
    redact: Any
    snapshot: Any
    api_prefix: str = "/api/v1"


async def table_evidence(table_id: str, *, deps: Deps) -> Any:
    """One table's evidence bundle (spec 140 US1, FR-140-002).

    Read-only. Groups what the projection already exposes -- stages, evidence
    refs, input defects, pending-live boundaries -- so the investigation view
    cannot disagree with the readiness the gate computes.
    """
    try:
        bundle = evidence.bundle_for(deps.snapshot(), table_id)
    except KeyError:
        return deps.problem(
            404,
            "Unknown table",
            "No onboarded table matches that identifier.",
            "Open the Command Room to see the tables in this workspace.",
        )
    return deps.redact(bundle.as_dict())


async def create_proposal(request: Request, *, deps: Deps) -> Any:
    """Prepare an immutable change proposal (spec 140 US2).

    The agent prepares; it does not decide. The response carries the hash and
    revision that bind any later decision.
    """
    payload = await _json_body(request)
    target = payload.get("target_artifact")
    intent = payload.get("intent")
    if not isinstance(target, str) or not isinstance(intent, str):
        return deps.problem(
            422,
            "Incomplete proposal request",
            "Both intent and target_artifact are required.",
            "Describe the change and name the artifact it would touch.",
        )
    proposal = decision_routes.prepare(
        target_artifact=target,
        intent=intent,
        workspace_revision=deps.snapshot().identity.revision,
        table_id=payload.get("table_id"),
    )
    deps.app.state.workbench_proposals[proposal.proposal_id] = proposal
    return deps.redact({**proposal.as_dict(), "stale": False})


async def read_proposal(proposal_id: str, *, deps: Deps) -> Any:
    proposal = deps.app.state.workbench_proposals.get(proposal_id)
    if proposal is None:
        return deps.problem(
            404,
            "Unknown proposal",
            "No prepared proposal matches that identifier.",
            "Prepare the change again to get a current proposal.",
        )
    stale = proposals.is_stale(proposal, deps.snapshot().identity.revision)
    return deps.redact({**proposal.as_dict(), "stale": stale})


async def record_decision(request: Request, *, deps: Deps) -> Any:
    """Record a named-human business decision (spec 140 US3).

    The ONLY route that writes a business decision. It writes into the working
    tree and reports `pending commit`; it never commits, and readiness does not
    move until a human does (FR-140-015, FR-140-021, FR-140-023).
    """
    payload = await _json_body(request)
    # Shape before staleness. A payload with no proposal_hash at all is the WRONG
    # SHAPE (422) -- e.g. a technical tool-approval body, which FR-140-013 keeps a
    # distinct model. Only a hash that is present but unrecognised is a stale or
    # superseded binding (409). Collapsing the two would report a mis-addressed
    # request as if the world had moved.
    if (
        not isinstance(payload.get("proposal_hash"), str)
        or not payload["proposal_hash"].strip()
    ):
        return deps.problem(
            422,
            "Decision not recorded",
            "proposal_hash is required; a business decision must name the exact "
            "proposal it decides. A technical tool approval is a different model "
            "and a different endpoint.",
            "Prepare a proposal, review it, then submit the decision.",
        )
    proposal = deps.app.state.workbench_proposals.get(
        _proposal_id_for(deps.app, payload["proposal_hash"])
    )
    if proposal is None:
        return deps.problem(
            409,
            "Unknown or superseded proposal",
            "That proposal is not the current prepared proposal.",
            "Prepare the change again and re-review it before signing.",
        )
    counter = deps.app.state.workbench_decision_counter = (
        deps.app.state.workbench_decision_counter + 1
    )
    try:
        receipt = decision_routes.record(
            context=decision_routes.WorkspaceContext(
                repo_root=deps.app.state.launch.workspace_root,
                current_revision=deps.snapshot().identity.revision,
                # Explicit: None means eligibility cannot be validated, which the
                # shipped predicate treats as fail-closed.
                authority=None,
                store_rel=decision_routes.DECISION_STORE_REL,
            ),
            payload=payload,
            proposal=proposal,
            decision_id=f"studio-{counter:04d}",
            recorded_at=_now_iso(),
        )
    except decision_routes.RecordRefused as refused:
        return deps.problem(
            refused.status,
            "Decision not recorded",
            refused.detail,
            "Nothing was written. Correct the submission and try again.",
        )
    return deps.redact(
        {
            "written_path": receipt.written_path,
            "decision_id": receipt.decision_id,
            "state": receipt.state,
            "gate_authority": receipt.gate_authority,
        }
    )


async def apply_proposal_route(
    proposal_id: str, request: Request, *, deps: Deps
) -> Any:
    """Apply exactly the reviewed proposal (spec 140 US4).

    Refused unless a COMMITTED decision authorizes it: a recorded decision is
    pending commit until a human commits, and pending commit is not authority.
    """
    proposal = deps.app.state.workbench_proposals.get(proposal_id)
    if proposal is None:
        return deps.problem(
            404,
            "Unknown proposal",
            "No prepared proposal matches that identifier.",
            "Prepare the change again to get a current proposal.",
        )
    try:
        receipt = apply_module.apply_proposal(
            committed=_CommittedReader(deps.app.state.launch.workspace_root),
            proposal=proposal,
            payload=await _json_body(request),
            context=decision_routes.WorkspaceContext(
                repo_root=deps.app.state.launch.workspace_root,
                current_revision=deps.snapshot().identity.revision,
                store_rel=decision_routes.DECISION_STORE_REL,
            ),
            live_available=False,
        )
    except apply_module.ApplyRefused as refused:
        return deps.problem(
            refused.status,
            "Apply refused",
            refused.detail,
            "Nothing was applied.",
        )
    return deps.redact(receipt.as_dict())


async def review(scope: str | None = None, *, deps: Deps) -> Any:
    """The client-review surface for one explicitly selected scope (US5)."""
    try:
        payload = review_scope.review_for(
            scope=scope,
            decisions=_working_tree_decisions(
                deps.app.state.launch.workspace_root,
                decision_routes.DECISION_STORE_REL,
            ),
        )
    except review_scope.ScopeRefused as refused:
        return deps.problem(
            refused.status,
            "Review scope required",
            refused.detail,
            "Select the exact scope to review.",
        )
    return deps.redact(payload)


def register(deps: Deps) -> None:
    """Bind the workbench route handlers to `app`.

    Each handler is a MODULE-LEVEL function taking its dependencies explicitly, so
    this function is a flat list of registrations with no branching of its own. It
    previously nested all six bodies, which made its cyclomatic complexity the SUM
    of theirs (28) while none of that complexity was actually its own.

    `problem`, `redact` and `snapshot` are passed IN rather than re-implemented:
    they are app.py's single definitions of the problem shape, the redaction
    boundary and the workspace projection.
    """
    API_PREFIX = deps.api_prefix
    app = deps.app

    @app.get(f"{API_PREFIX}/tables/{{table_id}}/evidence")
    async def _table_evidence(table_id: str) -> Any:
        return await table_evidence(table_id, deps=deps)

    @app.post(f"{API_PREFIX}/proposals", status_code=201)
    async def _create_proposal(request: Request) -> Any:
        return await create_proposal(request, deps=deps)

    @app.get(f"{API_PREFIX}/proposals/{{proposal_id}}")
    async def _read_proposal(proposal_id: str) -> Any:
        return await read_proposal(proposal_id, deps=deps)

    @app.post(f"{API_PREFIX}/decisions/record", status_code=201)
    async def _record_decision(request: Request) -> Any:
        return await record_decision(request, deps=deps)

    @app.post(f"{API_PREFIX}/proposals/{{proposal_id}}/apply")
    async def _apply_proposal_route(proposal_id: str, request: Request) -> Any:
        return await apply_proposal_route(proposal_id, request, deps=deps)

    @app.get(f"{API_PREFIX}/review")
    async def _review(scope: str | None = None) -> Any:
        return await review(scope, deps=deps)
