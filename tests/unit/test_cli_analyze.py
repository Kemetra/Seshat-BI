"""Closed CLI contract for governed statistical analysis."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from seshat.cli import _build_parser, main

pytestmark = pytest.mark.unit


def test_analyze_help_exposes_exact_closed_family(capsys) -> None:
    parser = _build_parser(prog="seshat")
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["analyze", "--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert all(name in output for name in ("validate", "run", "render"))


def test_analyze_parser_accepts_provider_specific_input_contract() -> None:
    parser = _build_parser(prog="seshat")
    local = parser.parse_args(
        [
            "analyze",
            "run",
            "--spec",
            "analysis.yaml",
            "--provider",
            "local_csv",
            "--input",
            "data.csv",
        ]
    )
    gold = parser.parse_args(
        [
            "analyze",
            "run",
            "--spec",
            "analysis.yaml",
            "--provider",
            "gold",
        ]
    )
    assert local.input == "data.csv"
    assert gold.input is None


def test_analyze_outcome_exit_codes_are_stable() -> None:
    from seshat.cli.commands.analyze import _exit_code

    assert {
        outcome: _exit_code(outcome)
        for outcome in (
            "computed",
            "withheld",
            "refused",
            "failed",
            "unavailable",
        )
    } == {
        "computed": 0,
        "withheld": 1,
        "refused": 2,
        "failed": 3,
        "unavailable": 4,
    }


def test_invalid_spec_emits_one_stable_json_object_without_artifact(
    tmp_path: Path, capsys
) -> None:
    spec = tmp_path / "bad.analysis.yaml"
    spec.write_text("analysis_id: broken\n", encoding="utf-8")

    rc = main(
        [
            "analyze",
            "validate",
            "--repo",
            str(tmp_path),
            "--spec",
            spec.name,
            "--format",
            "json",
        ],
        prog="seshat",
    )

    assert rc == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["analysis_id"] is None
    assert payload["outcome"] == "refused"
    assert payload["evidence_path"] is None
    assert payload["review_path"] is None
    assert payload["blockers"]
    assert captured.err == ""


def test_cli_import_does_not_load_numerical_statistics() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    probe = (
        "import sys; import seshat.cli; "
        "names=('numpy','scipy','statsmodels','ruptures'); "
        "print(','.join(name for name in names if name in sys.modules))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == ""
