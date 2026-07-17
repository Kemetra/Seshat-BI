"""seshat.dagster_adapter -- control layer for the Dagster orchestration adapter.

Spec 134 (activates spec 024 / F030). Constants and small read-only units only;
this package NEVER imports dagster -- the runtime always runs as a child
process in the orchestration project's own environment
(``orchestration/dagster/``). Authority boundary: the gate exit code and the
named human decide every readiness stage; nothing in this package writes a
readiness ``status``, a ``Gate status``, or an ``approvals[]`` entry.
"""

from __future__ import annotations

# The exact dagster pin the orchestration project must carry (spec 024
# auto-update posture: PR-only updates, no automerge majors). The dagster-dbt
# pin was DROPPED by spec 135 (FR-011 owner decision, 2026-07-17): no released
# dagster-dbt accepts dbt-core 1.12 and the dbt engine's execution path never
# imports dagster-dbt (it routes through seshat.dbt), so the unused library is
# removed rather than downgrading the spec-133 dbt pins.
PINNED_DAGSTER = "1.13.14"

# The canonical asset vocabulary, in graph order (spec 024; the extra
# live_validate row is the acceptance step recorded alongside the eleven).
ASSET_ORDER: tuple[str, ...] = (
    "raw_source_file",
    "bronze_table",
    "source_profile",
    "source_map",
    "silver_tables",
    "gold_tables",
    "live_validate",
    "metric_contracts",
    "semantic_model",
    "dashboard_blueprint",
    "handoff_pack",
    "publish_execution_evidence",
)

# The closed job vocabulary the runner may execute (contracts/dagster-cli.md).
ALLOWED_JOBS: frozenset[str] = frozenset({"full_sequence_job", "through_gold_job"})

# Execution outcome words. NEVER the readiness token "pass" (hard rule #9 /
# templates/dagster-run-evidence.md).
OUTCOMES: frozenset[str] = frozenset(
    {"materialized", "failed", "skipped", "blocked", "deferred"}
)
