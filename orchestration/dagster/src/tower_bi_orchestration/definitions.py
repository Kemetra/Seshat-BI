"""The Definitions object: per-table asset groups discovered from
``mappings/<table>/source-map.yaml``, the two jobs, one STOPPED schedule, and
one STOPPED sensor. ``build_definitions`` is the testable factory; module-level
``defs`` is what ``dagster job execute -m tower_bi_orchestration.definitions``
and the CI definitions-load smoke consume."""

from __future__ import annotations

from pathlib import Path

from dagster import Definitions

from .assets import build_table_assets
from .jobs import build_jobs
from .repo import discover_tables, find_repo_root
from .schedules import build_daily_schedule
from .sensors import build_raw_landing_sensor


def build_definitions(root: Path | None = None) -> Definitions:
    root = Path(root) if root is not None else find_repo_root()
    tables = discover_tables(root)
    assets = [asset for table in tables for asset in build_table_assets(table, root)]
    jobs = build_jobs(tables)
    full_sequence_job = jobs[0]
    return Definitions(
        assets=assets,
        jobs=jobs,
        schedules=[build_daily_schedule(full_sequence_job)],
        sensors=[build_raw_landing_sensor(full_sequence_job)],
    )


defs = build_definitions()
