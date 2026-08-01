"""X-Ray pins the live repo (Task 7). Mirrors the test_doctor pattern:
runs against the ACTUAL working tree, so run it on a quiescent tree."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from seshat.cli.commands.xray import xray_main

pytestmark = pytest.mark.integration

REPO_ROOT = str(Path(__file__).resolve().parents[2])


def test_xray_completes_on_live_repo(capsys):
    exit_code = xray_main(argparse.Namespace(repo=REPO_ROOT, output_format="json"))
    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"outcome":"completed"' in out
    # The committed report has no visual.json -> the degraded path
    # (report parsed, but binding evidence limited to what report/page JSON
    # carries) is exercised against real PBIP text either way.
    assert '"model":"powerbi/RetailStoreSales.SemanticModel"' in out
