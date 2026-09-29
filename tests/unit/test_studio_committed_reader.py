"""Studio's committed-decision reader: UTF-8 content, cwd-relative paths.

The locale-codec case only reproduces on a host whose preferred encoding cannot
decode the bytes (Windows cp1252); elsewhere it is a plain regression guard. The
subdirectory and decode-failure cases reproduce everywhere.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from seshat.studio import workbench_routes  # noqa: E402
from tests.unit._gitfix import commit_all, make_git_repo  # noqa: E402

pytestmark = pytest.mark.unit

_STORE = ".seshat/semantic-decisions.yaml"
# 'في' is UTF-8 D9 81 D9 8A; 0x81 is undefined in cp1252.
_ARABIC = "decisions:\n- answer: في\n"


def _commit_store(root: Path, text: str) -> None:
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    (root / _STORE).write_bytes(text.encode("utf-8"))


def test_committed_arabic_answer_is_read_as_utf8(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    _commit_store(repo, _ARABIC)
    commit_all(repo, "decision with an Arabic answer")

    text = workbench_routes._CommittedReader(repo).file_at_head(_STORE)

    assert text is not None and text.replace("\r\n", "\n") == _ARABIC


def test_subdirectory_workspace_reads_its_own_store(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    _commit_store(repo, "decisions: []\n")
    _commit_store(repo / "proj", _ARABIC)
    commit_all(repo, "toplevel twin plus project store")

    text = workbench_routes._CommittedReader(repo / "proj").file_at_head(_STORE)

    assert text is not None and "في" in text


def test_undecodable_output_is_an_error_not_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def lost_stdout(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=None)

    monkeypatch.setattr(workbench_routes.gitutil, "run_subprocess", lost_stdout)

    with pytest.raises(RuntimeError, match="could not be decoded"):
        workbench_routes._CommittedReader(tmp_path).file_at_head(_STORE)
