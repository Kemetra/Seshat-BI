"""CLI parser, parity, and concise refusal checks for ``adopt-pbip``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "pbip_adoption" / "supported"


def test_assess_json_is_one_parity_document_and_returns_governed_exit(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "supported"
    shutil.copytree(FIXTURE, project)
    code = main(["adopt-pbip", "assess", "--project", str(project), "--format", "json"])
    document = json.loads(capsys.readouterr().out)
    assert code in {0, 1}
    assert document["next_step"]["action"]
    assert document["scaffold_plan"]["approvals"] == []


def test_assess_text_and_json_share_the_same_digest(tmp_path: Path, capsys) -> None:
    project = tmp_path / "supported"
    shutil.copytree(FIXTURE, project)
    main(["adopt-pbip", "assess", "--project", str(project), "--format", "json"])
    machine = json.loads(capsys.readouterr().out)
    main(["adopt-pbip", "assess", "--project", str(project), "--format", "text"])
    text = capsys.readouterr().out
    assert machine["assessment_digest"] in text
    assert machine["next_step"]["action"] in text


def test_invalid_assessment_input_is_concise_and_traceback_free(capsys) -> None:
    code = main(
        ["adopt-pbip", "assess", "--project", "does-not-exist", "--format", "json"]
    )
    output = capsys.readouterr().out
    assert code == 2
    assert json.loads(output)["outcome"] == "input_defect"
    assert "Traceback" not in output
