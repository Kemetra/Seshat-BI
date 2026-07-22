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

_DRIVER_DISTRIBUTIONS: dict[str, tuple[str, ...]] = {
    "postgres": ("psycopg2-binary", "psycopg2"),
    "sqlserver": ("pyodbc",),
    "mysql": ("mysql-connector-python",),
    "snowflake": ("snowflake-connector-python",),
}
_LIVE_ENABLE_STEPS = (
    'pipx inject seshat-bi psycopg2-binary; or pip install "seshat-bi[db]"; '
    "set DATABASE_URL or ANALYTICS_DB_* in the gitignored .env"
)

_INSTALL_REMEDY = (
    "cd orchestration/dagster && uv venv .venv && "
    'uv pip install -p .venv "seshat-bi[dbt]" -e ".[dev]" '
    '(a development checkout uses -e "../..[dbt]" instead of "seshat-bi[dbt]")'
)


@dataclass(frozen=True)
class DoctorFinding:
    id: str
    severity: str  # "blocker" | "warning" | "info"
    message: str
    remedy: str
    state: str | None = None


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


def _driver_metadata_present(engine: str) -> bool:
    """Inspect installed-distribution metadata without importing a DB driver."""
    from importlib.metadata import PackageNotFoundError, version

    for distribution in _DRIVER_DISTRIBUTIONS[engine]:
        try:
            version(distribution)
        except PackageNotFoundError:
            continue
        return True
    return False


def live_readiness_findings(root: Path) -> list[DoctorFinding]:
    """Configuration-only DB diagnostics; never connect, query, or import drivers."""
    del root  # configuration is intentionally read only from the scoped environment
    from seshat.dialect import get_dialect

    engine = os.environ.get("ANALYTICS_DB_ENGINE", "postgres").strip().lower()
    try:
        dialect = get_dialect(engine)
        config = dialect.resolve_config(dict(os.environ))
    except ValueError:
        return [
            DoctorFinding(
                id="DAG-LIVE-ENGINE-01",
                severity="warning",
                message=(
                    "live-readiness engine configuration is invalid (value redacted)"
                ),
                remedy=(
                    "set ANALYTICS_DB_ENGINE to postgres, sqlserver, mysql, or "
                    "snowflake"
                ),
                state="invalid",
            ),
            DoctorFinding(
                id="DAG-LIVE-00",
                severity="warning",
                message=(
                    "live-readiness configuration is invalid; no connection or "
                    "query was attempted"
                ),
                remedy=_LIVE_ENABLE_STEPS,
                state="invalid",
            ),
        ]

    findings = [
        DoctorFinding(
            id="DAG-LIVE-ENGINE-00",
            severity="info",
            message=(
                f"live-readiness engine {engine} selected (no connection attempted)"
            ),
            remedy="none",
            state="available",
        )
    ]
    credentials_state = "available" if config is not None else "missing"
    findings.append(
        DoctorFinding(
            id="DAG-LIVE-CRED-00" if config is not None else "DAG-LIVE-CRED-01",
            severity="info" if config is not None else "warning",
            message=(
                "live-readiness credential source available (value redacted)"
                if config is not None
                else "live-readiness credential source missing"
            ),
            remedy="none" if config is not None else _LIVE_ENABLE_STEPS,
            state=credentials_state,
        )
    )
    driver_present = _driver_metadata_present(engine)
    findings.append(
        DoctorFinding(
            id="DAG-LIVE-DRIVER-00" if driver_present else "DAG-LIVE-DRIVER-01",
            severity="info" if driver_present else "warning",
            message=(
                "live-readiness driver metadata available (driver not imported)"
                if driver_present
                else "live-readiness driver metadata missing (driver not imported)"
            ),
            remedy="none" if driver_present else _LIVE_ENABLE_STEPS,
            state="available" if driver_present else "missing",
        )
    )
    overall = "available" if config is not None and driver_present else "pending_live"
    findings.append(
        DoctorFinding(
            id="DAG-LIVE-00",
            severity="info" if overall == "available" else "warning",
            message=(
                f"live-readiness configuration is {overall}; no connection or query "
                "was attempted"
            ),
            remedy="none" if overall == "available" else _LIVE_ENABLE_STEPS,
            state=overall,
        )
    )
    return findings


_PROJECT_ABSENT = DoctorFinding(
    id="DAG-PROJ-01",
    severity="blocker",
    message=(
        "orchestration project absent: orchestration/dagster/pyproject.toml not found"
    ),
    remedy=(
        "run `seshat dagster init` to materialize the governed orchestration "
        "project into this workspace, then create its .venv (see DAG-VENV-01)"
    ),
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
    if state.gate_status == "UNCOMMITTED":
        return DoctorFinding(
            id="DAG-GATE-01",
            severity="warning",
            message=(
                f"{table}: mapping gate artifact is not committed "
                f"(Gate status UNCOMMITTED, open rows {state.open_rows}) -- "
                "silver_tables will BLOCK fail-closed"
            ),
            remedy=(
                f"commit mappings/{table}/unresolved-questions.md -- an "
                "uncommitted gate artifact is never a GO signal (#334)"
            ),
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


def _venv_site_packages(venv: Path) -> tuple[Path, ...]:
    """Return existing Windows and POSIX virtual-environment site directories."""
    candidates = [venv / "Lib" / "site-packages"]
    candidates.extend(sorted((venv / "lib").glob("python*/site-packages")))
    return tuple(path for path in candidates if path.is_dir())


def _distribution_metadata_present(venv: Path, name: str) -> bool:
    """Check installed distribution metadata without executing the environment."""
    normalized = name.replace("-", "_")
    return any(
        any(site.glob(f"{normalized}-*.dist-info/METADATA"))
        for site in _venv_site_packages(venv)
    )


def _dbt_runtime_present(root: Path) -> bool:
    """True when the orchestration venv contains dbt-core metadata.

    Doctor is a read-only metadata probe: it must never execute a repository
    interpreter merely to discover whether dbt-core is installed.
    """
    venv = orchestration_dir(root) / ".venv"
    return _distribution_metadata_present(venv, "dbt-core")


def _dbt_profile_present(root: Path) -> bool:
    """True when the governed dbt live profile (SESHAT_DBT_*) resolves.

    The dbt engine reads its credentials from the SESHAT_DBT_* child
    environment (spec 133), not the migrations DSN -- report on the contract
    the dbt build actually uses. A malformed .env reads as absent here so a
    DIRECT caller (or a non-CLI entry point) still degrades read-only rather
    than raising; on the `seshat dagster` CLI path the malformed file is now
    intercepted earlier -- `applied_dotenv` raises at the command boundary and
    the family returns a clean exit 2 (issue #348) before this runs.
    """
    from seshat.cli.commands.dbt import EnvironmentConfigError, load_child_environment

    try:
        environment = load_child_environment(root)
    except EnvironmentConfigError:
        return False
    return bool(environment.get("SESHAT_DBT_HOST"))


def _engine_availability_finding(root: Path, table: str) -> DoctorFinding:
    """Under the dbt engine: is the dbt runtime + a live profile available?

    Truthful and categorical -- never a fabricated live pass. An absent runtime
    or profile is a concrete deferred/enable finding, not a blocker (everything
    static still works); credentials are reported present/absent only.
    """
    if not _dbt_runtime_present(root):
        return DoctorFinding(
            id="DAG-ENG-DBT-01",
            severity="warning",
            message=(
                f"{table}: engine dbt but the dbt runtime is absent from the "
                "orchestration environment -- the dbt build will block fail-closed"
            ),
            remedy=_INSTALL_REMEDY,
        )
    if not _dbt_profile_present(root):
        return DoctorFinding(
            id="DAG-ENG-DBT-02",
            severity="warning",
            message=(
                f"{table}: engine dbt but no live dbt profile (SESHAT_DBT_*) -- "
                "the dbt build will record a deferred boundary and block "
                "fail-closed"
            ),
            remedy=(
                "put the SESHAT_DBT_* values in the git-ignored .env; never "
                "commit a real value"
            ),
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
            _engine_availability_finding(root, table),
        ]
    if silver == "dbt":
        return [
            DoctorFinding(
                id="DAG-ENG-00",
                severity="info",
                message=f"{table}: build engine dbt (both layers)",
                remedy="none",
            ),
            _engine_availability_finding(root, table),
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


def run_doctor(root: Path, live_readiness: bool = False) -> list[DoctorFinding]:
    root = Path(root)
    project = _project_findings(root)
    if project and project[0].id == "DAG-PROJ-01":
        return project
    dsn = [_DSN_PRESENT if _dsn_present() else _DSN_ABSENT]
    findings = project + _table_findings(root) + dsn
    return findings + (live_readiness_findings(root) if live_readiness else [])


def has_blockers(findings: list[DoctorFinding]) -> bool:
    return any(finding.severity == "blocker" for finding in findings)
