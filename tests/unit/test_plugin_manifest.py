"""Closed-world tests for native Claude plugin capability surfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from seshat.integrations.catalog import McpSurfacePolicy, NativePluginPolicy
from seshat.integrations.plugin_manifest import (
    compare_plugin,
    locked_plugin_policy,
    observe_plugin,
)

pytestmark = pytest.mark.unit


def _write(path: Path, text: str = "test\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: object) -> Path:
    return _write(path, json.dumps(payload))


@dataclass(frozen=True)
class _PluginSpec:
    version: str = "1.2.3"
    skills: tuple[str, ...] = ("approved",)
    agents: tuple[str, ...] = ()
    hooks: tuple[str, ...] = ()
    mcp_servers: dict[str, object] | None = None


def _plugin(root: Path, spec: _PluginSpec = _PluginSpec()):
    for name in spec.skills:
        _write(root / "skills" / name / "SKILL.md")
    for name in spec.agents:
        _write(root / "agents" / f"{name}.md")
    if spec.hooks:
        _write_json(
            root / "hooks" / "hooks.json",
            {"hooks": {name: [] for name in spec.hooks}},
        )
    if spec.mcp_servers is not None:
        _write_json(root / ".mcp.json", {"mcpServers": spec.mcp_servers})
    return observe_plugin(root, {"id": "x@y", "version": spec.version})


def _policy(**overrides: object) -> NativePluginPolicy:
    values: dict[str, object] = {
        "plugin_id": "x@y",
        "manifest_path": ".claude-plugin/marketplace.json",
        "manifest_name": "x",
        "allowed_skills": ("approved",),
    }
    values.update(overrides)
    return NativePluginPolicy(**values)


@pytest.mark.parametrize("extra_kind", ["skill", "mcp", "agent", "hook"])
def test_undeclared_plugin_capability_blocks(tmp_path: Path, extra_kind: str) -> None:
    locked = _plugin(tmp_path / "locked")
    kwargs: dict[str, object] = {}
    if extra_kind == "skill":
        kwargs["skills"] = ("approved", "rogue")
    elif extra_kind == "mcp":
        kwargs["mcp_servers"] = {"rogue": {"command": "rogue", "args": []}}
    elif extra_kind == "agent":
        kwargs["agents"] = ("rogue",)
    else:
        kwargs["hooks"] = ("PreToolUse",)
    observed = _plugin(tmp_path / "observed", _PluginSpec(**kwargs))

    blockers = compare_plugin(_policy(), locked, observed)

    assert any(blocker.kind == f"undeclared-{extra_kind}" for blocker in blockers)


def test_powerbi_mcp_requires_fixed_readonly_coordinate(tmp_path: Path) -> None:
    mcp_policy = McpSurfacePolicy(
        name="powerbi-modeling-mcp",
        transport="stdio",
        package="@microsoft/powerbi-modeling-mcp@1.4.2",
        required_args=("--readonly",),
        forbidden_args=("--readwrite", "--read-write", "--skipconfirmation"),
    )
    policy = _policy(allowed_mcp_servers=(mcp_policy,))
    safe_server = {
        "powerbi-modeling-mcp": {
            "command": "npx",
            "args": [
                "-y",
                "@microsoft/powerbi-modeling-mcp@1.4.2",
                "--readonly",
            ],
        }
    }
    unsafe_server = {
        "powerbi-modeling-mcp": {
            "command": "npx",
            "args": ["-y", "@microsoft/powerbi-modeling-mcp@latest", "--start"],
        }
    }
    locked = _plugin(tmp_path / "locked", _PluginSpec(mcp_servers=safe_server))
    observed = _plugin(tmp_path / "observed", _PluginSpec(mcp_servers=unsafe_server))

    details = " ".join(
        blocker.detail for blocker in compare_plugin(policy, locked, observed)
    )

    assert "moving coordinate" in details
    assert "--readonly" in details


@pytest.mark.parametrize(
    "unsafe_arg", ["--readwrite", "--read-write", "--skipconfirmation"]
)
def test_forbidden_mcp_write_or_confirmation_flags_block(
    tmp_path: Path, unsafe_arg: str
) -> None:
    mcp_policy = McpSurfacePolicy(
        name="powerbi-modeling-mcp",
        transport="stdio",
        package="@microsoft/powerbi-modeling-mcp@1.4.2",
        required_args=("--readonly",),
        forbidden_args=("--readwrite", "--read-write", "--skipconfirmation"),
    )
    policy = _policy(allowed_mcp_servers=(mcp_policy,))
    safe = {
        "command": "npx",
        "args": ["-y", "@microsoft/powerbi-modeling-mcp@1.4.2", "--readonly"],
    }
    unsafe = {**safe, "args": [*safe["args"], unsafe_arg]}
    locked = _plugin(
        tmp_path / "locked",
        _PluginSpec(mcp_servers={"powerbi-modeling-mcp": safe}),
    )
    observed = _plugin(
        tmp_path / "observed",
        _PluginSpec(mcp_servers={"powerbi-modeling-mcp": unsafe}),
    )

    details = " ".join(
        blocker.detail for blocker in compare_plugin(policy, locked, observed)
    )

    assert unsafe_arg in details


def test_active_plugin_version_must_equal_locked_version(tmp_path: Path) -> None:
    locked = _plugin(tmp_path / "locked", _PluginSpec(version="1.2.3"))
    observed = _plugin(tmp_path / "observed", _PluginSpec(version="1.2.4"))

    blockers = compare_plugin(_policy(), locked, observed)

    assert any(blocker.kind == "version-mismatch" for blocker in blockers)


def test_unenumerable_capability_class_blocks(tmp_path: Path) -> None:
    locked = _plugin(tmp_path / "locked")
    observed_root = tmp_path / "observed"
    _write(observed_root / "skills")
    observed = observe_plugin(observed_root, {"id": "x@y", "version": "1.2.3"})

    blockers = compare_plugin(_policy(), locked, observed)

    assert any(blocker.kind == "unknown-skill" for blocker in blockers)


def test_locked_marketplace_entry_resolves_declared_plugin(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "x"
    _write(plugin_root / "skills" / "approved" / "SKILL.md")
    _write_json(
        tmp_path / ".claude-plugin" / "marketplace.json",
        {
            "plugins": [
                {
                    "name": "x",
                    "version": "1.2.3",
                    "source": "./plugins/x",
                }
            ]
        },
    )

    observed = locked_plugin_policy(tmp_path, _policy())

    assert observed.version == "1.2.3"
    assert observed.skills == frozenset({"approved"})


# --------------------------------------------------------------------------- #
# plugin.json component fields are enumeration roots too (closed world).
# --------------------------------------------------------------------------- #


def _with_manifest(root: Path, manifest: dict[str, object]):
    _write(root / "skills" / "approved" / "SKILL.md")
    _write_json(root / ".claude-plugin" / "plugin.json", manifest)
    return observe_plugin(root, {"id": "x@y", "version": "1.2.3"})


def _kinds(tmp_path: Path, manifest: dict[str, object], **policy: object) -> set:
    locked = _plugin(tmp_path / "locked")
    observed = _with_manifest(tmp_path / "observed", manifest)
    return {
        blocker.kind for blocker in compare_plugin(_policy(**policy), locked, observed)
    }


def test_inline_plugin_json_hook_blocks(tmp_path: Path) -> None:
    hook = {"matcher": "*", "hooks": [{"type": "command", "command": "true"}]}
    kinds = _kinds(tmp_path, {"name": "x", "hooks": {"PreToolUse": [hook]}})
    assert "undeclared-hook" in kinds


def test_inline_plugin_json_hook_in_hooks_json_shape_blocks(tmp_path: Path) -> None:
    kinds = _kinds(tmp_path, {"name": "x", "hooks": {"hooks": {"Stop": []}}})
    assert "undeclared-hook" in kinds


def test_default_commands_directory_blocks(tmp_path: Path) -> None:
    _write(tmp_path / "observed" / "commands" / "wipe.md")
    kinds = _kinds(tmp_path, {"name": "x"})
    assert "undeclared-command" in kinds


def test_declared_command_path_blocks_and_can_be_allowed(tmp_path: Path) -> None:
    _write(tmp_path / "a" / "observed" / "cmds" / "wipe.md")
    manifest = {"name": "x", "commands": "./cmds/"}
    assert "undeclared-command" in _kinds(tmp_path / "a", manifest)
    _write(tmp_path / "b" / "locked" / "commands" / "wipe.md")
    _write(tmp_path / "b" / "observed" / "cmds" / "wipe.md")
    assert not _kinds(tmp_path / "b", manifest, allowed_commands=("wipe",))


def test_custom_skill_paths_are_enumerated(tmp_path: Path) -> None:
    _write(tmp_path / "observed" / "extra" / "rogue" / "SKILL.md")
    kinds = _kinds(tmp_path, {"name": "x", "skills": ["./skills/", "./extra/"]})
    assert "undeclared-skill" in kinds


def test_custom_agent_file_is_enumerated(tmp_path: Path) -> None:
    _write(tmp_path / "observed" / "elsewhere" / "rogue.md")
    kinds = _kinds(tmp_path, {"name": "x", "agents": ["./elsewhere/rogue.md"]})
    assert "undeclared-agent" in kinds


def test_plugin_json_mcp_servers_merge_with_standalone_mcp_json(
    tmp_path: Path,
) -> None:
    _write_json(tmp_path / "observed" / ".mcp.json", {"mcpServers": {}})
    manifest = {"name": "x", "mcpServers": {"rogue": {"command": "rogue"}}}
    assert "undeclared-mcp" in _kinds(tmp_path, manifest)


def test_plugin_json_mcp_servers_path_is_read(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "observed" / "servers.json",
        {"mcpServers": {"rogue": {"command": "rogue"}}},
    )
    assert "undeclared-mcp" in _kinds(
        tmp_path, {"name": "x", "mcpServers": "./servers.json"}
    )


@pytest.mark.parametrize("key", ["outputStyles", "lspServers", "frobnicate"])
def test_unrecognised_plugin_json_key_fails_closed(tmp_path: Path, key: str) -> None:
    assert "unknown-component" in _kinds(tmp_path, {"name": "x", key: "./x"})


def test_a_declared_path_outside_the_plugin_is_unenumerable(tmp_path: Path) -> None:
    _write(tmp_path / "outside" / "rogue" / "SKILL.md")
    kinds = _kinds(tmp_path, {"name": "x", "skills": "../outside"})
    assert "unknown-skill" in kinds


def test_an_unreadable_plugin_json_fails_closed(tmp_path: Path) -> None:
    locked = _plugin(tmp_path / "locked")
    root = tmp_path / "observed"
    _write(root / "skills" / "approved" / "SKILL.md")
    _write(root / ".claude-plugin" / "plugin.json", "{not json")
    observed = observe_plugin(root, {"id": "x@y", "version": "1.2.3"})
    kinds = {b.kind for b in compare_plugin(_policy(), locked, observed)}
    assert "unknown-component" in kinds


def test_metadata_only_plugin_json_adds_no_blocker(tmp_path: Path) -> None:
    manifest = {
        "name": "x",
        "version": "1.2.3",
        "description": "d",
        "author": {"name": "a"},
        "homepage": "https://example.com",
        "repository": "https://example.com/r",
        "license": "MIT",
        "keywords": ["k"],
        "skills": "./skills/",
    }
    assert _kinds(tmp_path, manifest) == set()


def test_marketplace_entry_component_fields_are_enumerated(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "x"
    _write(plugin_root / "skills" / "approved" / "SKILL.md")
    _write(plugin_root / "tools" / "wipe.md")
    _write_json(
        tmp_path / ".claude-plugin" / "marketplace.json",
        {
            "plugins": [
                {
                    "name": "x",
                    "version": "1.2.3",
                    "source": "./plugins/x",
                    "commands": ["./tools/wipe.md"],
                }
            ]
        },
    )

    observed = locked_plugin_policy(tmp_path, _policy())

    assert observed.commands == frozenset({"wipe"})
