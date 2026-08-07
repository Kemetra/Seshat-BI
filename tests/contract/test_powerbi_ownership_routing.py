"""Phase 3 ownership contracts for the Power BI control plane."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _capabilities() -> dict[str, dict]:
    manifest = yaml.safe_load(
        (ROOT / "docs/capabilities/capabilities.yaml").read_text(encoding="utf-8")
    )
    return {entry["id"]: entry for entry in manifest["capabilities"]}


def test_powerbi_public_router_is_the_broad_front_door() -> None:
    cap = _capabilities()["powerbi-workflows-public-router"]
    ownership = cap["ownership"]
    assert ownership["capability_owner"] == "seshat-orchestrator"
    assert ownership["upstream_reference"] == "microsoft/skills-for-fabric"
    assert "Broad public front door" in ownership["overlap_note"]
    assert "pbi-mcp-doctor" in ownership["overlap_note"]


def test_official_report_authoring_is_explicit_and_not_claimed_discoverable() -> None:
    cap = _capabilities()["microsoft-powerbi-report-authoring"]
    assert cap["state"] == "deferred"
    assert cap["ownership"]["capability_owner"] == "official-upstream"
    assert cap["ownership"]["upstream_reference"] == "microsoft/skills-for-fabric"
    assert "activation/discovery is Phase 6" in cap["ownership"]["overlap_note"]


def test_design_router_is_nested_and_f016_excludes_report_authoring() -> None:
    caps = _capabilities()
    design = caps["powerbi-dashboard-design"]
    assert "Nested design-only router" in design["summary"]
    assert "powerbi-workflows" in design["ownership"]["overlap_note"]
    f016 = caps["f016-powerbi-execution-adapter"]
    assert "does not own PBIR report-page authoring" in f016["summary"]
    assert f016["state"] == "deferred"


def test_public_router_names_pre_gate_executor_and_post_validation() -> None:
    text = (
        ROOT / "distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "Seshat pre-gate",
        "Execution owner",
        "Seshat after execution",
        "powerbi-report-authoring",
        "dashboard_ready: pass",
        "binding, blueprint, and static validation",
    ):
        assert phrase in text


def test_active_design_surfaces_do_not_assign_native_report_authoring_to_f016() -> None:
    paths = (
        ".claude/skills/dashboard-design/SKILL.md",
        ".claude/skills/powerbi-dashboard-design/SKILL.md",
        ".claude/skills/powerbi-dashboard-design/workflows/powerbi-handoff.md",
        "docs/powerbi/visual-design-system.md",
        "docs/readiness/dashboard-ready.md",
        "templates/dashboard-layout.md",
        "templates/dashboard-page-blueprint.yaml",
        "templates/report-composition.yaml",
        "templates/theme-json-spec.md",
        "templates/visual-spec.yaml",
    )
    forbidden = (
        "F016 owns execution",
        "F016 owns rendering",
        "F016 owns that",
        "F016 (PBIR)",
        "F016 (PBIP/PBIR authoring",
    )
    for relpath in paths:
        text = (ROOT / relpath).read_text(encoding="utf-8")
        assert "powerbi-report-authoring" in text or "official report-authoring" in text
        for phrase in forbidden:
            assert phrase not in text, f"{relpath} still contains {phrase!r}"
