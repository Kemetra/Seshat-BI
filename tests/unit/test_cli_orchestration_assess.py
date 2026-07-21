"""Tests for `seshat orchestration-assess` (issue #401).

The CLI wraps the pure ``seshat.orchestration_assess.build_orchestration_assessment``
engine: ``--format text`` (default, human-readable, recommend-then-decide) and
``--format json`` (the machine surface). Read-only; exit 0 in every case
(including an empty repo -- a well-formed "orchestration not required" is success,
not an error). Never installs, runs, or approves an adapter.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import _build_parser, main

pytestmark = pytest.mark.unit


def _write_gold_table(tmp_path: Path, table_dir: str) -> None:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""\
table: "silver.{table_dir}"
current_stage: "gold_ready"
stages:
  source_ready: {{status: "pass", evidence: ["profile"]}}
  mapping_ready: {{status: "pass", evidence: ["map"]}}
  silver_ready: {{status: "pass", evidence: ["silver"]}}
  gold_ready: {{status: "pass", evidence: ["gold live-validated"]}}
""",
        encoding="utf-8",
    )


def test_verb_is_wired_into_the_parser() -> None:
    ns = _build_parser().parse_args(["orchestration-assess"])
    assert ns.command == "orchestration-assess"
    assert ns.repo == "."
    assert ns.output_format == "text"


def test_json_exits_zero_on_empty_repo(tmp_path: Path, capsys) -> None:
    exit_code = main(
        ["orchestration-assess", "--repo", str(tmp_path), "--format", "json"]
    )
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["recommendation"]["dbt"] == "not_recommended"
    assert parsed["recommendation"]["dagster"] == "not_recommended"


def test_json_projects_c086_single_table_case(tmp_path: Path, capsys) -> None:
    _write_gold_table(tmp_path, "sales_c086_raw")
    exit_code = main(
        ["orchestration-assess", "--repo", str(tmp_path), "--format", "json"]
    )
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["table_count"] == 1
    assert parsed["recommendation"]["dbt"] == "not_recommended"
    assert "revisit" in parsed["recommended_action"].lower()


def test_text_default_is_human_readable_not_json(tmp_path: Path, capsys) -> None:
    _write_gold_table(tmp_path, "orders")
    exit_code = main(["orchestration-assess", "--repo", str(tmp_path)])
    assert exit_code == 0
    out = capsys.readouterr().out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    # The recommend-then-decide framing is visible in the human output.
    lowered = out.lower()
    assert "recommend" in lowered
    assert (
        "human decides" in lowered or "you decide" in lowered or "decision" in lowered
    )


def test_text_names_the_opt_in_commands_but_does_not_run_them(
    tmp_path: Path, capsys
) -> None:
    _write_gold_table(tmp_path, "orders")
    main(["orchestration-assess", "--repo", str(tmp_path)])
    out = capsys.readouterr().out
    assert "seshat-bi[dbt]" in out
    assert "dagster init" in out


def test_cli_is_read_only(tmp_path: Path, capsys) -> None:
    _write_gold_table(tmp_path, "orders")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    main(["orchestration-assess", "--repo", str(tmp_path), "--format", "json"])
    capsys.readouterr()
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


def test_json_output_is_one_parseable_document(tmp_path: Path, capsys) -> None:
    _write_gold_table(tmp_path, "orders")
    main(["orchestration-assess", "--repo", str(tmp_path), "--format", "json"])
    json.loads(capsys.readouterr().out)  # must not raise


def test_json_never_emits_a_numeric_score(tmp_path: Path, capsys) -> None:
    _write_gold_table(tmp_path, "orders")
    main(["orchestration-assess", "--repo", str(tmp_path), "--format", "json"])
    dumped = capsys.readouterr().out.lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped
