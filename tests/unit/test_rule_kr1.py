"""Focused fixture coverage for KR1 registry consistency."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from seshat.core import RuleContext
from seshat.rules.rule_kr1 import REGISTRY_REL, check_kr1

pytestmark = pytest.mark.unit


def _entry(identifier: str, name: str, slug: str) -> dict[str, object]:
    return {
        "id": identifier,
        "slug": slug,
        "canonical_name": name,
        "aliases": [],
        "domain": "sales-and-revenue",
        "metric_kind": "base_metric",
        "lifecycle": "seeded",
        "knowledge_contract_ref": "skills/retail-kpi-knowledge/contracts/example.md",
        "derives_from": [],
        "required_concepts": ["sales_value"],
        "required_decision_types": ["kpi_definition"],
        "source_roles": ["sales_fact"],
    }


def _context(tmp_path: Path, entries: list[dict[str, object]]) -> RuleContext:
    registry = tmp_path / REGISTRY_REL
    registry.parent.mkdir(parents=True)
    registry.write_text(
        yaml.safe_dump({"version": 1, "entries": entries}, sort_keys=False),
        encoding="utf-8",
    )
    contract = tmp_path / "skills/retail-kpi-knowledge/contracts/example.md"
    contract.parent.mkdir(parents=True)
    contract.write_text("# Generic example\n", encoding="utf-8")
    return RuleContext(
        tmp_path,
        (
            REGISTRY_REL,
            "skills/retail-kpi-knowledge/contracts/example.md",
        ),
    )


def test_kr1_accepts_a_well_formed_registry(tmp_path: Path) -> None:
    findings = list(
        check_kr1(
            _context(tmp_path, [_entry("KPI-MC-01", "Gross Sales", "gross-sales")])
        )
    )

    assert findings == []


def test_kr1_reports_each_structural_defect(tmp_path: Path) -> None:
    first = _entry("KPI-MC-01", "Gross Sales", "gross-sales")
    duplicate = deepcopy(first)
    duplicate["slug"] = "duplicate-sales"
    duplicate["canonical_name"] = "Duplicate Sales"
    duplicate["aliases"] = ["Gross Sales"]
    duplicate["derives_from"] = ["KPI-MC-99"]
    duplicate["lifecycle"] = "unsupported"
    duplicate["knowledge_contract_ref"] = "gold.fct_forbidden"

    messages = [
        finding.message for finding in check_kr1(_context(tmp_path, [first, duplicate]))
    ]

    assert any("duplicate registry id" in message for message in messages)
    assert any("collides with a canonical_name" in message for message in messages)
    assert any("unresolved ids" in message for message in messages)
    assert any("lifecycle must be" in message for message in messages)
    assert any("does not resolve" in message for message in messages)
    assert any("physical layer binding" in message for message in messages)


def test_kr1_requires_blockers_for_a_planned_entry(tmp_path: Path) -> None:
    planned = _entry("KPI-MC-02", "Planned Measure", "planned-measure")
    planned["lifecycle"] = "planned"

    messages = [finding.message for finding in check_kr1(_context(tmp_path, [planned]))]

    assert any("must name concrete blockers" in message for message in messages)


def test_product_registry_indexes_existing_contracts_and_has_no_example_leakage() -> (
    None
):
    root = Path(__file__).parents[2]
    registry = yaml.safe_load((root / REGISTRY_REL).read_text(encoding="utf-8"))
    entries = registry["entries"]
    by_id = {entry["id"]: entry for entry in entries}

    assert len(entries) == 22
    assert {f"KPI-MC-{number:02d}" for number in range(1, 14)} <= set(by_id)
    assert by_id["KPI-MC-11"]["lifecycle"] == "seeded"
    assert by_id["KPI-MC-12"]["lifecycle"] == "planned"
    assert by_id["KPI-MC-13"]["lifecycle"] == "seeded"
    assert all(
        by_id[key]["lifecycle"] == "planned"
        for key in [
            "KPI-MC-12",
            "KPI-MC-16",
            "KPI-MC-17",
            "KPI-MC-18",
            "KPI-MC-19",
            "KPI-MC-20",
            "KPI-MC-21",
            "KPI-MC-22",
        ]
    )
    text = (root / REGISTRY_REL).read_text(encoding="utf-8").casefold()
    for token in (
        "c086",
        "retail_store_sales",
        "gold.fct_sales_rss",
        "total_spent",
        "quantity",
        "transaction_id",
        "discount_applied",
        "customer_id",
        "12575",
        "50.37",
        "q1",
        "q2",
        "q3",
        "q4",
        "ahmed shaaban",
        "billing code",
        "billing codes",
        "billing_code",
        "insurance pii",
    ):
        assert not re.search(rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])", text)
