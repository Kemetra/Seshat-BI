"""The 11-asset medallion graph (spec 024 shape), built per mapped table.

Shared helpers only in this module; the assets live in ``ingest.py`` /
``gates.py`` / ``downstream.py``. Every asset records exactly one execution
outcome (never the readiness token ``pass``); every halt raises
``dagster.Failure`` so downstream assets are SKIPPED and the run terminates
``failed`` -- the CI signal (FR-004/FR-013 of spec 024).
"""

from __future__ import annotations

import os
from pathlib import Path

from dagster import Failure

from ..evidence_writer import EvidenceWriter


def run_id_for(context) -> str:
    """The evidence run id: the runner's env override (so the parent process
    knows where records land) or Dagster's own run id."""
    return os.environ.get("SESHAT_DAGSTER_RUN_ID") or context.run_id


def writer_for(context, root: Path) -> EvidenceWriter:
    return EvidenceWriter(root, run_id_for(context))


def halt(
    writer: EvidenceWriter,
    *,
    asset: str,
    table: str,
    gate_command: str,
    exit_code: int | None,
    measured: dict,
    outcome: str,
    reason: str,
    owner: str,
) -> None:
    """Record a halted outcome and FAIL CLOSED (raise ``dagster.Failure``)."""
    writer.record(
        asset=asset,
        table=table,
        gate_command=gate_command,
        exit_code=exit_code,
        measured=measured,
        outcome=outcome,
        blocking_reason=reason,
        owner=owner,
    )
    raise Failure(description=f"[{table}] {asset} {outcome}: {reason}")


def build_table_assets(table: str, root: Path) -> list:
    """All 12 asset definitions (11 graph assets + live_validate) for one table."""
    from .downstream import build_downstream_assets
    from .gates import build_gate_assets
    from .ingest import build_ingest_assets

    return [
        *build_ingest_assets(table, root),
        *build_gate_assets(table, root),
        *build_downstream_assets(table, root),
    ]
