"""Architecture contracts for official skill activation and discovery."""

from __future__ import annotations

from pathlib import Path

import yaml

from seshat.integrations.catalog import (
    CLAUDE_CODE,
    CODEX,
    SUPPORTED_HARNESSES,
    component,
)

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_COMPONENTS = (
    "fabric-skills",
    "dbt-agent-skills",
    "dagster-agent-skills",
)


def test_every_official_skill_component_declares_one_contract_per_harness() -> None:
    for component_id in OFFICIAL_COMPONENTS:
        declarations = component(component_id).skill_activations
        assert tuple(entry.harness for entry in declarations) == SUPPORTED_HARNESSES
        assert len({entry.harness for entry in declarations}) == len(declarations)


def test_native_plugins_and_codex_projections_keep_upstream_ownership() -> None:
    for component_id in OFFICIAL_COMPONENTS:
        declarations = {
            entry.harness: entry for entry in component(component_id).skill_activations
        }
        claude = declarations[CLAUDE_CODE]
        codex = declarations[CODEX]
        assert claude.mechanism == "native-plugin"
        assert all(target.plugin_id for target in claude.targets)
        assert codex.mechanism == "agent-skills-projection"
        assert all(target.plugin_id is None for target in codex.targets)
        for declaration in declarations.values():
            for target in declaration.targets:
                assert not target.source_path.startswith(
                    (".claude/", "distribution/", "integrations/")
                )


def test_discovery_document_names_lifecycle_harnesses_and_no_copy_boundary() -> None:
    text = (ROOT / "docs/integrations/official-skill-discovery.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "installed",
        "activated",
        "discoverable",
        "--harness claude-code",
        "--harness codex",
        "independently copied `SKILL.md` is a conflict",
        "never installs, enables, updates, copies, or removes",
    ):
        assert phrase in text


def test_capability_records_no_longer_defer_skill_discovery_to_phase_6() -> None:
    manifest = yaml.safe_load(
        (ROOT / "docs/capabilities/capabilities.yaml").read_text(encoding="utf-8")
    )
    by_id = {entry["id"]: entry for entry in manifest["capabilities"]}
    for capability_id in (
        "microsoft-powerbi-report-authoring",
        "dbt-agent-skills",
        "dagster-agent-skills",
    ):
        text = str(by_id[capability_id])
        assert "Spec 148" in text
        assert "unproven until Phase 6" not in text


def test_cli_harness_choices_are_derived_from_catalog() -> None:
    source = (ROOT / "src/seshat/cli/parser_integrations.py").read_text(
        encoding="utf-8"
    )
    assert "SUPPORTED_HARNESSES" in source
    assert "choices=SUPPORTED_HARNESSES" in source
    assert 'choices=("claude-code", "codex")' not in source
