"""CLI tests for the `seshat dagster` family (spec 134, T026/T027).

Exit codes are stable API (contracts/dagster-cli.md): 0 success, 1 usage,
2 preflight/gate refusal, 3 run failed (the CI signal), 4 internal error.
The family is lazy: `import seshat.cli` must NOT import the adapter package.
"""

from __future__ import annotations

import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from seshat.cli.parser import _build_parser
from seshat.dagster_adapter import PINNED_DAGSTER

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


_GOOD_PYPROJECT = f"""[project]
name = "tower-bi-orchestration"
dependencies = [
    "dagster=={PINNED_DAGSTER}",
]
"""


def _green_repo(tmp_path: Path) -> Path:
    """A workspace with a present orchestration project + venv, so the doctor
    reaches the DSN check (DAG-DSN-*) instead of short-circuiting on a blocker.

    Mirrors ``test_dagster_doctor._repo``; kept local because that helper is not
    exported and the CLI-boundary test needs the same green baseline.
    """
    root = tmp_path / "repo"
    tdir = root / "mappings" / "demo_table"
    tdir.mkdir(parents=True)
    (tdir / "source-map.yaml").write_text("table: demo\n", encoding="utf-8")
    (tdir / "readiness-status.yaml").write_text(
        "stages: {}\napprovals: []\n", encoding="utf-8"
    )
    orch = root / "orchestration" / "dagster"
    orch.mkdir(parents=True)
    (orch / "pyproject.toml").write_text(_GOOD_PYPROJECT, encoding="utf-8")
    scripts = orch / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("", encoding="utf-8")
    return root


@pytest.fixture
def _no_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear any exported DSN vars so the ONLY source is the workspace .env."""
    for key in list(os.environ):
        if key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_"):
            monkeypatch.delenv(key, raising=False)


class TestDoctorLoadsDotenv:
    """#348: `dagster doctor` must resolve the DSN from the workspace `.env`,
    exactly as `retail validate` does post-#340 -- not from `os.environ` only."""

    def test_doctor_reads_dsn_from_workspace_dotenv(
        self, tmp_path: Path, capsys, _no_dsn: None
    ) -> None:
        from seshat.cli.commands.dagster import dagster_main

        root = _green_repo(tmp_path)
        (root / ".env").write_text(
            "ANALYTICS_DB_HOST=db.example\n"
            "ANALYTICS_DB_NAME=warehouse\n"
            "ANALYTICS_DB_USER=reader\n",
            encoding="utf-8",
        )

        code = dagster_main(_args(dagster_cmd="doctor", repo=str(root)))

        out = capsys.readouterr().out
        # The #348 bug: DAG-DSN-01 (no credentials) fires even with a populated
        # .env. With the fix it flips to DAG-DSN-00 (present), like validate.
        assert "DAG-DSN-01" not in out
        assert "DAG-DSN-00" in out
        assert code == 0  # a green repo with a resolvable DSN has no blockers
        # The value is never echoed (Principle IX).
        assert "db.example" not in out

    def test_malformed_dotenv_fails_clean_not_exit_4(
        self, tmp_path: Path, capsys, _no_dsn: None
    ) -> None:
        """A malformed `.env` raises EnvironmentConfigError on context entry; it
        must map to a clean, non-4 exit with an actionable message -- never the
        redacted 'internal error' the catch-all produces (the exit-4 trap)."""
        from seshat.cli.commands.dagster import dagster_main

        root = _green_repo(tmp_path)
        # Duplicate key -> the governed parser rejects the file.
        (root / ".env").write_text(
            "ANALYTICS_DB_HOST=a\nANALYTICS_DB_HOST=b\n", encoding="utf-8"
        )

        code = dagster_main(_args(dagster_cmd="doctor", repo=str(root)))

        captured = capsys.readouterr()
        # Exit 2 (preflight refusal) is stable API for a malformed .env: not the
        # redacted exit-4 internal-error path, and not a spurious exit-0 success.
        assert code == 2
        assert "internal error" not in (captured.out + captured.err)
        assert ".env" in (captured.out + captured.err)

    def test_run_propagates_dotenv_to_the_child_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_dsn: None
    ) -> None:
        """`run` is the verb that actually touches the DB (via the child process
        reading ``env = dict(os.environ)``). Pin that the workspace `.env` is
        applied for its body -- a single wrap on `run` must cover BOTH the doctor
        preflight and the runner child env, or #348 silently reopens for `run`."""
        from seshat.cli.commands.dagster import dagster_main
        from seshat.dagster_adapter import doctor, evidence, runner

        root = _green_repo(tmp_path)
        (root / ".env").write_text(
            "ANALYTICS_DB_HOST=child.example\n", encoding="utf-8"
        )
        monkeypatch.setattr(doctor, "run_doctor", lambda r: [])  # no blockers
        seen: dict[str, str | None] = {}

        def _capture_env(r, job, table=None):
            # The runner snapshots os.environ here; capture what it would inherit.
            seen["ANALYTICS_DB_HOST"] = os.environ.get("ANALYTICS_DB_HOST")
            return runner.RunResult(run_id="run-x", exit_code=0, output="")

        monkeypatch.setattr(runner, "execute_run", _capture_env)
        monkeypatch.setattr(
            evidence, "finalize_run", lambda *a, **k: {"run_status": "succeeded"}
        )
        monkeypatch.setattr(
            evidence, "write_run_evidence", lambda r, run_id: Path("run-x.md")
        )

        dagster_main(
            _args(
                dagster_cmd="run", repo=str(root), job="full_sequence_job", table=None
            )
        )

        # The .env value is visible in os.environ at the moment the child is spawned.
        assert seen["ANALYTICS_DB_HOST"] == "child.example"

    def test_exception_redacts_dotenv_secret_before_overlay_teardown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, _no_dsn: None
    ) -> None:
        """Codex P1 (#348): if a DB-touching verb raises with a `.env`-only secret
        in the message, the exit-4 redaction must run WHILE the overlay is still
        active -- `redact_text` discovers secrets from the current os.environ, so
        redacting after `applied_dotenv` tears down would print the secret. The
        secret must never reach stderr; the redaction marker must."""
        from seshat.cli.commands.dagster import dagster_main
        from seshat.dagster_adapter import doctor

        secret = "s3cr3t0nlyindotenvvalue"
        root = _green_repo(tmp_path)
        (root / ".env").write_text(
            f"ANALYTICS_DB_PASSWORD={secret}\nANALYTICS_DB_HOST=db.example\n",
            encoding="utf-8",
        )

        def _boom(r):
            # A downstream failure whose message carries the .env-only secret.
            raise RuntimeError(f"connection failed for password {secret}")

        monkeypatch.setattr(doctor, "run_doctor", _boom)

        code = dagster_main(_args(dagster_cmd="doctor", repo=str(root)))

        captured = capsys.readouterr()
        assert code == 4  # unexpected internal error, redacted
        # The .env-only secret must NOT leak to stderr; it must be redacted.
        assert secret not in (captured.out + captured.err)


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
