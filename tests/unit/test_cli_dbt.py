from __future__ import annotations

import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from seshat.cli import _build_parser, main

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "command",
    ("doctor", "validate", "scaffold", "plan", "build", "test", "inspect-run"),
)
def test_dbt_subcommands_are_parseable(command: str) -> None:
    argv = ["dbt", command]
    if command != "doctor":
        argv += ["--table", "retail_store_sales"]
    if command in {"build", "test"}:
        argv += ["--accept-plan", "a" * 64]
    if command == "inspect-run":
        argv += ["--artifacts", ".seshat/dbt/runs/run-id"]

    args = _build_parser().parse_args(argv)

    assert args.command == "dbt"
    assert args.dbt_command == command
    assert args.repo == "."
    assert args.output_format == "text"


def test_dbt_group_exposes_exact_subcommands() -> None:
    parser = _build_parser()
    args = parser.parse_args(["dbt", "doctor", "--format", "json"])

    assert args.dbt_command == "doctor"
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["dbt", "unknown"])
    assert error.value.code == 2


@pytest.mark.parametrize(
    "forbidden",
    (
        "--select",
        "--selector",
        "--exclude",
        "--target",
        "--profile",
        "--profiles-dir",
        "--project-dir",
        "--vars",
        "--full-refresh",
        "--threads",
        "--state",
        "--defer",
    ),
)
def test_dbt_rejects_raw_passthrough_flags(forbidden: str) -> None:
    code = main(
        [
            "dbt",
            "build",
            "--table",
            "retail_store_sales",
            "--accept-plan",
            "a" * 64,
            forbidden,
            "unsafe",
        ]
    )

    assert code == 2


def test_accept_plan_requires_exact_lowercase_sha256() -> None:
    assert (
        main(
            [
                "dbt",
                "build",
                "--table",
                "retail_store_sales",
                "--accept-plan",
                "ABC",
            ]
        )
        == 2
    )


def test_scaffold_is_dispatched_and_gate_blocks_are_governance_refusals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`dbt scaffold` is a registered verb; a missing/unapproved map fails closed
    as a governance refusal (exit 3), never an uncaught traceback."""
    import seshat.cli.commands.dbt as module

    assert "scaffold" in module._COMMANDS
    args = Namespace(
        command="dbt",
        dbt_command="scaffold",
        table="never_onboarded",
        repo=str(tmp_path),
        output_format="json",
    )

    code = module.dbt_main(args)
    output = capsys.readouterr().out

    assert code == 3
    payload = json.loads(output)
    assert payload["outcome"] == "blocked"
    assert "Traceback" not in output


def test_base_cli_import_is_adapter_lazy() -> None:
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,sys; import seshat.cli; "
                "print(json.dumps({"
                "'adapter': 'seshat.dbt' in sys.modules,"
                "'handler': 'seshat.cli.commands.dbt' in sys.modules,"
                "'external': 'dbt' in sys.modules,"
                "'dagster': 'dagster' in sys.modules,"
                "'dagster_dbt': 'dagster_dbt' in sys.modules}))"
            ),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )

    # spec 135 T003: importing base seshat loads NO governed dbt adapter and NO
    # third-party dagster / dagster_dbt / dbt module -- the static core import
    # path stays stdlib-only (FR-011, spec 134 FR-001).
    assert json.loads(result.stdout) == {
        "adapter": False,
        "handler": False,
        "external": False,
        "dagster": False,
        "dagster_dbt": False,
    }


def _args(tmp_path: Path, output_format: str = "json") -> Namespace:
    return Namespace(
        command="dbt",
        dbt_command="doctor",
        repo=str(tmp_path),
        output_format=output_format,
    )


def _copy_profile_pair(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    text = root.joinpath("profiles.example.yml").read_text(encoding="utf-8")
    tmp_path.joinpath("profiles.example.yml").write_text(text, encoding="utf-8")
    tmp_path.joinpath("profiles.yml").write_text(text, encoding="utf-8")


def test_doctor_requires_an_exact_runtime_profile(tmp_path: Path) -> None:
    import seshat.cli.commands.dbt as module

    with pytest.raises(module.DbtUnavailable, match="PENDING LIVE PROFILE"):
        module._verify_local_profile(tmp_path)

    _copy_profile_pair(tmp_path)
    module._verify_local_profile(tmp_path)
    with tmp_path.joinpath("profiles.yml").open("a", encoding="utf-8") as stream:
        stream.write("unexpected: literal\n")

    with pytest.raises(module.DbtUnavailable, match="exact governed template"):
        module._verify_local_profile(tmp_path)


def test_doctor_requires_runtime_profile_to_be_ignored_and_untracked(
    tmp_path: Path,
) -> None:
    import seshat.cli.commands.dbt as module

    _copy_profile_pair(tmp_path)
    tmp_path.joinpath(".gitignore").write_text("/profiles.yml\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)

    module._verify_profile_git_boundary(tmp_path)
    subprocess.run(["git", "add", "--force", "profiles.yml"], cwd=tmp_path, check=True)

    with pytest.raises(module.DbtUnavailable, match="untracked and gitignored"):
        module._verify_profile_git_boundary(tmp_path)


def _clear_dbt_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from seshat.dbt.redaction import DBT_ENVIRONMENT_KEYS

    for key in DBT_ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_doctor_environment_check_allows_defaulted_keys_to_be_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PORT/SCHEMA/SSLMODE carry an env_var(NAME, DEFAULT) in profiles.example.yml,
    so doctor must not flag them as missing required keys."""
    import seshat.cli.commands.dbt as module

    _clear_dbt_environment(monkeypatch)
    monkeypatch.setenv("SESHAT_DBT_HOST", "db.example.com")
    monkeypatch.setenv("SESHAT_DBT_USER", "seshat")
    monkeypatch.setenv("SESHAT_DBT_PASSWORD", "hunter2")
    monkeypatch.setenv("SESHAT_DBT_DBNAME", "ezaby_demo")

    module._verify_environment(tmp_path)


def test_doctor_environment_check_still_requires_genuine_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.cli.commands.dbt as module

    _clear_dbt_environment(monkeypatch)
    monkeypatch.setenv("SESHAT_DBT_HOST", "db.example.com")
    monkeypatch.setenv("SESHAT_DBT_USER", "seshat")
    monkeypatch.setenv("SESHAT_DBT_PASSWORD", "hunter2")

    with pytest.raises(module.DbtUnavailable, match="SESHAT_DBT_DBNAME"):
        module._verify_environment(tmp_path)


def test_doctor_rejects_a_present_but_empty_defaulted_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex #445: a defaulted key may be ABSENT (dbt uses env_var's default), but
    an explicitly EMPTY override (`SESHAT_DBT_PORT=`) is forwarded verbatim and does
    NOT trigger dbt's fallback -- so doctor must reject it, not pass and let dbt
    receive an empty port/schema/sslmode."""
    import seshat.cli.commands.dbt as module

    _clear_dbt_environment(monkeypatch)
    monkeypatch.setenv("SESHAT_DBT_HOST", "db.example.com")
    monkeypatch.setenv("SESHAT_DBT_USER", "seshat")
    monkeypatch.setenv("SESHAT_DBT_PASSWORD", "hunter2")
    monkeypatch.setenv("SESHAT_DBT_DBNAME", "ezaby_demo")
    monkeypatch.setenv("SESHAT_DBT_SCHEMA", "")  # present but empty -> must reject

    with pytest.raises(module.DbtUnavailable, match="SESHAT_DBT_SCHEMA"):
        module._verify_environment(tmp_path)


@pytest.mark.parametrize(
    "case",
    (
        (lambda module: module.HandledDbtFailure("dbt tests failed"), 1),
        (lambda module: module.DbtUnavailable("dbt unavailable"), 2),
        (
            lambda module: module.GovernanceError(
                "DBT_MAPPING_NOT_PASS", "mapping is blocked"
            ),
            3,
        ),
        (lambda module: module.PlanDrift("accepted plan drift"), 3),
        (lambda module: module.LockUnavailable("lock held"), 3),
        (lambda module: module.ArtifactIntegrityError("bad artifact"), 4),
    ),
)
def test_expected_errors_have_stable_exit_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    case,
) -> None:
    import seshat.cli.commands.dbt as module

    error_factory, expected = case

    def raise_error(args: Namespace):
        raise error_factory(module)

    monkeypatch.setitem(module._COMMANDS, "doctor", raise_error)

    code = module.dbt_main(_args(tmp_path))
    output = capsys.readouterr()
    payload = json.loads(output.out)

    assert code == expected
    assert payload["exit_code"] == expected
    assert payload["outcome"] != "pass"
    assert "Traceback" not in output.out + output.err


def test_json_output_is_one_sanitized_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import seshat.cli.commands.dbt as module

    monkeypatch.setattr(
        module,
        "load_child_environment",
        lambda root: {"SESHAT_DBT_PASSWORD": "private-pass"},
    )

    def unavailable(args: Namespace):
        raise module.DbtUnavailable(f"private-pass at {tmp_path}")

    monkeypatch.setitem(module._COMMANDS, "doctor", unavailable)

    assert module.dbt_main(_args(tmp_path)) == 2
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert output.count("\n") == 1
    assert payload["command"] == "doctor"
    assert "private-pass" not in output
    assert str(tmp_path) not in output
    assert "<redacted>" in output
    assert "<repo>" in output


@pytest.mark.parametrize("field", ("manifest_sha256", "run_results_sha256"))
def test_inspect_run_rejects_artifacts_not_bound_to_invocation(
    tmp_path: Path, field: str
) -> None:
    import seshat.cli.commands.dbt as module

    payload = {
        "invocation_id": "run-1",
        "operation": "build",
        "argv_summary": ["build"],
        "return_code": 0,
        "started_at": "2026-07-16T00:00:00.000Z",
        "completed_at": "2026-07-16T00:00:01.000Z",
        "manifest_sha256": "manifest-hash",
        "run_results_sha256": "results-hash",
    }
    payload[field] = "different-hash"
    tmp_path.joinpath("invocation.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    manifest = SimpleNamespace(sha256="manifest-hash")
    results = SimpleNamespace(sha256="results-hash")

    with pytest.raises(module.ArtifactIntegrityError, match="snapshot hashes"):
        module._load_invocation(tmp_path, manifest, results)


def test_unexpected_programmer_error_is_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.cli.commands.dbt as module

    def bug(args: Namespace):
        raise AssertionError("programmer bug")

    monkeypatch.setitem(module._COMMANDS, "doctor", bug)

    with pytest.raises(AssertionError, match="programmer bug"):
        module.dbt_main(_args(tmp_path))


def test_stale_plan_stops_before_lock_or_database_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import seshat.cli.commands.dbt as module

    seen = {"lock": False, "invoke": False}
    monkeypatch.setattr(module, "create_plan", lambda root, table, runner: object())

    def reject_digest(expected: str, actual: object) -> None:
        raise module.PlanDrift("accepted plan drift")

    def forbidden_lock(*args: object, **kwargs: object):
        seen["lock"] = True
        raise AssertionError("lock must not be acquired")

    def forbidden_invoke(*args: object, **kwargs: object):
        seen["invoke"] = True
        raise AssertionError("dbt must not be invoked")

    monkeypatch.setattr(module, "require_accepted_plan", reject_digest)
    monkeypatch.setattr(module, "target_lock", forbidden_lock)
    monkeypatch.setattr(module, "invoke_dbt", forbidden_invoke)
    args = Namespace(
        command="dbt",
        dbt_command="build",
        table="retail_store_sales",
        accept_plan="a" * 64,
        repo=str(tmp_path),
        output_format="json",
    )

    assert module.dbt_main(args) == 3
    assert seen == {"lock": False, "invoke": False}
    assert json.loads(capsys.readouterr().out)["outcome"] == "blocked"
