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
from ..evidence_writer import AssetOutcome
from . import halt, writer_for


def _artifact_count(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for entry in directory.iterdir() if entry.is_file())


def _metric_contracts_asset(table: str, root: Path):
    @asset(
        name="metric_contracts",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "live_validate"])],
    )
    def metric_contracts(context) -> None:
        """Reads approved contracts; AUTHORS NONE (spec 024 FR-003)."""
        writer = writer_for(context, root)
        count = _artifact_count(root / "mappings" / table / "metrics")
        writer.record(
            AssetOutcome(
                asset="metric_contracts",
                table=table,
                gate_command=(f"n/a -- reads mappings/{table}/metrics/ (authors none)"),
                exit_code=None,
                measured={"contracts_found": count},
                outcome="materialized",
            )
        )

    return metric_contracts


def _semantic_model_asset(table: str, root: Path):
    @asset(
        name="semantic_model",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "metric_contracts"])],
    )
    def semantic_model(context) -> None:
        """STOP (the same static gate CI runs) + HUMAN SEAM (the committed
        semantic-model approval; absent -> BLOCK, never self-grant)."""
        writer = writer_for(context, root)
        base = dict(
            asset="semantic_model",
            table=table,
            gate_command="seshat check + approvals[] read",
        )
        exit_code, output = commands.run_gate_command(commands.checker_argv(), cwd=root)
        if exit_code != 0:
            halt(
                writer,
                AssetOutcome(
                    **base,
                    exit_code=exit_code,
                    measured={"output_tail": output},
                    outcome="failed",
                    blocking_reason=(
                        f"static governance gate failed: seshat check exit {exit_code}"
                    ),
                    owner="the metric owner",
                ),
            )
        approval = read_gate_state(root, table).approval_for("semantic_model_ready")
        if approval is None:
            halt(
                writer,
                AssetOutcome(
                    **base,
                    exit_code=exit_code,
                    measured={},
                    outcome="blocked",
                    blocking_reason=(
                        "semantic-model approval absent (read approvals[] from "
                        f"mappings/{table}/readiness-status.yaml: none for stage "
                        "semantic_model_ready)"
                    ),
                    owner="the metric owner",
                ),
            )
        writer.record(
            AssetOutcome(
                **base,
                exit_code=exit_code,
                measured={"approved_by": approval.owner, "approved_at": approval.at},
                outcome="materialized",
            )
        )

    return semantic_model


def _committed_artifacts_asset(table: str, root: Path, spec: dict):
    """Shared shape for the two read-committed-artifacts assets
    (dashboard_blueprint reads design/, handoff_pack reads handoff/)."""

    @asset(
        name=spec["asset"],
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, spec["upstream"]])],
    )
    def committed_artifacts(context) -> None:
        writer = writer_for(context, root)
        count = _artifact_count(root / "mappings" / table / spec["directory"])
        base = dict(
            asset=spec["asset"],
            table=table,
            gate_command=(
                f"n/a -- reads mappings/{table}/{spec['directory']}/ ({spec['label']})"
            ),
            exit_code=None,
        )
        if count == 0:
            halt(
                writer,
                AssetOutcome(
                    **base,
                    measured={},
                    outcome="blocked",
                    blocking_reason=(
                        f"no committed {spec['label']} under "
                        f"mappings/{table}/{spec['directory']}/"
                    ),
                    owner=spec["owner"],
                ),
            )
        writer.record(
            AssetOutcome(
                **base,
                measured={spec["measure_key"]: count},
                outcome="materialized",
            )
        )

    return committed_artifacts


_DASHBOARD_SPEC = {
    "asset": "dashboard_blueprint",
    "upstream": "semantic_model",
    "directory": "design",
    "label": "design evidence",
    "owner": "the dashboard designer",
    "measure_key": "design_artifacts",
}

_HANDOFF_SPEC = {
    "asset": "handoff_pack",
    "upstream": "dashboard_blueprint",
    "directory": "handoff",
    "label": "handoff pack",
    "owner": "the BI handoff owner",
    "measure_key": "handoff_artifacts",
}


def _publish_asset(table: str, root: Path):
    @asset(
        name="publish_execution_evidence",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "handoff_pack"])],
    )
    def publish_execution_evidence(context) -> None:
        """The publish wall (Principle II): reads ``publish_ready``; may only
        TRIGGER F016; FAILS CLOSED while F016 is absent. Never publishes."""
        writer = writer_for(context, root)
        state = read_gate_state(root, table)
        base = dict(
            asset="publish_execution_evidence",
            table=table,
            gate_command=(
                f"reads publish_ready from mappings/{table}/readiness-status.yaml; "
                "triggers F016 if pass"
            ),
            exit_code=None,
        )
        if state.publish_ready != "pass":
            halt(
                writer,
                AssetOutcome(
                    **base,
                    measured={"publish_ready_read": state.publish_ready},
                    outcome="blocked",
                    blocking_reason=(
                        f"publish_ready not pass (read: {state.publish_ready})"
                    ),
                    owner="the named publish approver",
                ),
            )
        # publish_ready IS pass -- but the F016 Power BI Execution Adapter is
        # parked/absent this slice: FAIL CLOSED, publish nothing (spec 024).
        halt(
            writer,
            AssetOutcome(
                **base,
                measured={"publish_ready_read": "pass", "f016": "unavailable"},
                outcome="blocked",
                blocking_reason="F016 publish adapter not available",
                owner="the F016 owner",
            ),
        )

    return publish_execution_evidence


def build_downstream_assets(table: str, root: Path) -> list:
    return [
        _metric_contracts_asset(table, root),
        _semantic_model_asset(table, root),
        _committed_artifacts_asset(table, root, _DASHBOARD_SPEC),
        _committed_artifacts_asset(table, root, _HANDOFF_SPEC),
        _publish_asset(table, root),
    ]
