"""CLI-level test for `retail pbir-apply-theme` (adapter increment A)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir" / "theme_apply"


def _report_copy(tmp: Path) -> Path:
    dst = tmp / "Rpt.Report"
    shutil.copytree(FIXTURES, dst)
    return dst


def _theme(tmp: Path) -> Path:
    p = tmp / "theme.json"
    p.write_text(json.dumps({"name": "gen-dark", "dataColors": ["#111111"]}))
    return p


def test_cli_applies_theme_exit_zero(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    rc = main(
        [
            "pbir-apply-theme",
            "--theme",
            str(_theme(tmp_path)),
            "--report",
            str(report),
        ]
    )
    assert rc == 0
    rj = json.loads((report / "definition/report.json").read_text())
    assert rj["themeCollection"]["baseTheme"]["name"] == "gen-dark"


def test_cli_bad_report_exit_two(tmp_path: Path) -> None:
    rc = main(
        [
            "pbir-apply-theme",
            "--theme",
            str(_theme(tmp_path)),
            "--report",
            str(tmp_path / "nope.Report"),
        ]
    )
    assert rc == 2
