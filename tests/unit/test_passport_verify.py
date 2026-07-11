from __future__ import annotations

from pathlib import Path

import pytest

from seshat.passport import build_passport, verify_passport

pytestmark = pytest.mark.unit


def _write_table(root: Path, table: str = "orders") -> None:
    table_dir = root / "mappings" / table
    table_dir.mkdir(parents=True)
    (table_dir / "source-profile.md").write_text("profile\n", encoding="utf-8")
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
approvals: []
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_unchanged_reference_verifies_completely(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    result = verify_passport(tmp_path, passport)
    assert result["outcome"] == "verified"
    assert result["artifacts"]
    assert all(item["verification"] == "verified" for item in result["artifacts"])


def test_changed_evidence_is_reported_as_changed(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    (tmp_path / "mappings/orders/source-profile.md").write_text(
        "edited\n", encoding="utf-8"
    )
    result = verify_passport(tmp_path, passport)
    assert result["outcome"] == "changed"
    changed = [i for i in result["artifacts"] if i["verification"] == "changed"]
    assert changed and changed[0]["path"] == "mappings/orders/source-profile.md"


def test_missing_evidence_is_reported_as_missing(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    (tmp_path / "mappings/orders/source-profile.md").unlink()
    result = verify_passport(tmp_path, passport)
    assert result["outcome"] == "missing"
    assert any(item["verification"] == "missing" for item in result["artifacts"])


def test_unknown_schema_major_is_incompatible(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    passport["schema_version"] = "2.0"
    result = verify_passport(tmp_path, passport)
    assert result["outcome"] == "incompatible"
    assert "unsupported schema major" in result["note"]


def test_escaping_artifact_path_is_incompatible(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    passport["artifacts"].append(
        {
            "artifact_id": "evidence:../secret",
            "kind": "evidence",
            "path": "../secret",
            "sha256": "0" * 64,
            "verification": "verified",
            "note": None,
        }
    )
    result = verify_passport(tmp_path, passport)
    assert result["outcome"] == "incompatible"


def test_null_hash_evidence_is_unavailable_not_verified(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    passport["artifacts"][0]["sha256"] = None
    result = verify_passport(tmp_path, passport)
    assert result["outcome"] == "unavailable"
    assert result["artifacts"][0]["verification"] == "unavailable"


def test_uninterpretable_passport_is_incompatible(tmp_path: Path) -> None:
    result = verify_passport(tmp_path, ["not", "a", "passport"])
    assert result["outcome"] == "incompatible"


def test_verification_never_mutates_passport_or_workspace(tmp_path: Path) -> None:
    _write_table(tmp_path)
    passport = build_passport(tmp_path)
    import copy

    frozen = copy.deepcopy(passport)
    before = _snapshot(tmp_path)
    verify_passport(tmp_path, passport)
    assert passport == frozen
    assert _snapshot(tmp_path) == before
