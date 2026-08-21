"""Route registration for Operations and Client Review (spec 141).

Handlers are MODULE-LEVEL functions taking a frozen `Deps`, so `register` is a flat list
of registrations with no branching of its own. That pattern is not cosmetic: nesting
handlers inside a registrar makes the registrar's cyclomatic complexity the SUM of
theirs, which is exactly what had to be undone in `workbench_routes.py`.

The two reads of decision state sit side by side on purpose, and the difference is the
security model:

- **Client Review reads HEAD.** Only committed, approved evidence is client-facing
  (FR-141-021); a working-tree decision appears as a pending item, never as a decision.
- **History reads both.** Ephemeral runs come from process state and die on restart;
  durable ones cite committed state (FR-141-009, FR-141-010).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

from seshat import decision_write
from seshat.studio import decision_routes, exports, operations, review_scope

#: Fields a client-facing decision entry may carry. An ALLOWLIST: anything added
#: upstream later is absent by default rather than disclosed (FR-141-012).
_CLIENT_DECISION_FIELDS: tuple[str, ...] = ("id", "answer", "scope", "decision_type")


@dataclass(frozen=True)
class Deps:
    """The app-level seams every Operations handler needs.

    Bundled so each handler can be a module-level function rather than a closure, which
    is what keeps `register` branch-free.
    """

    app: Any
    problem: Any
    redact: Any
    api_prefix: str = "/api/v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _workspace_root(deps: Deps) -> Path:
    return Path(deps.app.state.launch.workspace_root)


async def _json_body(request: Request) -> dict[str, Any]:
    """The body as a mapping; a non-mapping becomes an empty one.

    Returning {} rather than raising lets each handler's own field checks produce the
    contracted 422 with a useful message instead of a framework-shaped error.
    """
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


async def operations_report(*, deps: Deps) -> Any:
    """Categorical health for the seven components (US1).

    No aggregate is computed here or anywhere: `ComponentDiagnostic` has no numeric
    field, so the payload cannot carry a roll-up (FR-141-002).
    """
    report = operations.report(_workspace_root(deps))
    return deps.redact({"components": [d.as_dict() for d in report]})


async def operations_recover(request: Request, *, deps: Deps) -> Any:
    """Refuse a recovery action (FR-141-005, FR-141-018).

    Unconditional by design. A diagnostic may NAME a recovery action, and Operations
    does that in the report's `recovery_action` field, but executing one is a mutation
    and must go through the same technical-approval and readiness policy as any other.
    Until that path exists, this refuses -- refusal is the default state, not an
    unfinished branch.
    """
    payload = await _json_body(request)
    component = payload.get("component", "<unnamed>")
    return deps.problem(
        422,
        "Recovery not executed",
        f"Executing a recovery action for {component} requires the same technical "
        "approval and readiness policy as any other mutation. Operations can "
        "recommend an action; it cannot perform one.",
        "Run the recommended action through the approved path.",
    )


async def operations_history(*, deps: Deps) -> Any:
    """Governed run history, ephemeral and durable (US2).

    Ephemeral runs are read from process state, so a restart loses them by
    construction rather than by cleanup. Durable runs cite committed state.
    """
    root = _workspace_root(deps)
    runs: list[operations.GovernedRunSummary] = []

    for entry in _committed_decisions(deps, root):
        runs.append(
            operations.summarize_run(
                run_id=str(entry.get("id", "")),
                requested=str(entry.get("answer", "")),
                committed_source=str(
                    entry.get("approval", {}).get("evidence_identity", "committed")
                ),
                decision_state="authoritative",
                decided_by=entry.get("approval", {}).get("approved_by"),
            )
        )

    for identifier in getattr(deps.app.state, "workbench_proposals", {}):
        runs.append(
            operations.summarize_run(
                run_id=identifier,
                requested="proposal prepared",
                committed_source=None,
            )
        )

    return deps.redact({"runs": [r.as_dict() for r in runs]})


def _committed_decisions(deps: Deps, root: Path) -> list[dict[str, Any]]:
    """Decisions visible AT HEAD: the gate's view, and the only client-facing one."""
    from seshat.studio import workbench_routes

    reader = workbench_routes._CommittedReader(root)
    return decision_write.decisions_at_head(reader, decision_routes.DECISION_STORE_REL)


async def client_review(scope: str | None = None, *, deps: Deps) -> Any:
    """The client-facing review for one explicit scope (US3).

    Reads committed state only. A recorded-but-uncommitted decision is surfaced under
    `pending_items` -- visible as pending, never counted as a decision (FR-141-021).
    """
    root = _workspace_root(deps)
    try:
        committed = review_scope.review_for(
            scope=scope, decisions=_committed_decisions(deps, root)
        )
    except review_scope.ScopeRefused as refused:
        return deps.problem(
            refused.status,
            "Review scope required",
            refused.detail,
            "Select the exact scope to review.",
        )

    pending = _pending_items(root, scope or "")
    decisions = [
        exports.scrub_for_export(
            entry, allowed=_CLIENT_DECISION_FIELDS, workspace_root=root
        )
        for entry in committed["decisions"]
    ]
    return deps.redact(
        {
            "scope": scope,
            "decisions": decisions,
            "pending_items": pending,
            "narrative": exports.build_narrative(
                selected_facts=tuple(str(d.get("answer", "")) for d in decisions),
                pending_items=tuple(pending),
            ),
            "available_responses": committed["available_responses"],
        }
    )


def _pending_items(root: Path, scope: str) -> list[str]:
    """Working-tree decisions not yet committed, as pending descriptions.

    A separate list rather than a filtered view of the decisions, so a renderer cannot
    omit them while rendering the happy path.
    """
    import yaml

    path = root / decision_routes.DECISION_STORE_REL
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(document, dict):
        return []
    committed_ids = {str(entry.get("id", "")) for entry in _committed_at_path(root)}
    return [
        f"{entry.get('answer', 'a decision')} -- awaiting commit"
        for entry in document.get("decisions") or []
        if is_pending_for_scope(entry, scope, committed_ids)
    ]


def is_pending_for_scope(entry: object, scope: str, committed_ids: set[str]) -> bool:
    """True when this working-tree entry is pending for the requested scope.

    Public so it can be tested directly: the committed-ids check below is the one that
    keeps an already-committed decision from ALSO appearing as pending, and a
    route-level test cannot distinguish "correctly excluded" from "never reached".

    Each condition is a distinct reason NOT to show an entry, and naming them together
    makes the whole set reviewable rather than four sequential skips.
    """
    if not isinstance(entry, dict):
        return False
    if str(entry.get("id", "")) in committed_ids:
        return False  # already committed: it is a decision, not a pending item
    reviewed = entry.get("approval", {}).get("reviewed_scope")
    return not scope or reviewed == scope


def _committed_at_path(root: Path) -> list[dict[str, Any]]:
    from seshat.studio import workbench_routes

    reader = workbench_routes._CommittedReader(root)
    return decision_write.decisions_at_head(reader, decision_routes.DECISION_STORE_REL)


def names_a_person_and_scope(scope: object, who: object) -> bool:
    """True when an acknowledgement identifies both what was seen and who saw it.

    Named rather than inlined because the four clauses answer one question: recording
    that "someone saw a result" is meaningless without which result and which someone.
    """
    return (
        isinstance(scope, str)
        and bool(scope.strip())
        and isinstance(who, str)
        and bool(who.strip())
    )


async def client_acknowledge(request: Request, *, deps: Deps) -> Any:
    """Record a client acknowledgement -- never a ruling (FR-141-011).

    Writes nothing to the decision store. `ClientAcknowledgment` has no answer field, so
    the two concepts cannot collapse even if a caller sends one.
    """
    payload = await _json_body(request)
    scope = payload.get("scope")
    who = payload.get("acknowledged_by")
    if not names_a_person_and_scope(scope, who):
        return deps.problem(
            422,
            "Acknowledgement not recorded",
            "Both scope and acknowledged_by are required; an acknowledgement names "
            "the person who saw the result.",
            "Supply the scope and who is acknowledging it.",
        )
    ack = exports.ClientAcknowledgment(
        scope=scope, acknowledged_by=who, acknowledged_at=_now_iso()
    )
    return deps.redact(ack.as_dict())


def register(deps: Deps) -> None:
    """Bind the Operations and Client Review handlers to the app.

    Flat by construction: every handler is module-level, so this function has no
    branching of its own.
    """
    app: FastAPI = deps.app
    prefix = deps.api_prefix

    @app.get(f"{prefix}/operations")
    async def _operations() -> Any:
        return await operations_report(deps=deps)

    @app.post(f"{prefix}/operations/recover")
    async def _recover(request: Request) -> Any:
        return await operations_recover(request, deps=deps)

    @app.get(f"{prefix}/operations/history")
    async def _history() -> Any:
        return await operations_history(deps=deps)

    @app.get(f"{prefix}/client-review")
    async def _review(scope: str | None = None) -> Any:
        return await client_review(scope, deps=deps)

    @app.post(f"{prefix}/client-review/acknowledge", status_code=201)
    async def _acknowledge(request: Request) -> Any:
        return await client_acknowledge(request, deps=deps)
