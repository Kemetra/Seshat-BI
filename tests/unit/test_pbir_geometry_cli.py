"""CLI-level test for `retail pbir-set-geometry`."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from seshat.cli import main
from tests.unit._pbir_gate_fixture import gate_args, pbir_gate_repo

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parent.parent / "fixtures" / "pbir" / "geometry.Report"


def _visual(tmp_path: Path) -> Path:
    dst = tmp_path / "geometry.Report"
    shutil.copytree(FIXTURE, dst)
    return dst / "definition" / "pages" / "pg" / "visuals" / "vA" / "visual.json"


def test_cli_sets_geometry_exit_zero(tmp_path: Path):
    repo = pbir_gate_repo(tmp_path)
    vp = _visual(tmp_path)
    rc = main(
        [
            "pbir-set-geometry",
            "--visual",
            str(vp),
            "--position",
            '{"x": 200, "y": 150, "width": 400, "height": 250}',
            *gate_args(repo),
        ]
    )
    assert rc == 0


def test_cli_bad_position_json_exit_two(tmp_path: Path):
    repo = pbir_gate_repo(tmp_path)
    vp = _visual(tmp_path)
    rc = main(
        [
            "pbir-set-geometry",
            "--visual",
            str(vp),
            "--position",
            "not-json",
            *gate_args(repo),
        ]
    )
    assert rc == 2


def test_cli_offcanvas_exit_two(tmp_path: Path):
    repo = pbir_gate_repo(tmp_path)
    vp = _visual(tmp_path)
    rc = main(
        [
            "pbir-set-geometry",
            "--visual",
            str(vp),
            "--position",
            '{"x": 1500, "width": 300, "height": 200}',
            *gate_args(repo),
        ]
    )
    assert rc == 2


def test_cli_gate_blocks_before_geometry_payload_read(tmp_path: Path) -> None:
    repo = pbir_gate_repo(tmp_path, approved=False)
    vp = _visual(tmp_path)
    before = vp.read_bytes()

    rc = main(
        [
            "pbir-set-geometry",
            "--visual",
            str(vp),
            "--position",
            str(tmp_path / "missing-position.json"),
            *gate_args(repo),
        ]
    )

    assert rc == 2
    assert vp.read_bytes() == before
