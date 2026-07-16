"""Unit tests for the shell-free closed-argv runner (spec 134, T024/T025)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.dagster_adapter import runner

pytestmark = pytest.mark.unit


def _fake_repo(tmp_path: Path) -> Path:
    scripts = tmp_path / "orchestration" / "dagster" / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("", encoding="utf-8")
    return tmp_path


class TestBuildRunArgv:
    def test_closed_argv_shape(self, tmp_path: Path) -> None:
        python = Path("py")
        argv = runner.build_run_argv(python, "through_gold_job")
        assert argv == [
            "py",
            "-m",
            "dagster",
            "job",
            "execute",
            "-m",
            "tower_bi_orchestration.definitions",
            "-j",
            "through_gold_job",
        ]

    def test_unknown_job_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="job must be one of"):
            runner.build_run_argv(Path("py"), "rm -rf; evil_job")

    def test_no_passthrough_parameters_exist(self) -> None:
        import inspect

        signature = inspect.signature(runner.execute_run)
        assert "extra_args" not in signature.parameters
        assert "raw_args" not in signature.parameters


class TestExecuteRun:
    def test_spawns_shell_free_child_with_run_scoped_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _fake_repo(tmp_path)
        captured: dict = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        monkeypatch.setattr(runner.subprocess, "run", fake_run)
        result = runner.execute_run(root, "full_sequence_job", table="demo_table")
        assert result.exit_code == 0
        assert captured["kwargs"].get("shell") is False
        env = captured["kwargs"]["env"]
        assert env["SESHAT_DAGSTER_RUN_ID"] == result.run_id
        assert env["SESHAT_DAGSTER_TABLES"] == "demo_table"
        assert env["SESHAT_REPO_ROOT"] == str(root)
        assert "demo_table" not in captured["argv"]  # scoping via env, never argv

    def test_child_failure_maps_to_nonzero_result_with_redacted_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _fake_repo(tmp_path)
        monkeypatch.setattr(
            runner.subprocess,
            "run",
            lambda argv, **kwargs: subprocess.CompletedProcess(
                argv, 1, stdout="", stderr="failed: postgresql://u:pw@h/d"
            ),
        )
        result = runner.execute_run(root, "full_sequence_job")
        assert result.exit_code == 1
        assert "pw@h" not in result.output
        assert "[REDACTED-DSN]" in result.output

    def test_missing_orchestration_env_raises_runner_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(runner.RunnerError, match="orchestration environment"):
            runner.execute_run(tmp_path, "full_sequence_job")
