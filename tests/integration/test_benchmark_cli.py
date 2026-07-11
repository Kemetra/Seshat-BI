"""Acceptance coverage for `retail benchmark run|report` (spec 120, US7).

Runs the committed scenario manifests end-to-end against the scripted
reference participant, validates the written run against the published
schema, and checks the report leg's stable exit codes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.ecosystem_contracts import validate_json_contract

pytestmark = pytest.mark.integration

_REPO = Path(__file__).parents[2]
_SCHEMA = json.loads(
    (_REPO / "schemas/benchmark-run.schema.json").read_text(encoding="utf-8")
)
_MANIFESTS = [
    "benchmark/scenarios/hard-stops.yaml",
    "benchmark/scenarios/retail-semantics.yaml",
]


def _run_cli(output: str) -> int:
    args = ["benchmark", "run", "--repo", str(_REPO), "--output", output]
    for manifest in _MANIFESTS:
        args += ["--scenarios", manifest]
    return main(args)


def test_reference_run_end_to_end_matches_schema_and_expectations(
    tmp_path: Path,
) -> None:
    output = ".seshat-output/benchmark/test-run.json"
    assert _run_cli(output) == 0
    document = json.loads((_REPO / output).read_text(encoding="utf-8"))
    assert validate_json_contract(document, _SCHEMA) == []
    assert document["participant"]["kind"] == "scripted"
    assert document["observations"]
    for observation in document["observations"]:
        assert observation["observed_behavior"] == observation["expected_behavior"]
        assert observation["evidence"]
    (_REPO / output).unlink()


def test_report_renders_run_and_flags_incomplete(tmp_path: Path) -> None:
    output = ".seshat-output/benchmark/test-report-run.json"
    assert _run_cli(output) == 0
    run_path = _REPO / output
    assert main(["benchmark", "report", "--run", str(run_path)]) == 0

    document = json.loads(run_path.read_text(encoding="utf-8"))
    document["participant"] = {"name": "mystery", "kind": "stochastic"}
    broken = tmp_path / "incomplete.json"
    broken.write_text(json.dumps(document), encoding="utf-8")
    assert main(["benchmark", "report", "--run", str(broken)]) == 1

    unreadable = tmp_path / "not-json.json"
    unreadable.write_text("{", encoding="utf-8")
    assert main(["benchmark", "report", "--run", str(unreadable)]) == 2
    run_path.unlink()


def test_run_refuses_uncontained_output() -> None:
    args = [
        "benchmark",
        "run",
        "--repo",
        str(_REPO),
        "--scenarios",
        _MANIFESTS[0],
        "--output",
        "benchmark/run.json",
    ]
    assert main(args) == 2
    assert not (_REPO / "benchmark/run.json").exists()
