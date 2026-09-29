"""Filter-free worktree comparisons: repo-local content filters never execute.

Every "does not run the filter" assertion is an ABSENCE assertion, so each one is
paired with a positive control: the same probe through plain ``git status`` on an
identical copy DOES create the sentinel. Without that control a platform or git
version that never ran the filter would keep these tests green vacuously.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from seshat import git_worktree
from seshat.git_worktree import worktree_matches_revision, worktree_status
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


def _configure_probe_filter(repo: Path, sentinel: Path) -> None:
    """Point the committed ``filter=probe`` attribute at a sentinel-writing clean."""
    subprocess.run(
        [
            "git",
            "config",
            "filter.probe.clean",
            f"touch '{sentinel.as_posix()}'; cat",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _filtered_copies(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path, Path]:
    """(control copy, probe copy, sentinel) of a repo with a repo-local filter.

    Order matters: commit BEFORE the filter is configured (so setup's own
    ``git add`` cannot fire it), then copy -- a fresh copy has dirty stat data for
    every entry, which is what makes git re-read content.
    """
    repo = make_git_repo(tmp_path)
    (repo / ".gitattributes").write_text("* filter=probe\n", encoding="utf-8")
    for rel, text in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    commit_all(repo, "seed")
    sentinel = tmp_path / "sentinel"
    _configure_probe_filter(repo, sentinel)
    control = tmp_path / "control"
    probe = tmp_path / "probe"
    shutil.copytree(repo, control)
    shutil.copytree(repo, probe)
    sentinel.unlink(missing_ok=True)
    return control, probe, sentinel


def _assert_control_fires(control: Path, sentinel: Path) -> None:
    subprocess.run(
        ["git", "status", "--porcelain"], cwd=control, check=True, capture_output=True
    )
    assert sentinel.exists(), "positive control: plain git status must run the filter"
    sentinel.unlink()


@pytest.fixture
def filtered(tmp_path: Path) -> tuple[Path, Path]:
    control, probe, sentinel = _filtered_copies(
        tmp_path, {"a.txt": "alpha\n", "mappings/t/unresolved-questions.md": "q\n"}
    )
    _assert_control_fires(control, sentinel)
    return probe, sentinel


def test_worktree_status_does_not_run_a_repo_local_filter(filtered) -> None:
    probe, sentinel = filtered
    status = worktree_status(probe)
    assert status is not None and status.clean
    assert not sentinel.exists()


def test_adoption_git_state_does_not_run_a_repo_local_filter(filtered) -> None:
    from seshat.pbip_adoption._safety import _git_state

    probe, sentinel = filtered
    assert _git_state(probe) == "clean"
    assert not sentinel.exists()


def test_committed_probe_does_not_run_a_repo_local_filter(filtered) -> None:
    from seshat.gitstate import committed_text, is_tracked_and_clean

    probe, sentinel = filtered
    rel = "mappings/t/unresolved-questions.md"
    assert is_tracked_and_clean(probe, rel) is True
    assert committed_text(probe, rel) == "q\n"
    assert not sentinel.exists()


def test_pbi_mcp_tree_probe_does_not_run_a_repo_local_filter(filtered) -> None:
    from seshat.cli.commands.pbi_mcp import _probe_tree_clean

    probe, sentinel = filtered
    assert _probe_tree_clean(probe) is True
    assert not sentinel.exists()


def test_backup_custody_does_not_run_a_repo_local_filter(filtered) -> None:
    from seshat.pbi_mcp_adapter.gate import _ref_holds_target

    probe, sentinel = filtered
    assert _ref_holds_target(probe, "HEAD", "a.txt") is True
    assert not sentinel.exists()


def test_dbt_clean_source_map_does_not_run_a_repo_local_filter(filtered) -> None:
    from seshat.dbt.gate import _require_clean_source_map

    probe, sentinel = filtered
    _require_clean_source_map(probe, "a.txt")  # raises when judged dirty
    assert not sentinel.exists()


def test_narrative_blob_ids_do_not_run_a_repo_local_filter(filtered) -> None:
    from seshat.narrative_check import _blob_ids

    probe, sentinel = filtered
    ids = _blob_ids(probe, probe / "a.txt")
    assert ids and git_worktree.blob_id(b"alpha\n") in ids
    assert not sentinel.exists()


def test_portfolio_semantic_dirty_probe_does_not_run_a_repo_local_filter(
    tmp_path: Path,
) -> None:
    from seshat.portfolio_watch import _semantic_inputs

    control, probe, sentinel = _filtered_copies(
        tmp_path, {"mappings/s/readiness-status.yaml": "x: 1\n"}
    )
    _assert_control_fires(control, sentinel)
    _inputs, dirty = _semantic_inputs(probe, "s")
    assert dirty is False
    assert not sentinel.exists()


# --------------------------------------------------------------------------
# Status semantics mirror `git status --porcelain --untracked-files=all`.
# --------------------------------------------------------------------------


def _seeded(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path)
    (repo / "a.txt").write_text("alpha\n", encoding="utf-8")
    (repo / "sub").mkdir()
    (repo / "sub" / "b.txt").write_text("beta\n", encoding="utf-8")
    commit_all(repo, "seed")
    return repo


def test_clean_tree_reads_clean(tmp_path: Path) -> None:
    status = worktree_status(_seeded(tmp_path))
    assert status is not None and status.clean


def test_edit_untracked_staged_and_deleted_paths_are_reported(tmp_path: Path) -> None:
    repo = _seeded(tmp_path)
    (repo / "a.txt").write_text("edited\n", encoding="utf-8")
    (repo / "new.txt").write_text("n\n", encoding="utf-8")
    (repo / "staged.txt").write_text("s\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=repo, check=True)
    subprocess.run(["git", "rm", "-q", "--cached", "sub/b.txt"], cwd=repo, check=True)

    status = worktree_status(repo)

    assert status is not None
    assert set(status.modified) == {"a.txt", "staged.txt", "sub/b.txt"}
    assert "new.txt" in status.untracked
    assert "sub/b.txt" in status.untracked


def test_missing_worktree_file_reads_modified(tmp_path: Path) -> None:
    repo = _seeded(tmp_path)
    (repo / "a.txt").unlink()
    status = worktree_status(repo)
    assert status is not None and status.modified == ("a.txt",)


def test_crlf_checkout_of_an_lf_blob_reads_clean(tmp_path: Path) -> None:
    repo = _seeded(tmp_path)
    (repo / "a.txt").write_bytes(b"alpha\r\n")
    status = worktree_status(repo)
    assert status is not None and status.clean


def test_pathspecs_limit_the_status(tmp_path: Path) -> None:
    repo = _seeded(tmp_path)
    (repo / "a.txt").write_text("edited\n", encoding="utf-8")
    status = worktree_status(repo, "sub")
    assert status is not None and status.clean


def test_unborn_branch_with_staged_file_reads_modified(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "a.txt").write_text("alpha\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    status = worktree_status(repo)
    assert status is not None and status.modified == ("a.txt",)


def test_non_repository_returns_none(tmp_path: Path) -> None:
    assert worktree_status(tmp_path) is None


def test_revision_match_is_relative_to_the_queried_root(tmp_path: Path) -> None:
    """A subdirectory root compares ITS file, not a same-named toplevel twin."""
    repo = make_git_repo(tmp_path)
    (repo / "x.md").write_text("top\n", encoding="utf-8")
    (repo / "proj").mkdir()
    (repo / "proj" / "x.md").write_text("proj\n", encoding="utf-8")
    commit_all(repo, "seed")

    assert worktree_matches_revision(repo / "proj", "HEAD", "x.md") is True
    (repo / "proj" / "x.md").write_text("changed\n", encoding="utf-8")
    assert worktree_matches_revision(repo / "proj", "HEAD", "x.md") is False


def test_revision_match_refuses_option_shaped_rev_and_absent_path(
    tmp_path: Path,
) -> None:
    repo = _seeded(tmp_path)
    assert worktree_matches_revision(repo, "-n1", "a.txt") is False
    assert worktree_matches_revision(repo, "HEAD", "absent.txt") is False
    assert worktree_matches_revision(repo, "HEAD", "../a.txt") is False


# --------------------------------------------------------------------------
# Repository-wide preconditions keep whole-repository scope from a subdirectory.
# --------------------------------------------------------------------------


def test_subdirectory_root_still_sees_a_dirty_file_elsewhere(tmp_path: Path) -> None:
    from seshat.cli.commands.pbi_mcp import _probe_tree_clean
    from seshat.git_worktree import repository_status
    from seshat.pbip_adoption._safety import _git_state

    repo = _seeded(tmp_path)
    assert _git_state(repo / "sub") == "clean"
    assert _probe_tree_clean(repo / "sub") is True

    (repo / "a.txt").write_text("edited outside the subdirectory\n", encoding="utf-8")

    probed = repository_status(repo / "sub")
    assert probed is not None and probed[1] == "sub/"
    assert probed[0].modified == ("a.txt",)
    assert _git_state(repo / "sub") == "dirty"
    assert _probe_tree_clean(repo / "sub") is False
