"""Thin re-export: the ONE build-engine resolver lives in the main package
(``seshat.dagster_adapter.engine``) so the orchestration assets and the
``seshat dagster doctor`` preflight resolve the engine through the SAME tested
implementation (FR-010) -- mirroring how ``evidence_writer`` and the gate
readers are shared across both environments. No orchestration-only logic here.
"""

from __future__ import annotations

from seshat.dagster_adapter.engine import (  # noqa: F401
    DBT,
    ENGINE_FILE,
    MIGRATIONS,
    resolve_build_engine,
)

__all__ = ["DBT", "ENGINE_FILE", "MIGRATIONS", "resolve_build_engine"]
