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
        # The child must EMIT utf-8 (not just be decoded as utf-8) so non-Latin-1
        # governed values don't UnicodeEncodeError on a legacy Windows code page,
        # and the parent's decode matches the child's output (#404).
        assert env["PYTHONUTF8"] == "1"
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert captured["kwargs"].get("encoding") == "utf-8"

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

    def test_dsn_straddling_tail_boundary_does_not_leak_password(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """#362 leak #2: truncate-before-redact. `runner` slices output to the last
        _TAIL_CHARS BEFORE redacting. A DSN straddling that cut loses its
        `scheme://` to the discarded front, so the schemeless remainder
        (`/alice:s3cretpw@...`) misses _DSN_RE (no scheme), misses _KEYWORD_RE (not
        keyword=value), and misses the value-replace (truncated != full env value)
        -- the password leaks. Fix: redact the FULL output, THEN slice.

        The ordering defect is size-independent, so we scale the BOUNDARY (a
        monkeypatchable module global read at call time) rather than build an
        absurd ~4 KB DSN -- a faithful reproduction of the same bug."""
        monkeypatch.setattr(runner, "_TAIL_CHARS", 40)
        secret = "postgresql://alice:s3cretpw@db.example.internal/gold"
        # sanity: at TAIL=40 the raw tail drops the scheme but keeps the password
        raw_tail = secret[-40:]
        assert "://" not in raw_tail
        assert "s3cretpw" in raw_tail
        root = _fake_repo(tmp_path)
        monkeypatch.setattr(
            runner.subprocess,
            "run",
            lambda argv, **kwargs: subprocess.CompletedProcess(
                argv, 1, stdout="", stderr=secret
            ),
        )
        result = runner.execute_run(root, "full_sequence_job")
        assert result.exit_code == 1
        assert "s3cretpw" not in result.output  # password must never leak

    def test_hung_child_maps_to_failed_result_not_an_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A timed-out child is a FAILED run result (fail-closed), never a
        raw TimeoutExpired the caller might mishandle (review finding)."""
        root = _fake_repo(tmp_path)

        def hung_child(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=1)

        monkeypatch.setattr(runner.subprocess, "run", hung_child)
        result = runner.execute_run(root, "full_sequence_job")
        assert result.exit_code == 124
        assert "timed out" in result.output

    def test_missing_orchestration_env_raises_runner_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(runner.RunnerError, match="orchestration environment"):
            runner.execute_run(tmp_path, "full_sequence_job")


class TestChildEnvironment:
    def test_drops_unrelated_ambient_secrets(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("UNRELATED_REVIEW_SECRET", "must-not-cross")
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
        monkeypatch.setenv("SESHAT_DBT_HOST", "db.internal")

        env = runner._child_env(tmp_path, "run-001", "orders", "csv")

        assert "UNRELATED_REVIEW_SECRET" not in env
        assert env["DATABASE_URL"] == "postgresql://u:p@h/db"
        assert env["SESHAT_DBT_HOST"] == "db.internal"

    def test_keeps_required_windows_and_tls_keys(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("SYSTEMROOT", r"C:\\Windows")
        monkeypatch.setenv("PATH", r"C:\\Python")
        monkeypatch.setenv("SSL_CERT_FILE", r"C:\\certs\\ca.pem")

        env = runner._child_env(tmp_path, "run-001", None, "csv")

        assert env["SYSTEMROOT"] == r"C:\\Windows"
        assert env["PATH"] == r"C:\\Python"
        assert env["SSL_CERT_FILE"] == r"C:\\certs\\ca.pem"


class TestSourceModeWiring:
    """The source mode travels via SESHAT_DAGSTER_SOURCE_MODE, never argv, set
    ONLY when non-default so the CSV child env stays byte-identical (#404/#405)."""

    def _capture_env(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
        captured: dict = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["env"] = kwargs["env"]
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

        monkeypatch.setattr(runner.subprocess, "run", fake_run)
        return captured

    def test_default_run_leaves_source_mode_env_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A stale var in the parent env must be popped for the default path so
        # the child sees the pre-feature environment exactly.
        monkeypatch.setenv("SESHAT_DAGSTER_SOURCE_MODE", "existing-bronze")
        root = _fake_repo(tmp_path)
        captured = self._capture_env(root, monkeypatch)
        runner.execute_run(root, "through_gold_job")  # source_mode defaults to None/csv
        assert "SESHAT_DAGSTER_SOURCE_MODE" not in captured["env"]

    def test_explicit_csv_also_leaves_the_env_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _fake_repo(tmp_path)
        captured = self._capture_env(root, monkeypatch)
        runner.execute_run(root, "through_gold_job", source_mode="csv")
        assert "SESHAT_DAGSTER_SOURCE_MODE" not in captured["env"]

    def test_existing_bronze_sets_the_env_var_never_argv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _fake_repo(tmp_path)
        captured = self._capture_env(root, monkeypatch)
        runner.execute_run(
            root, "through_gold_job", table="demo", source_mode="existing-bronze"
        )
        assert captured["env"]["SESHAT_DAGSTER_SOURCE_MODE"] == "existing-bronze"
        assert "existing-bronze" not in captured["argv"]  # scoping via env only

    def test_unknown_source_mode_is_refused_before_launch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = _fake_repo(tmp_path)

        def must_not_run(argv, **kwargs):
            raise AssertionError("child must not launch on an invalid source mode")

        monkeypatch.setattr(runner.subprocess, "run", must_not_run)
        with pytest.raises(runner.RunnerError, match="source mode must be one of"):
            runner.execute_run(root, "through_gold_job", source_mode="wipe-it")
