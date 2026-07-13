from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
import yaml

from scripts.external_agent_acceptance import validate_bundle

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = ROOT / "integrations" / "claude-code" / "seshat-bi"


def _version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def test_repository_root_is_the_only_claude_marketplace() -> None:
    manifests = [".claude-plugin/marketplace.json"]
    manifests.extend(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "integrations/claude-code").rglob("marketplace.json")
        if path.parent.name == ".claude-plugin"
    )
    manifests.sort()
    assert manifests == [".claude-plugin/marketplace.json"]

    marketplace = json.loads((ROOT / manifests[0]).read_text(encoding="utf-8"))
    assert marketplace["metadata"]["version"] == _version()
    assert len(marketplace["plugins"]) == 1
    entry = marketplace["plugins"][0]
    assert entry["name"] == "seshat-bi"
    assert entry["version"] == _version()
    assert entry["source"] == "./integrations/claude-code/seshat-bi"
    assert (ROOT / entry["source"]).resolve() == PLUGIN_ROOT.resolve()


def test_claude_manifest_and_components_follow_current_schema() -> None:
    plugin = json.loads(
        (PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    assert plugin["version"] == _version()
    assert plugin["skills"] == "./skills/"
    assert plugin["commands"] == "./commands/"
    assert not set(plugin).intersection({"hooks", "mcpServers", "apps"})
    assert validate_bundle(ROOT, "claude-code") == []

    for command in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
        text = command.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        assert frontmatter["description"]


def test_claude_bundle_is_portable_without_workspace_agent_file() -> None:
    router = (PLUGIN_ROOT / "skills/seshat-bi/SKILL.md").read_text(encoding="utf-8")
    assert "no `AGENTS.md`" in router
    assert "portable-operating-contract.md" in router
    rendered = "\n".join(
        path.read_text(encoding="utf-8") for path in PLUGIN_ROOT.rglob("*.md")
    )
    assert "C:\\Users\\" not in rendered
    assert "/Users/" not in rendered
    assert "requires a development-repository clone" not in rendered.casefold()
