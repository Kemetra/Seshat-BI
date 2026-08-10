"""CLI-level test for `retail pbir-apply-theme` (adapter increment A)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main
from tests.unit._pbir_gate_fixture import gate_args, pbir_gate_repo

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
    repo = pbir_gate_repo(tmp_path)
    report = _report_copy(tmp_path)
    rc = main(
        [
            "pbir-apply-theme",
            "--theme",
            str(_theme(tmp_path)),
            "--report",
            str(report),
            *gate_args(repo),
        ]
    )
    assert rc == 0
    rj = json.loads((report / "definition/report.json").read_text())
    assert rj["themeCollection"]["baseTheme"]["name"] == "gen-dark"


def test_cli_bad_report_exit_two(tmp_path: Path) -> None:
    repo = pbir_gate_repo(tmp_path)
    rc = main(
        [
            "pbir-apply-theme",
            "--theme",
            str(_theme(tmp_path)),
            "--report",
            str(tmp_path / "nope.Report"),
            *gate_args(repo),
        ]
    )
    assert rc == 2


def test_cli_gate_blocks_before_theme_mutation(tmp_path: Path) -> None:
    repo = pbir_gate_repo(tmp_path, approved=False)
    report = _report_copy(tmp_path)
    report_json = report / "definition/report.json"
    before = report_json.read_bytes()

    rc = main(
        [
            "pbir-apply-theme",
            "--theme",
            str(_theme(tmp_path)),
            "--report",
            str(report),
            *gate_args(repo),
        ]
    )

    assert rc == 2
    assert report_json.read_bytes() == before
