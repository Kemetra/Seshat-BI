"""Conformance tests for the product Knowledge Contracts (spec 121, T020).

Structural validation (stdlib-only, no jsonschema dependency) of the flow and
dashboard-blueprint contracts, plus the three boundary probes: KPI-meaning routes
to retail_kpi, bigdata needs scale evidence, and no execution adapter gains
meaning/mapping/metric/semantic/approval authority.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLOW = _REPO_ROOT / "contracts/knowledge/database-to-pbip-flow.yaml"
_BLUEPRINT = _REPO_ROOT / "contracts/report/dashboard-blueprint.yaml"
_AUTHORITY = _REPO_ROOT / "contracts/knowledge/approval-authority.yaml"

_ALLOWED_ROUTES = {
    "readiness",
    "retail_kpi",
    "sql",
    "dax",
    "python",
    "bigdata",
    "dashboard_design",
    "compass",
}
_ALLOWED_STAGES = {
    "discovery",
    "domain_guess",
    "scope_proposal",
    "business_knowledge_interview",
    "kpi_contracts",
    "silver_gold_model_planning",
    "semantic_model_dax",
    "report_intent",
    "dashboard_blueprint",
    "pbip_prototype_readiness",
    "evidence_pack",
}
_REQUIRED_KEYS = {
    "stage",
    "allowed_routes",
    "required_inputs",
    "required_outputs",
    "stop_rules",
    "blocking_decision_categories",
    "handoff",
    "non_goals",
    "evidence_requirements",
}
_CRITICAL_TYPES = {
    "kpi_definition",
    "pii_handling",
    "table_grain",
    "primary_key",
    "relationship_cardinality",
    "missing_value_rule",
    "data_exclusion",
    "policy_ruling",
    "dashboard_blueprint_approval",
    "publish_export",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _stages(path: Path) -> list[dict]:
    return _load(path)["stages"]


# ---- structural validity --------------------------------------------------


def test_flow_contract_parses_and_has_all_eleven_stages() -> None:
    stages = _stages(_FLOW)
    assert {s["stage"] for s in stages} == _ALLOWED_STAGES
    assert len(stages) == 11


@pytest.mark.parametrize("path", [_FLOW, _BLUEPRINT])
def test_every_entry_has_all_required_keys(path: Path) -> None:
    for entry in _stages(path):
        assert _REQUIRED_KEYS <= set(entry), (
            f"{entry.get('stage')} missing {_REQUIRED_KEYS - set(entry)}"
        )


@pytest.mark.parametrize("path", [_FLOW, _BLUEPRINT])
def test_routes_and_stages_use_known_vocabulary(path: Path) -> None:
    for entry in _stages(path):
        assert entry["stage"] in _ALLOWED_STAGES
        assert set(entry["allowed_routes"]) <= _ALLOWED_ROUTES
        for cat in entry["blocking_decision_categories"]:
            assert cat in _CRITICAL_TYPES, f"unknown blocking category {cat!r}"


@pytest.mark.parametrize("path", [_FLOW, _BLUEPRINT])
def test_stop_rules_name_what_unblocks_them(path: Path) -> None:
    for entry in _stages(path):
        assert entry["stop_rules"], f"{entry['stage']} has no stop rules"
        for rule in entry["stop_rules"]:
            assert rule.get("condition") and rule.get("unblocked_by"), (
                f"{entry['stage']} stop rule missing condition/unblocked_by"
            )


@pytest.mark.parametrize("path", [_FLOW, _BLUEPRINT])
def test_every_entry_declares_outputs_nongoals_evidence(path: Path) -> None:
    for entry in _stages(path):
        assert entry["required_outputs"]
        assert entry["non_goals"]
        assert entry["evidence_requirements"]


# ---- boundary probes ------------------------------------------------------


def test_probe_kpi_meaning_stages_route_to_retail_kpi() -> None:
    # Any stage that touches KPI meaning (kpi_definition in its blocking set)
    # must allow the retail_kpi route -- meaning is never invented elsewhere.
    for entry in _stages(_FLOW):
        if "kpi_definition" in entry["blocking_decision_categories"]:
            assert "retail_kpi" in entry["allowed_routes"], (
                f"{entry['stage']} gates on kpi_definition but cannot route to "
                "retail_kpi"
            )


def test_probe_dax_stage_does_not_own_meaning() -> None:
    dax_stage = next(s for s in _stages(_FLOW) if s["stage"] == "semantic_model_dax")
    assert "retail_kpi" in dax_stage["allowed_routes"]
    joined = " ".join(dax_stage["non_goals"]).lower()
    assert "meaning" in joined  # explicit non-goal: does not define KPI meaning


def test_probe_bigdata_requires_scale_evidence() -> None:
    # Wherever bigdata is an allowed route, a stop rule must gate it on recorded
    # scale evidence (else python).
    for entry in _stages(_FLOW):
        if "bigdata" in entry["allowed_routes"]:
            joined = " ".join(
                f"{r['condition']} {r['unblocked_by']}" for r in entry["stop_rules"]
            ).lower()
            assert "scale evidence" in joined, (
                f"{entry['stage']} allows bigdata without a scale-evidence stop rule"
            )


def test_probe_no_execution_adapter_route_anywhere() -> None:
    # No stage grants an execution/publish adapter a knowledge route -- execution
    # adapters define no meaning/mapping/metric/semantic logic/approval (FR-004).
    for entry in _stages(_FLOW) + _stages(_BLUEPRINT):
        assert "execution" not in set(entry["allowed_routes"])
        assert "pbip" not in set(entry["allowed_routes"])


def test_probe_pbip_stage_defers_generation_and_publish() -> None:
    pbip = next(s for s in _stages(_FLOW) if s["stage"] == "pbip_prototype_readiness")
    joined = " ".join(pbip["non_goals"]).lower()
    assert "freehand" in joined
    assert "publish" in joined
    assert "dashboard_blueprint_approval" in pbip["blocking_decision_categories"]


# ---- approval-authority contract ------------------------------------------


def test_approval_authority_covers_every_critical_type() -> None:
    data = _load(_AUTHORITY)
    eligibility = data["eligibility"]
    for dtype in _CRITICAL_TYPES:
        assert dtype in eligibility, f"no authority mapping for {dtype!r}"
        assert eligibility[dtype], f"empty eligibility for {dtype!r}"
