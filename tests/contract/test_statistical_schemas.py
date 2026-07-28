from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
import yaml

from seshat.ecosystem_contracts import validate_json_contract

ROOT = Path(__file__).resolve().parents[2]
SPEC_SCHEMA_PATH = ROOT / "schemas" / "statistical-analysis-spec.schema.json"
EVIDENCE_SCHEMA_PATH = ROOT / "schemas" / "statistical-analysis-evidence.schema.json"


def _schema(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_spec(method_id: str, parameters: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "analysis_id": "weekly_sales_signal",
        "revision": 1,
        "question": "Is the approved metric changing beyond normal variation?",
        "cadence": "weekly",
        "subject": "sample_orders",
        "owner": "Example Analyst (metric_owner)",
        "readiness_status": "mappings/sample_orders/readiness-status.yaml",
        "metric_contracts": [
            "mappings/sample_orders/metrics/TotalValue.yaml",
        ],
        "provider": {"kind": "local_csv", "dataset_id": "weekly_metric"},
        "population": {
            "grain": "one row per completed week",
            "inclusion": [],
            "exclusion": [],
        },
        "roles": {
            "response": {"column": "metric_value", "logical_type": "number"},
        },
        "method": {
            "id": method_id,
            "version": "1.0",
            "parameters": parameters,
        },
        "missing_data": {"policy": "complete_case"},
        "minimum_data": {
            "observations": 12,
            "groups": 1,
            "seasonal_cycles": 0,
        },
        "random_seed": 1729,
        "pii": {
            "classification": "none",
            "approval_evidence": [],
            "minimum_group_count": 5,
        },
        "outputs": {
            "evidence": (
                "mappings/sample_orders/analyses/weekly_sales_signal.evidence.json"
            ),
            "review": ("mappings/sample_orders/analyses/weekly_sales_signal.review.md"),
        },
    }


@pytest.mark.parametrize(
    ("method_id", "parameters"),
    [
        (
            "describe",
            {"quantiles": ["0.25", "0.5", "0.75"], "outlier_rule": "mad"},
        ),
        (
            "compare_groups",
            {
                "test": "welch_t",
                "alternative": "two-sided",
                "confidence_level": "0.95",
                "correction": "holm",
            },
        ),
        (
            "proportion",
            {
                "interval": "wilson",
                "alternative": "two-sided",
                "confidence_level": "0.95",
            },
        ),
        (
            "correlate",
            {
                "coefficient": "spearman",
                "confidence_level": "0.95",
                "correction": "benjamini-hochberg",
            },
        ),
        (
            "regress",
            {
                "family": "ols",
                "covariance": "HC3",
                "confidence_level": "0.95",
            },
        ),
        (
            "detect_anomalies",
            {
                "model": "seasonal_mad",
                "period": 12,
                "threshold": "3.5",
                "direction": "upper",
            },
        ),
        (
            "detect_change_points",
            {
                "model": "l2",
                "min_segment": 6,
                "algorithm": "dynamic_programming",
                "change_count": 2,
                "jump": 1,
            },
        ),
        (
            "forecast",
            {
                "candidates": [
                    "seasonal_naive",
                    "ets_add_trend",
                    "ets_add_damped",
                    "ets_add_seasonal",
                ],
                "period": 12,
                "horizon": 6,
                "confidence_level": "0.95",
                "evaluation_metric": "mase",
                "initial_window": 24,
                "step": 1,
                "max_folds": 6,
                "final_period": "complete",
                "partial_period_policy": "fail",
            },
        ),
    ],
)
def test_method_variants_are_closed(
    method_id: str, parameters: dict[str, object]
) -> None:
    schema = _schema(SPEC_SCHEMA_PATH)
    payload = valid_spec(method_id, parameters)

    assert validate_json_contract(payload, schema) == []
    assert validate_json_contract({**payload, "unexpected": True}, schema)
    method = dict(payload["method"])
    method["parameters"] = {**parameters, "unexpected": True}
    assert validate_json_contract({**payload, "method": method}, schema)


def test_decimal_parameters_are_strings_and_resource_bounds_are_enforced() -> None:
    schema = _schema(SPEC_SCHEMA_PATH)
    payload = valid_spec(
        "forecast",
        {
            "candidates": ["seasonal_naive"],
            "period": 12,
            "horizon": 366,
            "confidence_level": 0.95,
            "evaluation_metric": "mase",
            "initial_window": 24,
            "step": 1,
            "max_folds": 6,
            "final_period": "complete",
            "partial_period_policy": "fail",
        },
    )

    errors = validate_json_contract(payload, schema)

    assert any("confidence_level" in error for error in errors)
    assert any("horizon" in error for error in errors)


def test_evidence_authority_outcomes_and_readiness_effect_are_fixed() -> None:
    schema = _schema(EVIDENCE_SCHEMA_PATH)
    outcome_schema = schema["properties"]["outcome"]

    assert outcome_schema["enum"] == [
        "computed",
        "withheld",
        "refused",
        "failed",
        "unavailable",
    ]
    assert schema["properties"]["authority"]["const"] == "derived-evidence-only"
    assert (
        schema["properties"]["readiness_effect"]["const"]
        == "none; named-human approval required"
    )
    assert schema["properties"]["review_state"]["const"] == "pending"


def test_evidence_decimal_values_reject_json_numbers() -> None:
    schema = _schema(EVIDENCE_SCHEMA_PATH)
    payload = {
        "schema_version": "1.0",
        "engine_version": "1.0",
        "authority": "derived-evidence-only",
        "invocation_id": "invocation-001",
        "started_at": "2026-07-28T12:00:00Z",
        "completed_at": "2026-07-28T12:00:01Z",
        "analysis": {
            "path": "mappings/sample/analyses/example.yaml",
            "revision": 1,
            "sha256": "a" * 64,
        },
        "governance": {"readiness": [], "metric_contracts": []},
        "input": {
            "provider_kind": "local_csv",
            "source_digest": "b" * 64,
            "observation_grain": "one row per week",
            "input_count": 12,
            "excluded_count": 0,
            "exclusion_reasons": [],
        },
        "method": {
            "id": "describe",
            "version": "1.0",
            "libraries": [],
            "parameters": {},
            "random_seed": 1729,
        },
        "outcome": "computed",
        "estimates": [{"name": "mean", "value": 1.5, "unit": None}],
        "intervals": [],
        "tests": [],
        "diagnostics": [],
        "warnings": [],
        "blockers": [],
        "cautions": [],
        "readiness_effect": "none; named-human approval required",
        "review_state": "pending",
    }

    assert validate_json_contract(payload, schema)


def test_statistical_schemas_are_in_wheel_and_sdist_build_inputs() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    targets = project["tool"]["hatch"]["build"]["targets"]
    force_include = targets["wheel"]["force-include"]
    sdist_include = targets["sdist"]["include"]

    for name in (
        "statistical-analysis-spec.schema.json",
        "statistical-analysis-evidence.schema.json",
    ):
        source = f"schemas/{name}"
        assert force_include[source] == f"seshat/statistical/schemas/{name}"
        assert f"/{source}" in sdist_include


def test_generic_spec_template_is_valid_and_never_uses_c086() -> None:
    template_path = ROOT / "templates" / "statistical-analysis-spec.yaml"
    raw = template_path.read_text(encoding="utf-8")
    payload = yaml.safe_load(raw)

    assert "c086" not in raw.casefold()
    assert validate_json_contract(payload, _schema(SPEC_SCHEMA_PATH)) == []
