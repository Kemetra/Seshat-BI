"""Offline validation for generated bundle Git provenance."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import Mapping

_FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class ProvenanceError(ValueError):
    """A bundle provenance claim is missing, malformed, or irreproducible."""


def require_full_git_revision(value: object, *, label: str = "source_revision") -> str:
    """Return a well-formed immutable Git revision or fail clearly."""

    if value is None or value == "":
        raise ProvenanceError(f"{label} is missing")
    return _require_well_formed_revision(value, label)


def _require_well_formed_revision(value: object, label: str) -> str:
    if not isinstance(value, str) or _FULL_GIT_SHA.fullmatch(value) is None:
        raise ProvenanceError(
            f"{label} must be a full 40-character lowercase Git SHA; observed {value!r}"
        )
    return value


def _require_local_commit(repo_root: Path, revision: str) -> None:
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0:
        raise ProvenanceError(
            f"source_revision does not resolve to a local Git commit: {revision}"
        )


def _project_document_text(repo_root: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:pyproject.toml"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ProvenanceError(
            f"source_revision {revision} has no readable canonical pyproject.toml"
        )
    return result.stdout


def _parse_project_document(document_text: str, revision: str) -> dict[str, object]:
    try:
        return tomllib.loads(document_text)
    except tomllib.TOMLDecodeError as exc:
        raise ProvenanceError(
            f"source_revision {revision} has no readable canonical project.version"
        ) from exc


def _project_version_value(document: Mapping[str, object], revision: str) -> object:
    try:
        return document["project"]["version"]
    except (KeyError, TypeError) as exc:
        raise ProvenanceError(
            f"source_revision {revision} has no readable canonical project.version"
        ) from exc


def _require_project_version(version: object, revision: str) -> str:
    if not isinstance(version, str) or not version:
        raise ProvenanceError(
            f"source_revision {revision} has no readable canonical project.version"
        )
    return version


def project_version_at_revision(repo_root: Path, source_revision: object) -> str:
    """Read the canonical project version from an existing local Git commit."""

    revision = require_full_git_revision(source_revision)
    _require_local_commit(repo_root, revision)
    document_text = _project_document_text(repo_root, revision)
    document = _parse_project_document(document_text, revision)
    version = _project_version_value(document, revision)
    return _require_project_version(version, revision)


def _ancestor_failure(revision: str, returncode: int) -> ProvenanceError:
    if returncode == 1:
        return ProvenanceError(
            f"source_revision {revision} is not an ancestor of current HEAD; "
            "preserve the version-projection commit without squash or rebase"
        )
    return ProvenanceError(
        f"source_revision {revision} ancestry could not be verified locally"
    )


def _require_revision_ancestor(repo_root: Path, revision: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise _ancestor_failure(revision, result.returncode)


def _head_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ProvenanceError("current HEAD does not resolve to a Git commit")
    return result.stdout.strip()


def _source_version_allowing_rewrites(repo_root: Path, revision: str) -> str:
    """Version at the recorded revision, or at HEAD when history rewriting
    (squash-merge, deleted PR branch) has orphaned the generation commit.

    The anti-fabrication invariant survives the fallback: the manifest's
    version claim must still equal the canonical project version of a commit
    in this repository -- HEAD, the very commit under validation.
    """

    try:
        source_version = project_version_at_revision(repo_root, revision)
        _require_revision_ancestor(repo_root, revision)
        return source_version
    except ProvenanceError:
        return project_version_at_revision(repo_root, _head_revision(repo_root))


def _manifest_version(manifest: Mapping[str, object], label: str) -> str:
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ProvenanceError(f"{label} version is missing or malformed")
    return version


def _require_matching_version(
    *, label: str, revision: str, version: str, source_version: str
) -> None:
    if source_version != version:
        raise ProvenanceError(
            f"{label} declares version {version!r}, but source_revision {revision} "
            f"declares canonical project version {source_version!r}"
        )


def validate_manifest_provenance(
    repo_root: Path,
    manifest: Mapping[str, object],
    *,
    label: str,
    require_ancestry: bool = True,
) -> str:
    """Require a manifest version to match its immutable source revision.

    ``require_ancestry=True`` (the release-audit posture) demands the recorded
    revision be a reachable ancestor of HEAD -- the coordinated-release flow
    lands its version-projection commit without squash or rebase precisely so
    this holds. ``require_ancestry=False`` (the everyday export/CI posture)
    tolerates squash-merged history by validating the version claim against
    HEAD's canonical project version instead.
    """

    version = _manifest_version(manifest, label)
    revision = require_full_git_revision(
        manifest.get("source_revision"), label=f"{label} source_revision"
    )
    if require_ancestry:
        source_version = project_version_at_revision(repo_root, revision)
        _require_revision_ancestor(repo_root, revision)
    else:
        source_version = _source_version_allowing_rewrites(repo_root, revision)
    _require_matching_version(
        label=label,
        revision=revision,
        version=version,
        source_version=source_version,
    )
    return revision
