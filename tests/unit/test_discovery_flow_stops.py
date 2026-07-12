"""Recorded-artifact oracles for spec 122's bounded discovery flow."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
import yaml

from seshat.core import RuleContext
from seshat.decision_gate import compute_verdict
from seshat.decision_store import CRITICAL_DECISION_TYPES, load_store
from seshat.rules.decision_store import (
    check_ds1,
    check_ds2,
    check_ds3,
    check_ds4,
    check_ds5,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "portfolio-survey"
FLOW_REL = "contracts/knowledge/database-to-pbip-flow.yaml"
AUTHORITY_REL = "contracts/knowledge/approval-authority.yaml"
STORE_REL = ".seshat/semantic-decisions.yaml"


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _rule_findings(tmp_path: Path, fixture: Path) -> list[Any]:
    files = {
        STORE_REL: fixture.read_text(encoding="utf-8"),
        AUTHORITY_REL: (REPO_ROOT / AUTHORITY_REL).read_text(encoding="utf-8"),
    }
    for rel, body in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=tuple(files))
    findings: list[Any] = []
    for check in (check_ds1, check_ds2, check_ds3, check_ds4, check_ds5):
        findings.extend(check(ctx))
    return findings


def _decision(data: dict[str, Any], decision_id: str | None = None) -> dict[str, Any]:
    decisions = data["decisions"]
    assert isinstance(decisions, list) and decisions
    if decision_id is None:
        return decisions[0]
    return next(item for item in decisions if item["id"] == decision_id)


def _flow_stages() -> dict[str, dict[str, Any]]:
    flow = _load(REPO_ROOT / FLOW_REL)
    return {entry["stage"]: entry for entry in flow["stages"]}


@pytest.mark.parametrize("name", ["proposed.yaml", "ambiguous.yaml"])
def test_domain_proposals_are_grounded_noncritical_records(
    tmp_path: Path, name: str
) -> None:
    fixture = FIXTURES / "domain" / name
    data = _load(fixture)
    record = _decision(data)

    assert _rule_findings(tmp_path, fixture) == []
    assert record["decision_type"] == "domain_classification"
    assert record["decision_type"] not in CRITICAL_DECISION_TYPES
    assert record["status"] == "proposed"
    assert record["confidence"] in {"low", "medium", "high"}
    assert record["proposed_by"] == "agent"
    assert record["proposed_at"]
    assert record["evidence"]
    assert record["decision_type"] not in set(
        _flow_stages()["domain_guess"]["blocking_decision_categories"]
    )
    if name == "ambiguous.yaml":
        assert "undetermined" in record["statement"].lower()
        assert len(record["alternatives"]) > 1


@pytest.mark.parametrize(
    "name", ["coherent.yaml", "cross-boundary.yaml", "explicit-limit.yaml"]
)
def test_scope_proposals_are_bounded_grounded_and_nonnumeric(
    tmp_path: Path, name: str
) -> None:
    fixture = FIXTURES / "scope" / name
    data = _load(fixture)
    record = _decision(data)
    rendered = fixture.read_text(encoding="utf-8").lower()

    assert _rule_findings(tmp_path, fixture) == []
    assert record["decision_type"] == "scope_proposal"
    assert record["decision_type"] not in CRITICAL_DECISION_TYPES
    assert record["proposed_by"] == "agent"
    assert record["proposed_at"]
    assert len(record["evidence"]) >= 2
    assert not any(token in rendered for token in ("score:", "threshold:", "rank:"))
    assert record["decision_type"] not in set(
        _flow_stages()["scope_proposal"]["blocking_decision_categories"]
    )
    if name == "explicit-limit.yaml":
        assert record["scope"]["tables"] == record["owner_limit"]
    if name == "cross-boundary.yaml":
        assert record["status"] == "needs_user_input"
        assert len(record["alternatives"]) >= 2


def test_partial_scope_acceptance_uses_bidirectional_supersession(
    tmp_path: Path,
) -> None:
    fixture = FIXTURES / "scope" / "partial-acceptance.yaml"
    data = _load(fixture)
    old = _decision(data, "scope_proposal.order_sales.v1")
    new = _decision(data, "scope_proposal.order_sales.v2")

    assert _rule_findings(tmp_path, fixture) == []
    assert old["status"] == "superseded"
    assert old["superseded_by"] == new["id"]
    assert new["status"] == "proposed"
    assert new["supersedes"] == old["id"]
    assert new["scope"]["tables"] == ["analytics.orders"]


def test_layer_b_delegation_does_not_expand_the_survey() -> None:
    survey = (FIXTURES / "db-schema" / "survey.md").read_text(encoding="utf-8")
    skill = (
        REPO_ROOT / ".claude" / "skills" / "retail-discover-portfolio" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "retail-onboard-table" in skill
    assert "Do not deep-profile inside the survey" in skill
    for forbidden in (
        "measured uniqueness:",
        "measured missingness:",
        "date coverage:",
    ):
        assert forbidden not in survey.lower()


def test_handoff_matches_the_existing_interview_contract_exactly() -> None:
    handoff = _load(FIXTURES / "handoff" / "manifest.yaml")
    contract = _load(
        REPO_ROOT / "contracts/interview/business-knowledge-interview.yaml"
    )
    required = contract["stages"][0]["required_inputs"]

    assert handoff["required_inputs"] == required
    assert all(
        path.startswith("mappings/") and path.endswith("/source-profile.md")
        for path in handoff["discovery_profiles"]
    )
    assert not any("survey" in path for path in handoff["discovery_profiles"])
    assert handoff["existing_decision_ids"]
    assert handoff["present_existing_for"] == ["confirmation", "supersession"]
    assert handoff["preserve_existing_records"] is True
    assert handoff["records_interview_outcomes"] is False
    assert handoff["grants_approval"] is False
    assert handoff["kpi_meaning_route"] == "retail_kpi"


def _derive_next_action(state: dict[str, bool]) -> str:
    if state.get("beyond_handoff"):
        return "STOP; continue under the downstream stage contract, not this skill."
    if not state["survey"]:
        return "Produce the Layer-A portfolio survey."
    if not state["domain"]:
        return "Record the grounded domain proposal."
    if not state["scope"]:
        return "Record the bounded scope proposal."
    if not state["layer_b_complete"]:
        return "Invoke retail-onboard-table for the missing Layer-B profile."
    return "Hand off to business-knowledge-interview, then STOP."


@pytest.mark.parametrize(
    "fixture",
    sorted((FIXTURES / "flow").glob("*.yaml")),
    ids=lambda path: path.stem,
)
def test_recorded_state_has_one_derivable_next_action(fixture: Path) -> None:
    case = _load(fixture)
    assert _derive_next_action(case["state"]) == case["expected"]


def test_absent_store_gate_pass_proves_local_stop_is_feature_owned(
    tmp_path: Path,
) -> None:
    flow_target = tmp_path / FLOW_REL
    flow_target.parent.mkdir(parents=True, exist_ok=True)
    flow_target.write_bytes((REPO_ROOT / FLOW_REL).read_bytes())
    store = load_store(tmp_path, (FLOW_REL,))
    case = _load(FIXTURES / "flow" / "no-survey.yaml")

    assert case["local_stop"] == "portfolio survey missing; complete Layer-A discovery"
    for stage in ("discovery", "domain_guess", "scope_proposal"):
        assert compute_verdict(tmp_path, store, stage).verdict == "pass"


def test_top_level_contracts_and_authority_map_are_unchanged() -> None:
    # Baseline re-pinned when spec 123 landed: the governed-dashboard flow added
    # `report_intent_approval` as a blocking category (+ stop rule) to the report
    # intent/blueprint stages, and the authority map granted `report_owner` the
    # `report_intent_approval` class. Both are legitimate spec-123 contract
    # extensions; these digests guard against UNintended drift from that baseline.
    expected = {
        FLOW_REL: "2cced083e5661a2e25fefd9edf74020a084437b790ec67d3e75a15f0130f7552",
        AUTHORITY_REL: (
            "a6da9c32629ab5bc368dee7a9fdcd6410fe18747fd170fcd5457ab3dcd78ddc7"
        ),
    }
    for rel, digest in expected.items():
        assert hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest() == digest


def test_discovery_flow_adds_no_runtime_engine_or_state_file() -> None:
    forbidden = (
        "src/seshat/portfolio_discovery_flow.py",
        "src/seshat/discovery_router.py",
        "src/seshat/discovery_state.py",
    )
    assert all(not (REPO_ROOT / path).exists() for path in forbidden)
