"""CLI-level test for `retail pbir-format-visual` (adapter increment B)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures/pbir/visual_fmt.Report/definition/pages/pg/visuals/v1/visual.json"
)


def _copy(tmp: Path) -> Path:
    dst = tmp / "x.Report" / "v" / "visual.json"
    dst.parent.mkdir(parents=True)
    shutil.copy(FIXTURE, dst)
    return dst


def test_cli_formats_visual_exit_zero(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    rc = main(
        [
            "pbir-format-visual",
            "--visual",
            str(vj),
            "--formatting",
            json.dumps({"objects": {"labels": {"show": True}}}),
        ]
    )
    assert rc == 0
    doc = json.loads(vj.read_text())
    assert "labels" in doc["visual"]["objects"]


def test_cli_bad_formatting_json_exit_two(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    rc = main(["pbir-format-visual", "--visual", str(vj), "--formatting", "{not json"])
    assert rc == 2


def test_cli_out_of_allowlist_exit_two(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    rc = main(
        [
            "pbir-format-visual",
            "--visual",
            str(vj),
            "--formatting",
            json.dumps({"query": {"x": {}}}),
        ]
    )
    assert rc == 2
