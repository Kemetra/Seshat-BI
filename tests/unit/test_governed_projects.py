"""`seshat dbt init` / `seshat dagster init` self-sufficiency (issue #325).

A bare workspace (no development repository) must gain the full governed
dbt / Dagster capability surface from bundled templates. Only table-neutral
content is materialized (constitution VII), nothing existing is ever
overwritten, and the results satisfy the exact same doctor checks that
previously demanded the dev repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_EXAMPLE_TOKENS = ("retail_store_sales", "c086", "pharmacy")


def test_dbt_init_materializes_the_doctor_required_paths(tmp_path: Path) -> None:
    from seshat.cli.commands.dbt import _verify_ignore_rules, _verify_required_paths
    from seshat.governed_projects import dbt_init

    report = dbt_init(tmp_path)

    _verify_required_paths(tmp_path)  # no raise: doctor's exact path set
    _verify_ignore_rules(tmp_path)  # no raise: doctor's exact ignore rules
    assert "dbt/dbt_project.yml" in report.written
    assert "dbt/selectors.yml" in report.written
    assert any("profiles.example.yml" in note for note in report.notes)


def test_dbt_init_refuses_a_symlinked_parent_escape(tmp_path: Path) -> None:
    """#351: a symlinked `dbt/` pointing outside the workspace would let
    `dbt_init` write governed files OUT of the repo -- a deterministic escape
    (no race). The hardened writer (safe_write) must refuse it."""
    import os

    from seshat.governed_projects import dbt_init
    from seshat.safe_write import SafeWriteError

    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, root / "dbt", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError):
        dbt_init(root)
    # nothing was written through the symlink, out of the workspace
    assert not (outside / "dbt_project.yml").exists()
    assert not (outside / "selectors.yml").exists()


def test_dbt_init_cli_converts_safewriteerror_to_clean_refusal(tmp_path: Path) -> None:
    """#351 Codex P2: when `seshat dbt init` refuses a path-safety violation
    (SafeWriteError), the dbt CLI boundary must map it to a clean nonzero
    CommandResult, never an uncaught traceback."""
    import os

    from seshat.cli.commands.dbt import dbt_main

    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, root / "dbt", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    class _Args:
        dbt_command = "init"
        repo = str(root)
        output_format = "text"

    # No traceback escapes; a clean nonzero exit code is returned.
    code = dbt_main(_Args())
    assert code != 0
    assert not (outside / "dbt_project.yml").exists()  # nothing escaped


def test_dagster_init_cli_maps_safewriteerror_to_exit_2(tmp_path: Path) -> None:
    """#351 Codex P2: `seshat dagster init` refusing a path-safety violation
    (SafeWriteError from a symlinked orchestration/ parent) must map to the
    contract's preflight-refusal exit 2, not the redacted exit-4 'internal
    error' -- mirroring the dbt boundary."""
    import os
    import types

    from seshat.cli.commands.dagster import dagster_main

    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, root / "orchestration", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    args = types.SimpleNamespace(dagster_cmd="init", repo=str(root), as_json=False)
    code = dagster_main(args)
    assert code == 2  # preflight refusal, not exit 4


def test_dbt_init_never_overwrites_and_is_idempotent(tmp_path: Path) -> None:
    from seshat.governed_projects import dbt_init

    dbt_init(tmp_path)
    marker = tmp_path / "dbt" / "selectors.yml"
    marker.write_text("selectors: [] # hand-edited\n", encoding="utf-8")

    second = dbt_init(tmp_path)

    assert second.written == ()
    assert "dbt/selectors.yml" in second.kept
    assert marker.read_text(encoding="utf-8") == "selectors: [] # hand-edited\n"


def test_dbt_init_appends_only_missing_ignore_rules(tmp_path: Path) -> None:
    from seshat.governed_projects import dbt_init

    (tmp_path / ".gitignore").write_text("/profiles.yml\nuser-line\n", encoding="utf-8")

    dbt_init(tmp_path)

    lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "user-line" in lines
    assert lines.count("/profiles.yml") == 1
    for required in ("/.user.yml", "/dbt/target/", "/dbt/logs/", "/.seshat/dbt/"):
        assert required in lines


def test_both_inits_protect_the_credential_file(tmp_path: Path) -> None:
    """Every next-step instruction points the user at .env for SESHAT_DBT_* /
    DSN credentials, so a fresh workspace's generated .gitignore must cover it
    (and the dagster run records) -- `git add .` may never stage a secret."""
    from seshat.governed_projects import dagster_init, dbt_init

    dbt_init(tmp_path)
    dagster_init(tmp_path)

    lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    for required in (".env", ".env.*", ".seshat/dagster/"):
        assert required in lines
    assert lines.count(".env") == 1  # the second init appends only what is missing


def test_dagster_init_clears_the_project_absent_blocker(tmp_path: Path) -> None:
    from seshat.dagster_adapter import doctor
    from seshat.governed_projects import dagster_init

    report = dagster_init(tmp_path)

    findings = {finding.id for finding in doctor.run_doctor(tmp_path)}
    assert "orchestration/dagster/pyproject.toml" in report.written
    assert any(path.startswith("orchestration/dagster/src/") for path in report.written)
    assert "DAG-PROJ-01" not in findings
    assert "DAG-PAIR-01" not in findings
    # The venv is inherently user-created; init points at the remedy instead,
    # and the remedy must work WITHOUT a development checkout (installing
    # seshat-bi from the package index, not from a ../.. editable path).
    assert "DAG-VENV-01" in findings
    assert any("uv venv" in note for note in report.notes)
    assert any('"seshat-bi[dbt]"' in note for note in report.notes)


def test_dagster_init_never_overwrites(tmp_path: Path) -> None:
    from seshat.governed_projects import dagster_init

    dagster_init(tmp_path)
    marker = tmp_path / "orchestration" / "dagster" / "pyproject.toml"
    marker.write_text("# hand-edited\n", encoding="utf-8")

    second = dagster_init(tmp_path)

    assert second.written == ()
    assert marker.read_text(encoding="utf-8") == "# hand-edited\n"


def test_bundled_templates_carry_no_worked_table_answers(tmp_path: Path) -> None:
    """Constitution VII: everything either init materializes is table-neutral
    -- no worked-example table name may reach a fresh workspace."""
    from seshat.governed_projects import dagster_init, dbt_init

    dbt_init(tmp_path)
    dagster_init(tmp_path)

    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore").lower()
        for token in _EXAMPLE_TOKENS:
            assert token not in text, (path, token)


def test_cli_init_verbs_run_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from seshat.cli import main

    dbt_exit = main(["dbt", "init", "--repo", str(tmp_path)])
    dagster_exit = main(["dagster", "init", "--repo", str(tmp_path)])

    out = capsys.readouterr().out
    assert dbt_exit == 0
    assert dagster_exit == 0
    assert "materialized" in out
    assert (tmp_path / "dbt" / "dbt_project.yml").is_file()
    assert (tmp_path / "orchestration" / "dagster" / "pyproject.toml").is_file()
