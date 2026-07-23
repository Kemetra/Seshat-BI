"""Unit tests for evidence validation + deterministic rendering (spec 134, T019/T020).

The renderer refuses invalid records (the code validator mirrors
schemas/dagster-run-evidence.schema.json) and produces a byte-deterministic
markdown per templates/dagster-run-evidence.md -- outcomes stay execution
words, halted rows carry reason + owner, and no numeric score can appear.
"""

from __future__ import annotations

import subprocess
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
        "workspace_dirty": False,
        "records_sha256": "0" * 64,
        "input_artifacts": {},
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

    def test_non_mapping_record_is_rejected(self) -> None:
        errors = evidence.validate_records(_summary(), ["not-an-object"])
        assert errors == ["records[0]: must be an object"]

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

    @pytest.mark.parametrize(
        ("field", "value"),
        (
            ("table", ""),
            ("gate_command", ""),
            ("exit_code", True),
            ("measured", []),
            ("blocking_reason", 7),
            ("owner", 7),
            ("ts", 7),
        ),
    )
    def test_schema_invalid_record_values_are_rejected(
        self, field: str, value: object
    ) -> None:
        record = _record()
        record[field] = value

        errors = evidence.validate_records(_summary(), [record])

        assert any(field in error for error in errors)

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


def _finalized_green_run(
    root: Path, run_id: str, child_exit_code: int | None = None
) -> dict:
    """Record one materialized seam asset and finalize -- the shared green-run
    setup for the write/list/child-exit tests."""
    evidence.EvidenceWriter(root, run_id).record(
        evidence.AssetOutcome(
            asset="source_map",
            table="demo_table",
            gate_command="reads Gate status",
            exit_code=None,
            measured={},
            outcome="materialized",
        )
    )
    return evidence.finalize_run(
        root,
        run_id,
        ["demo_table"],
        evidence.RunMeta(
            started="2026-07-17T00:00:00Z", child_exit_code=child_exit_code
        ),
    )


class TestWriteRunEvidence:
    @pytest.mark.parametrize(
        "run_id",
        ("../escape", "..\\escape", ".", "..", "C:drive", "/absolute", "a/b"),
    )
    def test_run_id_rejects_path_syntax(self, tmp_path: Path, run_id: str) -> None:
        with pytest.raises(ValueError, match="run id"):
            evidence.evidence_out_path(tmp_path, run_id)

    def test_safe_legacy_run_id_remains_contained(self, tmp_path: Path) -> None:
        path = evidence.evidence_out_path(tmp_path, "run-001")
        assert path.is_relative_to(tmp_path.resolve())

    def test_load_run_rejects_path_syntax_before_reading(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="run id"):
            evidence.load_run(tmp_path, "../escape")

    def test_existing_symlink_cannot_escape_evidence_root(self, tmp_path: Path) -> None:
        from seshat.dagster_adapter.run_identity import contained_path

        runs = tmp_path / ".seshat" / "dagster" / "runs"
        runs.mkdir(parents=True)
        outside = tmp_path.parent / "outside"
        outside.mkdir(exist_ok=True)
        link = runs / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("symlink creation is unavailable in this environment")

        with pytest.raises(ValueError, match="escapes"):
            contained_path(
                tmp_path,
                ".seshat",
                "dagster",
                "runs",
                "linked",
                "records.jsonl",
            )

    def test_writes_committed_markdown_from_raw_records(self, tmp_path: Path) -> None:
        _finalized_green_run(tmp_path, "run-001")
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
        with pytest.raises(ValueError, match="records_sha256"):
            evidence.write_run_evidence(tmp_path, "run-002")

    def test_child_crash_with_zero_records_finalizes_failed(
        self, tmp_path: Path
    ) -> None:
        """A child that died before recording ANY asset must never read as
        succeeded -- the back-filled all-skipped set alone would (review
        finding); the child exit code keeps the run fail-closed."""
        summary = evidence.finalize_run(
            tmp_path,
            "run-crash",
            ["demo_table"],
            evidence.RunMeta(started="2026-07-17T00:00:00Z", child_exit_code=1),
        )
        assert summary["run_status"] == "failed"
        records = evidence.EvidenceWriter(tmp_path, "run-crash").records()
        assert all(row["outcome"] == "skipped" for row in records)

    def test_finalize_refuses_an_empty_table_selection(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="without mapped tables"):
            evidence.finalize_run(
                tmp_path,
                "run-empty",
                [],
                evidence.RunMeta(started="2026-07-17T00:00:00Z"),
            )

    def test_green_child_exit_keeps_succeeded(self, tmp_path: Path) -> None:
        summary = _finalized_green_run(tmp_path, "run-ok", child_exit_code=0)
        assert summary["run_status"] == "succeeded"

    def test_commit_sha_survives_a_hung_git(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            evidence,
            "git_output",
            lambda *args: (_ for _ in ()).throw(RuntimeError("git unavailable")),
        )
        assert evidence.commit_sha(tmp_path) == "0000000"

    def test_finalize_run_survives_a_missing_git_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            evidence,
            "git_output",
            lambda *args: (_ for _ in ()).throw(FileNotFoundError("git missing")),
        )

        summary = _finalized_green_run(tmp_path, "run-no-git")

        assert summary["commit_sha"] == "0000000"
        assert summary["workspace_dirty"] is False
        assert summary["input_artifacts"] == {}

    def test_list_runs_reports_known_runs(self, tmp_path: Path) -> None:
        _finalized_green_run(tmp_path, "run-003")
        runs = evidence.list_runs(tmp_path)
        assert [run["run_id"] for run in runs] == ["run-003"]
        assert runs[0]["run_status"] == "succeeded"


class TestEvidenceIntegrity:
    def test_tampered_records_are_refused_before_rendering(
        self, tmp_path: Path
    ) -> None:
        _finalized_green_run(tmp_path, "run-tampered")
        records_path = (
            tmp_path / ".seshat" / "dagster" / "runs" / "run-tampered" / "records.jsonl"
        )
        records_path.write_text(
            records_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )

        with pytest.raises(ValueError, match="records_sha256"):
            evidence.write_run_evidence(tmp_path, "run-tampered")

    def test_finalized_summary_binds_tracked_inputs_and_dirty_state(
        self, tmp_path: Path
    ) -> None:
        table = "demo_table"
        paths = {
            "mappings/demo_table/source-map.yaml": "table: demo_table\n",
            "mappings/demo_table/readiness-status.yaml": (
                "stages: {}\napprovals:\n"
                "  - stage: semantic_model_ready\n"
                '    owner: "Ada Lovelace (metric_owner)"\n'
                '    at: "2026-07-22"\n'
                '    note: "approved metric contract TotalSales"\n'
            ),
            "mappings/demo_table/metrics/TotalSales.yaml": (
                "name: TotalSales\nowner: metric_owner\n"
                "binds_to: {gold_table: gold.sales}\n"
                "definition: {kind: base, aggregation: sum, filter: []}\nreadiness:\n"
                "  status: pass\n  evidence: [approved]\n"
                "  blocking_reasons: []\n"
            ),
            "warehouse/migrations/001_gold.sql": "select 1;\n",
            "powerbi/Model.SemanticModel/definition/tables/sales.tmdl": (
                "table 'sales'\n"
            ),
        }
        for relative, contents in paths.items():
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgSign=false",
                "-c",
                "user.name=Evidence Test",
                "-c",
                "user.email=evidence@example.test",
                "commit",
                "-m",
                "fixture",
            ],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        summary = _finalized_green_run(tmp_path, "run-bound")

        assert summary["workspace_dirty"] is False
        assert len(summary["records_sha256"]) == 64
        assert set(paths) <= set(summary["input_artifacts"])
        assert all(
            not Path(relative).is_absolute() for relative in summary["input_artifacts"]
        )

        (tmp_path / "mappings" / table / "source-map.yaml").write_text(
            "table: changed\n", encoding="utf-8"
        )
        dirty_summary = _finalized_green_run(tmp_path, "run-dirty")
        assert dirty_summary["workspace_dirty"] is True
