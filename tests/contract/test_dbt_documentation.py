"""Truth contracts for the activated governed dbt adapter."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import yaml

from seshat.capability_feeders import read_dbt_adapter_state

ROOT = Path(__file__).resolve().parents[2]

ACTIVE_DBT_DOCS = (
    ".claude/skills/dbt-transformation-adapter/SKILL.md",
    "docs/integrations/dbt-adapter.md",
    "docs/decisions/0009-dbt-is-transformation-adapter.md",
    "templates/dbt-adapter-contract.md",
    "templates/dbt-model-contract.md",
)
STALE = (
    "the dbt project itself is a PLANNED future output",
    "this slice creates NO dbt files",
    "Until the dbt project exists",
)
EXACT_DBT_VERSIONS = ("dbt-core==1.12.0", "dbt-postgres==1.10.2")


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_active_dbt_docs_do_not_claim_runtime_is_absent() -> None:
    for relative in ACTIVE_DBT_DOCS:
        text = _text(relative)
        for phrase in STALE:
            assert phrase.casefold() not in text.casefold(), relative


def test_history_preserves_planning_then_activation_sequence() -> None:
    adr = _text("docs/decisions/0009-dbt-is-transformation-adapter.md")
    assert "2026-06-26" in adr
    assert "feature 023" in adr.casefold()
    assert "feature 133" in adr.casefold()
    assert "activated" in adr.casefold()


def test_capability_declares_real_dbt_feeders() -> None:
    document = yaml.safe_load(_text("docs/capabilities/capabilities.yaml"))
    entry = next(
        item
        for item in document["capabilities"]
        if item["id"] == "dbt-transformation-adapter"
    )
    assert entry["state"] == "deferred"
    assert entry["provenance"] == "unrecorded"
    assert entry["authority"] == "agent-runnable"
    assert entry["surface"] == "execution-adapter"
    assert entry["requirements"] == ["database", "optional-dependency"]
    assert entry["command"] == "dbt"
    assert entry["references"]["dispatch"] == "dbt"
    assert entry["references"]["runtime_project"] == "dbt/dbt_project.yml"
    assert entry["references"]["public_skill"] == "dbt-workflows"
    assert entry["references"]["package_extra"] == "dbt"
    assert entry["references"]["activation_status"] == (
        "docs/operations/dbt-activation-status.yaml"
    )
    assert entry["references"]["tests"]


def test_dbt_feeder_requires_every_activation_signal(tmp_path: Path) -> None:
    assert read_dbt_adapter_state(ROOT) == "partial"

    required = (
        "src/seshat/cli/__init__.py",
        "dbt/dbt_project.yml",
        "distribution/public-command-surface.yaml",
        "integrations/claude-code/seshat-bi/skills/dbt-workflows/SKILL.md",
        "integrations/codex/seshat-bi/skills/dbt-workflows/SKILL.md",
        "pyproject.toml",
        "tests/contract/test_dbt_project.py",
        "tests/contract/test_dbt_public_surface.py",
        "tests/integration/test_dbt_artifact_flow.py",
        "docs/operations/dbt-activation-status.yaml",
    )
    for relative in required:
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    assert read_dbt_adapter_state(tmp_path) == "partial"
    status_path = tmp_path / "docs/operations/dbt-activation-status.yaml"
    status = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    status["status"] = "pass"
    status["owner"] = "compatibility-owner"
    status["evidence"]["compile"] = "pass"
    status["evidence"]["live_parity"] = "pass"
    status["blockers"] = []
    status_path.write_text(yaml.safe_dump(status), encoding="utf-8")

    assert read_dbt_adapter_state(tmp_path) == "shipped"
    (tmp_path / "dbt/dbt_project.yml").unlink()
    assert read_dbt_adapter_state(tmp_path) == "partial"


def test_exact_versions_and_governed_commands_are_documented() -> None:
    combined = "\n".join(
        _text(path)
        for path in (
            "docs/integrations/dbt-adapter.md",
            "docs/install/developer-install.md",
            "docs/operations/adapter-update-policy.md",
        )
    )
    for version in EXACT_DBT_VERSIONS:
        assert version in combined
    for command in (
        "seshat dbt doctor",
        "seshat dbt validate",
        "seshat dbt plan",
        "seshat dbt build",
        "seshat dbt inspect-run",
    ):
        assert command in combined
    assert "[PENDING LIVE PROFILE]" in combined


def test_active_spec_kit_markers_agree_and_resolve() -> None:
    feature_directory = json.loads((ROOT / ".specify/feature.json").read_text())[
        "feature_directory"
    ]
    agents_text = _text("AGENTS.md")
    claude_text = _text("CLAUDE.md")
    pattern = re.compile(r"specs/\d{3}-[a-z0-9-]+/plan\.md")
    fence = re.compile(
        r"<!-- SPECKIT START -->(?P<body>.*?)<!-- SPECKIT END -->", re.DOTALL
    )
    agents_body = fence.search(agents_text).group("body").strip()
    claude_body = fence.search(claude_text).group("body").strip()
    if feature_directory is None:
        assert agents_body == "No active Spec Kit implementation plan."
        assert claude_body == "No active Spec Kit implementation plan."
        assert not pattern.search(agents_body + claude_body)
        return

    assert isinstance(feature_directory, str)
    expected = f"{feature_directory}/plan.md"
    assert pattern.findall(agents_body) == [expected]
    assert pattern.findall(claude_body) == [expected]
    assert (ROOT / expected).is_file()
    tasks = ROOT / feature_directory / "tasks.md"
    assert tasks.is_file()
    assert "- [ ]" in tasks.read_text(encoding="utf-8")
