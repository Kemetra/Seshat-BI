"""CLI-level test for `retail pbir-format-visual` (adapter increment B)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main
from tests.unit._pbir_gate_fixture import gate_args, pbir_gate_repo

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
    repo = pbir_gate_repo(tmp_path)
    vj = _copy(tmp_path)
    rc = main(
        [
            "pbir-format-visual",
            "--visual",
            str(vj),
            "--formatting",
            json.dumps({"objects": {"labels": {"show": True}}}),
            *gate_args(repo),
        ]
    )
    assert rc == 0
    doc = json.loads(vj.read_text())
    assert "labels" in doc["visual"]["objects"]


def test_cli_bad_formatting_json_exit_two(tmp_path: Path) -> None:
    repo = pbir_gate_repo(tmp_path)
    vj = _copy(tmp_path)
    rc = main(
        [
            "pbir-format-visual",
            "--visual",
            str(vj),
            "--formatting",
            "{not json",
            *gate_args(repo),
        ]
    )
    assert rc == 2


def test_cli_out_of_allowlist_exit_two(tmp_path: Path) -> None:
    repo = pbir_gate_repo(tmp_path)
    vj = _copy(tmp_path)
    rc = main(
        [
            "pbir-format-visual",
            "--visual",
            str(vj),
            "--formatting",
            json.dumps({"query": {"x": {}}}),
            *gate_args(repo),
        ]
    )
    assert rc == 2


def test_cli_gate_blocks_before_formatting_payload_read(tmp_path: Path) -> None:
    repo = pbir_gate_repo(tmp_path, approved=False)
    vj = _copy(tmp_path)
    before = vj.read_bytes()

    rc = main(
        [
            "pbir-format-visual",
            "--visual",
            str(vj),
            "--formatting",
            str(tmp_path / "missing-formatting.json"),
            *gate_args(repo),
        ]
    )

    assert rc == 2
    assert vj.read_bytes() == before
