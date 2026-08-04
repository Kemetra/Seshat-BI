"""Optional MCP v1 stdio adapter for the transport-neutral governor."""

# NO `from __future__ import annotations` here, unlike the rest of the package.
# FastMCP introspects these signatures at runtime to build each tool's input
# schema, and the parameter annotations below reference names that are not module
# globals -- the lazily imported `pydantic.Field` (the SDK and its dependencies
# must stay optional, see tests/unit/test_issue_regression_513_extra_enable.py)
# and the `_Params` fields. Deferred (string) annotations resolve against module
# globals only, so they would fail with `InvalidSignature`.

from pathlib import Path
from typing import Annotated, Any, NamedTuple

from .service import GovernorService

# Server-level context every tool description leans on, so no single tool has to
# restate the readiness model. Stage vocabulary and the four per-stage statuses
# come from templates/readiness-status.yaml; keep them in step with that file.
_INSTRUCTIONS = """Read-only readiness governance for BI pipelines.

Each table advances through seven readiness stages -- source_ready ->
mapping_ready -> silver_ready -> gold_ready -> semantic_model_ready ->
dashboard_ready -> publish_ready. A stage is entered only once the prior stage
passes, and every stage reads not_started, blocked, warning or pass.

Tools report that state and nothing more: they never execute warehouse or Power
BI work, write files, connect to a database, or grant approvals. Human sign-off
is a separate seam outside this server. Every response carries schema_version,
outcome, evidence, blockers and read_only_proof: true, and errors are sanitized
of absolute paths and secrets."""

# Parameter semantics, stated once and shared. The wording is the schema's only
# description of each field, so it carries the constraints GovernorService
# actually enforces (workspace must equal the server root; table rejects path
# separators) rather than leaving an agent to infer them from the name.
_TABLE_RULES = "May not contain '/', '\\' or '..'."
_WORKSPACE_DOC = (
    "Path to the local Seshat BI workspace to read. Must resolve to exactly the "
    "root this server was started with; a parent or subdirectory is refused."
)
_TABLE_OPTIONAL_DOC = (
    "Single table to scope the answer to, matching a table name or its mapping "
    "directory (for example 'retail_store_sales'). Omit to cover every "
    f"onboarded table in the workspace. {_TABLE_RULES}"
)
_TABLE_REQUIRED_DOC = (
    "The one table to report on, matching a table name or its mapping directory "
    f"(for example 'retail_store_sales'). Required. {_TABLE_RULES}"
)
_DECISION_ID_DOC = (
    "Caller's identifier for the decision this request covers, recorded verbatim "
    "in the prepared request. Must be non-empty text."
)
_REQUESTED_SCOPE_DOC = (
    "Plain-text action you intend to take, checked against what readiness "
    "currently forbids; words longer than three characters are matched, and a "
    "collision returns outcome 'blocked' instead of an allowed action. Omit to "
    "simply read the allowed action."
)


class _Params(NamedTuple):
    """The annotated parameter types the six tools draw on."""

    workspace: Any
    table_optional: Any
    table_required: Any
    decision_id: Any
    requested_scope: Any


def _build_params(field: Any) -> _Params:
    """Bind the parameter docs to ``pydantic.Field``, passed in lazily."""
    return _Params(
        workspace=Annotated[str, field(description=_WORKSPACE_DOC)],
        table_optional=Annotated[str | None, field(description=_TABLE_OPTIONAL_DOC)],
        table_required=Annotated[str, field(description=_TABLE_REQUIRED_DOC)],
        decision_id=Annotated[str, field(description=_DECISION_ID_DOC)],
        requested_scope=Annotated[str | None, field(description=_REQUESTED_SCOPE_DOC)],
    )


def _add_get_status(tool: Any, invoke: Any, p: _Params) -> None:
    @tool
    def seshat_get_status(
        workspace: p.workspace, table: p.table_optional = None
    ) -> dict[str, Any]:
        """Report which readiness stage each table currently sits in.

        Use when: you need the overall readiness picture, or one table's stage,
            evidence and blocker list.
        Not for: why a stage is blocked (use seshat_explain_blockers) or what may
            be done next (use seshat_get_next_action).
        Returns: a projection listing each table with its current stage of the
            seven (source_ready .. publish_ready), evidence and blockers.
            Outcome is 'ok' unless an input is malformed.
        Read-only: reads committed files under the workspace and writes nothing.
        """
        return invoke("seshat_get_status", workspace, table=table)


def _add_get_next_action(tool: Any, invoke: Any, p: _Params) -> None:
    @tool
    def seshat_get_next_action(
        workspace: p.workspace,
        table: p.table_optional = None,
        requested_scope: p.requested_scope = None,
    ) -> dict[str, Any]:
        """Return the one action readiness allows now, and refuse anything past it.

        Use when: you need the single permitted next step, or want to check an
            intended action is allowed before starting it.
        Not for: the full stage picture (use seshat_get_status) or blocker detail
            (use seshat_explain_blockers).
        Returns: one allowed action plus forbidden scope, the stop point and the
            authority required to go further. Outcome is 'blocked' when
            requested_scope is forbidden or a named-human decision is
            outstanding.
        Read-only: names the action but never performs it, and grants no
            approval.
        """
        return invoke(
            "seshat_get_next_action",
            workspace,
            table=table,
            requested_scope=requested_scope,
        )


def _add_explain_blockers(tool: Any, invoke: Any, p: _Params) -> None:
    @tool
    def seshat_explain_blockers(
        workspace: p.workspace, table: p.table_required
    ) -> dict[str, Any]:
        """Explain what blocks one table's next stage, and who can clear it.

        Use when: a table is not advancing and you need the concrete reason, the
            missing evidence, the owner, and the recovery action.
        Not for: an all-table overview (use seshat_get_status) or picking the
            next step (use seshat_get_next_action).
        Returns: one entry per blocker for the named table. Outcome is 'blocked'
            when blockers exist and 'ok' when none do.
        Read-only: reports blockers and never clears, waives or overrides one.
        """
        return invoke("seshat_explain_blockers", workspace, table=table)


def _add_prepare_approval_request(tool: Any, invoke: Any, p: _Params) -> None:
    @tool
    def seshat_prepare_approval_request(
        workspace: p.workspace, table: p.table_required, decision_id: p.decision_id
    ) -> dict[str, Any]:
        """Draft the request a named human must rule on, approving nothing.

        Use when: readiness needs a human ruling and you want the request
            assembled with its supporting issue and the authority required.
        Not for: granting, recording or standing in for an approval -- no tool
            here can do that, and a human signs off outside this server.
        Returns: a request with status 'prepared_not_approved', the requested
            authority and the supporting issue. Outcome is always 'blocked', by
            design, because preparing a request advances nothing.
        Read-only: writes no approval receipt and grants no readiness.
        """
        return invoke(
            "seshat_prepare_approval_request",
            workspace,
            table=table,
            decision_id=decision_id,
        )


def _add_run_static_check(tool: Any, invoke: Any, p: _Params) -> None:
    @tool
    def seshat_run_static_check(workspace: p.workspace) -> dict[str, Any]:
        """Run the static governance rules and state what was not checked.

        Use when: you want committed SQL, TMDL, PBIR and readiness artifacts
            checked against the shipped rule set without any database.
        Not for: live data validation -- that needs a database connection and
            stays a separate CLI operation this server never performs.
        Returns: the findings, plus a boundary object recording that
            live_validation was 'not_run' and that semantic correctness is not
            claimed. Outcome is 'blocked' when any finding is error severity.
        Read-only: opens no database connection and writes no file.
        """
        return invoke("seshat_run_static_check", workspace)


def _add_export_evidence_pack(tool: Any, invoke: Any, p: _Params) -> None:
    @tool
    def seshat_export_evidence_pack(
        workspace: p.workspace, table: p.table_required
    ) -> dict[str, Any]:
        """Assemble one table's evidence pack in memory and return it as data.

        Use when: you need a table's collected readiness evidence to review or
            hand off, as a structured response rather than a file.
        Not for: writing the pack to disk -- despite the name nothing is
            exported, and file export stays an explicit CLI operation.
        Returns: the evidence-pack projection for the named table with any
            blockers. Outcome is 'input_defect' when the table cannot be
            resolved.
        Read-only: creates nothing on disk.
        """
        return invoke("seshat_export_evidence_pack", workspace, table=table)


_REGISTRARS = (
    _add_get_status,
    _add_get_next_action,
    _add_explain_blockers,
    _add_prepare_approval_request,
    _add_run_static_check,
    _add_export_evidence_pack,
)


def create_server(repo_root: Path | str):
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    from pydantic import Field

    service = GovernorService(repo_root)
    server = FastMCP(
        "Seshat BI Agent Governor",
        instructions=_INSTRUCTIONS,
        log_level="ERROR",
    )
    tool = server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )

    def invoke(operation: str, workspace: str, **request: Any) -> dict[str, Any]:
        return service.call(operation, {"workspace": workspace, **request})

    params = _build_params(Field)
    for register in _REGISTRARS:
        register(tool, invoke, params)
    return server


def run_stdio(repo_root: Path | str) -> None:
    create_server(repo_root).run(transport="stdio")
