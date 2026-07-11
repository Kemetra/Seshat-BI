from __future__ import annotations

from pathlib import Path

import pytest

from seshat.benchmark.model import BenchmarkError
from seshat.benchmark.runner import load_scenarios

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]
_MANIFESTS = (
    "benchmark/scenarios/hard-stops.yaml",
    "benchmark/scenarios/retail-semantics.yaml",
)

_TEMPLATE = """\
version: 1
scenarios:
  - scenario_id: {scenario_id}
    title: "{title}"
    principle: example_principle
    fixture: fixtures/data.csv
    prompt: "{prompt}"
    expected_behavior: {expected}
    observable_evidence:
      - "Names the boundary."
    vendor_neutral: {neutral}
"""


def _write_manifest(root: Path, **overrides) -> Path:
    values = {
        "scenario_id": "syn-1",
        "title": "Synthetic scenario",
        "prompt": "Do the synthetic thing.",
        "expected": "refuse",
        "neutral": "true",
    }
    values.update(overrides)
    (root / "fixtures").mkdir(exist_ok=True)
    (root / "fixtures/data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    manifest = root / "scenarios.yaml"
    manifest.write_text(_TEMPLATE.format(**values), encoding="utf-8")
    return manifest


def test_valid_scenario_loads(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    scenarios = load_scenarios(tmp_path, manifest)
    assert scenarios[0].scenario_id == "syn-1"
    assert scenarios[0].expected_behavior == "refuse"


def test_missing_field_fails_closed(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "    principle: example_principle\n", ""
        ),
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkError, match="principle"):
        load_scenarios(tmp_path, manifest)


def test_unknown_expected_behavior_fails_closed(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, expected="comply")
    with pytest.raises(BenchmarkError, match="expected_behavior"):
        load_scenarios(tmp_path, manifest)


def test_vendor_neutral_false_is_rejected(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, neutral="false")
    with pytest.raises(BenchmarkError, match="vendor_neutral"):
        load_scenarios(tmp_path, manifest)


def test_vendor_naming_scenario_is_rejected(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, prompt="Ask copilot to write silver SQL.")
    with pytest.raises(BenchmarkError, match="vendor term"):
        load_scenarios(tmp_path, manifest)


def test_absent_fixture_is_rejected(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    (tmp_path / "fixtures/data.csv").unlink()
    with pytest.raises(BenchmarkError, match="fixture"):
        load_scenarios(tmp_path, manifest)


def test_duplicate_scenario_ids_are_rejected(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    body = manifest.read_text(encoding="utf-8")
    manifest.write_text(body + body.split("scenarios:\n", 1)[1], encoding="utf-8")
    with pytest.raises(BenchmarkError, match="duplicate"):
        load_scenarios(tmp_path, manifest)


def test_committed_scenarios_cover_hard_stops_and_semantic_classes() -> None:
    scenarios = load_scenarios(_REPO, *_MANIFESTS)
    principles = {scenario.principle for scenario in scenarios}
    # SC-008: every named hard stop is covered ...
    assert {
        "never_self_grant_approval",
        "no_silver_before_mapping_cleared",
        "no_dashboard_before_metric_contracts",
        "never_fabricate_a_confidence_score",
    } <= principles
    # ... plus at least six retail semantic failure classes.
    semantic = {p for p in principles if p.startswith("retail_semantics_")}
    assert len(semantic) >= 6
    # Expected behaviors span the full categorical vocabulary.
    behaviors = {scenario.expected_behavior for scenario in scenarios}
    assert behaviors == {
        "proceed",
        "refuse",
        "block_for_evidence",
        "request_human_decision",
    }


def test_committed_scenarios_use_synthetic_fixtures_only() -> None:
    for scenario in load_scenarios(_REPO, *_MANIFESTS):
        assert scenario.fixture.startswith("benchmark/scenarios/fixtures/")
        body = (_REPO / scenario.fixture).read_text(encoding="utf-8")
        assert "SYN-" in body or "synthetic" in body.lower()
