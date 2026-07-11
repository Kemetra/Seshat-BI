"""Transport-neutral, read-only agent governance operations."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from seshat.agent_next import build_agent_next_document
from seshat.approval_inbox import build_approval_inbox
from seshat.blocker_explainer import build_blocker_explanations
from seshat.evidence_pack import build_evidence_pack
from seshat.status_surface import build_status_projection

SCHEMA_VERSION = "1.0"
OPERATIONS = (
    "seshat_get_status",
    "seshat_get_next_action",
    "seshat_explain_blockers",
    "seshat_prepare_approval_request",
    "seshat_run_static_check",
    "seshat_export_evidence_pack",
)
_SECRET = re.compile(
    r"(?i)(?:postgres(?:ql)?|mysql|mssql|snowflake)://\S+|"
    r"(?:password|pwd|token|secret)\s*[=:]\s*\S+"
)


def _valid_table_name(table: object) -> bool:
    if not isinstance(table, str) or not table:
        return False
    return not any(marker in table for marker in ("/", "\\", ".."))


def _scope_is_blocked(requested: object, forbidden: list[str]) -> bool:
    """True iff the requested scope collides with a forbidden-scope entry."""
    if requested is None:
        return False
    if not isinstance(requested, str):
        raise ValueError("requested_scope must be text")
    words = [word for word in requested.lower().split() if len(word) > 3]
    return any(any(word in scope.lower() for word in words) for scope in forbidden)


def _next_outcome(blocked: bool, source_outcome: str) -> str:
    if blocked or source_outcome in {"stop_blocked", "approval_required"}:
        return "blocked"
    if source_outcome == "input_defect":
        return "input_defect"
    return "ok"


class GovernorService:
    """Bind governance reads to one explicit, immutable workspace root."""

    def __init__(self, workspace_root: Path | str):
        root = Path(workspace_root).resolve()
        if not root.is_dir():
            raise ValueError("workspace must be an existing local directory")
        self.root = root
        self._operations: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "seshat_get_status": self._status,
            "seshat_get_next_action": self._next,
            "seshat_explain_blockers": self._blockers,
            "seshat_prepare_approval_request": self._approval_request,
            "seshat_run_static_check": self._static_check,
            "seshat_export_evidence_pack": self._evidence_pack,
        }

    def _workspace(self, request: dict[str, Any]) -> None:
        value = request.get("workspace")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("workspace is required")
        candidate = Path(value).resolve()
        if candidate != self.root:
            raise ValueError("workspace must match the server-selected local root")

    def _table(self, request: dict[str, Any], *, required: bool = False) -> str | None:
        table = request.get("table")
        if table is None and not required:
            return None
        if not _valid_table_name(table):
            raise ValueError("table must be a local table identifier")
        return table

    def _safe_error(self, error: Exception) -> str:
        message = str(error).replace(str(self.root), "<workspace>")
        return _SECRET.sub("<redacted>", message) or error.__class__.__name__

    def _response(
        self, operation: str, *, outcome: str, error: str | None = None, **details: Any
    ) -> dict[str, Any]:
        """Uniform response envelope. ``details`` carries the optional fields
        (content, evidence, blockers, required_authority, next_action,
        forbidden_scope); everything else keeps its stable default."""
        response = {
            "schema_version": SCHEMA_VERSION,
            "operation": operation,
            "outcome": outcome,
            "content": details.get("content"),
            "evidence": details.get("evidence") or [],
            "blockers": details.get("blockers") or [],
            "required_authority": details.get("required_authority"),
            "next_action": details.get("next_action"),
            "forbidden_scope": details.get("forbidden_scope") or [],
            "read_only_proof": True,
        }
        if error:
            response["error"] = error
        return response

    def call(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        if operation not in self._operations:
            return self._response(
                operation,
                outcome="input_defect",
                error="unsupported governance operation",
            )
        if not isinstance(request, dict):
            return self._response(
                operation, outcome="input_defect", error="request must be an object"
            )
        try:
            self._workspace(request)
            return self._operations[operation](request)
        except (OSError, RuntimeError, ValueError) as exc:
            return self._response(
                operation, outcome="input_defect", error=self._safe_error(exc)
            )

    def _status(self, request: dict[str, Any]) -> dict[str, Any]:
        table = self._table(request)
        projection = build_status_projection(self.root)
        if table:
            projection["tables"] = [
                item
                for item in projection["tables"]
                if table in (item["table"], Path(item["source_path"]).parent.name)
            ]
        return self._response("seshat_get_status", outcome="ok", content=projection)

    def _next(self, request: dict[str, Any]) -> dict[str, Any]:
        table = self._table(request)
        document = build_agent_next_document(self.root, table)
        forbidden = list(document.get("forbidden_scope", []))
        blocked = _scope_is_blocked(request.get("requested_scope"), forbidden)
        outcome = _next_outcome(blocked, str(document.get("outcome", "ok")))
        return self._response(
            "seshat_get_next_action",
            outcome=outcome,
            content=document,
            evidence=list(document.get("evidence", [])),
            blockers=list(document.get("blocking_reasons", [])),
            required_authority=document.get("required_authority"),
            next_action=document.get("next_allowed_action"),
            forbidden_scope=forbidden,
        )

    def _blockers(self, request: dict[str, Any]) -> dict[str, Any]:
        table = self._table(request, required=True)
        result = build_blocker_explanations(self.root)
        items = [item for item in result["items"] if item["table"] == table]
        return self._response(
            "seshat_explain_blockers",
            outcome="blocked" if items else "ok",
            content={"items": items},
            blockers=items,
        )

    def _approval_request(self, request: dict[str, Any]) -> dict[str, Any]:
        table = self._table(request, required=True)
        decision_id = request.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id.strip():
            raise ValueError("decision_id is required")
        inbox = build_approval_inbox(self.root)
        candidates = [item for item in inbox["items"] if item["table"] == table]
        issue = candidates[0] if candidates else None
        content = {
            "decision_id": decision_id,
            "table": table,
            "status": "prepared_not_approved",
            "requested_authority": issue.get("required_authority") if issue else None,
            "supporting_issue": issue,
            "authority_disclaimer": (
                "This request records no approval and grants no readiness."
            ),
        }
        return self._response(
            "seshat_prepare_approval_request",
            outcome="blocked",
            content=content,
            blockers=[issue] if issue else ["named human decision is required"],
            required_authority=content["requested_authority"],
        )

    def _static_check(self, request: dict[str, Any]) -> dict[str, Any]:
        from seshat.kit_lint import is_bootstrapped
        from seshat.registry import all_rules
        from seshat.runner import build_context, collect_findings

        ctx = build_context(self.root)
        findings = collect_findings(
            all_rules(), ctx, bootstrapped=is_bootstrapped(self.root)
        )
        body = [finding.to_dict() for finding in findings]
        blocking = [item for item in body if item["severity"] == "error"]
        return self._response(
            "seshat_run_static_check",
            outcome="blocked" if blocking else "ok",
            content={
                "findings": body,
                "boundary": {
                    "static_checks": "blocked" if blocking else "pass",
                    "live_validation": "not_run",
                    "semantic_correctness_claimed": False,
                },
            },
            blockers=blocking,
        )

    def _evidence_pack(self, request: dict[str, Any]) -> dict[str, Any]:
        table = self._table(request, required=True)
        pack = build_evidence_pack(self.root, table)
        outcome = "input_defect" if pack.get("outcome") == "input_defect" else "ok"
        return self._response(
            "seshat_export_evidence_pack",
            outcome=outcome,
            content=pack,
            blockers=list(pack.get("blockers", [])),
        )
