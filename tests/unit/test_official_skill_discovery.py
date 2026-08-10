"""Official Agent Skills lifecycle: installed != activated != discoverable."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from seshat.cli.commands.integrations import integrations_main
from seshat.integrations.catalog import (
    CLAUDE_CODE,
    CODEX,
    Channel,
    Component,
    NativePluginPolicy,
    SkillActivation,
    SkillTarget,
    SourceType,
    component,
)
from seshat.integrations.discovery import (
    ACTIVATION_REQUIRED,
    CONFLICT,
    DISCOVERABLE,
    FAILED,
    NOT_CHECKED,
    STALE,
    DiscoveryInputs,
    inspect_locked_component,
    inspect_official_skills,
)
from seshat.integrations.installer import SetupOutcome
from seshat.integrations.render import as_json, as_text
from tests.unit._curated_stack_fixtures import _args, _workspace

pytestmark = pytest.mark.unit


def _write(path: Path, body: str = "test\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _runner_for(entries: list[dict]):
    def _runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
        assert command == ["claude", "plugin", "list", "--json"]
        return subprocess.CompletedProcess(command, 0, json.dumps(entries), "")

    return _runner


def _claude_entries(
    root: Path,
    item_id: str,
    *,
    locked_version: str = "1.2.3",
    active_version: str = "1.2.3",
) -> list[dict]:
    item = component(item_id)
    activation = next(
        entry for entry in item.skill_activations if entry.harness == CLAUDE_CODE
    )
    entries: list[dict] = []
    marketplace_entries: list[dict] = []
    upstream = root / ".seshat/integrations/skills" / item.id
    for policy in activation.native_plugins:
        plugin_id = policy.plugin_id
        plugin = root / "active-plugins" / plugin_id.replace("@", "-")
        locked_plugin = upstream / "plugins" / policy.manifest_name
        for skill_name in policy.allowed_skills:
            _write(plugin / "skills" / skill_name / "SKILL.md")
            _write(locked_plugin / "skills" / skill_name / "SKILL.md")
        marketplace_entries.append(
            {
                "name": policy.manifest_name,
                "version": locked_version,
                "source": f"./plugins/{policy.manifest_name}",
            }
        )
        entries.append(
            {
                "id": plugin_id,
                "enabled": True,
                "version": active_version,
                "installPath": str(plugin),
            }
        )
    manifest_path = upstream / Path(
        *activation.native_plugins[0].manifest_path.split("/")
    )
    _write(manifest_path, json.dumps({"plugins": marketplace_entries}))
    return entries


def test_catalog_declares_both_harnesses_for_each_official_package() -> None:
    for component_id in (
        "fabric-skills",
        "dbt-agent-skills",
        "dagster-agent-skills",
    ):
        declarations = component(component_id).skill_activations
        assert {entry.harness for entry in declarations} == {CLAUDE_CODE, CODEX}
        assert all(entry.targets for entry in declarations)
        assert all(entry.install_hint for entry in declarations)


def test_catalog_refuses_an_escaping_activation_source() -> None:
    with pytest.raises(ValueError, match="skill source path"):
        Component(
            id="bad-activation",
            source_type=SourceType.GITHUB,
            source="github-dbt-labs-skills",
            channel=Channel.STABLE,
            role="test",
            coordinate="dbt-labs/dbt-agent-skills",
            skill_activations=(
                SkillActivation(
                    harness=CODEX,
                    mechanism="agent-skills-projection",
                    targets=(SkillTarget("bad", "../outside/SKILL.md"),),
                    install_hint="stop",
                ),
            ),
        )


def test_native_plugin_policy_refuses_duplicate_skill_names() -> None:
    with pytest.raises(ValueError, match="duplicate allowed skill"):
        NativePluginPolicy(
            plugin_id="x@y",
            manifest_path=".claude-plugin/marketplace.json",
            manifest_name="x",
            allowed_skills=("same", "same"),
        )


def test_powerbi_catalog_declares_design_and_blocks_broad_plugin() -> None:
    item = component("fabric-skills")
    claude = next(
        activation
        for activation in item.skill_activations
        if activation.harness == CLAUDE_CODE
    )
    names = {target.name for target in claude.targets}
    assert "powerbi-report-design" in names

    policy = next(
        policy
        for policy in claude.native_plugins
        if policy.plugin_id == "powerbi-authoring@fabric-collection"
    )
    assert "powerbi-report-planning" in policy.incompatible_capabilities
    assert "powerbi-report-management" in policy.incompatible_capabilities


def test_omitted_harness_is_explicitly_not_checked_and_not_actionable(
    tmp_path: Path,
) -> None:
    item = component("dagster-agent-skills")
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
    )

    assert {result.status for result in results} == {NOT_CHECKED}
    assert all(result.installed is True for result in results)
    assert all(result.activated is None for result in results)
    assert all(result.discoverable is None for result in results)
    assert not any(result.needs_action for result in results)


def test_claude_native_plugin_inventory_proves_expected_skills(
    tmp_path: Path,
) -> None:
    item = component("dbt-agent-skills")
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(_claude_entries(tmp_path, item.id)),
            tool_lookup=lambda name: name,
        ),
    )
    result = next(entry for entry in results if entry.harness == CLAUDE_CODE)

    assert result.status == DISCOVERABLE
    assert result.installed is True
    assert result.activated is True
    assert result.discoverable is True
    assert len(result.evidence) >= 3


def test_expected_files_do_not_hide_an_extra_claude_skill(tmp_path: Path) -> None:
    item = component("dbt-agent-skills")
    entries = _claude_entries(tmp_path, item.id)
    _write(Path(entries[0]["installPath"]) / "skills/publish-everything/SKILL.md")

    result = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(entries),
            tool_lookup=lambda name: name,
        ),
    )[0]

    assert result.status == CONFLICT
    assert result.discoverable is False
    assert "publish-everything" in " ".join(result.blockers)


def test_active_plugin_version_must_match_locked_manifest(tmp_path: Path) -> None:
    item = component("dbt-agent-skills")
    entries = _claude_entries(
        tmp_path, item.id, locked_version="1.2.3", active_version="1.2.4"
    )

    result = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(entries),
            tool_lookup=lambda name: name,
        ),
    )[0]

    assert result.status == STALE
    assert result.discoverable is False


def test_incompatible_powerbi_plugin_surface_blocks(tmp_path: Path) -> None:
    item = component("fabric-skills")
    entries = _claude_entries(tmp_path, item.id)
    powerbi = next(
        entry
        for entry in entries
        if entry["id"] == "powerbi-authoring@fabric-collection"
    )
    install_path = Path(powerbi["installPath"])
    _write(install_path / "skills/powerbi-report-planning/SKILL.md")
    _write(install_path / "skills/powerbi-report-management/SKILL.md")
    _write(
        install_path / ".mcp.json",
        json.dumps(
            {
                "mcpServers": {
                    "powerbi-modeling-mcp": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@microsoft/powerbi-modeling-mcp@latest",
                            "--start",
                        ],
                    }
                }
            }
        ),
    )

    result = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(entries),
            tool_lookup=lambda name: name,
        ),
    )[0]

    assert result.status == CONFLICT
    assert result.discoverable is False
    blockers = " ".join(result.blockers)
    assert "powerbi-report-planning" in blockers
    assert "powerbi-modeling-mcp" in blockers


def test_disabled_claude_plugin_blocks_discovery(tmp_path: Path) -> None:
    item = component("dagster-agent-skills")
    entries = _claude_entries(tmp_path, item.id)
    entries[0]["enabled"] = False
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(entries),
            tool_lookup=lambda name: name,
        ),
    )
    result = next(entry for entry in results if entry.harness == CLAUDE_CODE)

    assert result.status == ACTIVATION_REQUIRED
    assert result.discoverable is False
    assert "disabled" in " ".join(result.blockers)


def _install_marker(root: Path, item_id: str, ref: str) -> None:
    _write(
        root / ".seshat/integrations/skills" / item_id / ".seshat-installed", f"{ref}\n"
    )


def test_a_marker_ref_behind_the_resolved_ref_is_stale_not_discoverable(
    tmp_path: Path,
) -> None:
    """An upgrade must not report the NEW coordinate as proven by an OLD
    checkout (Codex P2, #597). Every activation-time fact is otherwise perfect:
    the plugin is enabled and every SKILL.md is on disk. Only the ref differs.
    """
    item = component("dbt-agent-skills")
    _install_marker(tmp_path, item.id, "v1.0.0")
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(_claude_entries(tmp_path, item.id)),
            tool_lookup=lambda name: name,
            resolved_refs={item.id: "v2.0.0"},
        ),
    )
    result = next(entry for entry in results if entry.harness == CLAUDE_CODE)

    assert result.status == STALE
    assert result.discoverable is False
    assert result.activated is False
    blockers = " ".join(result.blockers)
    assert "v1.0.0" in blockers and "v2.0.0" in blockers
    assert "--refresh" in result.next_action


def test_a_matching_marker_ref_still_reaches_discovery(tmp_path: Path) -> None:
    """The drift check must not swallow a legitimately current install."""
    item = component("dbt-agent-skills")
    _install_marker(tmp_path, item.id, "v2.0.0")
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(_claude_entries(tmp_path, item.id)),
            tool_lookup=lambda name: name,
            resolved_refs={item.id: "v2.0.0"},
        ),
    )
    result = next(entry for entry in results if entry.harness == CLAUDE_CODE)

    assert result.status == DISCOVERABLE
    assert result.discoverable is True


def test_discovery_without_resolved_refs_keeps_prior_behaviour(
    tmp_path: Path,
) -> None:
    """A caller that resolved nothing gets exactly the pre-existing verdict:
    the drift check is inert rather than guessing at a coordinate."""
    item = component("dbt-agent-skills")
    _install_marker(tmp_path, item.id, "v1.0.0")
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CLAUDE_CODE,),
            runner=_runner_for(_claude_entries(tmp_path, item.id)),
            tool_lookup=lambda name: name,
        ),
    )
    result = next(entry for entry in results if entry.harness == CLAUDE_CODE)

    assert result.status == DISCOVERABLE


def _codex_projection(root: Path, codex_root: Path, item_id: str) -> None:
    item = component(item_id)
    activation = next(
        entry for entry in item.skill_activations if entry.harness == CODEX
    )
    upstream = root / ".seshat/integrations/skills" / item.id
    for target in activation.targets:
        source = _write(upstream / Path(*target.source_path.split("/")))
        projected = codex_root / target.name / "SKILL.md"
        projected.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, projected)


def test_codex_projection_must_resolve_to_locked_upstream_payload(
    tmp_path: Path,
) -> None:
    item = component("dagster-agent-skills")
    codex_root = tmp_path / "codex-skills"
    _codex_projection(tmp_path, codex_root, item.id)
    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CODEX,),
            harness_roots={CODEX: codex_root},
        ),
    )
    result = next(entry for entry in results if entry.harness == CODEX)

    assert result.status == DISCOVERABLE
    assert result.activated is True
    assert result.discoverable is True


def test_copied_codex_skill_is_a_provenance_conflict(tmp_path: Path) -> None:
    item = component("dagster-agent-skills")
    codex_root = tmp_path / "codex-skills"
    activation = next(
        entry for entry in item.skill_activations if entry.harness == CODEX
    )
    target = activation.targets[0]
    _write(
        tmp_path
        / ".seshat/integrations/skills"
        / item.id
        / Path(*target.source_path.split("/"))
    )
    _write(codex_root / target.name / "SKILL.md")

    results = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CODEX,),
            harness_roots={CODEX: codex_root},
        ),
    )
    result = next(entry for entry in results if entry.harness == CODEX)

    assert result.status == CONFLICT
    assert result.activated is True
    assert result.discoverable is False
    assert "not linked" in " ".join(result.blockers)


def test_extra_codex_projection_from_locked_payload_is_a_conflict(
    tmp_path: Path,
) -> None:
    item = component("dagster-agent-skills")
    codex_root = tmp_path / "codex-skills"
    _codex_projection(tmp_path, codex_root, item.id)
    upstream = tmp_path / ".seshat/integrations/skills" / item.id
    extra_source = _write(upstream / "skills/rogue/SKILL.md")
    extra_projection = codex_root / "rogue" / "SKILL.md"
    extra_projection.parent.mkdir(parents=True)
    os.link(extra_source, extra_projection)

    result = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CODEX,),
            harness_roots={CODEX: codex_root},
        ),
    )[1]

    assert result.status == CONFLICT
    assert result.discoverable is False
    assert "rogue" in " ".join(result.blockers)


def test_unrelated_codex_user_skill_is_not_an_upstream_extra(tmp_path: Path) -> None:
    item = component("dagster-agent-skills")
    codex_root = tmp_path / "codex-skills"
    _codex_projection(tmp_path, codex_root, item.id)
    _write(codex_root / "my-private-skill/SKILL.md")

    result = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
        inputs=DiscoveryInputs(
            harnesses=(CODEX,),
            harness_roots={CODEX: codex_root},
        ),
    )[1]

    assert result.status == DISCOVERABLE
    assert result.discoverable is True


def test_locked_component_inspection_requires_matching_lock_and_marker(
    tmp_path: Path,
) -> None:
    item = component("dagster-agent-skills")
    codex_root = tmp_path / "codex-skills"
    _codex_projection(tmp_path, codex_root, item.id)
    _install_marker(tmp_path, item.id, "v1.2.3")
    _write(
        tmp_path / ".seshat/integrations/lock.json",
        json.dumps(
            {
                "schema": "seshat.integrations-lock/v1",
                "profile": "orchestration",
                "resolved_at": "2026-08-10T00:00:00Z",
                "components": {
                    item.id: {
                        "source_type": "github",
                        "tag": "v1.2.3",
                        "commit": None,
                    }
                },
            }
        ),
    )

    result = inspect_locked_component(
        tmp_path,
        item.id,
        CODEX,
        inputs=DiscoveryInputs(harness_roots={CODEX: codex_root}),
    )

    assert result.status == DISCOVERABLE
    assert result.discoverable is True


def test_locked_component_inspection_fails_when_lock_is_absent(
    tmp_path: Path,
) -> None:
    result = inspect_locked_component(tmp_path, "dagster-agent-skills", CODEX)

    assert result.status == FAILED
    assert result.discoverable is False
    assert "lock is missing" in " ".join(result.blockers)


def test_renderers_expose_three_separate_lifecycle_facts(tmp_path: Path) -> None:
    item = component("dagster-agent-skills")
    result = inspect_official_skills(
        tmp_path,
        (item,),
        installed={item.id: True},
    )[0]
    outcome = SetupOutcome(profile="orchestration", discovery=[result])

    payload = json.loads(as_json(outcome))
    assert payload["discovery"][0]["installed"] is True
    assert payload["discovery"][0]["activated"] is None
    assert payload["discovery"][0]["discoverable"] is None
    rendered = as_text(outcome)
    assert "installed=true" in rendered
    assert "activated=not-checked" in rendered
    assert "discoverable=not-checked" in rendered


def test_cli_passes_only_explicit_harness_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _workspace(tmp_path)
    calls: list[dict] = []

    def _plan(*args, **kwargs) -> SetupOutcome:
        calls.append(kwargs)
        return SetupOutcome(profile="orchestration")

    monkeypatch.setattr("seshat.integrations_setup.plan_profile", _plan)

    assert integrations_main(_args(root, profile="orchestration")) == 0
    assert integrations_main(_args(root, profile="orchestration", harness=[CODEX])) == 0
    capsys.readouterr()

    assert "harnesses" not in calls[0]
    assert calls[1]["harnesses"] == (CODEX,)
