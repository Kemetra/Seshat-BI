from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
import yaml

from scripts.external_agent_acceptance import validate_bundle

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = ROOT / "integrations" / "codex" / "seshat-bi"


def _version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def test_repository_codex_catalog_points_to_native_plugin() -> None:
    catalog = json.loads(
        (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
    )
    assert catalog["name"] == "seshat-bi-repository"
    assert catalog["interface"]["displayName"] == "Seshat BI Repository"
    assert len(catalog["plugins"]) == 1
    entry = catalog["plugins"][0]
    assert entry == {
        "name": "seshat-bi",
        "source": {
            "source": "local",
            "path": "./integrations/codex/seshat-bi",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }
    assert (ROOT / entry["source"]["path"]).resolve() == PLUGIN_ROOT.resolve()


def test_codex_manifest_is_skills_only_and_current_schema() -> None:
    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == _version()
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["defaultPrompt"].startswith("Use $seshat-bi")
    assert manifest["interface"]["capabilities"] == [
        "Skills",
        "Read-only guidance",
    ]
    assert not set(manifest).intersection(
        {"commands", "agents", "hooks", "mcpServers", "apps"}
    )
    assert validate_bundle(ROOT, "codex") == []


def test_codex_skills_use_supported_layout_and_frontmatter() -> None:
    skills = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    assert [path.parent.name for path in skills] == [
        "bi-bigdata-knowledge",
        "bi-dax-knowledge",
        "bi-python-knowledge",
        "bi-sql-knowledge",
        "retail-kpi-knowledge",
        "seshat-bi",
    ]
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        assert frontmatter["name"] == skill.parent.name
        assert frontmatter["description"]


def test_codex_bundle_supports_fresh_and_repository_contexts() -> None:
    contexts = yaml.safe_load(
        (
            ROOT / "tests/fixtures/public_distribution/codex/discovery-contexts.yaml"
        ).read_text(encoding="utf-8")
    )
    assert {case["id"] for case in contexts["cases"]} == {
        "fresh-no-agents",
        "seshat-repository",
        "undeclared-capability",
    }
    router = (PLUGIN_ROOT / "skills/seshat-bi/SKILL.md").read_text(encoding="utf-8")
    assert "no `AGENTS.md`" in router
    assert "$seshat-bi" in (PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(
        encoding="utf-8"
    )
