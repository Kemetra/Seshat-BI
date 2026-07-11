from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.ecosystem_contracts import ContractError
from seshat.passport import AUTHORITY_DISCLAIMER, build_passport

pytestmark = pytest.mark.unit


def _write_table(root: Path, table: str, *, evidence_body: str = "profile\n") -> None:
    table_dir = root / "mappings" / table
    table_dir.mkdir(parents=True)
    (table_dir / "source-profile.md").write_text(evidence_body, encoding="utf-8")
    (table_dir / "readiness-status.yaml").write_text(
        f"""\
table: {table}
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    evidence: [mappings/{table}/source-profile.md]
    blocking_reasons: []
  mapping_ready:
    status: blocked
    evidence: []
    blocking_reasons: [grain needs owner approval]
  silver_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  gold_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  semantic_model_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  dashboard_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  publish_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
blocking_reasons: [grain needs owner approval]
approvals:
  - stage: source_ready
    owner: Jordan Rivera (analyst)
    at: 2026-07-01
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def test_export_is_deterministic_for_identical_inputs(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    first = build_passport(tmp_path, generated_at="2026-07-11T00:00:00+00:00")
    second = build_passport(tmp_path, generated_at="2026-07-11T00:00:00+00:00")
    assert first == second


def test_passport_id_is_digest_derived_and_excludes_generated_at(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path, "orders")
    first = build_passport(tmp_path, generated_at="2026-07-11T00:00:00+00:00")
    second = build_passport(tmp_path, generated_at="2027-01-01T00:00:00+00:00")
    assert first["passport_id"] == second["passport_id"]
    assert first["passport_id"].startswith("passport-")


def test_export_carries_required_disclaimer_verbatim(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    passport = build_passport(tmp_path)
    assert passport["authority_disclaimer"] == AUTHORITY_DISCLAIMER
    assert "does not grant approval" in passport["authority_disclaimer"]


def test_export_scope_is_explicit_and_unknown_tables_fail_closed(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path, "orders")
    _write_table(tmp_path, "returns")
    scoped = build_passport(tmp_path, tables=["orders"])
    assert scoped["scope"] == ["orders"]
    assert [entry["table_id"] for entry in scoped["readiness"]] == ["orders"]
    assert all("returns" not in item["path"] for item in scoped["artifacts"])
    with pytest.raises(ContractError, match="unknown table"):
        build_passport(tmp_path, tables=["nope"])


def test_empty_workspace_scope_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="scope is empty"):
        build_passport(tmp_path)


def test_all_artifact_paths_are_workspace_relative_posix(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    passport = build_passport(tmp_path)
    assert passport["artifacts"]
    for item in passport["artifacts"]:
        assert not item["path"].startswith("/")
        assert ":" not in item["path"]
        assert "\\" not in item["path"]
        assert ".." not in item["path"].split("/")


def test_export_records_approval_receipts_with_shape_observation(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path, "orders")
    passport = build_passport(tmp_path)
    receipt = passport["approvals"][0]
    assert receipt["stage"] == "source_ready"
    assert receipt["owner"] == "Jordan Rivera (analyst)"
    assert receipt["source_artifact"] == "mappings/orders/readiness-status.yaml"
    assert receipt["valid_shape"] is True


def test_deferred_live_evidence_is_unavailable_not_missing(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    status = tmp_path / "mappings/orders/readiness-status.yaml"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "evidence: [mappings/orders/source-profile.md]",
            'evidence: ["[PENDING LIVE PROFILE]"]',
        ),
        encoding="utf-8",
    )
    passport = build_passport(tmp_path)
    deferred = [
        item
        for item in passport["artifacts"]
        if item["path"] == "[PENDING LIVE PROFILE]"
    ]
    assert deferred and deferred[0]["verification"] == "unavailable"
    assert deferred[0]["sha256"] is None


def test_export_never_emits_score_and_boundary_is_static(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    passport = build_passport(tmp_path)
    payload = json.dumps(passport).lower()
    assert '"score"' not in payload
    assert '"confidence"' not in payload
    assert passport["validation_boundary"]["live"] == "unavailable"
