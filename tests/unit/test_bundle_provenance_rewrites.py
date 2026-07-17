"""Squash-merge tolerance contract for bundle manifest provenance.

Feature PRs regenerate bundles on their branch; squash-merging orphans the
recorded generation commit. The everyday (non-release) posture must keep the
anti-fabrication invariant -- the manifest version equals the canonical
project version of a commit in this repository -- without demanding ancestry
that squash-merges structurally destroy. The release audit keeps the strict
posture; tests/contract/test_release_version_sync.py pins that side.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.bundle_provenance import ProvenanceError, validate_manifest_provenance

pytestmark = pytest.mark.unit


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=Seshat Tests",
            "-c",
            "user.email=tests@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_version(root: Path, version: str, message: str) -> str:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "seshat-bi"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    # A per-commit marker keeps every commit non-empty even when the
    # version (and so pyproject.toml) is identical across commits.
    (root / "marker.txt").write_text(message, encoding="utf-8")
    _git(root, "add", "pyproject.toml", "marker.txt")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _squashed_repository(tmp_path: Path, *, version: str = "0.3.1") -> tuple[Path, str]:
    """A repo whose HEAD does NOT descend from the bundle-generation commit,
    mirroring main after a squash-merge: same version, rewritten history."""

    _git(tmp_path, "init", "-b", "main")
    _commit_version(tmp_path, version, "seed")
    _git(tmp_path, "switch", "-c", "feature")
    orphaned = _commit_version(
        tmp_path, version, "feature work (bundle export ran here)"
    )
    _git(tmp_path, "switch", "main")
    squashed = _commit_version(tmp_path, version, "feature work (#N squash)")
    _git(tmp_path, "branch", "-D", "feature")
    assert orphaned != squashed
    return tmp_path, orphaned


def test_orphaned_revision_with_truthful_version_passes_everyday_posture(
    tmp_path: Path,
) -> None:
    repo, orphaned = _squashed_repository(tmp_path)
    manifest = {"version": "0.3.1", "source_revision": orphaned}
    validated = validate_manifest_provenance(
        repo, manifest, label="committed bundle", require_ancestry=False
    )
    assert validated == orphaned


def test_orphaned_revision_with_fabricated_version_still_fails(
    tmp_path: Path,
) -> None:
    repo, orphaned = _squashed_repository(tmp_path)
    manifest = {"version": "9.9.9", "source_revision": orphaned}
    with pytest.raises(ProvenanceError, match="9.9.9"):
        validate_manifest_provenance(
            repo, manifest, label="committed bundle", require_ancestry=False
        )


def test_unresolvable_revision_falls_back_to_head_version(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _commit_version(tmp_path, "0.3.1", "seed")
    vanished = "1" * 40
    manifest = {"version": "0.3.1", "source_revision": vanished}
    validated = validate_manifest_provenance(
        tmp_path, manifest, label="committed bundle", require_ancestry=False
    )
    assert validated == vanished


def test_default_posture_still_requires_ancestry(tmp_path: Path) -> None:
    repo, orphaned = _squashed_repository(tmp_path)
    manifest = {"version": "0.3.1", "source_revision": orphaned}
    with pytest.raises(ProvenanceError, match="not an ancestor"):
        validate_manifest_provenance(repo, manifest, label="committed bundle")


def test_exporter_revalidation_tolerates_the_orphaned_revision(
    tmp_path: Path,
) -> None:
    """--check reuses the committed manifest's revision inside build_bundle;
    that downstream re-validation must not reinstate the ancestry demand the
    upstream fallback just tolerated (Codex P1 on PR #302)."""
    from scripts.export_agent_bundles import _validated_source_revision

    repo, orphaned = _squashed_repository(tmp_path)
    validated = _validated_source_revision(
        repo, version="0.3.1", source_revision=orphaned
    )
    assert validated == orphaned
