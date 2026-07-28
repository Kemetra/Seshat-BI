from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from seshat.ecosystem_contracts import validate_json_contract
from seshat.statistical.contracts import (
    AnalysisEvidence,
    Blocker,
    Diagnostic,
    Estimate,
    Interval,
    Outcome,
)
from seshat.statistical.contracts import (
    TestStatistic as StatisticalTest,
)
from seshat.statistical.evidence import (
    EvidenceRefused,
    NonFiniteResult,
    build_evidence,
    decimal_text,
    evidence_payload,
    write_evidence,
)


def sample_evidence(**overrides: object) -> AnalysisEvidence:
    values: dict[str, object] = {
        "engine_version": "1.0",
        "invocation_id": "invocation-001",
        "started_at": "2026-07-28T12:00:00Z",
        "completed_at": "2026-07-28T12:00:01Z",
        "analysis": {
            "path": "mappings/sample/analyses/example.yaml",
            "revision": 1,
            "sha256": "a" * 64,
        },
        "governance": {"readiness": (), "metric_contracts": ()},
        "input_provenance": {
            "provider_kind": "local_csv",
            "source_digest": "b" * 64,
            "observation_grain": "one row per week",
            "input_count": 12,
            "excluded_count": 1,
            "exclusion_reasons": ("missing response",),
        },
        "method": {
            "id": "describe",
            "version": "1.0",
            "libraries": (),
            "parameters": {},
            "random_seed": 1729,
        },
        "outcome": Outcome.COMPUTED,
        "estimates": (Estimate("mean", "10.5", "USD"),),
        "effect_sizes": (),
        "intervals": (Interval("mean", "9.5", "11.5", "0.95", "bootstrap"),),
        "tests": (
            StatisticalTest(
                "location",
                "1.25",
                "0.2",
                None,
                "two-sided",
                "example",
            ),
        ),
        "diagnostics": (
            Diagnostic("STAT_SAMPLE_SIZE", "holds", "12", "Minimum data met."),
        ),
        "warnings": (),
        "blockers": (),
        "cautions": ("Derived evidence is not a causal claim.",),
    }
    values.update(overrides)
    return AnalysisEvidence(**values)


def test_decimal_text_refuses_non_finite_values() -> None:
    assert decimal_text(Decimal("1.2500")) == "1.25"
    assert decimal_text(-0.0) == "0"
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(NonFiniteResult):
            decimal_text(value)


def test_atomic_writer_leaves_no_partial_final_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "result.json"
    monkeypatch.setattr(os, "replace", Mock(side_effect=OSError("interrupted")))

    with pytest.raises(OSError):
        write_evidence(final, sample_evidence(), repo_root=tmp_path)

    assert not final.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_writer_emits_canonical_finite_schema_shape(tmp_path: Path) -> None:
    final = tmp_path / "result.json"

    written = write_evidence(final, sample_evidence(), repo_root=tmp_path)
    raw = written.read_text(encoding="utf-8")
    payload = json.loads(raw)

    assert raw.endswith("\n")
    assert raw.index('"analysis"') < raw.index('"authority"')
    assert payload["authority"] == "derived-evidence-only"
    assert payload["input"]["input_count"] == 12
    assert payload["readiness_effect"] == "none; named-human approval required"
    assert payload["review_state"] == "pending"
    assert "NaN" not in raw
    assert "Infinity" not in raw


def test_typed_evidence_conforms_to_committed_schema() -> None:
    root = Path(__file__).resolve().parents[3]
    schema = json.loads(
        (root / "schemas" / "statistical-analysis-evidence.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert validate_json_contract(evidence_payload(sample_evidence()), schema) == []


def test_build_evidence_freezes_nested_provenance() -> None:
    analysis = {
        "path": "mappings/sample/analyses/example.yaml",
        "revision": 1,
        "sha256": "a" * 64,
    }
    evidence = build_evidence(
        engine_version="1.0",
        invocation_id="invocation-002",
        started_at="2026-07-28T12:00:00Z",
        completed_at="2026-07-28T12:00:01Z",
        analysis=analysis,
        governance={"readiness": (), "metric_contracts": ()},
        input_provenance=sample_evidence().input_provenance,
        method=sample_evidence().method,
        outcome=Outcome.COMPUTED,
    )
    analysis["revision"] = 2

    assert evidence.analysis["revision"] == 1
    with pytest.raises(TypeError):
        evidence.analysis["revision"] = 3


@pytest.mark.parametrize(
    "unsafe_input",
    [
        {"rows": ({"metric_value": 10},)},
        {"dsn": "postgres://user:password@private-host/database"},
        {"source_path": "C:/Users/example/private.csv"},
    ],
)
def test_writer_refuses_raw_rows_secrets_and_absolute_paths(
    tmp_path: Path, unsafe_input: dict[str, object]
) -> None:
    evidence = sample_evidence(
        input_provenance={
            **sample_evidence().input_provenance,
            **unsafe_input,
        }
    )

    with pytest.raises(EvidenceRefused):
        write_evidence(tmp_path / "result.json", evidence, repo_root=tmp_path)


def test_writer_refuses_output_path_outside_repository(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.evidence.json"

    with pytest.raises(EvidenceRefused, match="repository"):
        write_evidence(outside, sample_evidence(), repo_root=tmp_path)


def test_blocked_evidence_serializes_recovery_without_authorizing() -> None:
    evidence = sample_evidence(
        outcome=Outcome.REFUSED,
        blockers=(
            Blocker(
                "readiness_not_passed",
                "Gold readiness is not passed.",
                "Complete the named readiness evidence.",
            ),
        ),
    )

    assert evidence.outcome is Outcome.REFUSED
    assert evidence.blockers[0].recovery.startswith("Complete")
    assert evidence.readiness_effect == "none; named-human approval required"
