"""Focused fixture coverage for KP1 provenance structure."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from seshat.core import RuleContext
from seshat.rules.rule_kp1 import REGISTRY_REL, check_kp1

pytestmark = pytest.mark.unit

_CONTRACT_REL = "mappings/orders/metrics/NetSales.yaml"
_SOURCE_REL = "mappings/orders/source-map.yaml"


def _context(tmp_path: Path, contract: dict[str, object]) -> RuleContext:
    registry = tmp_path / REGISTRY_REL
    registry.parent.mkdir(parents=True)
    registry.write_text(
        yaml.safe_dump({"version": 1, "entries": [{"id": "KPI-MC-02"}]}),
        encoding="utf-8",
    )
    source = tmp_path / _SOURCE_REL
    source.parent.mkdir(parents=True)
    source.write_text("version: 1\n", encoding="utf-8")
    metric = tmp_path / _CONTRACT_REL
    metric.parent.mkdir(parents=True)
    metric.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return RuleContext(tmp_path, (REGISTRY_REL, _SOURCE_REL, _CONTRACT_REL))


def _generic_contract() -> dict[str, object]:
    return {
        "generic_kpi_ref": "KPI-MC-02",
        "custom": False,
        "decision_refs": ["kpi_definition.net_sales"],
        "source_evidence": [f"{_SOURCE_REL}#net_sales"],
    }


def test_kp1_accepts_well_formed_generic_provenance(tmp_path: Path) -> None:
    assert list(check_kp1(_context(tmp_path, _generic_contract()))) == []


def test_kp1_leaves_legacy_contracts_without_provenance_valid(tmp_path: Path) -> None:
    assert list(check_kp1(_context(tmp_path, {"name": "LegacyMetric"}))) == []


def test_kp1_rejects_source_evidence_pointing_at_a_non_evidence_artifact(
    tmp_path: Path,
) -> None:
    contract = deepcopy(_generic_contract())
    contract["source_evidence"] = [_CONTRACT_REL]

    messages = [finding.message for finding in check_kp1(_context(tmp_path, contract))]

    assert any("source_evidence ref" in message for message in messages)


def test_kp1_reports_classification_and_reference_defects(tmp_path: Path) -> None:
    contract = deepcopy(_generic_contract())
    contract["custom"] = True
    contract["generic_kpi_ref"] = "KPI-MC-99"
    contract["decision_refs"] = []
    contract["source_evidence"] = ["https://not-a-repo-reference"]

    messages = [finding.message for finding in check_kp1(_context(tmp_path, contract))]

    assert any("exactly one" in message for message in messages)
    assert any("does not resolve" in message for message in messages)
    assert any("decision_refs" in message for message in messages)
    assert any("source_evidence ref" in message for message in messages)
