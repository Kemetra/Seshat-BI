"""Hardened read-only git state probes (issue #334) -- all probes fail CLOSED."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.gitstate import committed_text, is_tracked_and_clean
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


def test_committed_clean_file_is_trusted(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "artifact.md").write_text("committed truth\n", encoding="utf-8")
    commit_all(repo, "record artifact")

    assert is_tracked_and_clean(repo, "artifact.md") is True
    assert committed_text(repo, "artifact.md") == "committed truth\n"


def test_untracked_file_fails_closed(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "keep.md").write_text("x\n", encoding="utf-8")
    commit_all(repo, "seed")
    (repo / "artifact.md").write_text("worktree only\n", encoding="utf-8")

    assert is_tracked_and_clean(repo, "artifact.md") is False
    assert committed_text(repo, "artifact.md") is None


def test_dirty_tracked_file_fails_closed(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "artifact.md").write_text("committed truth\n", encoding="utf-8")
    commit_all(repo, "record artifact")
    (repo / "artifact.md").write_text("uncommitted edit\n", encoding="utf-8")

    assert is_tracked_and_clean(repo, "artifact.md") is False
    assert committed_text(repo, "artifact.md") is None


def test_outside_any_repository_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "artifact.md").write_text("x\n", encoding="utf-8")

    assert is_tracked_and_clean(tmp_path / "bare", "artifact.md") is False
    assert committed_text(tmp_path / "bare", "artifact.md") is None


# --------------------------------------------------------------------------
# Issue #663 gap 2 -- git output must not be decoded with the locale codec.
# --------------------------------------------------------------------------


def test_a_filename_undecodable_in_the_locale_codec_does_not_kill_stdout(
    tmp_path: Path,
) -> None:
    """`text=True` with no encoding loses the whole listing, not just one name.

    Measured on Windows/cp1252: the Cyrillic `Ё` encodes to UTF-8 `0xD0 0x81`,
    and `0x81` is undefined in cp1252. The UnicodeDecodeError is raised inside
    subprocess's READER THREAD, so it never reaches the caller -- `stdout` comes
    back as None and every consumer that touches it dies on AttributeError.
    A path-level recovery helper cannot fix this: it never runs.
    """
    from seshat.gitstate import run_git

    repo = make_git_repo(tmp_path)
    (repo / "Ё.tmdl").write_text("table x\n", encoding="utf-8")
    commit_all(repo, "add a non-cp1252 filename")

    listed = run_git(repo, "ls-files", "-z", "--cached")

    assert listed.returncode == 0
    assert listed.stdout is not None, "stdout was lost to the locale codec"
    assert "Ё.tmdl" in listed.stdout.replace("\x00", "")


# --------------------------------------------------------------------------
# A governed root that is a SUBDIRECTORY of the git toplevel (monorepo /
# drop-in layout): the committed read must name the SAME file the tracked/clean
# probe verified, never a same-named twin at the toplevel.
# --------------------------------------------------------------------------


def test_subdirectory_root_reads_its_own_committed_file(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    rel = "mappings/t/unresolved-questions.md"
    (repo / "mappings" / "t").mkdir(parents=True)
    (repo / rel).write_text("Gate status: CLEARED\n", encoding="utf-8")
    (repo / "proj" / "mappings" / "t").mkdir(parents=True)
    (repo / "proj" / rel).write_text("Gate status: OPEN\n", encoding="utf-8")
    commit_all(repo, "toplevel twin plus project file")

    assert is_tracked_and_clean(repo / "proj", rel) is True
    assert committed_text(repo / "proj", rel) == "Gate status: OPEN\n"


def test_subdirectory_root_without_a_twin_is_still_readable(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "proj").mkdir()
    (repo / "proj" / "artifact.md").write_text("project truth\n", encoding="utf-8")
    commit_all(repo, "project only")

    assert committed_text(repo / "proj", "artifact.md") == "project truth\n"
