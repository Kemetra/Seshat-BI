"""CLI tests for the `seshat dagster` family (spec 134, T026/T027).

Exit codes are stable API (contracts/dagster-cli.md): 0 success, 1 usage,
2 preflight/gate refusal, 3 run failed (the CI signal), 4 internal error.
The family is lazy: `import seshat.cli` must NOT import the adapter package.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

from seshat.cli.parser import _build_parser

pytestmark = pytest.mark.unit


class TestParserRegistration:
    def test_dagster_family_parses(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["dagster", "doctor"])
        assert args.command == "dagster"
        assert args.dagster_cmd == "doctor"
        args = parser.parse_args(
            ["dagster", "run", "--job", "through_gold_job", "--table", "demo_table"]
        )
        assert args.dagster_cmd == "run"
        assert args.job == "through_gold_job"
        assert args.table == "demo_table"
        args = parser.parse_args(
            ["dagster", "evidence", "--run-id", "run-001", "--json"]
        )
        assert args.dagster_cmd == "evidence"
        assert args.run_id == "run-001"
        assert args.as_json is True

    def test_run_rejects_unknown_job_at_parse_time(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["dagster", "run", "--job", "surprise_job"])


class TestLazyImportGuard:
    def test_importing_the_cli_never_imports_the_adapter(self) -> None:
        code = (
            "import sys; import seshat.cli; "
            "bad = [m for m in sys.modules if m.startswith('seshat.dagster_adapter')]; "
            "raise SystemExit(1 if bad else 0)"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        assert proc.returncode == 0, proc.stderr


def _args(**kwargs) -> types.SimpleNamespace:
    base = {"repo": ".", "as_json": False}
    base.update(kwargs)
    return types.SimpleNamespace(**base)


class TestDoctorExitCodes:
    def test_blockers_exit_2(self, tmp_path: Path, capsys) -> None:
        from seshat.cli.commands.dagster import dagster_main

        code = dagster_main(_args(dagster_cmd="doctor", repo=str(tmp_path)))
        assert code == 2
        out = capsys.readouterr().out
        assert "DAG-PROJ-01" in out


class TestEvidenceExitCodes:
    def test_no_runs_lists_nothing_and_exits_0(self, tmp_path: Path, capsys) -> None:
        from seshat.cli.commands.dagster import dagster_main

        code = dagster_main(
            _args(dagster_cmd="evidence", repo=str(tmp_path), run_id=None)
        )
        assert code == 0
        assert "no runs" in capsys.readouterr().out.lower()

    def test_unknown_run_id_exits_2(self, tmp_path: Path, capsys) -> None:
        from seshat.cli.commands.dagster import dagster_main

        code = dagster_main(
            _args(dagster_cmd="evidence", repo=str(tmp_path), run_id="ghost-run")
        )
        assert code == 2


class TestRunExitCodes:
    def test_doctor_blockers_refuse_the_run_with_exit_2(self, tmp_path: Path) -> None:
        from seshat.cli.commands.dagster import dagster_main

        code = dagster_main(
            _args(
                dagster_cmd="run",
                repo=str(tmp_path),
                job="full_sequence_job",
                table=None,
            )
        )
        assert code == 2

    @pytest.mark.parametrize(
        "case",
        [(1, "failed", 3), (0, "succeeded", 0)],
        ids=["failed-run-exits-3", "green-run-exits-0"],
    )
    def test_run_exit_follows_finalized_run_status_and_renders_evidence(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        case: tuple[int, str, int],
    ) -> None:
        child_exit, run_status, expected_code = case
        from seshat.cli.commands.dagster import dagster_main
        from seshat.dagster_adapter import doctor, evidence, runner

        monkeypatch.setattr(doctor, "run_doctor", lambda root: [])
        monkeypatch.setattr(
            runner,
            "execute_run",
            lambda root, job, table=None: runner.RunResult(
                run_id="run-x", exit_code=child_exit, output="child output"
            ),
        )
        calls: dict = {}
        monkeypatch.setattr(
            evidence,
            "finalize_run",
            lambda root, run_id, tables, meta: (
                calls.setdefault("finalized", run_id),
                {"run_status": run_status},
            )[1],
        )
        monkeypatch.setattr(
            evidence,
            "write_run_evidence",
            lambda root, run_id: calls.setdefault("rendered", Path("run-x.md")),
        )
        code = dagster_main(
            _args(
                dagster_cmd="run",
                repo=str(tmp_path),
                job="full_sequence_job",
                table=None,
            )
        )
        assert code == expected_code
        assert calls["finalized"] == "run-x"  # evidence finalized in BOTH cases
        assert calls["rendered"] == Path("run-x.md")
