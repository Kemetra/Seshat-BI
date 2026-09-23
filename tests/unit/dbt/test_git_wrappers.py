"""The dbt governance git reads share the one hardened wrapper (gitstate.run_git)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _capture(monkeypatch: pytest.MonkeyPatch) -> dict:
    from seshat import gitutil

    seen: dict = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(gitutil.subprocess, "run", fake_run)
    return seen


@pytest.mark.parametrize(
    "module_name", ["seshat.dbt.gate", "seshat.dbt.scaffold.orchestrator"]
)
def test_git_reads_carry_safe_directory_devnull_stdin_and_a_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module_name: str
) -> None:
    import importlib

    module = importlib.import_module(module_name)
    seen = _capture(monkeypatch)
    module._git(tmp_path, "rev-parse", "HEAD")
    assert any(part.startswith("safe.directory=") for part in seen["cmd"])
    assert seen["kwargs"]["stdin"] == subprocess.DEVNULL
    assert seen["kwargs"]["timeout"]


def test_scaffold_committed_blob_fails_safe_on_a_hung_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from seshat.dbt.scaffold import orchestrator

    def hung(root, *args):
        raise subprocess.TimeoutExpired(["git"], 1)

    monkeypatch.setattr(orchestrator, "_git", hung)
    assert orchestrator._committed_blob(tmp_path, "docs/x.yaml") is None
