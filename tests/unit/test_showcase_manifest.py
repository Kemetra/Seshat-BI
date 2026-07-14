"""Four-category disclosure manifest unit coverage (spec 127, US3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.showcase.manifest import build_manifest, normalize_portability

pytestmark = pytest.mark.unit


def _mixed_tables() -> list[dict]:
    return [
        {
            "table_id": "orders",
            "source_path": "mappings/orders/readiness-status.yaml",
            "stages": {
                "source_ready": {
                    "status": "pass",
                    "evidence": [
                        {
                            "reference": "mappings/orders/source-profile.md",
                            "state": "available",
                        }
                    ],
                    "blocking_reasons": [],
                },
                "silver_ready": {
                    "status": "warning",
                    "evidence": [
                        {"reference": "[PENDING LIVE PROFILE]", "state": "deferred"}
                    ],
                    "blocking_reasons": [],
                },
                "gold_ready": {
                    "status": "blocked",
                    "evidence": [
                        {
                            "reference": "mappings/orders/missing.md",
                            "state": "missing",
                        }
                    ],
                    "blocking_reasons": ["reconciliation report not yet produced"],
                },
            },
        },
        {
            "table_id": "broken",
            "source_path": "mappings/broken/readiness-status.yaml",
            "input_defect": "readiness-status.yaml is not an interpretable mapping",
            "stages": {},
        },
    ]


def _lineage() -> dict:
    return {
        "nodes": [
            {
                "node_id": "metric:orders:NetSales",
                "kind": "metric_contract",
                "label": "NetSales",
                "evidence": "mappings/orders/metrics/NetSales.yaml",
            },
            {
                "node_id": "defect:mappings/orders/metrics/Broken.yaml",
                "kind": "input_defect",
                "label": "unreadable metric contract",
                "evidence": "mappings/orders/metrics/Broken.yaml",
            },
        ],
        "edges": [],
    }


def _table_references(table: dict) -> set[str]:
    if "input_defect" in table:
        return {table["source_path"]}
    return {
        f"{table['table_id']}#{stage}:{item['reference']}"
        for stage, block in table["stages"].items()
        for item in block["evidence"]
    }


def _all_references(tables: list[dict], lineage: dict) -> set[str]:
    references: set[str] = set()
    for table in tables:
        references |= _table_references(table)
    references |= {node["node_id"] for node in lineage["nodes"]}
    return references


def test_every_composed_item_appears_under_exactly_one_category() -> None:
    tables = _mixed_tables()
    lineage = _lineage()
    manifest = build_manifest(tables, lineage, redactions=[])
    expected = _all_references(tables, lineage)
    seen: dict[str, str] = {}
    for category in ("included", "unavailable", "omitted", "redacted"):
        for entry in manifest[category]:
            assert entry["locator"] not in seen, "locator appears in >1 category"
            seen[entry["locator"]] = category
    assert set(seen) == expected


def test_available_evidence_is_included() -> None:
    manifest = build_manifest(_mixed_tables(), _lineage(), redactions=[])
    locators = {entry["locator"] for entry in manifest["included"]}
    assert any("source-profile.md" in locator for locator in locators)


def test_deferred_evidence_is_unavailable() -> None:
    manifest = build_manifest(_mixed_tables(), _lineage(), redactions=[])
    locators = {entry["locator"] for entry in manifest["unavailable"]}
    assert any("PENDING LIVE PROFILE" in locator for locator in locators)


def test_missing_evidence_and_input_defect_are_omitted() -> None:
    manifest = build_manifest(_mixed_tables(), _lineage(), redactions=[])
    locators = {entry["locator"] for entry in manifest["omitted"]}
    assert any("missing.md" in locator for locator in locators)
    assert "mappings/broken/readiness-status.yaml" in locators


def test_unreadable_metric_contract_is_omitted() -> None:
    manifest = build_manifest(_mixed_tables(), _lineage(), redactions=[])
    locators = {entry["locator"] for entry in manifest["omitted"]}
    assert "defect:mappings/orders/metrics/Broken.yaml" in locators


def test_absolute_path_normalizes_to_repo_relative_and_is_redacted(
    tmp_path: Path,
) -> None:
    target = tmp_path / "mappings" / "orders" / "source-profile.md"
    target.parent.mkdir(parents=True)
    target.write_text("profile\n", encoding="utf-8")
    document = {"reference": str(target)}
    normalized, redactions = normalize_portability(tmp_path, document)
    assert normalized["reference"] == "mappings/orders/source-profile.md"
    assert len(redactions) == 1
    assert redactions[0]["category"] == "redacted"
    assert redactions[0]["original_class"] == "absolute_path"


def test_private_url_is_stripped_and_redacted(tmp_path: Path) -> None:
    document = {"note": "dashboard at http://reports.internal/dash for review"}
    normalized, redactions = normalize_portability(tmp_path, document)
    assert "reports.internal" not in normalized["note"]
    assert "[private URL removed]" in normalized["note"]
    assert redactions[0]["original_class"] == "private_url"


def test_foreign_absolute_path_outside_root_is_left_for_the_scanner(
    tmp_path: Path,
) -> None:
    """An absolute path that does not resolve inside the workspace root is
    NOT silently rewritten -- it survives so the disclosure scan can block it
    (FR-010/FR-019); normalization never invents a fake relative path."""
    document = {"reference": "/home/someone/outside/file.csv"}
    normalized, redactions = normalize_portability(tmp_path, document)
    assert normalized["reference"] == "/home/someone/outside/file.csv"
    assert redactions == []


def test_absolute_path_outside_the_fixed_prefix_whitelist_still_normalizes(
    tmp_path: Path,
) -> None:
    """A workspace mounted at a root not in the old home/Users/var/etc/opt/tmp
    whitelist (e.g. a container mount like /workspace/...) must still be
    detected as absolute and reduced to repo-relative when it resolves inside
    the workspace root -- any absolute path is disclosure-sensitive, not just
    a fixed prefix list."""
    root = tmp_path / "workspace" / "Seshat_BI"
    target = root / "mappings" / "orders" / "source-profile.md"
    target.parent.mkdir(parents=True)
    target.write_text("profile\n", encoding="utf-8")
    document = {"reference": str(target)}
    normalized, redactions = normalize_portability(root, document)
    assert normalized["reference"] == "mappings/orders/source-profile.md"
    assert len(redactions) == 1
    assert redactions[0]["original_class"] == "absolute_path"


def test_multiple_private_urls_in_one_value_are_all_stripped(
    tmp_path: Path,
) -> None:
    """A single value naming more than one private/internal URL must have
    every occurrence stripped, not just the first match -- otherwise a
    residual internal endpoint would leak into the rendered bundle."""
    document = {
        "note": (
            "primary at http://reports.internal/dash, "
            "mirror at http://10.0.0.5:8080/dash"
        )
    }
    normalized, redactions = normalize_portability(tmp_path, document)
    assert "reports.internal" not in normalized["note"]
    assert "10.0.0.5" not in normalized["note"]
    assert normalized["note"].count("[private URL removed]") == 2
    assert redactions[0]["original_class"] == "private_url"
