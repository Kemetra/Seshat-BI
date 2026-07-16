"""Contract test for schemas/dagster-run-evidence.schema.json (spec 134, T009).

The schema is the machine-readable contract for raw Dagster run evidence.
This test pins the load-bearing clauses: execution-word outcomes (never the
readiness token ``pass``), closed record shapes (no score field can be added
silently), and the halted-outcome requirement of a concrete blocking_reason +
named owner.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "dagster-run-evidence.schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_exists_and_parses(schema: dict) -> None:
    assert schema["title"].startswith("Seshat BI Dagster run evidence")


def test_outcomes_are_execution_words_never_pass(schema: dict) -> None:
    outcome = schema["$defs"]["assetRecord"]["properties"]["outcome"]["enum"]
    assert set(outcome) == {"materialized", "failed", "skipped", "blocked", "deferred"}
    assert "pass" not in outcome


def test_run_status_is_the_ci_signal_vocabulary(schema: dict) -> None:
    run_status = schema["$defs"]["runSummary"]["properties"]["run_status"]["enum"]
    assert set(run_status) == {"succeeded", "failed"}


def test_record_shapes_are_closed_so_no_score_field_can_appear(schema: dict) -> None:
    for def_name in ("runSummary", "assetRecord"):
        definition = schema["$defs"][def_name]
        assert definition["additionalProperties"] is False, def_name
        for prop in definition["properties"]:
            assert "score" not in prop.lower(), f"{def_name}.{prop}"


def test_halted_outcomes_require_reason_and_owner(schema: dict) -> None:
    conditions = schema["$defs"]["assetRecord"]["allOf"]
    halted = conditions[0]
    assert set(halted["if"]["properties"]["outcome"]["enum"]) == {
        "failed",
        "skipped",
        "blocked",
        "deferred",
    }
    then_props = halted["then"]["properties"]
    assert then_props["blocking_reason"]["type"] == "string"
    assert then_props["owner"]["type"] == "string"


def test_asset_vocabulary_is_the_spec_024_graph(schema: dict) -> None:
    assets = schema["$defs"]["assetRecord"]["properties"]["asset"]["enum"]
    assert assets == [
        "raw_source_file",
        "bronze_table",
        "source_profile",
        "source_map",
        "silver_tables",
        "gold_tables",
        "live_validate",
        "metric_contracts",
        "semantic_model",
        "dashboard_blueprint",
        "handoff_pack",
        "publish_execution_evidence",
    ]


def test_contract_copy_matches_canonical_schema() -> None:
    contract = ROOT / "specs" / "134-activate-dagster-mvp" / "contracts" / "dagster-run-evidence.schema.json"
    assert json.loads(contract.read_text(encoding="utf-8")) == json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )
