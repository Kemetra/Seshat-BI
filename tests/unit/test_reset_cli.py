"""``seshat reset`` CLI surface (#433): exit codes, confirmation ergonomics,
``--dry-run``, ``--format json``, the #430 ``seshat check`` seam, and post-reset
truthfulness via ``seshat next --table``.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from seshat.cli import main
from tests.unit._gitfix import commit_all, make_git_repo
from tests.unit._reset_fixtures import add_dagster_run, build_workspace

pytestmark = pytest.mark.unit


def _onboarded_repo(tmp_path: Path, tables: tuple[str, ...] = ("orders",)) -> Path:
    repo = make_git_repo(tmp_path)
    build_workspace(repo, tables)
    add_dagster_run(repo, "20260101T000000Z-aaaaaaaa", (tables[0],))
    commit_all(repo, "feat: onboard fixture tables")
    return repo


# ---------------------------------------------------------------------------
# Refusals exit non-zero with a named reason
# ---------------------------------------------------------------------------


def test_unsafe_table_is_refused_with_named_reason(capsys, tmp_path: Path) -> None:
    rc = main(["reset", "../evil", "--repo", str(tmp_path)], prog="seshat")
    err = capsys.readouterr().err
    assert rc == 2
    assert "refused (unsafe_table)" in err
    assert "seshat reset:" in err


def test_non_interactive_without_yes_is_refused(capsys, tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path)
    # Under pytest stdin is not a TTY -- exactly the fail-closed situation.
    rc = main(["reset", "orders", "--repo", str(repo)], prog="seshat")
    err = capsys.readouterr().err
    assert rc == 2
    assert "refused (confirmation_required)" in err
    # Nothing was removed.
    assert (repo / "mappings" / "orders").is_dir()


def _interactive_reset(repo: Path, monkeypatch: pytest.MonkeyPatch, answer: str) -> int:
    """Run ``seshat reset orders`` with a fake interactive stdin answering."""
    fake_stdin = io.StringIO(answer)
    fake_stdin.isatty = lambda: True  # type: ignore[method-assign]
    monkeypatch.setattr("sys.stdin", fake_stdin)
    return main(["reset", "orders", "--repo", str(repo)], prog="seshat")


def test_declined_confirmation_removes_nothing(
    capsys, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _onboarded_repo(tmp_path)
    rc = _interactive_reset(repo, monkeypatch, "n\n")
    err = capsys.readouterr().err
    assert rc == 2
    assert "refused (declined)" in err
    assert (repo / "mappings" / "orders").is_dir()


def test_confirmed_on_stdin_executes(
    capsys, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _onboarded_repo(tmp_path)
    rc = _interactive_reset(repo, monkeypatch, "y\n")
    assert rc == 0
    assert not (repo / "mappings" / "orders").exists()


# ---------------------------------------------------------------------------
# Dry-run prints the plan and writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing_and_exits_zero(capsys, tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path)
    rc = main(["reset", "orders", "--repo", str(repo), "--dry-run"], prog="seshat")
    out = capsys.readouterr().out
    assert rc == 0
    assert "mappings/orders" in out
    assert (repo / "mappings" / "orders").is_dir()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert status.strip() == ""


def test_dry_run_json_shape(capsys, tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path)
    rc = main(
        ["reset", "orders", "--repo", str(repo), "--dry-run", "--format", "json"],
        prog="seshat",
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["outcome"] == "plan"
    assert payload["table"] == "orders"
    assert "mappings/orders" in payload["remove_dirs"]
    assert isinstance(payload["remove_files"], list)
    assert isinstance(payload["shared_file_edits"], list)
    assert payload["preserved"] == ["data/raw/orders.csv"]
    assert payload["reason"] is None


def test_refusal_json_shape(capsys, tmp_path: Path) -> None:
    rc = main(
        ["reset", "foo/bar", "--repo", str(tmp_path), "--format", "json"],
        prog="seshat",
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["outcome"] == "refused"
    assert payload["reason"] == "unsafe_table"


# ---------------------------------------------------------------------------
# Success path with --yes, JSON document, and the no-op case
# ---------------------------------------------------------------------------


def test_yes_resets_and_reports_json(capsys, tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path)
    rc = main(
        ["reset", "orders", "--repo", str(repo), "--yes", "--format", "json"],
        prog="seshat",
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["outcome"] == "reset"
    assert payload["verification_findings"] == []
    assert payload["post_reset"]["stage"] == "source_ready"
    assert payload["post_reset"]["outcome"] == "next_action"
    assert not (repo / "mappings" / "orders").exists()


def test_nothing_to_reset_is_a_clean_no_op(capsys, tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    rc = main(["reset", "orders", "--repo", str(repo), "--yes"], prog="seshat")
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing to reset" in out


# ---------------------------------------------------------------------------
# The #430 seam: `seshat check` exits 0 after a reset (staged deletions)
# ---------------------------------------------------------------------------


def test_check_exits_zero_after_reset(
    capsys, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from seshat.workspace_init import init_project

    monkeypatch.chdir(tmp_path)  # init_project scaffolds under the CWD
    target = tmp_path / "shop-bi"
    init_project(str(target))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=target, check=True)
    for key, value in (
        ("user.email", "t@example.com"),
        ("user.name", "Test"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "config", key, value],
            cwd=target,
            check=True,
            capture_output=True,
        )
    commit_all(target, "feat: scaffold workspace")
    build_workspace(target, ("orders",))
    commit_all(target, "feat: onboard orders")

    rc = main(["reset", "orders", "--repo", str(target), "--yes"], prog="seshat")
    assert rc == 0
    capsys.readouterr()

    check_rc = main(["check", "--repo", str(target)], prog="seshat")
    check_output = capsys.readouterr()
    assert check_rc == 0, check_output.out + check_output.err


# ---------------------------------------------------------------------------
# Truthfulness: `seshat next --table` reports a fresh Source stage
# ---------------------------------------------------------------------------


def test_next_reports_fresh_source_stage_after_reset(capsys, tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path)
    rc = main(["reset", "orders", "--repo", str(repo), "--yes"], prog="seshat")
    assert rc == 0
    capsys.readouterr()

    next_rc = main(
        ["next", "--repo", str(repo), "--table", "orders", "--format", "json"],
        prog="seshat",
    )
    payload = json.loads(capsys.readouterr().out)
    assert next_rc == 0
    assert payload["outcome"] == "next_action"
    assert payload["stage"] == "source_ready"
