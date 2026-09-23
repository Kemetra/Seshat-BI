"""Spec 124 answerability and governed contract authoring fixtures."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from seshat.kpi_answerability import (
    AnswerabilityInputs,
    derive_answerability,
    render_answerability_artifact,
)
from seshat.kpi_contracts import (
    ContractDraftRefused,
    ContractDraftRequest,
    FinalizationContext,
    draft_project_metric_contract,
    finalize_project_metric_contract,
)

pytestmark = pytest.mark.unit

_AUTHORITY = {
    "kpi_definition": frozenset({"metric_owner"}),
    "policy_ruling": frozenset({"metric_owner"}),
}
_EVIDENCE = "mappings/orders/source-map.yaml#net_sales"
_REPO_ROOT = Path(__file__).resolve().parents[2]
# Decision approval evidence is RE-VERIFIED at finalize (never trusted from the
# caller), so the fixtures cite a real committed file and its current identity.
_DECISION_EVIDENCE = "docs/conventions.md"
_DECISION_SHA = hashlib.sha256(
    (_REPO_ROOT / _DECISION_EVIDENCE).read_bytes()
).hexdigest()


def _entry(*, lifecycle: str = "seeded") -> dict[str, object]:
    entry: dict[str, object] = {
        "id": "KPI-MC-02",
        "knowledge_contract_ref": "skills/retail-kpi-knowledge/contracts/net-sales.md",
        "lifecycle": lifecycle,
        "required_concepts": ["sales_value"],
        "required_decision_types": ["kpi_definition", "policy_ruling"],
        "source_roles": ["sales_fact"],
    }
    if lifecycle == "planned":
        entry["blockers"] = ["a required source role has not been designed"]
    return entry


def _approved(
    decision_type: str, identifier: str, kpi: str = "net_sales"
) -> dict[str, object]:
    return {
        "id": identifier,
        "decision_type": decision_type,
        "status": "approved",
        "scope": {"kpis": [kpi]},
        "approval": {
            "approved_by": "Jane Doe (metric_owner)",
            "approved_at": "2026-07-13",
            "source": "owner review",
            "evidence": [_DECISION_EVIDENCE],
            "evidence_identity": {_DECISION_EVIDENCE: _DECISION_SHA},
            "reviewed_scope": "orders",
        },
    }


# A superset authority: the pii_handling class is harmless for non-PII contracts
# and lets one helper serve both the PII and non-PII finalization tests.
_FINALIZE_AUTHORITY = {**_AUTHORITY, "pii_handling": frozenset({"metric_owner"})}


def _finalize(
    contract: dict[str, object],
    *,
    decisions: list[dict[str, object]],
    evidence_freshness: dict[str, bool] | None = None,
    named_human_approval: str | None = "Jane Doe (metric_owner)",
) -> dict[str, object]:
    return finalize_project_metric_contract(
        contract,
        FinalizationContext(
            decisions=decisions,
            authority=_FINALIZE_AUTHORITY,
            evidence_freshness=(
                {_EVIDENCE: True} if evidence_freshness is None else evidence_freshness
            ),
            named_human_approval=named_human_approval,
            repo_root=_REPO_ROOT,
        ),
    )


def _bound_draft() -> dict[str, object]:
    draft = _draft()
    draft["binds_to"] = {
        "gold_table": "gold.fct_sales",
        "columns": ["net_sales_amount"],
        "pii_sensitive": False,
    }
    return draft


def _net_sales_decisions() -> list[dict[str, object]]:
    return [
        _approved("kpi_definition", "kpi_definition.net_sales"),
        _approved("policy_ruling", "policy_ruling.net_sales"),
    ]


def test_answerability_fails_closed_for_lookalike_policy_and_stale_evidence() -> None:
    lookalike = derive_answerability(
        _entry(),
        AnswerabilityInputs(
            scope="orders",
            available_source_roles=["sales_fact"],
            mapped_concepts=[],
            approved_decision_types=[],
            evidence=[_EVIDENCE],
            evidence_is_fresh=True,
            domain_served=True,
            lookalike_concepts=["sales_value"],
        ),
    )
    stale = derive_answerability(
        _entry(),
        AnswerabilityInputs(
            scope="orders",
            available_source_roles=["sales_fact"],
            mapped_concepts=["sales_value"],
            approved_decision_types=["kpi_definition", "policy_ruling"],
            evidence=[_EVIDENCE],
            evidence_is_fresh=False,
            domain_served=True,
        ),
    )

    assert lookalike.status == "Blocked -- needs business definition"
    assert "lookalike" in lookalike.blockers[0]
    assert stale.status == "Blocked -- missing field"
    assert "stale" in stale.blockers[0]


@pytest.mark.parametrize(
    ("lifecycle", "domain_served", "roles", "expected"),
    [
        ("planned", True, ["sales_fact"], "Planned"),
        ("seeded", False, ["sales_fact"], "Out of scope"),
        ("seeded", True, [], "Blocked -- missing field"),
    ],
)
def test_answerability_handles_planned_scope_and_missing_role(
    lifecycle: str, domain_served: bool, roles: list[str], expected: str
) -> None:
    row = derive_answerability(
        _entry(lifecycle=lifecycle),
        AnswerabilityInputs(
            scope="orders",
            available_source_roles=roles,
            mapped_concepts=["sales_value"],
            approved_decision_types=["kpi_definition", "policy_ruling"],
            evidence=[_EVIDENCE],
            evidence_is_fresh=True,
            domain_served=domain_served,
        ),
    )

    assert row.status == expected


def test_rendered_answerability_is_scorecard_shaped_and_unscored() -> None:
    row = derive_answerability(
        _entry(),
        AnswerabilityInputs(
            scope="orders",
            available_source_roles=["sales_fact"],
            mapped_concepts=["sales_value"],
            approved_decision_types=["kpi_definition", "policy_ruling"],
            evidence=[_EVIDENCE],
            evidence_is_fresh=True,
            domain_served=True,
        ),
    )

    artifact = render_answerability_artifact("orders", [row])

    assert "> Table: orders" in artifact
    assert "| KPI | Contract | Coverage status | Blocker |" in artifact
    assert not re.search(r"\d\s*%", artifact)


def test_draft_requires_approved_definition_and_policy() -> None:
    with pytest.raises(ContractDraftRefused, match="kpi_definition"):
        draft_project_metric_contract(
            ContractDraftRequest(
                name="NetSales",
                formula_intent="Realized sales value.",
                grain="sales line",
                owner="Sales owner",
                generic_kpi_ref="KPI-MC-02",
                custom=False,
                registry_ids=["KPI-MC-02"],
                decisions=[],
                authority=_AUTHORITY,
                required_decision_types=["kpi_definition", "policy_ruling"],
                source_evidence=[_EVIDENCE],
            )
        )


def _draft() -> dict[str, object]:
    return draft_project_metric_contract(
        ContractDraftRequest(
            name="NetSales",
            formula_intent="Realized sales value after the approved exclusions.",
            grain="sales line",
            owner="Sales owner",
            generic_kpi_ref="KPI-MC-02",
            custom=False,
            registry_ids=["KPI-MC-02"],
            decisions=[
                _approved("kpi_definition", "kpi_definition.net_sales"),
                _approved("policy_ruling", "policy_ruling.net_sales"),
            ],
            authority=_AUTHORITY,
            required_decision_types=["kpi_definition", "policy_ruling"],
            source_evidence=[_EVIDENCE],
            time_additivity="fully",
            unit="currency",
        )
    )


def test_draft_records_provenance_and_an_honest_gold_blocker() -> None:
    draft = _draft()

    assert draft["generic_kpi_ref"] == "KPI-MC-02"
    assert draft["custom"] is False
    assert draft["decision_refs"] == [
        "kpi_definition.net_sales",
        "policy_ruling.net_sales",
    ]
    assert draft["source_evidence"] == [_EVIDENCE]
    assert draft["readiness"]["status"] == "blocked"
    assert (
        "physical gold binding is not materialized"
        in draft["readiness"]["blocking_reasons"][0]
    )


@pytest.mark.parametrize(
    ("formula_intent", "expected"),
    [
        ("SELECT net_sales FROM fact_sales", "SQL implementation"),
        ("CALCULATE([Net Sales])", "DAX implementation"),
        ("Use host = <unapproved-host>", "connection string"),
        ("Show the result in a dashboard visual", "visual or dashboard implementation"),
        ("Customer email = <redacted> contributes to the total", "raw PII value"),
        (
            "Read gold.fct_sales before the binding is approved",
            "physical layer binding",
        ),
    ],
)
def test_draft_rejects_implementation_sensitive_values_and_premature_bindings(
    formula_intent: str, expected: str
) -> None:
    with pytest.raises(ContractDraftRefused, match=expected):
        draft_project_metric_contract(
            ContractDraftRequest(
                name="NetSales",
                formula_intent=formula_intent,
                grain="sales line",
                owner="Sales owner",
                generic_kpi_ref="KPI-MC-02",
                custom=False,
                registry_ids=["KPI-MC-02"],
                decisions=[
                    _approved("kpi_definition", "kpi_definition.net_sales"),
                    _approved("policy_ruling", "policy_ruling.net_sales"),
                ],
                authority=_AUTHORITY,
                required_decision_types=["kpi_definition", "policy_ruling"],
                source_evidence=[_EVIDENCE],
            )
        )


def test_custom_draft_requires_named_owner_and_does_not_need_registry_entry() -> None:
    decisions = [_approved("kpi_definition", "kpi_definition.custom", "CustomMetric")]
    registry_ids = ["KPI-MC-02"]
    registry_before = registry_ids.copy()
    with pytest.raises(ContractDraftRefused, match="named eligible owner"):
        draft_project_metric_contract(
            ContractDraftRequest(
                name="CustomMetric",
                formula_intent="A project-specific value.",
                grain="daily",
                owner="owner",
                generic_kpi_ref=None,
                custom=True,
                registry_ids=registry_ids,
                decisions=decisions,
                authority=_AUTHORITY,
                required_decision_types=["kpi_definition"],
                source_evidence=[_EVIDENCE],
                time_additivity="fully",
                unit="each",
                required_fields=["custom_value"],
            )
        )

    custom = draft_project_metric_contract(
        ContractDraftRequest(
            name="CustomMetric",
            formula_intent="A project-specific value.",
            grain="daily",
            owner="Jane Doe (metric_owner)",
            generic_kpi_ref=None,
            custom=True,
            registry_ids=registry_ids,
            decisions=decisions,
            authority=_AUTHORITY,
            required_decision_types=["kpi_definition"],
            source_evidence=[_EVIDENCE],
            time_additivity="fully",
            unit="each",
            required_fields=["custom_value"],
        )
    )

    assert custom["custom"] is True
    assert "generic_kpi_ref" not in custom
    assert registry_ids == registry_before


def test_finalization_passes_when_every_precondition_holds() -> None:
    passing = _finalize(_bound_draft(), decisions=_net_sales_decisions())

    assert passing["readiness"]["status"] == "pass"
    assert set(passing["handoff_intent"]) == {"sql", "dax", "python", "big_data"}


def test_finalization_blocks_an_unmaterialized_binding() -> None:
    unbound = _finalize(_draft(), decisions=_net_sales_decisions())

    assert unbound["readiness"]["status"] == "blocked"
    assert any("binding" in item for item in unbound["readiness"]["blocking_reasons"])


def test_finalization_blocks_stale_evidence() -> None:
    stale = _finalize(
        _bound_draft(),
        decisions=_net_sales_decisions(),
        evidence_freshness={_EVIDENCE: False},
    )

    assert stale["readiness"]["status"] == "blocked"
    assert any("stale" in item for item in stale["readiness"]["blocking_reasons"])


def test_finalization_blocks_a_superseded_decision() -> None:
    superseded = _net_sales_decisions()
    superseded[0]["status"] = "superseded"

    invalid = _finalize(_bound_draft(), decisions=superseded)

    assert invalid["readiness"]["status"] == "blocked"
    assert any(
        "superseded" in item for item in invalid["readiness"]["blocking_reasons"]
    )


def test_finalization_blocks_missing_named_approval() -> None:
    missing = _finalize(
        _bound_draft(), decisions=_net_sales_decisions(), named_human_approval=None
    )

    assert missing["readiness"]["status"] == "blocked"
    assert any("approval" in item for item in missing["readiness"]["blocking_reasons"])


def test_finalization_preserves_an_unresolved_declared_blocker() -> None:
    draft = _bound_draft()
    draft["readiness"]["blocking_reasons"] = ["source mapping needs review"]

    blocked = _finalize(draft, decisions=_net_sales_decisions())

    assert blocked["readiness"]["status"] == "blocked"
    assert "source mapping needs review" in blocked["readiness"]["blocking_reasons"]


def _pii_draft() -> dict[str, object]:
    draft = _bound_draft()
    draft["binds_to"]["pii_sensitive"] = True
    return draft


def test_finalization_blocks_pii_binding_without_approved_pii_handling() -> None:
    result = _finalize(_pii_draft(), decisions=_net_sales_decisions())

    assert result["readiness"]["status"] == "blocked"
    assert any(
        "pii_handling" in item for item in result["readiness"]["blocking_reasons"]
    )


def test_finalization_blocks_pii_comparison_without_approved_handling() -> None:
    draft = _bound_draft()
    draft["compares_to"] = {
        "gold_table": "gold.fct_targets",
        "columns": ["target_amount"],
        "pii_sensitive": True,
    }

    result = _finalize(draft, decisions=_net_sales_decisions())

    assert result["readiness"]["status"] == "blocked"
    assert any(
        "pii_handling" in item for item in result["readiness"]["blocking_reasons"]
    )


def test_finalization_blocks_pii_when_handling_decision_is_unreferenced() -> None:
    decisions = [
        *_net_sales_decisions(),
        _approved("pii_handling", "pii_handling.net_sales"),
    ]

    result = _finalize(_pii_draft(), decisions=decisions)

    assert result["readiness"]["status"] == "blocked"
    assert any(
        "pii_handling" in item for item in result["readiness"]["blocking_reasons"]
    )


def test_finalization_passes_pii_binding_with_approved_pii_handling() -> None:
    draft = _pii_draft()
    draft["decision_refs"] = [*draft["decision_refs"], "pii_handling.net_sales"]
    decisions = [
        *_net_sales_decisions(),
        _approved("pii_handling", "pii_handling.net_sales"),
    ]

    result = _finalize(draft, decisions=decisions)

    assert result["readiness"]["status"] == "pass"


def test_new_generic_contracts_do_not_copy_worked_example_tokens() -> None:
    root = Path(__file__).parents[2]
    paths = (
        "skills/retail-kpi-knowledge/contracts/discounted-transaction-rate.md",
        "skills/retail-kpi-knowledge/contracts/average-basket-size-units.md",
    )
    text = "\n".join(
        (root / path).read_text(encoding="utf-8") for path in paths
    ).casefold()

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
        assert token not in text


def test_draft_refuses_a_decision_approved_for_another_kpi() -> None:
    """Audit F071: an approved kpi_definition for net_sales does not stand in for
    Gross Margin."""
    with pytest.raises(ContractDraftRefused, match="scoped to this KPI"):
        draft_project_metric_contract(
            ContractDraftRequest(
                name="GrossMargin",
                formula_intent="Sales value less cost.",
                grain="sales line",
                owner="Sales owner",
                generic_kpi_ref="KPI-MC-09",
                custom=False,
                registry_ids=["KPI-MC-09"],
                decisions=[_approved("kpi_definition", "kpi_definition.net_sales")],
                authority=_AUTHORITY,
                required_decision_types=["kpi_definition"],
                source_evidence=[_EVIDENCE],
            )
        )


@pytest.mark.parametrize(
    "approver", ["Claude Agent (wizard)", "Someone Else (metric_owner)"]
)
def test_finalize_refuses_an_approver_who_did_not_approve(approver: str) -> None:
    """Audit F071: the caller-supplied approver string is not authority -- it must
    be the eligible named human who approved a referenced kpi_definition."""
    result = _finalize(
        _bound_draft(),
        decisions=_net_sales_decisions(),
        named_human_approval=approver,
    )
    assert result["readiness"]["status"] == "blocked"


def test_finalize_blocks_on_stale_decision_evidence() -> None:
    """Audit F071: decision evidence freshness is computed, not caller-supplied."""
    decisions = _net_sales_decisions()
    decisions[0]["approval"]["evidence_identity"] = {_DECISION_EVIDENCE: "0" * 64}
    result = _finalize(_bound_draft(), decisions=decisions)
    assert result["readiness"]["status"] == "blocked"
    assert any("stale" in r for r in result["readiness"]["blocking_reasons"])
