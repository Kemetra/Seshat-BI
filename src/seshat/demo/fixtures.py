"""Materialize the committed demo fixtures into the working directory (spec 083).

The committed source of truth is ``mappings/demo_sample_orders/`` (mapping-gate +
readiness fixtures) and ``tests/fixtures/demo/demo_sample_orders.csv`` (the sample
data). ``init`` copies these into ``.demo-work/`` (git-ignored) so a demo run
operates on a throwaway copy and NEVER writes a tracked file (FR-010).
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import BinaryIO, Protocol

from . import MAPPINGS_DIR, SAMPLE_CSV, SAMPLE_NAME, WORK_DIR

_SOURCE_ROOT = Path(__file__).resolve().parents[3]


def work_dir(repo: Path) -> Path:
    """The git-ignored throwaway working directory under ``repo``."""
    return repo / WORK_DIR


class _Resource(Protocol):
    def read_bytes(self) -> bytes: ...

    def read_text(self, encoding: str = "utf-8") -> str: ...

    def open(self, mode: str = "rb") -> BinaryIO: ...


def _packaged_resource(*parts: str) -> _Resource:
    resource = files("seshat").joinpath("demo", "resources", *parts)
    return resource  # type: ignore[return-value]


def _mapping_source(repo: Path, name: str) -> Path | _Resource:
    local = repo / MAPPINGS_DIR / name
    if local.is_file():
        return local
    source_checkout = _SOURCE_ROOT / MAPPINGS_DIR / name
    if source_checkout.is_file():
        return source_checkout
    return _packaged_resource("demo_sample_orders", name)


def committed_readiness_status(repo: Path) -> Path | _Resource:
    """Tracked source fixture, falling back to the wheel's bundled copy."""
    return _mapping_source(repo, "readiness-status.yaml")


def packaged_brand_asset(repo: Path) -> Path | _Resource:
    local = repo / "assets" / "brand" / "seshat-seven-star.svg"
    if local.is_file():
        return local
    source_checkout = _SOURCE_ROOT / "assets" / "brand" / "seshat-seven-star.svg"
    if source_checkout.is_file():
        return source_checkout
    return _packaged_resource("seshat-seven-star.svg")


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
    for name in (
        "source-profile.md",
        "source-map.yaml",
        "assumptions.md",
        "unresolved-questions.md",
        "readiness-status.yaml",
    ):
        src = _mapping_source(repo, name)
        (sample_dir / name).write_bytes(src.read_bytes())

    # Copy the sample CSV.
    csv_src = repo / SAMPLE_CSV
    checkout_csv = _SOURCE_ROOT / SAMPLE_CSV
    if csv_src.is_file():
        csv_resource: Path | _Resource = csv_src
    elif checkout_csv.is_file():
        csv_resource = checkout_csv
    else:
        csv_resource = _packaged_resource("demo_sample_orders.csv")
    (sample_dir / "demo_sample_orders.csv").write_bytes(csv_resource.read_bytes())

    return wd
