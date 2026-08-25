from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
CONTRACT = ROOT / "templates" / "metric-contract.yaml"
VARIANCE = ROOT / "templates" / "metric-contract-shape.variance-vs-target.yaml"


def _load(path: Path) -> dict[str, object]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_metric_contract_exposes_optional_scalar_comparison_binding() -> None:
    comparison = _load(CONTRACT)["compares_to"]

    assert set(comparison) == {"gold_table", "columns", "pii_sensitive"}
    assert isinstance(comparison["gold_table"], str)
    assert isinstance(comparison["columns"], list)
    assert isinstance(comparison["pii_sensitive"], bool)


def test_variance_shape_uses_comparison_binding_and_ratio_definition() -> None:
    document = _load(VARIANCE)

    assert set(document["compares_to"]) == {
        "gold_table",
        "columns",
        "pii_sensitive",
    }
    assert document["definition"]["kind"] == "ratio"
    assert (
        document["definition"]["numerator"]["source"]["table"]
        == document["binds_to"]["gold_table"]
    )
    assert (
        document["definition"]["denominator"]["source"]["table"]
        == document["compares_to"]["gold_table"]
    )
    assert (
        document["definition"]["numerator"]["source"]["column"]
        in document["binds_to"]["columns"]
    )
    assert (
        document["definition"]["denominator"]["source"]["column"]
        in document["compares_to"]["columns"]
    )


def test_variance_shape_keeps_owner_decisions_unfilled_and_generic() -> None:
    document = _load(VARIANCE)
    serialized = VARIANCE.read_text(encoding="utf-8").lower()

    assert "c086" not in serialized
    assert "retail_store_sales" not in serialized
    assert "target_value" not in document
    assert all(
        value == "none" or "<" in value for value in document["thresholds"].values()
    )
    assert document["readiness"]["status"] == "blocked"
    assert document["readiness"]["blocking_reasons"]
