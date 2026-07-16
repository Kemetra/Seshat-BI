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

from ..evidence_writer import AssetOutcome, EvidenceWriter


def run_id_for(context) -> str:
    """The evidence run id: the runner's env override (so the parent process
    knows where records land) or Dagster's own run id."""
    return os.environ.get("SESHAT_DAGSTER_RUN_ID") or context.run_id


def writer_for(context, root: Path) -> EvidenceWriter:
    return EvidenceWriter(root, run_id_for(context))


def halt(writer: EvidenceWriter, outcome: AssetOutcome) -> None:
    """Record a halted outcome and FAIL CLOSED (raise ``dagster.Failure``)."""
    writer.record(outcome)
    raise Failure(
        description=(
            f"[{outcome.table}] {outcome.asset} {outcome.outcome}: "
            f"{outcome.blocking_reason}"
        )
    )


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
