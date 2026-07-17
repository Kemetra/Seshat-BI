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

from . import PINNED_DAGSTER
from .engine import resolve_build_engine
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

_PIN_MISMATCH = DoctorFinding(
    id="DAG-PAIR-01",
    severity="blocker",
    message=(
        "pinned dagster mismatch: orchestration/dagster/pyproject.toml must pin "
        f"dagster=={PINNED_DAGSTER} (spec 024 auto-update posture; the dagster-dbt "
        "pin was dropped by spec 135 FR-011)"
    ),
    remedy="restore the dagster pin; bumps land via PR only, never independently",
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
    if f"dagster=={PINNED_DAGSTER}" not in pyproject:
        findings.append(_PIN_MISMATCH)
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


def _dbt_runtime_present() -> bool:
    """True when the pinned dbt runtime is importable in THIS environment.

    Read-only metadata probe (no dbt module import); mirrors the seshat dbt
    doctor's version check without asserting the exact version here.
    """
    import importlib.metadata

    try:
        importlib.metadata.version("dbt-core")
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def _engine_availability_finding(table: str) -> DoctorFinding:
    """Under the dbt engine: is the dbt runtime + a live profile available?

    Truthful and categorical -- never a fabricated live pass. An absent runtime
    or DSN is a concrete deferred/enable finding, not a blocker (everything
    static still works); the DSN is reported present/absent only.
    """
    if not _dbt_runtime_present():
        return DoctorFinding(
            id="DAG-ENG-DBT-01",
            severity="warning",
            message=(
                f"{table}: engine dbt but the dbt runtime is absent from the "
                "orchestration environment -- the dbt build will block fail-closed"
            ),
            remedy=_INSTALL_REMEDY,
        )
    if not _dsn_present():
        return DoctorFinding(
            id="DAG-ENG-DBT-02",
            severity="warning",
            message=(
                f"{table}: engine dbt but no database credentials -- the dbt "
                "build will record a deferred boundary and block fail-closed"
            ),
            remedy="put the DSN in the git-ignored .env; never commit a real value",
        )
    return DoctorFinding(
        id="DAG-ENG-DBT-00",
        severity="info",
        message=(
            f"{table}: engine dbt; the dbt runtime and database credentials are "
            "PRESENT (live drive stays [PENDING LIVE PROFILE])"
        ),
        remedy="none",
    )


def _engine_mode_findings(root: Path, table: str) -> list[DoctorFinding]:
    """Per-table resolved build engine (migrations vs dbt), per layer.

    Reports the resolved engine truthfully; warns on a MIXED configuration (a
    migrations layer may read a real relation this run's dbt layer never
    rebuilt -- FR-015/plan-review R2). A migrations-only table asserts nothing
    about dbt.
    """
    silver = resolve_build_engine(root, table, "silver")
    gold = resolve_build_engine(root, table, "gold")
    if silver != gold:
        return [
            DoctorFinding(
                id="DAG-ENG-MIX-01",
                severity="warning",
                message=(
                    f"{table}: MIXED build engines (silver={silver}, gold={gold}) "
                    "-- a migrations layer may read a real relation the dbt layer "
                    "only rebuilt in shadow this run"
                ),
                remedy=(
                    "set both layers to the same engine in "
                    "mappings/<table>/build-engine.yaml unless the mix is intended"
                ),
            ),
            _engine_availability_finding(table),
        ]
    if silver == "dbt":
        return [
            DoctorFinding(
                id="DAG-ENG-00",
                severity="info",
                message=f"{table}: build engine dbt (both layers)",
                remedy="none",
            ),
            _engine_availability_finding(table),
        ]
    return [
        DoctorFinding(
            id="DAG-ENG-00",
            severity="info",
            message=f"{table}: build engine migrations (both layers, the default)",
            remedy="none",
        )
    ]


def _table_findings(root: Path) -> list[DoctorFinding]:
    tables = list_mapped_tables(root)
    if not tables:
        return [_NO_TABLES]
    findings: list[DoctorFinding] = []
    for table in tables:
        findings.append(_gate_finding(table, read_gate_state(root, table)))
        findings.extend(_engine_mode_findings(root, table))
    return findings


def run_doctor(root: Path) -> list[DoctorFinding]:
    root = Path(root)
    project = _project_findings(root)
    if project and project[0].id == "DAG-PROJ-01":
        return project
    dsn = [_DSN_PRESENT if _dsn_present() else _DSN_ABSENT]
    return project + _table_findings(root) + dsn


def has_blockers(findings: list[DoctorFinding]) -> bool:
    return any(finding.severity == "blocker" for finding in findings)
