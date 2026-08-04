"""Phase 2: the opt-in rule-coverage census on the agent status surface.

The load-bearing guarantee is INVARIANCE -- without ``--coverage`` the projection is
byte-identical to what it was before this feature, and even with it no stage status,
evidence entry or blocking reason moves. Making an unevaluated rule block a stage is a
separate, owner-ratified step (Phase 3).

See docs/superpowers/specs/2026-08-04-rule-coverage-honesty-design.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.status_surface import build_status_projection

pytestmark = pytest.mark.unit

SCHEMA = Path("schemas/agent-status.schema.json")


def _repo(tmp_path: Path) -> Path:
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    table = tmp_path / "mappings" / "demo"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_text(
        "table: bronze.demo\n"
        "stages:\n"
        "  source_ready:\n"
        "    status: pass\n"
        "    evidence: ['mappings/demo/source-profile.md']\n",
        encoding="utf-8",
    )
    return tmp_path


# --- invariance ---------------------------------------------------------------


def test_default_projection_has_no_coverage_key(tmp_path: Path) -> None:
    """Opt-in: the default agent surface is unchanged by this feature."""
    projection = build_status_projection(_repo(tmp_path))
    assert set(projection) == {"tables"}


def test_coverage_does_not_alter_the_tables_projection(tmp_path: Path) -> None:
    """The invariance guarantee, asserted rather than documented."""
    root = _repo(tmp_path)
    without = build_status_projection(root)
    with_coverage = build_status_projection(root, include_coverage=True)
    assert with_coverage["tables"] == without["tables"]
    assert json.dumps(with_coverage["tables"], sort_keys=True) == json.dumps(
        without["tables"], sort_keys=True
    )


def test_coverage_is_additive_only(tmp_path: Path) -> None:
    projection = build_status_projection(_repo(tmp_path), include_coverage=True)
    assert set(projection) == {"tables", "coverage"}


# --- the census content -------------------------------------------------------


def test_coverage_reports_one_record_per_registered_rule(tmp_path: Path) -> None:
    import seshat.rules  # noqa: F401
    from seshat.registry import all_rules

    projection = build_status_projection(_repo(tmp_path), include_coverage=True)
    assert len(projection["coverage"]) == len(all_rules())
    assert {r["rule_id"] for r in projection["coverage"]} == {r.id for r in all_rules()}


def test_every_record_carries_a_categorical_state_never_a_score(
    tmp_path: Path,
) -> None:
    """Principle V: coverage is categorical; a numeric coverage % is forbidden."""
    projection = build_status_projection(_repo(tmp_path), include_coverage=True)
    allowed = {"evaluated", "unevaluable", "undeclared", "not-applicable"}
    states = {record["state"] for record in projection["coverage"]}
    assert states <= allowed
    for record in projection["coverage"]:
        assert not any(isinstance(value, (int, float)) for value in record.values())


def test_a_not_applicable_record_always_carries_its_basis(tmp_path: Path) -> None:
    """No self-granted opt-in can reach the agent surface."""
    projection = build_status_projection(_repo(tmp_path), include_coverage=True)
    for record in projection["coverage"]:
        if record["state"] == "not-applicable":
            assert record["basis"], (
                f"{record['rule_id']} claims an opt-in with no basis"
            )


# --- schema conformance -------------------------------------------------------


def test_schema_permits_coverage_and_keeps_it_optional() -> None:
    """additionalProperties:false means the key MUST be declared to be legal."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert "coverage" in schema["properties"]
    assert schema["required"] == ["tables"]  # coverage stays optional


def test_both_projections_validate_against_the_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    root = _repo(tmp_path)
    jsonschema.validate(build_status_projection(root), schema)
    jsonschema.validate(build_status_projection(root, include_coverage=True), schema)


def test_schema_rejects_a_numeric_coverage_state() -> None:
    """Guards the enum: a score must not be able to sneak in as a state."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    bad = {"tables": [], "coverage": [{"rule_id": "X1", "state": 87}]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
