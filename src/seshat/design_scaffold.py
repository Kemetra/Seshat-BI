"""Materialize the Stage-6/7 design + handoff blank templates (#440, #441).

Dashboard-Ready (Stage 6) and Publish-Ready (Stage 7) authoring reads six
templates as REPO-RELATIVE paths from the user's working tree --
``templates/dashboard-page-blueprint.yaml``, ``templates/visual-spec.yaml``,
``templates/report-composition.yaml``, ``design/grids/16x9-grid.yaml``,
``templates/handoff/bi-handoff-pack.md``, and
``templates/handoff/handoff-review-checklist.md`` -- consumed by
``blueprint_preview``, ``dashboard_coordinator``, and the ``publish_pack``
rule. Those blanks previously shipped only with the development repository, and
unlike the Stage-1 templates (``stage1_scaffold``), no verb materialized them
into a pip-only workspace -- so a package-only user had nothing to copy.

``scaffold_design`` closes that gap the same way ``stage1_scaffold`` does:
bundled package data (wheel force-include) first, a development-checkout
fallback second (mirrors ``seshat.governed_projects``). The packaged layout is
deliberately FLATTENED under ``seshat/design_templates/`` (see the pyproject
force-include comment), so each template needs an explicit
``(packaged_subpath, dest_relpath)`` pair rather than the identity mapping
``governed_projects`` uses -- the dev-checkout fallback reads
``_SOURCE_ROOT / dest_relpath`` because the destination layout IS the repo
layout. Writes go through the shared hardened writer (``seshat.safe_write``):
per-file non-destructive, containment- and symlink-guarded. Pure stdlib -- no
DB, no network.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from seshat.safe_write import write_if_absent

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_PACKAGED_ROOT = "design_templates"

# (packaged_subpath, dest_relpath) -- the packaged tree is flattened (no
# templates/ prefix, grids/ instead of design/grids/); the destination is the
# exact repo-relative path blueprint_preview / dashboard_coordinator /
# publish_pack expect. Only these six ship (constitution VII): the rest of the
# ~dozen design/handoff templates stay dev-only.
_DESIGN_FILES: tuple[tuple[str, str], ...] = (
    ("dashboard-page-blueprint.yaml", "templates/dashboard-page-blueprint.yaml"),
    ("visual-spec.yaml", "templates/visual-spec.yaml"),
    ("report-composition.yaml", "templates/report-composition.yaml"),
    ("grids/16x9-grid.yaml", "design/grids/16x9-grid.yaml"),
    ("handoff/bi-handoff-pack.md", "templates/handoff/bi-handoff-pack.md"),
    (
        "handoff/handoff-review-checklist.md",
        "templates/handoff/handoff-review-checklist.md",
    ),
)


@dataclass(frozen=True)
class DesignScaffoldResult:
    """What one ``scaffold_design`` call did, per file."""

    written: tuple[str, ...]
    kept: tuple[str, ...]


def _resource_bytes(packaged_subpath: str, dest_relpath: str) -> bytes:
    """One bundled template's bytes: wheel data first, dev checkout fallback.

    The dev-checkout fallback reads ``_SOURCE_ROOT / dest_relpath`` (not the
    packaged subpath) because the destination layout IS the repo layout --
    the flattening only exists in the packaged copy.
    """
    packaged = files("seshat").joinpath(_PACKAGED_ROOT, *packaged_subpath.split("/"))
    if packaged.is_file():
        return packaged.read_bytes()
    source = _SOURCE_ROOT / Path(*dest_relpath.split("/"))
    if source.is_file():
        return source.read_bytes()
    raise FileNotFoundError(
        f"bundled design template is missing: {dest_relpath} "
        "(reinstall seshat-bi, or run from a development checkout)"
    )


def scaffold_design(repo_root: Path) -> DesignScaffoldResult:
    """Write the six Stage-6/7 design + handoff blank templates into ``repo_root``.

    Per-file non-destructive: an existing file is kept, never overwritten.
    Containment and symlink safety are delegated entirely to
    ``seshat.safe_write.write_if_absent`` (raises ``SafeWriteError`` on a
    symlinked path component or an escape attempt). Returns a
    ``DesignScaffoldResult`` of what was written vs kept.
    """
    root = Path(repo_root).resolve()
    written: list[str] = []
    kept: list[str] = []
    for packaged_subpath, dest_relpath in _DESIGN_FILES:
        data = _resource_bytes(packaged_subpath, dest_relpath)
        if write_if_absent(root, dest_relpath, data):
            written.append(dest_relpath)
        else:
            kept.append(dest_relpath)
    return DesignScaffoldResult(written=tuple(written), kept=tuple(kept))
