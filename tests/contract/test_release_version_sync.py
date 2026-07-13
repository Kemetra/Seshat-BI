from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_release_versions import audit_versions

pytestmark = pytest.mark.unit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json(path: Path, value: object) -> None:
    _write(path, json.dumps(value))


def _repository(root: Path, version: str = "0.2.0") -> None:
    _write(
        root / "pyproject.toml",
        f'[project]\nname = "seshat-bi"\nversion = "{version}"\n',
    )
    _json(
        root / "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
        {"version": version},
    )
    _json(
        root / ".claude-plugin/marketplace.json",
        {"metadata": {"version": version}},
    )
    _json(
        root / "integrations/claude-code/seshat-bi/bundle-manifest.json",
        {"version": version},
    )
    _json(
        root / "integrations/codex/seshat-bi/.codex-plugin/plugin.json",
        {"version": version},
    )
    _json(root / ".agents/plugins/marketplace.json", {"plugins": [{}]})
    _json(
        root / "integrations/codex/seshat-bi/bundle-manifest.json",
        {"version": version},
    )
    _write(root / "CHANGELOG.md", f"# Changelog\n\n## [{version}]\n")
    major_minor = ".".join(version.split(".")[:2])
    _write(root / f"docs/releases/v{major_minor}.md", f"# Seshat BI v{major_minor}\n")


def test_governed_locations_pass_with_pending_owner_actions(tmp_path: Path) -> None:
    _repository(tmp_path)
    report = audit_versions(tmp_path, source_revision="a" * 40, tags={})
    assert report["status"] == "pass"
    statuses = {item["surface"]: item["status"] for item in report["projections"]}
    assert statuses["codex_catalog"] == "not_schema_supported"
    assert statuses["git_tag"] == "pending_owner_action"


def test_missing_governed_location_is_a_concrete_blocker(tmp_path: Path) -> None:
    _repository(tmp_path)
    (tmp_path / "integrations/codex/seshat-bi/.codex-plugin/plugin.json").unlink()
    report = audit_versions(tmp_path, source_revision="a" * 40, tags={})
    assert report["status"] == "blocked"
    assert any(
        "required governed version location" in item
        for item in report["blocking_reasons"]
    )


def test_version_mismatch_and_missing_release_note_block(tmp_path: Path) -> None:
    _repository(tmp_path)
    _json(
        tmp_path / "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
        {"version": "9.9.9"},
    )
    (tmp_path / "docs/releases/v0.2.md").unlink()
    report = audit_versions(tmp_path, source_revision="a" * 40, tags={})
    assert report["status"] == "blocked"
    assert len(report["blocking_reasons"]) == 2


def test_existing_tag_at_another_revision_blocks_reuse(tmp_path: Path) -> None:
    _repository(tmp_path)
    report = audit_versions(
        tmp_path,
        source_revision="a" * 40,
        tags={"v0.2.0": "b" * 40},
    )
    assert report["status"] == "blocked"
    assert any("existing immutable tag" in item for item in report["blocking_reasons"])
