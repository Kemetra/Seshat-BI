"""The readiness gate these surfaces sit behind.

Rendering requires ``dashboard_ready: pass``, because a report surface presents an
APPROVED design. With no approved design there is nothing to render, and letting a
renderer decide what appears would make it a second place a report's content is
decided -- the failure the whole bundle arrangement exists to prevent.

This module reads committed state and refuses. It never writes a status, never
advances a stage, and never infers an approval.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from seshat.report.model import ReportError

REQUIRED_STAGE = "dashboard_ready"
PASS = "pass"


def readiness_path(repo_root: Path, table: str) -> Path:
    return repo_root / "mappings" / table / "readiness-status.yaml"


def stage_status(repo_root: Path, table: str) -> str:
    """The recorded status of the gating stage, verbatim.

    A missing file or a missing stage is reported as ``not_started`` rather than
    guessed at: absence of evidence is not a pass.
    """
    path = readiness_path(repo_root, table)
    if not path.is_file():
        return "not_started"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read {path}: {exc}") from exc
    stages = payload.get("stages")
    if not isinstance(stages, dict):
        return "not_started"
    stage = stages.get(REQUIRED_STAGE)
    if isinstance(stage, dict):
        return str(stage.get("status") or "not_started")
    return str(stage or "not_started")


def assert_renderable(repo_root: Path, table: str) -> None:
    status = stage_status(repo_root, table)
    if status != PASS:
        raise ReportError(
            f"{REQUIRED_STAGE} is {status!r} for {table!r}, not {PASS!r}. These "
            "surfaces render an APPROVED design, so the design must be approved "
            "first -- run the dashboard design and review flow, then retry."
        )
