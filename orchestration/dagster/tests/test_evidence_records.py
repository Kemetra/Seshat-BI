"""US3 + T010: raw evidence records are schema-shaped, halted rows carry a
concrete reason + named owner, and a green through-gold run produces an
end-to-end record set with a succeeded summary."""

from __future__ import annotations

import json

import pytest
from conftest import TABLE, stub_green_db
from dagster import materialize
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import (
    AssetOutcome,
    EvidenceWriter,
    RunMeta,
    finalize_run,
)
from tower_bi_orchestration.jobs import THROUGH_GOLD_ASSETS


class TestEvidenceWriter:
    def test_records_are_schema_shaped_jsonl(self, green_repo) -> None:
        writer = EvidenceWriter(green_repo, "testrun-001")
        writer.record(
            AssetOutcome(
                asset="source_map",
                table=TABLE,
                gate_command="reads Gate status",
                exit_code=None,
                measured={"gate_status": "CLEARED", "open_rows": 0},
                outcome="materialized",
            )
        )
        raw = writer.records_path.read_text(encoding="utf-8").strip()
        row = json.loads(raw)
        assert set(row) == {
            "run_id",
            "asset",
            "table",
            "gate_command",
            "exit_code",
            "measured",
            "outcome",
            "blocking_reason",
            "owner",
            "ts",
        }

    def test_halted_outcome_requires_reason_and_owner(self, green_repo) -> None:
        writer = EvidenceWriter(green_repo, "testrun-001")
        with pytest.raises(ValueError, match="requires blocking_reason"):
            writer.record(
                AssetOutcome(
                    asset="silver_tables",
                    table=TABLE,
                    gate_command="seshat check",
                    exit_code=1,
                    measured={},
                    outcome="failed",
                )
            )

    def test_outcome_vocabulary_is_closed(self, green_repo) -> None:
        writer = EvidenceWriter(green_repo, "testrun-001")
        with pytest.raises(ValueError, match="execution word"):
            writer.record(
                AssetOutcome(
                    asset="gold_tables",
                    table=TABLE,
                    gate_command="seshat check",
                    exit_code=0,
                    measured={},
                    outcome="pass",  # the readiness token is NOT an execution word
                )
            )

    def test_records_are_redacted(self, green_repo, monkeypatch) -> None:
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "supersecretpw")
        writer = EvidenceWriter(green_repo, "testrun-001")
        row = writer.record(
            AssetOutcome(
                asset="live_validate",
                table=TABLE,
                gate_command="seshat validate",
                exit_code=1,
                measured={"output_tail": "auth failed with supersecretpw"},
                outcome="failed",
                # Split so the committed text never carries a whole DSN shape (C2).
                blocking_reason="validate failed: dsn postgresql:"
                + "//u:supersecretpw@h/d",
                owner="warehouse owner",
            )
        )
        text = json.dumps(row)
        assert "supersecretpw" not in text


class TestGreenRunEndToEnd:
    def test_green_through_gold_run_yields_succeeded_summary(
        self, green_repo, monkeypatch
    ) -> None:
        stub_green_db(monkeypatch)
        assets = [
            asset
            for asset in build_table_assets(TABLE, green_repo)
            if asset.key.path[-1] in THROUGH_GOLD_ASSETS
        ]
        result = materialize(assets)
        assert result.success is True
        summary = finalize_run(
            green_repo,
            "testrun-001",
            [TABLE],
            RunMeta(started="2026-07-17T00:00:00Z", trigger="manual-CI"),
        )
        assert summary["run_status"] == "succeeded"
        assert summary["tables"] == [TABLE]
        assert set(summary) == {
            "run_id",
            "commit_sha",
            "started",
            "finished",
            "trigger",
            "tables",
            "run_status",
        }
        records = EvidenceWriter(green_repo, "testrun-001").records()
        by_asset = {row["asset"]: row for row in records}
        for name in THROUGH_GOLD_ASSETS:
            assert by_asset[name]["outcome"] == "materialized", name
        # finalize back-filled the tail assets the job never selected:
        assert by_asset["publish_execution_evidence"]["outcome"] == "skipped"
