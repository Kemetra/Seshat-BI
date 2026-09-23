"""``dbt doctor`` read-only probes fail closed and never hang (audit F152)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.cli.commands import dbt as dbt_cmd
from seshat.dbt.runner import DbtUnavailable

pytestmark = pytest.mark.unit


def test_missing_gitignore_is_a_pending_blocker_not_a_crash(tmp_path: Path) -> None:
    with pytest.raises(DbtUnavailable, match=r"\[PENDING LIVE PROFILE\]"):
        dbt_cmd._verify_ignore_rules(tmp_path)


def test_profile_git_probe_detaches_stdin_and_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def _capture(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _capture)
    dbt_cmd._profile_git_result(tmp_path, "check-ignore", "--quiet")

    assert seen.get("stdin") is subprocess.DEVNULL
    assert seen.get("timeout")


@pytest.mark.parametrize(
    "error", [OSError("git not found"), subprocess.TimeoutExpired("git", 1)]
)
def test_profile_git_probe_failure_is_a_pending_blocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def _raise(cmd, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "run", _raise)
    with pytest.raises(DbtUnavailable, match=r"\[PENDING LIVE PROFILE\]"):
        dbt_cmd._profile_git_result(tmp_path, "check-ignore", "--quiet")
