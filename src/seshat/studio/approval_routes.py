"""The technical approval relay: registration and one decision (T024, T026).

Split out of `agent_routes` rather than added to it. That module already carries the
thread, turn, and SSE lifecycle and had reached the ~800-line mark where this repo's
Code Health gate starts objecting; the approval concern is cohesive enough to stand
alone, so the seam falls here naturally rather than being cut to satisfy a threshold.

**What this module does NOT do.** It does not deliver a decision to a provider.
`AgentBridge` exposes `run_turn` and `describe` and no respond seam, while real Codex
sends `item/*/requestApproval` as a JSON-RPC server request carrying an `id` and waits
for a response keyed to it (`tests/fixtures/codex_app_server/approvals.jsonl`). So a
decision here is *accepted and recorded*, not *relayed onward* -- which is exactly why
`app._bootstrap_capabilities` still reports `technical_approvals: False`. Closing that
round trip is the remaining work in Phase 6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Response

from seshat.studio.approvals import (
    StaleApproval,
    forbidden_scope_for,
    normalize_approval,
)

__all__ = [
    "ApprovalRequest",
    "decide_approval",
    "register_approval",
    "selected_table",
]

#: The contract's `decision` enum for a technical approval response. Anything else --
#: including a missing key -- is refused rather than coerced, because the only value
#: worth guessing would be the one that grants permission.
ALLOW_DECISION = "allow_once"
DENY_DECISION = "deny"


def selected_table(thread: Any) -> str | None:
    """The table this thread was opened against, read back from its own opening event.

    Recovered from the event log rather than threaded through `TurnRequest`: the value
    is already recorded in `thread_started`, and adding a fourth field to the request
    would put the same fact in two places that could disagree.
    """
    for event in thread.retained():
        if event.type == "thread_started":
            selected = event.payload.get("selected_table_id")
            return str(selected) if selected else None
    return None


def register_approval(app: FastAPI, thread_id: str, thread: Any, produced: Any) -> None:
    """Make one streamed approval decidable, and only as far as readiness allows.

    Called BEFORE the event is appended, so the id the browser reads from the stream is
    already known to the ledger -- otherwise the panel renders an approval that every
    relay call refuses as unknown (FR-018: the scope check runs before exposure, not
    after the click).

    A `named_human` item is registered too, deliberately. It must be *visible* as a
    prepared summary, and registering it is what lets the relay answer 403 with the real
    reason instead of a bare "unknown approval". `normalize_approval` has already made
    it unallowable, so registration grants nothing.
    """
    forbidden = forbidden_scope_for(
        app.state.launch.workspace_root, selected_table(thread)
    )
    app.state.pending_approvals.register(
        normalize_approval(dict(produced.payload), forbidden, thread_id=thread_id)
    )


@dataclass(frozen=True)
class ApprovalRequest:
    """One decision arriving from the browser, plus the responses it may need.

    A PUBLIC dataclass rather than six parameters. `problem` and `unknown_thread` have
    to be injected -- `agent_routes` owns those response shapes and imports THIS
    module, so reaching back would be an import cycle -- but each injection is another
    argument, and two of them pushed this past the argument-count bar. Bundling makes
    the seam ONE named thing that a caller can construct in one place, which is also
    the honest description of it: this is the request plus how to refuse it.
    """

    app: FastAPI
    thread_id: str
    approval_id: str
    body: dict[str, Any]
    problem: Any
    unknown_thread: Any


def decide_approval(request: ApprovalRequest) -> Response:
    """Record one analyst decision.

    The browser sends a decision and nothing else -- no tool runs here, no artifact is
    written (FR-020). Every refusal path returns a Problem rather than a silent no-op,
    because an approval that appears to succeed and does nothing is worse than one that
    visibly fails.

    **Two refusal codes, because they mean different things to a client.** A `403`
    says the allow itself was impermissible -- readiness forbids the scope, or the
    authority was never Studio's to grant. A `409` says the request was addressed to an
    approval that is not awaiting a decision: unknown, already decided, or raised on a
    different thread. Collapsing them would tell an analyst "try again later" when the
    honest answer is "never".
    """
    approvals = request.app.state.pending_approvals
    if not request.app.state.threads.has_thread(request.thread_id):
        return request.unknown_thread()

    decision = request.body.get("decision")
    if decision not in {ALLOW_DECISION, DENY_DECISION}:
        return request.problem(*_unrecognized_decision(decision))

    allow = decision == ALLOW_DECISION
    envelope = approvals.envelope(request.approval_id)
    if allow and _is_impermissible(envelope):
        return request.problem(*_impermissible_allow(envelope))

    try:
        approvals.decide(request.approval_id, allow=allow, thread_id=request.thread_id)
    except StaleApproval as refused:
        return request.problem(*_not_awaiting_decision(refused))
    return Response(status_code=204)


def _is_impermissible(envelope: Any) -> bool:
    """True when a KNOWN envelope forbids being allowed.

    An unknown envelope is deliberately NOT impermissible here: it is not awaiting a
    decision at all, which `decide` reports as 409. Answering 403 for it would claim
    Studio had judged something it never saw.
    """
    return envelope is not None and not envelope.allow_permitted


def _unrecognized_decision(decision: Any) -> tuple[int, str, str, str]:
    return (
        422,
        "Unrecognized approval decision",
        f"decision must be {ALLOW_DECISION!r} or {DENY_DECISION!r}, not {decision!r}",
        "Re-send the decision using one of the two documented values.",
    )


def _impermissible_allow(envelope: Any) -> tuple[int, str, str, str]:
    return (
        403,
        "That approval may not be allowed here",
        "; ".join(envelope.forbidden_reasons) or f"authority is {envelope.authority}",
        "A named-human ruling or a closed readiness gate cannot be cleared from "
        "Studio; resolve it at its own seam.",
    )


def _not_awaiting_decision(refused: Exception) -> tuple[int, str, str, str]:
    return (
        409,
        "That approval is not awaiting your decision",
        str(refused),
        "Re-read the current approval request; a decision already recorded "
        "cannot be changed here.",
    )
