"""Phase 5 ownership contracts for the Dagster control plane."""

from __future__ import annotations

from pathlib import Path

import yaml

from seshat.integrations import catalog
from seshat.integrations.installer import _BUNDLED_SKILLS

ROOT = Path(__file__).resolve().parents[2]


def _capabilities() -> dict[str, dict]:
    manifest = yaml.safe_load(
        (ROOT / "docs/capabilities/capabilities.yaml").read_text(encoding="utf-8")
    )
    return {entry["id"]: entry for entry in manifest["capabilities"]}


def test_catalog_separates_seshat_router_from_official_skills() -> None:
    ids = {item.id for item in catalog.profile_components("orchestration")}
    assert "seshat-dagster-workflows" in ids
    assert "dagster-agent-skills" in ids
    assert "dagster-skills" not in ids

    official = catalog.component("dagster-agent-skills")
    assert official.source == "github-dagster-skills"
    assert official.coordinate == "dagster-io/skills"
    assert official.required_paths == ("skills/dagster-expert/SKILL.md",)


def test_legacy_bundled_component_lookup_is_compatibility_only() -> None:
    assert catalog.component("dagster-skills").id == "seshat-dagster-workflows"
    assert "seshat-dagster-workflows" in _BUNDLED_SKILLS
    assert "dagster-skills" not in _BUNDLED_SKILLS


def test_official_dagster_skill_is_explicit_and_not_claimed_discoverable() -> None:
    cap = _capabilities()["dagster-agent-skills"]
    assert cap["state"] == "deferred"
    assert cap["ownership"]["capability_owner"] == "official-upstream"
    assert cap["ownership"]["upstream_surface"] == "skill"
    assert cap["ownership"]["upstream_reference"] == "dagster-io/skills"
    assert "Phase 6" in cap["ownership"]["overlap_note"]


def test_seshat_adapter_keeps_only_the_governed_delta() -> None:
    cap = _capabilities()["dagster-orchestration-adapter"]
    ownership = cap["ownership"]
    assert ownership["capability_owner"] == "seshat-adapter"
    for phrase in (
        "readiness-aware",
        "named-human",
        "fail-closed",
        "derived run evidence",
    ):
        assert phrase in ownership["seshat_delta"]


def test_public_router_names_pre_gate_executor_and_post_validation() -> None:
    text = (
        ROOT
        / "distribution/bundle-templates/shared/skills/dagster-workflows/SKILL.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "Seshat pre-gate",
        "Execution owner",
        "Seshat afterward",
        "official `dagster-expert`",
        "Dagster through `seshat dagster`",
        "activation and discovery",
        "Phase 6",
    ):
        assert phrase in text


def test_internal_adapter_disclaims_generic_dagster_competence() -> None:
    text = (
        ROOT / ".claude/skills/dagster-orchestration-adapter/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "not the owner of generic Dagster competence" in text
    assert "official `dagster-expert`" in text
    assert "activation and discovery" in text


def test_public_surface_describes_broad_routing_boundary() -> None:
    surface = yaml.safe_load(
        (ROOT / "distribution/public-command-surface.yaml").read_text(
            encoding="utf-8"
        )
    )
    skill = next(
        item for item in surface["skills"] if item["name"] == "dagster-workflows"
    )
    assert "official Dagster" in skill["intent"]
    assert "governed" in skill["intent"]
