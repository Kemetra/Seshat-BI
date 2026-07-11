"""Materialize the committed demo fixtures into the working directory (spec 083).

The committed source of truth is ``mappings/demo_sample_orders/`` (mapping-gate +
readiness fixtures) and ``tests/fixtures/demo/demo_sample_orders.csv`` (the sample
data). ``init`` copies these into ``.demo-work/`` (git-ignored) so a demo run
operates on a throwaway copy and NEVER writes a tracked file (FR-010).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import MAPPINGS_DIR, SAMPLE_CSV, SAMPLE_NAME, WORK_DIR


def work_dir(repo: Path) -> Path:
    """The git-ignored throwaway working directory under ``repo``."""
    return repo / WORK_DIR


def committed_readiness_status(repo: Path) -> Path:
    """The COMMITTED, tracked readiness-status fixture (never written by a run)."""
    return repo / MAPPINGS_DIR / "readiness-status.yaml"


def materialize(repo: Path, *, force: bool = False) -> Path:
    """Copy the committed fixtures into ``.demo-work/``; return the working dir.

    Idempotent without ``force``: if the working dir already holds the sample, it is
    left as-is (no overwrite). With ``force``, the working dir is refreshed from the
    committed fixtures. Never touches any tracked file.
    """
    wd = work_dir(repo)
    sample_dir = wd / SAMPLE_NAME
    marker = sample_dir / "readiness-status.yaml"

    if marker.exists() and not force:
        return wd

    sample_dir.mkdir(parents=True, exist_ok=True)

    # Copy the mapping-gate + readiness fixtures.
    src_mappings = repo / MAPPINGS_DIR
    for name in (
        "source-profile.md",
        "source-map.yaml",
        "assumptions.md",
        "unresolved-questions.md",
        "readiness-status.yaml",
    ):
        src = src_mappings / name
        if src.exists():
            shutil.copyfile(src, sample_dir / name)

    # Copy the sample CSV.
    csv_src = repo / SAMPLE_CSV
    if csv_src.exists():
        shutil.copyfile(csv_src, sample_dir / "demo_sample_orders.csv")

    return wd
