"""Phase 4 ownership contracts for the dbt control plane."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _capabilities() -> dict[str, dict]:
    manifest = yaml.safe_load(
        (ROOT / "docs/capabilities/capabilities.yaml").read_text(encoding="utf-8")
    )
    return {entry["id"]: entry for entry in manifest["capabilities"]}


def test_dbt_execution_and_competence_have_explicit_upstream_owners() -> None:
    caps = _capabilities()
    expected = {
        "dbt-core-execution": ("cli", "dbt-core"),
        "dbt-agent-skills": ("skill", "dbt-labs/dbt-agent-skills"),
        "dbt-mcp": ("mcp", "dbt-mcp"),
    }
    for capability_id, (surface, reference) in expected.items():
        cap = caps[capability_id]
        assert cap["state"] == "deferred"
        assert cap["ownership"]["capability_owner"] == "official-upstream"
        assert cap["ownership"]["upstream_surface"] == surface
        assert cap["ownership"]["upstream_reference"] == reference
        assert "Phase 6" in cap["ownership"]["overlap_note"]


def test_seshat_adapter_keeps_only_the_governed_delta() -> None:
    cap = _capabilities()["dbt-transformation-adapter"]
    ownership = cap["ownership"]
    assert ownership["capability_owner"] == "seshat-adapter"
    assert ownership["upstream_surface"] == "cli"
    assert ownership["upstream_reference"] == "dbt-core"
    for phrase in (
        "Mapping Ready",
        "accepted-plan",
        "shadow-schema",
        "DERIVED evidence",
    ):
        assert phrase in ownership["seshat_delta"]


def test_public_router_names_pre_gate_executor_and_post_validation() -> None:
    text = (
        ROOT / "distribution/bundle-templates/shared/skills/dbt-workflows/SKILL.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "Seshat pre-gate",
        "Execution owner",
        "Seshat afterward",
        "dbt Labs agent skills",
        "dbt Core through `seshat dbt`",
        "activation and discovery",
        "Phase 6",
    ):
        assert phrase in text


def test_internal_adapter_disclaims_generic_dbt_competence() -> None:
    text = (ROOT / ".claude/skills/dbt-transformation-adapter/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "not the owner of generic dbt competence" in text
    assert "dbt Labs agent skills" in text
    assert "activation and discovery" in text


def test_public_surface_describes_broad_routing_boundary() -> None:
    surface = yaml.safe_load(
        (ROOT / "distribution/public-command-surface.yaml").read_text(
            encoding="utf-8"
        )
    )
    skill = next(item for item in surface["skills"] if item["name"] == "dbt-workflows")
    assert "official dbt Labs" in skill["intent"]
    assert "governed" in skill["intent"]


def test_phase_four_does_not_claim_live_activation() -> None:
    status = yaml.safe_load(
        (ROOT / "docs/operations/dbt-activation-status.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert status["status"] != "pass"
    assert status["blockers"]
