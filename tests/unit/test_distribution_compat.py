"""Spec 119 compatibility tests for the renamed import module."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _run_module(module: str, workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, "check", "--repo", str(workspace)],
        text=True,
        capture_output=True,
        env=_environment(),
        check=False,
    )


def test_retail_import_shim_resolves() -> None:
    import retail
    import seshat

    assert retail is not None
    assert seshat is not None


def test_legacy_module_cli_matches_seshat(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    legacy = _run_module("retail.cli", tmp_path)
    primary = _run_module("seshat.cli", tmp_path)

    assert legacy.returncode == primary.returncode
    assert legacy.stdout == primary.stdout
    assert legacy.stderr == primary.stderr
