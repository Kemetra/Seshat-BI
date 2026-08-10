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


def test_official_report_authoring_uses_the_spec_148_discovery_boundary() -> None:
    cap = _capabilities()["microsoft-powerbi-report-authoring"]
    assert cap["state"] == "deferred"
    assert cap["ownership"]["capability_owner"] == "official-upstream"
    assert cap["ownership"]["upstream_reference"] == "microsoft/skills-for-fabric"
    note = cap["ownership"]["overlap_note"]
    assert "Spec 148" in note
    assert "without treating installation as discovery" in note


def test_official_report_design_and_authoring_are_declared_owners() -> None:
    caps = _capabilities()
    for capability_id, skill_name in (
        ("microsoft-powerbi-report-design", "powerbi-report-design"),
        ("microsoft-powerbi-report-authoring", "powerbi-report-authoring"),
    ):
        cap = caps[capability_id]
        assert cap["ownership"]["capability_owner"] == "official-upstream"
        assert cap["ownership"]["upstream_reference"] == "microsoft/skills-for-fabric"
        assert skill_name in str(cap)


def test_broad_official_powerbi_capabilities_remain_deferred_and_incompatible() -> None:
    caps = _capabilities()
    for capability_id in (
        "microsoft-powerbi-report-planning",
        "microsoft-powerbi-report-management",
    ):
        cap = caps[capability_id]
        assert cap["state"] == "deferred"
        assert "incompatible" in str(cap).lower()


def test_capability_readme_names_current_official_execution() -> None:
    text = (ROOT / "docs/capabilities/README.md").read_text(encoding="utf-8")
    assert "does not invoke an official executor today" not in text
    assert "powerbi-report-design" in text
    assert "powerbi-report-authoring" in text


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


def test_mutating_pbir_skill_examples_require_exact_repo_and_table() -> None:
    paths = (
        ".claude/skills/pbir-authoring-adapter/SKILL.md",
        "docs/integrations/pbir-adapter.md",
        "distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md",
        "distribution/bundle-templates/claude/commands/powerbi-theme.md",
        "distribution/bundle-templates/claude/commands/powerbi-format.md",
    )
    commands = (
        "pbir-apply-theme",
        "pbir-format-visual",
        "pbir-set-page-background",
        "pbir-set-geometry",
    )
    combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in paths)
    for command in commands:
        matching_lines = [line for line in combined.splitlines() if command in line]
        assert any("--repo" in line and "--table" in line for line in matching_lines)
