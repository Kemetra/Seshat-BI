"""Acceptance coverage for `retail passport export|verify` (spec 120, US4).

Asserts the exported document validates against the published schema, the
verify leg exits with the stable codes, and neither leg writes outside the
contained `.seshat-output/` root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.ecosystem_contracts import validate_json_contract

pytestmark = pytest.mark.integration

SCHEMA = json.loads(
    (Path(__file__).parents[2] / "schemas/readiness-passport.schema.json").read_text(
        encoding="utf-8"
    )
)


def _write_table(root: Path) -> None:
    table_dir = root / "mappings" / "orders"
    table_dir.mkdir(parents=True)
    (table_dir / "source-profile.md").write_text("profile\n", encoding="utf-8")
    (table_dir / "readiness-status.yaml").write_text(
        """\
table: orders
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    evidence: [mappings/orders/source-profile.md]
    blocking_reasons: []
  mapping_ready:
    status: blocked
    evidence: []
    blocking_reasons: [grain needs owner approval]
  silver_ready: {status: not_started, evidence: [], blocking_reasons: []}
  gold_ready: {status: not_started, evidence: [], blocking_reasons: []}
  semantic_model_ready: {status: not_started, evidence: [], blocking_reasons: []}
  dashboard_ready: {status: not_started, evidence: [], blocking_reasons: []}
  publish_ready: {status: not_started, evidence: [], blocking_reasons: []}
blocking_reasons: [grain needs owner approval]
approvals: []
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def _source_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".seshat-output" not in path.parts
    }


def test_export_writes_schema_valid_passport_with_zero_source_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_table(tmp_path)
    before = _source_snapshot(tmp_path)
    exit_code = main(
        [
            "passport",
            "export",
            "--repo",
            str(tmp_path),
            "--table",
            "orders",
        ]
    )
    assert exit_code == 0
    assert _source_snapshot(tmp_path) == before
    target = tmp_path / ".seshat-output/passports/passport.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    assert validate_json_contract(document, SCHEMA) == []
    out = capsys.readouterr().out
    assert "does not grant approval" in out


def test_export_refuses_output_outside_contained_root(tmp_path: Path) -> None:
    _write_table(tmp_path)
    exit_code = main(
        [
            "passport",
            "export",
            "--repo",
            str(tmp_path),
            "--output",
            "mappings/passport.json",
        ]
    )
    assert exit_code == 2
    assert not (tmp_path / "mappings/passport.json").exists()


def test_verify_round_trip_exit_codes(tmp_path: Path) -> None:
    _write_table(tmp_path)
    assert main(["passport", "export", "--repo", str(tmp_path)]) == 0
    passport_path = tmp_path / ".seshat-output/passports/passport.json"

    before = _source_snapshot(tmp_path)
    assert (
        main(
            [
                "passport",
                "verify",
                "--repo",
                str(tmp_path),
                "--passport",
                str(passport_path),
            ]
        )
        == 0
    )
    assert _source_snapshot(tmp_path) == before

    (tmp_path / "mappings/orders/source-profile.md").write_text(
        "edited\n", encoding="utf-8"
    )
    assert (
        main(
            [
                "passport",
                "verify",
                "--repo",
                str(tmp_path),
                "--passport",
                str(passport_path),
            ]
        )
        == 1
    )


def test_verify_incompatible_schema_exits_2(tmp_path: Path) -> None:
    _write_table(tmp_path)
    assert main(["passport", "export", "--repo", str(tmp_path)]) == 0
    passport_path = tmp_path / ".seshat-output/passports/passport.json"
    document = json.loads(passport_path.read_text(encoding="utf-8"))
    document["schema_version"] = "9.0"
    passport_path.write_text(json.dumps(document), encoding="utf-8")
    assert (
        main(
            [
                "passport",
                "verify",
                "--repo",
                str(tmp_path),
                "--passport",
                str(passport_path),
            ]
        )
        == 2
    )
