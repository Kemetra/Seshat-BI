"""Unit tests for evidence validation + deterministic rendering (spec 134, T019/T020).

The renderer refuses invalid records (the code validator mirrors
schemas/dagster-run-evidence.schema.json) and produces a byte-deterministic
markdown per templates/dagster-run-evidence.md -- outcomes stay execution
words, halted rows carry reason + owner, and no numeric score can appear.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dagster_adapter import evidence

pytestmark = pytest.mark.unit


def _summary(**overrides) -> dict:
    base = {
        "run_id": "run-001",
        "commit_sha": "abc1234",
        "started": "2026-07-17T00:00:00Z",
        "finished": "2026-07-17T00:05:00Z",
        "trigger": "manual-CI",
        "tables": ["demo_table"],
        "run_status": "succeeded",
    }
    base.update(overrides)
    return base


def _record(**overrides) -> dict:
    base = {
        "run_id": "run-001",
        "asset": "source_map",
        "table": "demo_table",
        "gate_command": "reads Gate status",
        "exit_code": None,
        "measured": {"gate_status": "CLEARED", "open_rows": 0},
        "outcome": "materialized",
        "blocking_reason": None,
        "owner": None,
        "ts": "2026-07-17T00:01:00Z",
    }
    base.update(overrides)
    return base


class TestValidateRecords:
    def test_good_records_have_no_errors(self) -> None:
        assert evidence.validate_records(_summary(), [_record()]) == []

    def test_outcome_pass_is_rejected(self) -> None:
        errors = evidence.validate_records(_summary(), [_record(outcome="pass")])
        assert any("outcome" in error for error in errors)

    def test_halted_without_reason_or_owner_is_rejected(self) -> None:
        errors = evidence.validate_records(
            _summary(), [_record(outcome="blocked", blocking_reason=None, owner=None)]
        )
        assert any("blocking_reason" in error for error in errors)

    def test_unknown_keys_are_rejected(self) -> None:
        bad = _record()
        bad["confidence"] = 0.9
        errors = evidence.validate_records(_summary(), [bad])
        assert any("unknown key" in error for error in errors)

    def test_score_keys_are_rejected_even_inside_measured(self) -> None:
        bad = _record(measured={"health_score": 97})
        errors = evidence.validate_records(_summary(), [bad])
        assert any("score" in error.lower() for error in errors)

    def test_bad_run_status_is_rejected(self) -> None:
        errors = evidence.validate_records(_summary(run_status="green"), [_record()])
        assert any("run_status" in error for error in errors)

    def test_unknown_asset_is_rejected(self) -> None:
        errors = evidence.validate_records(_summary(), [_record(asset="mystery_step")])
        assert any("asset" in error for error in errors)


class TestRenderMarkdown:
    def test_rendering_is_deterministic_and_template_shaped(self) -> None:
        records = [
            _record(),
            _record(
                asset="silver_tables",
                gate_command="seshat check",
                exit_code=1,
                measured={},
                outcome="failed",
                blocking_reason="static governance gate failed: seshat check exit 1",
                owner="warehouse owner",
            ),
        ]
        summary = _summary(run_status="failed")
        first = evidence.render_markdown(summary, records)
        second = evidence.render_markdown(summary, records)
        assert first == second
        assert "# Dagster Run Evidence -- `run-001`" in first
        assert "| Run status | `failed` |" in first
        assert "## Per-asset results" in first
        assert "## Blocked / skipped assets" in first
        assert "warehouse owner" in first
        assert "## What this run did NOT write" in first
        assert "pass" not in first.split("## Per-asset results")[1].split("##")[
            0
        ].replace("n/a -- did not run", "").replace("did not run", "")

    def test_rendered_outcomes_are_execution_words(self) -> None:
        text = evidence.render_markdown(_summary(), [_record()])
        assert "materialized" in text
        assert "ASCII" not in text  # rendered doc, not the template's guidance prose


class TestWriteRunEvidence:
    def test_writes_committed_markdown_from_raw_records(self, tmp_path: Path) -> None:
        writer = evidence.EvidenceWriter(tmp_path, "run-001")
        writer.record(
            evidence.AssetOutcome(
                asset="source_map",
                table="demo_table",
                gate_command="reads Gate status",
                exit_code=None,
                measured={"gate_status": "CLEARED", "open_rows": 0},
                outcome="materialized",
            )
        )
        evidence.finalize_run(
            tmp_path,
            "run-001",
            ["demo_table"],
            evidence.RunMeta(started="2026-07-17T00:00:00Z"),
        )
        out = evidence.write_run_evidence(tmp_path, "run-001")
        assert (
            out
            == tmp_path / "orchestration" / "dagster" / "run-evidence" / "run-001.md"
        )
        assert out.is_file()
        assert "# Dagster Run Evidence -- `run-001`" in out.read_text(encoding="utf-8")

    def test_refuses_invalid_records(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".seshat" / "dagster" / "runs" / "run-002"
        run_dir.mkdir(parents=True)
        (run_dir / "records.jsonl").write_text(
            '{"run_id": "run-002", "asset": "source_map", "outcome": "pass"}\n',
            encoding="utf-8",
        )
        (run_dir / "summary.json").write_text('{"run_id": "run-002"}', encoding="utf-8")
        with pytest.raises(ValueError, match="invalid run evidence"):
            evidence.write_run_evidence(tmp_path, "run-002")

    def test_list_runs_reports_known_runs(self, tmp_path: Path) -> None:
        writer = evidence.EvidenceWriter(tmp_path, "run-003")
        writer.record(
            evidence.AssetOutcome(
                asset="source_map",
                table="demo_table",
                gate_command="reads Gate status",
                exit_code=None,
                measured={},
                outcome="materialized",
            )
        )
        evidence.finalize_run(
            tmp_path,
            "run-003",
            ["demo_table"],
            evidence.RunMeta(started="2026-07-17T00:00:00Z"),
        )
        runs = evidence.list_runs(tmp_path)
        assert [run["run_id"] for run in runs] == ["run-003"]
        assert runs[0]["run_status"] == "succeeded"
