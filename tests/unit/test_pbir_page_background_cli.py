"""CLI-level test for `retail pbir-set-page-background` (adapter increment C)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"
FX_REPORT = FIXTURES / "page_bg.Report"
ASSET = FIXTURES / "placeholder-asset.png"


def _report_copy(tmp: Path) -> Path:
    dst = tmp / "R.Report"
    shutil.copytree(FX_REPORT, dst)
    return dst


def test_cli_sets_page_background_exit_zero(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    rc = main(
        [
            "pbir-set-page-background",
            "--asset",
            str(ASSET),
            "--report",
            str(report),
            "--page",
            "pg",
            "--scaling",
            "Fill",
        ]
    )
    assert rc == 0
    page = json.loads((report / "definition/pages/pg/page.json").read_text())
    assert "background" in page["objects"]


def test_cli_missing_asset_exit_two(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    rc = main(
        [
            "pbir-set-page-background",
            "--asset",
            str(tmp_path / "nope.png"),
            "--report",
            str(report),
            "--page",
            "pg",
        ]
    )
    assert rc == 2
