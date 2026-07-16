"""Downstream assets: metric_contracts -> semantic_model [HUMAN SEAM] ->
dashboard_blueprint -> handoff_pack -> publish_execution_evidence [publish wall].

The terminal asset only TRIGGERS F016 once ``publish_ready = pass`` -- and
FAILS CLOSED while F016 is absent (spec 024 clarification 2026-06-25): the
publish wall holds even when the only authorized publisher is missing.
"""

from __future__ import annotations

from pathlib import Path

from dagster import AssetKey, asset

from seshat.dagster_adapter.gate import read_gate_state

from .. import commands
from . import halt, writer_for


def _artifact_count(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for entry in directory.iterdir() if entry.is_file())


def build_downstream_assets(table: str, root: Path) -> list:
    prefix = [table]
    table_dir = root / "mappings" / table

    @asset(
        name="metric_contracts",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "live_validate"])],
    )
    def metric_contracts(context) -> None:
        """Reads approved contracts; AUTHORS NONE (spec 024 FR-003)."""
        writer = writer_for(context, root)
        count = _artifact_count(table_dir / "metrics")
        writer.record(
            asset="metric_contracts",
            table=table,
            gate_command=f"n/a -- reads mappings/{table}/metrics/ (authors none)",
            exit_code=None,
            measured={"contracts_found": count},
            outcome="materialized",
        )

    @asset(
        name="semantic_model",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "metric_contracts"])],
    )
    def semantic_model(context) -> None:
        """STOP (the same static gate CI runs) + HUMAN SEAM (the committed
        semantic-model approval; absent -> BLOCK, never self-grant)."""
        writer = writer_for(context, root)
        gate_command = "seshat check + approvals[] read"
        exit_code, output = commands.run_gate_command(commands.checker_argv(), cwd=root)
        if exit_code != 0:
            halt(
                writer,
                asset="semantic_model",
                table=table,
                gate_command=gate_command,
                exit_code=exit_code,
                measured={"output_tail": output},
                outcome="failed",
                reason=f"static governance gate failed: seshat check exit {exit_code}",
                owner="the metric owner",
            )
        approval = read_gate_state(root, table).approval_for("semantic_model_ready")
        if approval is None:
            halt(
                writer,
                asset="semantic_model",
                table=table,
                gate_command=gate_command,
                exit_code=exit_code,
                measured={},
                outcome="blocked",
                reason=(
                    "semantic-model approval absent (read approvals[] from "
                    f"mappings/{table}/readiness-status.yaml: none for stage "
                    "semantic_model_ready)"
                ),
                owner="the metric owner",
            )
        writer.record(
            asset="semantic_model",
            table=table,
            gate_command=gate_command,
            exit_code=exit_code,
            measured={"approved_by": approval.owner, "approved_at": approval.at},
            outcome="materialized",
        )

    @asset(
        name="dashboard_blueprint",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "semantic_model"])],
    )
    def dashboard_blueprint(context) -> None:
        writer = writer_for(context, root)
        count = _artifact_count(table_dir / "design")
        gate_command = f"n/a -- reads mappings/{table}/design/ (design evidence)"
        if count == 0:
            halt(
                writer,
                asset="dashboard_blueprint",
                table=table,
                gate_command=gate_command,
                exit_code=None,
                measured={},
                outcome="blocked",
                reason=f"no committed design evidence under mappings/{table}/design/",
                owner="the dashboard designer",
            )
        writer.record(
            asset="dashboard_blueprint",
            table=table,
            gate_command=gate_command,
            exit_code=None,
            measured={"design_artifacts": count},
            outcome="materialized",
        )

    @asset(
        name="handoff_pack",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "dashboard_blueprint"])],
    )
    def handoff_pack(context) -> None:
        writer = writer_for(context, root)
        count = _artifact_count(table_dir / "handoff")
        gate_command = f"n/a -- reads mappings/{table}/handoff/ (the BI handoff bundle)"
        if count == 0:
            halt(
                writer,
                asset="handoff_pack",
                table=table,
                gate_command=gate_command,
                exit_code=None,
                measured={},
                outcome="blocked",
                reason=f"no committed handoff pack under mappings/{table}/handoff/",
                owner="the BI handoff owner",
            )
        writer.record(
            asset="handoff_pack",
            table=table,
            gate_command=gate_command,
            exit_code=None,
            measured={"handoff_artifacts": count},
            outcome="materialized",
        )

    @asset(
        name="publish_execution_evidence",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "handoff_pack"])],
    )
    def publish_execution_evidence(context) -> None:
        """The publish wall (Principle II): reads ``publish_ready``; may only
        TRIGGER F016; FAILS CLOSED while F016 is absent. Never publishes."""
        writer = writer_for(context, root)
        state = read_gate_state(root, table)
        gate_command = (
            f"reads publish_ready from mappings/{table}/readiness-status.yaml; "
            "triggers F016 if pass"
        )
        if state.publish_ready != "pass":
            halt(
                writer,
                asset="publish_execution_evidence",
                table=table,
                gate_command=gate_command,
                exit_code=None,
                measured={"publish_ready_read": state.publish_ready},
                outcome="blocked",
                reason=f"publish_ready not pass (read: {state.publish_ready})",
                owner="the named publish approver",
            )
        # publish_ready IS pass -- but the F016 Power BI Execution Adapter is
        # parked/absent this slice: FAIL CLOSED, publish nothing (spec 024).
        halt(
            writer,
            asset="publish_execution_evidence",
            table=table,
            gate_command=gate_command,
            exit_code=None,
            measured={"publish_ready_read": "pass", "f016": "unavailable"},
            outcome="blocked",
            reason="F016 publish adapter not available",
            owner="the F016 owner",
        )

    return [
        metric_contracts,
        semantic_model,
        dashboard_blueprint,
        handoff_pack,
        publish_execution_evidence,
    ]
