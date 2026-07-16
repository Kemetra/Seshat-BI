"""The daily schedule -- shipped STOPPED (FR-013; Principle V).

Enabling it is a named-human action (in the Dagster UI or via a deliberate
default-status change reviewed in a PR); this slice never turns it on.
"""

from __future__ import annotations

from dagster import DefaultScheduleStatus, ScheduleDefinition


def build_daily_schedule(full_sequence_job) -> ScheduleDefinition:
    return ScheduleDefinition(
        name="daily_full_sequence_schedule",
        job=full_sequence_job,
        cron_schedule="0 6 * * *",
        execution_timezone="UTC",
        default_status=DefaultScheduleStatus.STOPPED,
        description=(
            "Daily unattended run of the full medallion sequence. Ships STOPPED; "
            "a named human enables it."
        ),
    )
