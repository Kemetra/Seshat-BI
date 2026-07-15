from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.check_release_versions import audit_versions

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json(path: Path, value: object) -> None:
    _write(path, json.dumps(value))


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_version(root: Path, version: str) -> str:
    _write(
        root / "pyproject.toml",
        f'[project]\nname = "seshat-bi"\nversion = "{version}"\n',
    )
    _git(root, "init")
    _git(root, "add", "pyproject.toml")
    _git(
        root,
        "-c",
        "user.name=Seshat Tests",
        "-c",
        "user.email=tests@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        f"project {version}",
    )
    return _git(root, "rev-parse", "HEAD")


def _repository(
    root: Path, version: str = "0.2.0", *, source_version: str | None = None
) -> str:
    revision = _commit_version(root, source_version or version)
    if source_version is not None and source_version != version:
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
        {"version": version, "source_revision": revision},
    )
    _json(
        root / "integrations/codex/seshat-bi/.codex-plugin/plugin.json",
        {"version": version},
    )
    _json(root / ".agents/plugins/marketplace.json", {"plugins": [{}]})
    _json(
        root / "integrations/codex/seshat-bi/bundle-manifest.json",
        {"version": version, "source_revision": revision},
    )
    _write(root / "CHANGELOG.md", f"# Changelog\n\n## [{version}]\n")
    major_minor = ".".join(version.split(".")[:2])
    _write(root / f"docs/releases/v{major_minor}.md", f"# Seshat BI v{major_minor}\n")
    return revision


def test_governed_locations_pass_with_pending_owner_actions(tmp_path: Path) -> None:
    revision = _repository(tmp_path)
    report = audit_versions(tmp_path, source_revision=revision, tags={})
    assert report["status"] == "pass"
    statuses = {item["surface"]: item["status"] for item in report["projections"]}
    assert statuses["codex_catalog"] == "not_schema_supported"
    assert statuses["git_tag"] == "pending_owner_action"


def test_missing_governed_location_is_a_concrete_blocker(tmp_path: Path) -> None:
    revision = _repository(tmp_path)
    (tmp_path / "integrations/codex/seshat-bi/.codex-plugin/plugin.json").unlink()
    report = audit_versions(tmp_path, source_revision=revision, tags={})
    assert report["status"] == "blocked"
    assert any(
        "required governed version location" in item
        for item in report["blocking_reasons"]
    )


def test_version_mismatch_and_missing_release_note_block(tmp_path: Path) -> None:
    revision = _repository(tmp_path)
    _json(
        tmp_path / "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
        {"version": "9.9.9"},
    )
    (tmp_path / "docs/releases/v0.2.md").unlink()
    report = audit_versions(tmp_path, source_revision=revision, tags={})
    assert report["status"] == "blocked"
    assert len(report["blocking_reasons"]) == 2


def test_existing_tag_at_another_revision_blocks_reuse(tmp_path: Path) -> None:
    revision = _repository(tmp_path)
    report = audit_versions(
        tmp_path,
        source_revision=revision,
        tags={"v0.2.0": "b" * 40},
    )
    assert report["status"] == "blocked"
    assert any("existing immutable tag" in item for item in report["blocking_reasons"])


def test_bundle_revision_version_mismatch_blocks_both_targets(tmp_path: Path) -> None:
    revision = _repository(tmp_path, source_version="0.1.0")
    report = audit_versions(tmp_path, source_revision=revision, tags={})
    blockers = "\n".join(report["blocking_reasons"])
    assert report["status"] == "blocked"
    assert "claude bundle manifest declares version '0.2.0'" in blockers
    assert "codex bundle manifest declares version '0.2.0'" in blockers
    assert blockers.count("canonical project version '0.1.0'") == 2


def test_missing_bundle_revision_fails_clearly(tmp_path: Path) -> None:
    revision = _repository(tmp_path)
    path = tmp_path / "integrations/claude-code/seshat-bi/bundle-manifest.json"
    _json(path, {"version": "0.2.0"})
    report = audit_versions(tmp_path, source_revision=revision, tags={})
    assert any(
        "claude bundle manifest source_revision is missing" in blocker
        for blocker in report["blocking_reasons"]
    )


@pytest.mark.parametrize("revision", ["not-a-sha", "A" * 40])
def test_malformed_bundle_revision_fails_clearly(tmp_path: Path, revision: str) -> None:
    candidate_revision = _repository(tmp_path)
    path = tmp_path / "integrations/codex/seshat-bi/bundle-manifest.json"
    _json(path, {"version": "0.2.0", "source_revision": revision})
    report = audit_versions(tmp_path, source_revision=candidate_revision, tags={})
    expected = (
        "codex bundle manifest source_revision must be a full 40-character "
        "lowercase Git SHA"
    )
    assert any(expected in blocker for blocker in report["blocking_reasons"])


def test_unknown_bundle_revision_fails_without_network(tmp_path: Path) -> None:
    candidate_revision = _repository(tmp_path)
    path = tmp_path / "integrations/codex/seshat-bi/bundle-manifest.json"
    _json(path, {"version": "0.2.0", "source_revision": "f" * 40})
    report = audit_versions(tmp_path, source_revision=candidate_revision, tags={})
    assert any(
        "source_revision does not resolve to a local Git commit" in blocker
        for blocker in report["blocking_reasons"]
    )


def test_non_ancestor_bundle_revision_fails_clearly(tmp_path: Path) -> None:
    source_revision = _repository(tmp_path)
    _git(tmp_path, "switch", "--orphan", "unrelated")
    _write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "seshat-bi"\nversion = "0.2.0"\n',
    )
    _git(tmp_path, "add", "pyproject.toml")
    _git(
        tmp_path,
        "-c",
        "user.name=Seshat Tests",
        "-c",
        "user.email=tests@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "unrelated project 0.2.0",
    )
    report = audit_versions(
        tmp_path, source_revision=_git(tmp_path, "rev-parse", "HEAD"), tags={}
    )
    blockers = "\n".join(report["blocking_reasons"])
    assert source_revision in blockers
    assert "is not an ancestor of current HEAD" in blockers


def test_coordinated_release_commits_version_before_bundle_export() -> None:
    workflow = (ROOT / ".github/workflows/prepare-coordinated-release.yml").read_text(
        encoding="utf-8"
    )
    version_commit = workflow.index(
        'git commit -m "chore: project v${VERSION} version metadata"'
    )
    bundle_export = workflow.index(
        "python scripts/export_agent_bundles.py", version_commit
    )
    bundle_commit = workflow.index(
        'git commit -m "chore: generate v${VERSION} agent bundles"'
    )
    assert version_commit < bundle_export < bundle_commit
    assert "Do not squash or rebase" in workflow
