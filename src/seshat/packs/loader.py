"""Explicit local pack-manifest loading (spec 120, US5).

Loads exactly the manifest files the caller names -- no directory discovery,
no remote registry, and no import or execution of any pack content. Every
path must stay within the workspace root (fail closed).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..artifact_identity import canonical_relative_path, resolve_within
from .model import PackError


def _read_manifest_text(resolved: Path, relative: str) -> str:
    try:
        return resolved.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise PackError(f"pack manifest is unreadable: {relative}") from exc
    except UnicodeDecodeError as exc:
        raise PackError(f"pack manifest is not valid UTF-8: {relative}") from exc


def _parse_manifest(raw: str, relative: str) -> dict[str, Any]:
    import yaml  # lazy: keep module import stdlib-light (B1/B3)

    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise PackError(f"pack manifest is not valid YAML: {relative}") from exc
    if not isinstance(document, dict):
        raise PackError(f"pack manifest is not a mapping: {relative}")
    return document


def load_pack_document(
    repo_root: Path | str, manifest_path: Path | str
) -> tuple[dict[str, Any], str]:
    """Read one named manifest and return ``(document, repo_relative_path)``.

    Raises :class:`PackError` with a disclosure-safe message on containment,
    read, parse, or shape failures. Never executes or imports pack content.
    """
    root = Path(repo_root).resolve()
    try:
        resolved = resolve_within(root, manifest_path)
    except ValueError as exc:
        raise PackError("pack manifest path resolves outside the workspace") from exc
    relative = canonical_relative_path(root, resolved)
    document = _parse_manifest(_read_manifest_text(resolved, relative), relative)
    return document, relative
