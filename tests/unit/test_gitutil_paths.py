"""gitutil path framing: option-shaped paths, -z listings, cwd-relative REV:path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat import gitutil
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


def test_check_ignore_treats_a_dash_prefixed_path_as_a_path(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text("-ignored.pbip\n", encoding="utf-8")
    (repo / "--no-index.pbip").write_text("{}\n", encoding="utf-8")
    (repo / "-ignored.pbip").write_text("{}\n", encoding="utf-8")

    assert gitutil.git_check_ignore(repo, "--no-index.pbip") is False
    assert gitutil.git_check_ignore(repo, "-ignored.pbip") is True


def test_list_paths_returns_non_ascii_paths_verbatim(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "sql").mkdir()
    (repo / "sql" / "café.sql").write_text("select 1;\n", encoding="utf-8")
    commit_all(repo, "seed")

    assert gitutil.list_paths(repo, "ls-files", "--", "sql") == ("sql/café.sql",)


def test_list_paths_raises_on_git_failure(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="ls-tree"):
        gitutil.list_paths(tmp_path, "ls-tree", "-r", "--name-only", "HEAD")


def test_committed_ref_is_cwd_relative(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "x.md").write_text("top\n", encoding="utf-8")
    (repo / "proj").mkdir()
    (repo / "proj" / "x.md").write_text("proj\n", encoding="utf-8")
    commit_all(repo, "seed")

    shown = subprocess.run(
        ["git", "show", gitutil.committed_ref("HEAD", "x.md")],
        cwd=repo / "proj",
        capture_output=True,
        text=True,
        check=True,
    )
    assert shown.stdout == "proj\n"
