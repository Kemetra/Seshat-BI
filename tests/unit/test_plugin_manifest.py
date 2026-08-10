"""Closed-world tests for native Claude plugin capability surfaces."""

from __future__ import annotations

import json
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


def _plugin(
    root: Path,
    *,
    version: str = "1.2.3",
    skills: tuple[str, ...] = ("approved",),
    agents: tuple[str, ...] = (),
    hooks: tuple[str, ...] = (),
    mcp_servers: dict[str, object] | None = None,
):
    for name in skills:
        _write(root / "skills" / name / "SKILL.md")
    for name in agents:
        _write(root / "agents" / f"{name}.md")
    if hooks:
        _write_json(
            root / "hooks" / "hooks.json", {"hooks": {name: [] for name in hooks}}
        )
    if mcp_servers is not None:
        _write_json(root / ".mcp.json", {"mcpServers": mcp_servers})
    return observe_plugin(root, {"id": "x@y", "version": version})


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
    observed = _plugin(tmp_path / "observed", **kwargs)

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
    locked = _plugin(tmp_path / "locked", mcp_servers=safe_server)
    observed = _plugin(tmp_path / "observed", mcp_servers=unsafe_server)

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
    locked = _plugin(tmp_path / "locked", mcp_servers={"powerbi-modeling-mcp": safe})
    observed = _plugin(
        tmp_path / "observed", mcp_servers={"powerbi-modeling-mcp": unsafe}
    )

    details = " ".join(
        blocker.detail for blocker in compare_plugin(policy, locked, observed)
    )

    assert unsafe_arg in details


def test_active_plugin_version_must_equal_locked_version(tmp_path: Path) -> None:
    locked = _plugin(tmp_path / "locked", version="1.2.3")
    observed = _plugin(tmp_path / "observed", version="1.2.4")

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
