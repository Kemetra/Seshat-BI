"""Public contract checks for the governed existing-PBIP entry path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbip_adoption import assess_pbip
from tests.unit._schema_check import _validate, assert_matches_schema

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "pbip_adoption" / "supported"


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _assessment() -> dict:
    return assess_pbip(FIXTURE)


def test_public_schemas_are_byte_for_byte_design_contract_promotions() -> None:
    contracts = ROOT / "specs" / "126-adopt-existing-pbip" / "contracts"
    for name in (
        "pbip-adoption-assessment.schema.json",
        "pbip-adoption-scaffold-result.schema.json",
    ):
        assert (ROOT / "schemas" / name).read_bytes() == (contracts / name).read_bytes()


def test_valid_minimum_assessment_matches_closed_schema() -> None:
    assert_matches_schema(
        _assessment(), _schema("pbip-adoption-assessment.schema.json")
    )


def test_assessment_uses_only_the_five_fact_classifications() -> None:
    allowed = {"observed", "proposed", "missing", "blocked", "unavailable_with_reason"}
    assessment = _assessment()
    assert {fact["classification"] for fact in assessment["facts"]} <= allowed
    assert all(
        fact["artifact"]
        or fact["reason"]
        or fact["classification"] in {"missing", "blocked", "proposed"}
        for fact in assessment["facts"]
    )


def test_paths_are_relative_and_response_has_exactly_one_next_step() -> None:
    assessment = _assessment()
    paths = [
        component["artifact"] for component in assessment["target"]["components"]
    ] + [fact["artifact"] for fact in assessment["facts"] if fact["artifact"]]
    assert all(
        not Path(path).is_absolute() and ".." not in Path(path).parts for path in paths
    )
    assert set(assessment["next_step"]) == {
        "kind",
        "stage",
        "action",
        "blocking_reasons",
        "required_authority",
    }
    assert assessment["scaffold_plan"]["approvals"] == []


def test_contract_has_no_score_and_seeded_invalid_documents_fail() -> None:
    schema = _schema("pbip-adoption-assessment.schema.json")
    assessment = _assessment()
    serialized = json.dumps(assessment).lower()
    assert "score" not in serialized
    assert _validate(
        {key: value for key, value in assessment.items() if key != "target"},
        schema,
        schema,
    )
    invalid_classification = {
        **assessment,
        "facts": [{**assessment["facts"][0], "classification": "approved"}],
    }
    assert _validate(invalid_classification, schema, schema)
    invalid_extra = {**assessment, "score": 1}
    assert _validate(invalid_extra, schema, schema)


def test_scaffold_schema_keeps_approvals_empty_and_refusals_write_nothing() -> None:
    schema = _schema("pbip-adoption-scaffold-result.schema.json")
    result = {
        "schema_version": "1.0",
        "outcome": "refused",
        "assessment_digest": None,
        "written": [],
        "blocking_reasons": ["accepted digest is stale"],
        "next_step": _assessment()["next_step"],
        "approvals": [],
    }
    assert_matches_schema(result, schema)
    assert result["approvals"] == []
    assert result["written"] == []
