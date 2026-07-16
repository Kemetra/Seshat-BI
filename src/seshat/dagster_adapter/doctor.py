"""`seshat dagster doctor` -- truthful read-only preflight (spec 134 US4).

Findings are categorical (blocker / warning / info) with a concrete remedy --
never a numeric severity or health score (hard rule #9). A present DSN is
reported as PRESENT only; its value is never echoed (Principle IX). An absent
DSN is a WARNING (the deferred boundary), not a blocker: everything static
still works without one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import PINNED_DAGSTER, PINNED_DAGSTER_DBT
from .gate import GateState, list_mapped_tables, read_gate_state

_INSTALL_REMEDY = (
    "cd orchestration/dagster && uv venv .venv && "
    'uv pip install -p .venv -e ../.. -e ".[dev]"'
)


@dataclass(frozen=True)
class DoctorFinding:
    id: str
    severity: str  # "blocker" | "warning" | "info"
    message: str
    remedy: str


def orchestration_dir(root: Path) -> Path:
    return Path(root) / "orchestration" / "dagster"


def orchestration_python(root: Path) -> Path | None:
    """The orchestration venv's interpreter, or None when it is not installed."""
    venv = orchestration_dir(root) / ".venv"
    for candidate in (venv / "Scripts" / "python.exe", venv / "bin" / "python"):
        if candidate.is_file():
            return candidate
    return None


def _dsn_present() -> bool:
    from seshat.validate import resolve_dsn  # driver-free env resolution

    return resolve_dsn(dict(os.environ)) is not None


_PROJECT_ABSENT = DoctorFinding(
    id="DAG-PROJ-01",
    severity="blocker",
    message=(
        "orchestration project absent: orchestration/dagster/pyproject.toml not found"
    ),
    remedy="check out the full repo (the orchestration project ships with spec 134)",
)

_PAIR_MISMATCH = DoctorFinding(
    id="DAG-PAIR-01",
    severity="blocker",
    message=(
        "pinned pair mismatch: orchestration/dagster/pyproject.toml must pin "
        f"dagster=={PINNED_DAGSTER} and dagster-dbt=={PINNED_DAGSTER_DBT} "
        "TOGETHER (spec 024 auto-update posture)"
    ),
    remedy="restore the pinned pair; bumps land via PR only, never independently",
)

_VENV_ABSENT = DoctorFinding(
    id="DAG-VENV-01",
    severity="blocker",
    message=(
        "orchestration environment absent: "
        "orchestration/dagster/.venv has no interpreter"
    ),
    remedy=_INSTALL_REMEDY,
)

_NO_TABLES = DoctorFinding(
    id="DAG-TBL-01",
    severity="warning",
    message="no mapped tables found under mappings/ (nothing to orchestrate)",
    remedy="onboard a table first (retail-onboard-table -> source-mapping)",
)

_DSN_ABSENT = DoctorFinding(
    id="DAG-DSN-01",
    severity="warning",
    message=(
        "no database credentials in the environment (DATABASE_URL / "
        "ANALYTICS_DB_*) -- DB-touching assets will record a deferred "
        "boundary and block fail-closed"
    ),
    remedy="put the DSN in the git-ignored .env; never commit a real value",
)

_DSN_PRESENT = DoctorFinding(
    id="DAG-DSN-00",
    severity="info",
    message="database credentials PRESENT in the environment (value not shown)",
    remedy="none",
)


def _project_findings(root: Path) -> list[DoctorFinding]:
    orch = orchestration_dir(root)
    if not (orch / "pyproject.toml").is_file():
        return [_PROJECT_ABSENT]
    findings: list[DoctorFinding] = []
    pyproject = (orch / "pyproject.toml").read_text(encoding="utf-8")
    expected = (f"dagster=={PINNED_DAGSTER}", f"dagster-dbt=={PINNED_DAGSTER_DBT}")
    if not all(pin in pyproject for pin in expected):
        findings.append(_PAIR_MISMATCH)
    if orchestration_python(root) is None:
        findings.append(_VENV_ABSENT)
    return findings


def _gate_finding(table: str, state: GateState) -> DoctorFinding:
    if state.silver_permitted:
        return DoctorFinding(
            id="DAG-GATE-00",
            severity="info",
            message=(
                f"{table}: mapping gate CLEARED (0 open rows) -- silver build permitted"
            ),
            remedy="none",
        )
    return DoctorFinding(
        id="DAG-GATE-01",
        severity="warning",
        message=(
            f"{table}: mapping gate not CLEARED "
            f"(Gate status {state.gate_status}, open rows {state.open_rows}) -- "
            "silver_tables will BLOCK fail-closed"
        ),
        remedy="the mapping reviewer clears the gate in unresolved-questions.md",
    )


def _table_findings(root: Path) -> list[DoctorFinding]:
    tables = list_mapped_tables(root)
    if not tables:
        return [_NO_TABLES]
    return [_gate_finding(table, read_gate_state(root, table)) for table in tables]


def run_doctor(root: Path) -> list[DoctorFinding]:
    root = Path(root)
    project = _project_findings(root)
    if project and project[0].id == "DAG-PROJ-01":
        return project
    dsn = [_DSN_PRESENT if _dsn_present() else _DSN_ABSENT]
    return project + _table_findings(root) + dsn


def has_blockers(findings: list[DoctorFinding]) -> bool:
    return any(finding.severity == "blocker" for finding in findings)
