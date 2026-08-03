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
    stages = _payload(path).get("stages")
    if not isinstance(stages, dict):
        return "not_started"
    return _recorded(stages.get(REQUIRED_STAGE))


def _payload(path: Path) -> dict:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read {path}: {exc}") from exc
    return loaded if isinstance(loaded, dict) else {}


def _recorded(stage: object) -> str:
    """A stage is written either as a mapping carrying a status, or as a bare token."""
    if isinstance(stage, dict):
        stage = stage.get("status")
    return str(stage or "not_started")


def stage_evidence(repo_root: Path, table: str) -> tuple[str, ...]:
    """The evidence recorded beside the gating stage's status.

    A bare ``dashboard_ready: pass`` token records no evidence at all, and neither
    does a mapping with an empty ``evidence`` list. Both come back empty here.
    """
    path = readiness_path(repo_root, table)
    if not path.is_file():
        return ()
    stages = _payload(path).get("stages")
    if not isinstance(stages, dict):
        return ()
    stage = stages.get(REQUIRED_STAGE)
    if not isinstance(stage, dict):
        return ()
    evidence = stage.get("evidence")
    if not isinstance(evidence, list):
        return ()
    return tuple(str(item) for item in evidence if item)


def assert_renderable(repo_root: Path, table: str) -> None:
    status = stage_status(repo_root, table)
    if status != PASS:
        raise ReportError(
            f"{REQUIRED_STAGE} is {status!r} for {table!r}, not {PASS!r}. These "
            "surfaces render an APPROVED design, so the design must be approved "
            "first -- run the dashboard design and review flow, then retry."
        )
    if not stage_evidence(repo_root, table):
        raise ReportError(
            f"{REQUIRED_STAGE} is {PASS!r} for {table!r} but records no evidence. A "
            "status with nothing behind it is not an approval under the readiness "
            "contract -- a bare `pass` token, or an empty evidence list, is how an "
            "unreviewed design ends up on a board's desk. Record the evidence that "
            "the design review actually happened, then retry."
        )
