"""``seshat reset`` refuses to destroy uncommitted work (audit finding F047).

A planned directory can hold untracked or modified files that git cannot bring
back. Reset must name them and refuse (``dirty_tree``) unless the operator opts
in with ``--discard-uncommitted``; and ``--format json`` must still show the
plan before it asks for confirmation.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.reset import ResetError, execute_reset, plan_reset
from tests.unit._gitfix import commit_all, make_git_repo
from tests.unit._reset_fixtures import build_workspace

pytestmark = pytest.mark.unit


def _repo(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path)
    build_workspace(repo, ("orders",))
    commit_all(repo, "feat: onboard fixture table")
    return repo


def _add_untracked_draft(repo: Path) -> Path:
    draft = repo / "mappings" / "orders" / "assumptions.md"
    draft.write_text("hand-written notes\n", encoding="utf-8")
    return draft


def test_plan_names_untracked_content(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _add_untracked_draft(repo)

    plan = plan_reset(repo, "orders")

    assert plan.uncommitted == ("mappings/orders/assumptions.md",)


def test_execute_refuses_untracked_content_and_removes_nothing(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    plan = plan_reset(repo, "orders")
    draft = _add_untracked_draft(repo)  # appears AFTER planning: re-checked

    with pytest.raises(ResetError) as excinfo:
        execute_reset(repo, plan)

    assert excinfo.value.reason == "dirty_tree"
    assert "mappings/orders/assumptions.md" in str(excinfo.value)
    assert draft.is_file()


def test_execute_refuses_modified_tracked_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source_map = next((repo / "mappings" / "orders").glob("*.yaml"))
    source_map.write_text(
        source_map.read_text(encoding="utf-8") + "# edit\n", encoding="utf-8"
    )
    plan = plan_reset(repo, "orders")

    with pytest.raises(ResetError) as excinfo:
        execute_reset(repo, plan)

    assert excinfo.value.reason == "dirty_tree"
    assert source_map.is_file()


def test_execute_discards_only_when_explicitly_allowed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _add_untracked_draft(repo)
    plan = plan_reset(repo, "orders")

    execute_reset(repo, plan, allow_uncommitted=True)

    assert not (repo / "mappings" / "orders").exists()


def test_failing_git_status_inside_a_repo_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git failure inside a real repo must not read as "not a repo"."""
    import subprocess as sp

    import seshat.gitstate as gitstate

    repo = _repo(tmp_path)
    plan = plan_reset(repo, "orders")
    real_run_git = gitstate.run_git

    def _broken_status(root: Path, *args: str) -> sp.CompletedProcess[str]:
        if args[:1] == ("status",):
            return sp.CompletedProcess(args, 128, "", "fatal: index file corrupt")
        return real_run_git(root, *args)

    monkeypatch.setattr(gitstate, "run_git", _broken_status)
    with pytest.raises(ResetError) as excinfo:
        execute_reset(repo, plan)

    assert excinfo.value.reason == "dirty_tree"
    assert (repo / "mappings" / "orders").is_dir()


def test_cli_refuses_dirty_tree_with_named_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    draft = _add_untracked_draft(repo)

    rc = main(["reset", "orders", "--repo", str(repo), "--yes"], prog="retail")

    err = capsys.readouterr().err
    assert rc == 2
    assert "retail reset: refused (dirty_tree)" in err
    assert draft.is_file()


def test_cli_discard_flag_allows_the_reset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _add_untracked_draft(repo)

    rc = main(
        ["reset", "orders", "--repo", str(repo), "--yes", "--discard-uncommitted"],
        prog="seshat",
    )

    assert rc == 0
    assert not (repo / "mappings" / "orders").exists()


def test_cli_dry_run_json_lists_uncommitted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _add_untracked_draft(repo)

    rc = main(
        ["reset", "orders", "--repo", str(repo), "--dry-run", "--format", "json"],
        prog="seshat",
    )

    document = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert document["uncommitted"] == ["mappings/orders/assumptions.md"]


def test_json_confirmation_shows_the_plan_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    fake_stdin = io.StringIO("n\n")
    fake_stdin.isatty = lambda: True  # type: ignore[method-assign]
    monkeypatch.setattr("sys.stdin", fake_stdin)

    rc = main(
        ["reset", "orders", "--repo", str(repo), "--format", "json"], prog="seshat"
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "mappings/orders/" in captured.err
    json.loads(captured.out)  # stdout stays one JSON document
