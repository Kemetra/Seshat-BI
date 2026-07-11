"""Optional MCP v1 stdio adapter for the transport-neutral governor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .service import GovernorService


def create_server(repo_root: Path | str):
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations

    service = GovernorService(repo_root)
    server = FastMCP(
        "Seshat BI Agent Governor",
        instructions=(
            "Read-only readiness governance. Tools never execute warehouse or Power BI "
            "work, write files, or grant approvals."
        ),
        log_level="ERROR",
    )
    annotations = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    def invoke(operation: str, workspace: str, **request: Any) -> dict[str, Any]:
        return service.call(operation, {"workspace": workspace, **request})

    @server.tool(annotations=annotations, structured_output=True)
    def seshat_get_status(workspace: str, table: str | None = None) -> dict[str, Any]:
        """Return the committed seven-stage status projection."""
        return invoke("seshat_get_status", workspace, table=table)

    @server.tool(annotations=annotations, structured_output=True)
    def seshat_get_next_action(
        workspace: str,
        table: str | None = None,
        requested_scope: str | None = None,
    ) -> dict[str, Any]:
        """Return one allowed action and refuse scope forbidden by readiness."""
        return invoke(
            "seshat_get_next_action",
            workspace,
            table=table,
            requested_scope=requested_scope,
        )

    @server.tool(annotations=annotations, structured_output=True)
    def seshat_explain_blockers(workspace: str, table: str) -> dict[str, Any]:
        """Explain concrete blockers and their recovery surface."""
        return invoke("seshat_explain_blockers", workspace, table=table)

    @server.tool(annotations=annotations, structured_output=True)
    def seshat_prepare_approval_request(
        workspace: str, table: str, decision_id: str
    ) -> dict[str, Any]:
        """Prepare a named-human request; never record an approval receipt."""
        return invoke(
            "seshat_prepare_approval_request",
            workspace,
            table=table,
            decision_id=decision_id,
        )

    @server.tool(annotations=annotations, structured_output=True)
    def seshat_run_static_check(workspace: str) -> dict[str, Any]:
        """Run existing pure static rules and state the live boundary."""
        return invoke("seshat_run_static_check", workspace)

    @server.tool(annotations=annotations, structured_output=True)
    def seshat_export_evidence_pack(workspace: str, table: str) -> dict[str, Any]:
        """Return an in-memory evidence pack without writing an export."""
        return invoke("seshat_export_evidence_pack", workspace, table=table)

    return server


def run_stdio(repo_root: Path | str) -> None:
    create_server(repo_root).run(transport="stdio")
