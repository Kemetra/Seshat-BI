"""Canonical local artifact identity helpers; no network and no file writes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def resolve_within(root: Path | str, candidate: Path | str) -> Path:
    workspace = Path(root).resolve()
    raw = Path(candidate)
    resolved = (workspace / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError("artifact path resolves outside workspace")
    return resolved


def canonical_relative_path(root: Path | str, candidate: Path | str) -> str:
    workspace = Path(root).resolve()
    return resolve_within(workspace, candidate).relative_to(workspace).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_identity(
    root: Path | str,
    candidate: Path | str,
    *,
    kind: str,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    path = resolve_within(root, candidate)
    relative = canonical_relative_path(root, path)
    exists = path.is_file()
    return {
        "artifact_id": artifact_id or f"{kind}:{relative}",
        "kind": kind,
        "path": relative,
        "sha256": sha256_file(path) if exists else None,
        "verification": "verified" if exists else "missing",
        "note": None if exists else "artifact is not available in the workspace",
    }
