"""Tests for `retail status` (spec 109, roadmap M4, Option B).

The CLI wraps the pure ``seshat.status_surface.build_status_projection``
projection: ``--format text`` (default, human-readable, additive/unchanged
posture) and ``--format json`` (the machine surface, mirroring
``runner.run_json``'s style). Read-only; must degrade gracefully (exit 0,
empty projection) on a repo with no committed readiness-status.yaml -- this
repo, on this branch, is exactly that case.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str) -> None:
    rel = Path("mappings") / table_dir / "readiness-status.yaml"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""\
table: "silver.{table_dir}"
current_stage: "mapping_ready"
stages:
  source_ready:
    {{status: "pass", evidence: ["source-profile.md"], blocking_reasons: []}}
  mapping_ready:
    {{status: "blocked", evidence: [], blocking_reasons: ["grain not confirmed"]}}
blocking_reasons: ["grain not confirmed"]
next_action: "resolve open grain question"
""",
        encoding="utf-8",
    )


def test_status_json_exits_zero_on_empty_repo(tmp_path: Path, capsys) -> None:
    exit_code = main(["status", "--repo", str(tmp_path), "--format", "json"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"tables": []}


def test_status_json_default_repo_is_cwd(capsys) -> None:
    """No --repo given -> defaults to '.', matching every other subcommand's
    convention (check/validate/kit-lint/... all default --repo to '.')."""
    exit_code = main(["status", "--format", "json"])
    assert exit_code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "tables" in parsed
    assert isinstance(parsed["tables"], list)


def test_status_json_projects_committed_table(tmp_path: Path, capsys) -> None:
    _write_status(tmp_path, "orders")
    exit_code = main(["status", "--repo", str(tmp_path), "--format", "json"])
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert len(parsed["tables"]) == 1
    table = parsed["tables"][0]
    assert table["table"] == "silver.orders"
    assert table["current_stage"] == "mapping_ready"
    assert table["next_action"] == "resolve open grain question"


def test_status_text_default_format(tmp_path: Path, capsys) -> None:
    """--format defaults to text (FR-005: text default unchanged/additive)."""
    _write_status(tmp_path, "orders")
    exit_code = main(["status", "--repo", str(tmp_path)])
    assert exit_code == 0
    out = capsys.readouterr().out
    # Text output is human-readable, not raw JSON.
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert "silver.orders" in out
    assert "mapping_ready" in out


def test_status_text_on_empty_repo_is_not_an_error(tmp_path: Path, capsys) -> None:
    exit_code = main(["status", "--repo", str(tmp_path)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert out  # some human-readable "nothing tracked yet" message, not silence


def test_status_never_emits_a_numeric_score_field(tmp_path: Path, capsys) -> None:
    _write_status(tmp_path, "orders")
    main(["status", "--repo", str(tmp_path), "--format", "json"])
    out = capsys.readouterr().out
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in out.lower()


def test_status_json_is_read_only(tmp_path: Path, capsys) -> None:
    _write_status(tmp_path, "orders")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    main(["status", "--repo", str(tmp_path), "--format", "json"])
    capsys.readouterr()
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


def test_status_json_output_is_valid_json_document(tmp_path: Path, capsys) -> None:
    """The whole stdout is ONE parseable JSON document (mirrors run_json's
    contract), not JSON mixed with other printed lines."""
    _write_status(tmp_path, "orders")
    main(["status", "--repo", str(tmp_path), "--format", "json"])
    out = capsys.readouterr().out
    json.loads(out)  # must not raise
