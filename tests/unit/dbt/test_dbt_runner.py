from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def context(tmp_path: Path):
    from seshat.dbt.contracts import Operation, RunContext

    project_dir = tmp_path / "dbt"
    project_dir.mkdir()
    return RunContext(
        repo_root=tmp_path,
        project_dir=project_dir,
        profiles_dir=tmp_path,
        operation=Operation.BUILD,
        table_id="retail_store_sales",
        selector="seshat_table_retail_store_sales",
        target="shadow",
        run_dir=tmp_path / ".seshat" / "dbt" / "runs" / "run-1234",
        environment={
            "PATH": "ignored-global-path",
            "SESHAT_DBT_HOST": "private-host",
            "SESHAT_DBT_PASSWORD": "private-pass",
        },
        timeout_s=12.0,
    )


def test_resolve_dbt_executable_uses_only_supplied_scripts_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from seshat.dbt.runner import resolve_dbt_executable

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    expected = scripts / "dbt.exe"
    expected.write_text("stub", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path / "global-bin"))

    assert resolve_dbt_executable(scripts) == expected.resolve()


def test_resolve_dbt_executable_has_no_global_path_fallback(tmp_path: Path) -> None:
    from seshat.dbt.runner import DbtUnavailable, resolve_dbt_executable

    scripts = tmp_path / "empty-scripts"
    scripts.mkdir()

    with pytest.raises(DbtUnavailable, match="current Python environment"):
        resolve_dbt_executable(scripts)


def test_build_argv_has_fixed_governed_selector(
    context, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.runner as runner
    from seshat.dbt.contracts import Operation

    executable = context.repo_root / "scripts" / "dbt.exe"
    monkeypatch.setattr(runner, "resolve_dbt_executable", lambda: executable)

    argv = runner.build_dbt_argv(Operation.BUILD, context)

    assert argv[1:4] == (
        "build",
        "--select",
        "selector:seshat_table_retail_store_sales",
    )
    assert "--target" in argv and "shadow" in argv
    assert "--profiles-dir" in argv and str(context.profiles_dir) in argv
    assert "--project-dir" in argv and str(context.project_dir) in argv
    assert all(";" not in part and "&&" not in part for part in argv)


def test_list_uses_quiet_text_logs_for_direct_json_rows(
    context, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.runner as runner
    from seshat.dbt.contracts import Operation

    monkeypatch.setattr(
        runner,
        "resolve_dbt_executable",
        lambda: context.repo_root / "scripts" / "dbt.exe",
    )

    argv = runner.build_dbt_argv(Operation.LIST, context)

    assert argv[argv.index("--log-format") + 1] == "text"
    assert argv[1:3] == ("--quiet", "ls")
    assert argv[-4:] == ("--output", "json", "--output-keys", "unique_id")


@pytest.mark.parametrize("operation", ("PARSE", "LIST", "BUILD", "TEST", "SHOW"))
def test_build_argv_supports_only_closed_operations(
    context, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    import seshat.dbt.runner as runner
    from seshat.dbt.contracts import Operation

    monkeypatch.setattr(
        runner,
        "resolve_dbt_executable",
        lambda: context.repo_root / "scripts" / "dbt.exe",
    )

    selected = getattr(Operation, operation)
    argv = runner.build_dbt_argv(selected, context)

    assert isinstance(argv, tuple)
    command_index = 2 if selected is Operation.LIST else 1
    assert argv[command_index] == (
        "ls" if selected is Operation.LIST else selected.value
    )
    assert "--target-path" in argv
    assert "--log-path" in argv
    if selected is Operation.PARSE:
        assert "--select" not in argv
    elif selected is Operation.SHOW:
        assert argv[2:4] == (
            "--select",
            "audit_retail_store_sales_parity",
        )
    else:
        selector_index = command_index + 1
        assert argv[selector_index : selector_index + 2] == (
            "--select",
            "selector:seshat_table_retail_store_sales",
        )
    if selected is Operation.SHOW:
        # --limit lifts dbt show's default 5-row preview cap so a full parity
        # audit (more than five assertions) is not silently truncated.
        assert argv[-4:] == ("--output", "json", "--limit", "1000")


def test_invoke_never_uses_a_shell_and_sanitizes_output(
    context, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.runner as runner

    seen: dict[str, object] = {}
    executable = context.repo_root / "scripts" / "dbt.exe"
    monkeypatch.setattr(runner, "resolve_dbt_executable", lambda: executable)

    def fake_run(argv: tuple[str, ...], **kwargs: object):
        seen.update(argv=argv, kwargs=kwargs)
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="connected private-host",
            stderr="password private-pass",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    argv = runner.build_dbt_argv(context.operation, context)

    result = runner.invoke_dbt(context, argv)

    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert seen["argv"] == argv
    assert kwargs["shell"] is False
    assert kwargs["check"] is False
    assert kwargs["cwd"] == context.project_dir
    assert kwargs["env"] is context.environment
    assert kwargs["timeout"] == context.timeout_s
    assert result.return_code == 0
    assert "private-" not in result.stdout + result.stderr
    assert str(context.repo_root) not in " ".join(result.argv_summary)


def test_invoke_list_preserves_allowlisted_ids_when_a_secret_overlaps(
    context, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.runner as runner
    from seshat.dbt.contracts import Operation

    list_context = replace(
        context,
        operation=Operation.LIST,
        environment={**context.environment, "SESHAT_DBT_PASSWORD": "seshat"},
    )
    monkeypatch.setattr(
        runner,
        "resolve_dbt_executable",
        lambda: context.repo_root / "scripts" / "dbt.exe",
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"unique_id": "model.seshat_bi.safe_model"}\n',
            stderr="",
        ),
    )

    result = runner.invoke_dbt(
        list_context, runner.build_dbt_argv(Operation.LIST, list_context)
    )

    assert json.loads(result.stdout) == {"unique_id": "model.seshat_bi.safe_model"}


@pytest.mark.parametrize(
    "stdout",
    (
        '{"info": {"msg": "unexpected dbt log"}}\n',
        '{"unique_id": "model.foreign.unsafe"}\n',
        "not-json\n",
    ),
)
def test_invoke_list_rejects_non_allowlisted_rows(
    context, monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    import seshat.dbt.runner as runner
    from seshat.dbt.contracts import Operation

    list_context = replace(context, operation=Operation.LIST)
    monkeypatch.setattr(
        runner,
        "resolve_dbt_executable",
        lambda: context.repo_root / "scripts" / "dbt.exe",
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 0, stdout=stdout, stderr=""
        ),
    )

    with pytest.raises(runner.DbtUnavailable, match="allowlisted JSON rows"):
        runner.invoke_dbt(
            list_context, runner.build_dbt_argv(Operation.LIST, list_context)
        )


def test_invoke_maps_timeout_to_sanitized_dbt_unavailable(
    context, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.runner as runner

    executable = context.repo_root / "scripts" / "dbt.exe"
    monkeypatch.setattr(runner, "resolve_dbt_executable", lambda: executable)

    def timeout(argv: tuple[str, ...], **kwargs: object):
        raise subprocess.TimeoutExpired(argv, context.timeout_s, stderr="private-pass")

    monkeypatch.setattr(runner.subprocess, "run", timeout)

    with pytest.raises(runner.DbtUnavailable, match="timed out") as error:
        runner.invoke_dbt(context, runner.build_dbt_argv(context.operation, context))

    assert "private-pass" not in str(error.value)


def test_invoke_refuses_modified_argv_before_subprocess(
    context, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.runner as runner

    executable = context.repo_root / "scripts" / "dbt.exe"
    monkeypatch.setattr(runner, "resolve_dbt_executable", lambda: executable)

    def must_not_run(*args: object, **kwargs: object):
        raise AssertionError("subprocess must not run for modified argv")

    monkeypatch.setattr(runner.subprocess, "run", must_not_run)
    argv = (*runner.build_dbt_argv(context.operation, context), "--full-refresh")

    with pytest.raises(runner.DbtUnavailable, match="governed argument set"):
        runner.invoke_dbt(context, argv)


def test_target_lock_refuses_existing_lock_without_deleting_it(tmp_path: Path) -> None:
    from seshat.dbt.runner import LockUnavailable, target_lock

    lock = tmp_path / ".seshat" / "dbt" / "locks" / "table-shadow.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("stale-owner", encoding="utf-8")

    with pytest.raises(LockUnavailable, match="already in progress"):
        with target_lock(tmp_path, "table", "shadow", timeout_s=0):
            raise AssertionError("lock must not be acquired")

    assert lock.read_text(encoding="utf-8") == "stale-owner"


def test_target_lock_writes_safe_metadata_and_cleans_up(tmp_path: Path) -> None:
    from seshat.dbt.runner import target_lock

    lock = tmp_path / ".seshat" / "dbt" / "locks" / "table-shadow.lock"

    with target_lock(tmp_path, "table", "shadow", timeout_s=0):
        metadata = json.loads(lock.read_text(encoding="utf-8"))
        assert metadata["table_id"] == "table"
        assert metadata["target"] == "shadow"
        assert isinstance(metadata["pid"], int)
        assert "acquired_at" in metadata
        assert str(tmp_path) not in lock.read_text(encoding="utf-8")

    assert not lock.exists()


def test_target_lock_cleans_up_after_body_exception(tmp_path: Path) -> None:
    from seshat.dbt.runner import target_lock

    lock = tmp_path / ".seshat" / "dbt" / "locks" / "table-shadow.lock"

    with pytest.raises(RuntimeError, match="body failed"):
        with target_lock(tmp_path, "table", "shadow", timeout_s=0):
            raise RuntimeError("body failed")

    assert not lock.exists()


def test_target_lock_does_not_delete_replacement_owner(tmp_path: Path) -> None:
    from seshat.dbt.runner import target_lock

    lock = tmp_path / ".seshat" / "dbt" / "locks" / "table-shadow.lock"

    with target_lock(tmp_path, "table", "shadow", timeout_s=0):
        lock.write_text("replacement-owner", encoding="utf-8")

    assert lock.read_text(encoding="utf-8") == "replacement-owner"


def test_target_lock_rejects_path_injection(tmp_path: Path) -> None:
    from seshat.dbt.runner import LockUnavailable, target_lock

    with pytest.raises(LockUnavailable, match="safe identifier"):
        with target_lock(tmp_path, "../outside", "shadow", timeout_s=0):
            raise AssertionError("unsafe lock must not be acquired")
