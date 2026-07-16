"""Repo-root and mapped-table discovery (research D7).

Generic by construction (Principle VII): tables are discovered from
``mappings/<table>/source-map.yaml`` -- no table name is baked in anywhere in
this package.
"""

from __future__ import annotations

import os
from pathlib import Path


def find_repo_root() -> Path:
    """The Seshat repo root: ``SESHAT_REPO_ROOT`` when set (tests, CI), else
    the nearest ancestor of this file carrying ``mappings/`` + ``warehouse/``."""
    override = os.environ.get("SESHAT_REPO_ROOT")
    if override:
        return Path(override)
    for parent in Path(__file__).resolve().parents:
        if (parent / "mappings").is_dir() and (parent / "warehouse").is_dir():
            return parent
    raise RuntimeError(
        "Seshat repo root not found (no ancestor with mappings/ + warehouse/); "
        "set SESHAT_REPO_ROOT explicitly."
    )


def discover_tables(root: Path) -> list[str]:
    """Mapped tables (sorted), optionally narrowed by ``SESHAT_DAGSTER_TABLES``
    (comma-separated) -- the closed table-scoping seam the runner uses."""
    from seshat.dagster_adapter.gate import list_mapped_tables

    tables = list_mapped_tables(root)
    scoped = os.environ.get("SESHAT_DAGSTER_TABLES")
    if scoped:
        wanted = {name.strip() for name in scoped.split(",") if name.strip()}
        tables = [table for table in tables if table in wanted]
    return tables
