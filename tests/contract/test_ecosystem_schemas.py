from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.ecosystem_contracts import validate_json_contract

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_passport_reference_shape_and_seeded_invalid_shape() -> None:
    valid = {
        "schema_version": "1.0",
        "passport_id": "sha256:abc",
        "source_revision": None,
        "scope": ["orders"],
        "readiness": [],
        "artifacts": [],
        "approvals": [],
        "validation_boundary": {},
        "generated_at": "2026-07-11T00:00:00Z",
        "authority_disclaimer": "Records evidence; grants no approval.",
    }
    schema = _schema("readiness-passport.schema.json")
    assert validate_json_contract(valid, schema) == []
    assert validate_json_contract({**valid, "scope": []}, schema)


def test_extension_pack_reference_shape_and_unknown_field() -> None:
    valid = {
        "schema_version": "1.0",
        "pack_id": "example.sales",
        "version": "1.0.0",
        "category": "kpi",
        "owner": "Example Maintainer",
        "description": "Generic sales metrics",
        "core_compatibility": ">=0.1,<1",
        "provides": ["total_sales"],
        "requires": [],
        "conflicts": [],
        "artifacts": [],
        "human_decisions": [],
        "fixtures": [],
        "verification": ["validate manifest"],
        "non_goals": ["does not define universal semantics"],
    }
    schema = _schema("seshat-extension-pack.schema.json")
    assert validate_json_contract(valid, schema) == []
    assert validate_json_contract({**valid, "exec": "hook.py"}, schema)


def test_benchmark_and_projection_minimal_contracts() -> None:
    benchmark = {
        "schema_version": "1.0",
        "run_id": "run-1",
        "participant": {"name": "reference", "kind": "scripted"},
        "instructions_digest": "0" * 64,
        "environment": {},
        "repetitions": 1,
        "started_at": "2026-07-11T00:00:00Z",
        "observations": [],
    }
    projection = {
        "schema_version": "1.0",
        "workspace": {"label": "demo"},
        "tables": [],
        "lineage": {"nodes": [], "edges": []},
        "generated_at": None,
        "disclosure": {"status": "pass", "findings": []},
    }
    assert validate_json_contract(benchmark, _schema("benchmark-run.schema.json")) == []
    assert (
        validate_json_contract(
            projection, _schema("static-readiness-projection.schema.json")
        )
        == []
    )
