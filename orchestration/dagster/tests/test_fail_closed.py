"""US1: a failed gate asset halts every downstream asset and fails the run.

In-process ``materialize()`` over a fixture repo with the gate command forced
to a non-zero exit at ``silver_tables``. Asserts fail-closed propagation, the
failed run status (the CI signal), the evidence trail, and -- the load-bearing
one -- that NOTHING under ``mappings/`` changed (no authored truth).
"""

from __future__ import annotations

from conftest import TABLE, mappings_digest, stub_green_db
from dagster import materialize
from tower_bi_orchestration import commands
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import (
    EvidenceWriter,
    RunMeta,
    finalize_run,
)


def test_failed_gate_halts_downstream_and_fails_the_run(
    green_repo, monkeypatch
) -> None:
    stub_green_db(monkeypatch)

    def failing_gate(argv: list[str], cwd) -> tuple[int, str]:
        return 1, "3 rule violations"

    monkeypatch.setattr(commands, "run_gate_command", failing_gate)
    before = mappings_digest(green_repo)

    result = materialize(build_table_assets(TABLE, green_repo), raise_on_error=False)
    assert result.success is False  # the CI signal

    summary = finalize_run(
        green_repo, "testrun-001", [TABLE], RunMeta(started="2026-07-17T00:00:00Z")
    )
    assert summary["run_status"] == "failed"

    records = {
        row["asset"]: row for row in EvidenceWriter(green_repo, "testrun-001").records()
    }
    assert records["source_map"]["outcome"] == "materialized"  # seam was CLEARED
    silver = records["silver_tables"]
    assert silver["outcome"] == "failed"
    assert silver["exit_code"] == 1
    assert "exit 1" in silver["blocking_reason"]
    for downstream in (
        "gold_tables",
        "live_validate",
        "metric_contracts",
        "semantic_model",
        "dashboard_blueprint",
        "handoff_pack",
        "publish_execution_evidence",
    ):
        row = records[downstream]
        assert row["outcome"] == "skipped", downstream
        assert "upstream STOP edge: silver_tables" in row["blocking_reason"], downstream
        assert row["owner"], downstream

    assert mappings_digest(green_repo) == before  # zero authored truth


def test_green_gates_materialize_through_gold(green_repo, monkeypatch) -> None:
    stub_green_db(monkeypatch)
    assets = build_table_assets(TABLE, green_repo)
    through_gold = [
        asset
        for asset in assets
        if asset.key.path[-1]
        in {
            "raw_source_file",
            "bronze_table",
            "source_profile",
            "source_map",
            "silver_tables",
            "gold_tables",
            "live_validate",
        }
    ]
    result = materialize(through_gold)
    assert result.success is True
    records = {
        row["asset"]: row for row in EvidenceWriter(green_repo, "testrun-001").records()
    }
    assert records["gold_tables"]["outcome"] == "materialized"
    assert records["gold_tables"]["exit_code"] == 0
