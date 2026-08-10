"""Contracts for temporary local capability gaps beside official integrations."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LOCAL_PBIR_WRITERS = (
    "pbir-apply-theme",
    "pbir-format-visual",
    "pbir-set-page-background",
    "pbir-set-geometry",
)


def _records() -> tuple[dict[str, dict], dict[str, dict]]:
    capabilities_doc = yaml.safe_load(
        (ROOT / "docs/capabilities/capabilities.yaml").read_text(encoding="utf-8")
    )
    gaps_doc = yaml.safe_load(
        (ROOT / "docs/capabilities/upstream-gaps.yaml").read_text(encoding="utf-8")
    )
    capabilities = {item["id"]: item for item in capabilities_doc["capabilities"]}
    gaps = {item["id"]: item for item in gaps_doc["gaps"]}
    return capabilities, gaps


def test_gap_records_are_complete_reviewable_and_not_expired() -> None:
    _, gaps = _records()
    required = {
        "id",
        "seshat_capability",
        "upstream_checked",
        "checked_at",
        "gap",
        "scope",
        "review_by",
        "retire_when",
    }
    assert gaps
    for gap in gaps.values():
        assert set(gap) == required
        assert all(gap[field] for field in required)
        assert date.fromisoformat(str(gap["review_by"])) >= date(2026, 8, 10)
        assert date.fromisoformat(str(gap["checked_at"])) <= date.fromisoformat(
            str(gap["review_by"])
        )


def test_every_local_overlapping_pbir_writer_cites_the_reviewed_gap() -> None:
    capabilities, gaps = _records()
    gap_id = "powerbi-bounded-pbir-patching"
    assert gaps[gap_id]["review_by"] == "2026-11-10"
    for capability_id in LOCAL_PBIR_WRITERS:
        ownership = capabilities[capability_id]["ownership"]
        assert ownership["gap_reference"] == gap_id
        assert ownership["capability_owner"] == "seshat-adapter"


def test_gap_scope_is_bounded_and_has_an_official_retirement_trigger() -> None:
    _, gaps = _records()
    record = gaps["powerbi-bounded-pbir-patching"]
    combined = f"{record['gap']} {record['scope']} {record['retire_when']}".lower()
    for phrase in ("temporary", "deterministic", "binding-preserving", "allow-listed"):
        assert phrase in combined
    assert "official" in record["retire_when"].lower()
    assert "firewall" in record["retire_when"].lower()
