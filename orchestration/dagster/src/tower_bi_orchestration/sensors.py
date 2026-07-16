"""The raw-landing file sensor -- shipped STOPPED (FR-013; Principle V).

Watches the configured landing directory (``SESHAT_RAW_LANDING_DIR``, default
``<repo>/data/raw``) for new/changed ``<table>.csv`` files and requests a run
when one appears. Ships STOPPED; a named human enables it.
"""

from __future__ import annotations

import os
from pathlib import Path

from dagster import DefaultSensorStatus, RunRequest, SkipReason, sensor

from .repo import find_repo_root


def _landing_dir() -> Path:
    override = os.environ.get("SESHAT_RAW_LANDING_DIR")
    return Path(override) if override else find_repo_root() / "data" / "raw"


def build_raw_landing_sensor(full_sequence_job):
    @sensor(
        name="raw_landing_sensor",
        job=full_sequence_job,
        minimum_interval_seconds=300,
        default_status=DefaultSensorStatus.STOPPED,
        description=(
            "Requests a full-sequence run when a raw landing CSV appears or "
            "changes. Ships STOPPED; a named human enables it."
        ),
    )
    def raw_landing_sensor(context):
        landing = _landing_dir()
        if not landing.is_dir():
            return SkipReason(f"landing directory absent: {landing.name}")
        latest = 0.0
        for entry in landing.glob("*.csv"):
            latest = max(latest, entry.stat().st_mtime)
        if latest == 0.0:
            return SkipReason("no raw landing files present")
        previous = float(context.cursor) if context.cursor else 0.0
        if latest <= previous:
            return SkipReason("no new raw landing files since last evaluation")
        context.update_cursor(str(latest))
        return RunRequest(run_key=f"raw-landing-{latest}")

    return raw_landing_sensor
