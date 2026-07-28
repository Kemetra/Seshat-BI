from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from seshat.statistical.contracts import AnalysisSpec
from seshat.statistical.schema import (
    SpecRefused,
    load_analysis_spec,
    resolve_statistical_schema,
)

ROOT = Path(__file__).resolve().parents[3]


def _valid_document() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "analysis_id": "weekly_signal",
        "revision": 1,
        "question": "Is the approved metric changing?",
        "cadence": "weekly",
        "subject": "sample_orders",
        "owner": "Example Analyst (metric_owner)",
        "readiness_status": "mappings/sample/readiness-status.yaml",
        "metric_contracts": ["mappings/sample/metrics/TotalValue.yaml"],
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
            "id": "describe",
            "version": "1.0",
            "parameters": {
                "quantiles": ["0.25", "0.5", "0.75"],
                "outlier_rule": "mad",
            },
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
            "evidence": "mappings/sample/analyses/weekly_signal.evidence.json",
            "review": "mappings/sample/analyses/weekly_signal.review.md",
        },
    }


def _write_spec(path: Path, document: dict[str, object]) -> None:
    path.write_text(
        "\ufeff" + yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )


def test_resolve_statistical_schema_prefers_development_repository() -> None:
    resolved = resolve_statistical_schema(ROOT, "statistical-analysis-spec.schema.json")

    assert resolved == ROOT / "schemas" / "statistical-analysis-spec.schema.json"


def test_load_analysis_spec_normalizes_immutable_contracts(tmp_path: Path) -> None:
    path = tmp_path / "analysis.yaml"
    _write_spec(path, _valid_document())

    spec = load_analysis_spec(path, ROOT)

    assert isinstance(spec, AnalysisSpec)
    assert spec.method.method_id == "describe"
    assert spec.roles["response"].logical_type == "number"
    assert tuple(item.as_posix() for item in spec.metric_contracts) == (
        "mappings/sample/metrics/TotalValue.yaml",
    )
    assert spec.outputs["evidence"].as_posix().endswith(".evidence.json")
    with pytest.raises(FrozenInstanceError):
        spec.revision = 2


def test_load_analysis_spec_aggregates_schema_errors(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    document = _valid_document()
    document["analysis_id"] = "INVALID ID"
    document["unexpected"] = True
    _write_spec(path, document)

    with pytest.raises(SpecRefused) as exc_info:
        load_analysis_spec(path, ROOT)

    assert len(exc_info.value.errors) >= 2
    assert any("analysis_id" in error for error in exc_info.value.errors)
    assert any("unexpected" in error for error in exc_info.value.errors)


@pytest.mark.parametrize(
    "field, value",
    [
        ("readiness_status", "../outside.yaml"),
        ("readiness_status", "C:/private/readiness-status.yaml"),
    ],
)
def test_load_analysis_spec_refuses_paths_outside_repository(
    tmp_path: Path, field: str, value: str
) -> None:
    path = tmp_path / "unsafe.yaml"
    document = _valid_document()
    document[field] = value
    _write_spec(path, document)

    with pytest.raises(SpecRefused) as exc_info:
        load_analysis_spec(path, ROOT)

    assert any("repo-relative" in error for error in exc_info.value.errors)


def test_load_analysis_spec_refuses_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(SpecRefused, match="mapping"):
        load_analysis_spec(path, ROOT)
