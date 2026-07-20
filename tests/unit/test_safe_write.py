"""Shared non-destructive workspace writer (#351/#352).

`safe_write.write_if_absent(root, relative, data)` is the hardened primitive the
`seshat init` writers (governed_projects, workspace_init) delegate to, so the
non-destructive + containment contract cannot drift per-writer. It closes the
same classes stage1_scaffold closed in #342/#345:
  * a pre-existing REGULAR file is kept (non-destructive);
  * a symlink / non-file node at the final component is refused;
  * a symlinked directory component (parent) is refused (containment);
  * a resolved path outside `root` is refused (containment);
  * the write is an atomic O_CREAT|O_EXCL create (TOCTOU race backstop).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_writes_a_fresh_nested_file(tmp_path: Path) -> None:
    from seshat.safe_write import write_if_absent

    assert write_if_absent(tmp_path, "dbt/macros/gen.sql", b"select 1\n") is True
    assert (tmp_path / "dbt" / "macros" / "gen.sql").read_bytes() == b"select 1\n"


def test_keeps_a_preexisting_regular_file(tmp_path: Path) -> None:
    from seshat.safe_write import write_if_absent

    target = tmp_path / "profiles.yml"
    target.write_text("# hand-authored\n", encoding="utf-8")

    assert write_if_absent(tmp_path, "profiles.yml", b"generated\n") is False
    assert target.read_text(encoding="utf-8") == "# hand-authored\n"


def test_writes_bytes_verbatim_no_newline_translation(tmp_path: Path) -> None:
    from seshat.safe_write import write_if_absent

    write_if_absent(tmp_path, "f.yml", b"line1\nline2\n")
    assert (tmp_path / "f.yml").read_bytes() == b"line1\nline2\n"  # no \r on Windows


def test_atomic_create_keeps_a_racing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file materializing after the guards but before the write (concurrent
    process) is kept via O_EXCL, never truncated. Plant it from the last pre-write
    step (mkdir) so the guards have already passed on the absent path."""
    from seshat.safe_write import write_if_absent

    target = tmp_path / "raced.yml"
    planted = b"planted-by-a-concurrent-process\n"
    real_mkdir = Path.mkdir

    def _mkdir_then_race(self: Path, *args, **kwargs) -> None:
        real_mkdir(self, *args, **kwargs)
        target.write_bytes(planted)

    monkeypatch.setattr(Path, "mkdir", _mkdir_then_race)

    assert write_if_absent(tmp_path, "raced.yml", b"ours\n") is False
    assert target.read_bytes() == planted


def test_refuses_a_symlinked_output_file(tmp_path: Path) -> None:
    """A symlink (even dangling) at the final component would let the write escape
    the workspace. Refuse it before writing."""
    from seshat.safe_write import SafeWriteError, write_if_absent

    outside = tmp_path / "outside.yml"  # dangling target
    try:
        os.symlink(outside, tmp_path / "link.yml")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError):
        write_if_absent(tmp_path, "link.yml", b"data\n")
    assert not outside.exists()


def test_refuses_a_symlinked_parent_directory_escape(tmp_path: Path) -> None:
    """The deterministic parent-component escape the per-file guard misses: if a
    parent dir (`dbt/`) is a symlink pointing outside root, writing `dbt/x.yml`
    escapes the workspace. Refuse a symlinked directory component."""
    from seshat.safe_write import SafeWriteError, write_if_absent

    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, root / "dbt", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError):
        write_if_absent(root, "dbt/profiles.yml", b"data\n")
    assert not (outside / "profiles.yml").exists()  # nothing escaped


def test_refuses_non_file_collision(tmp_path: Path) -> None:
    """A directory sitting where a file must go: exists() is true but the file is
    absent. Refuse rather than report a misleading 'kept'."""
    from seshat.safe_write import SafeWriteError, write_if_absent

    (tmp_path / "collide").mkdir()

    with pytest.raises(SafeWriteError):
        write_if_absent(tmp_path, "collide", b"data\n")


def test_refuses_traversal_relative_path(tmp_path: Path) -> None:
    """A relative path resolving outside root (../escape) is refused."""
    from seshat.safe_write import SafeWriteError, write_if_absent

    with pytest.raises(SafeWriteError):
        write_if_absent(tmp_path, "../escape.yml", b"data\n")
