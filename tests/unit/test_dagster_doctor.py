"""Unit tests for `seshat dagster doctor` findings (spec 134, T022/T023)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dagster_adapter import PINNED_DAGSTER, doctor

pytestmark = pytest.mark.unit


# spec 135 (FR-011 owner decision, 2026-07-17) dropped the dagster-dbt pin; the
# orchestration project pins dagster only.
GOOD_PYPROJECT = f"""[project]
name = "tower-bi-orchestration"
dependencies = [
    "dagster=={PINNED_DAGSTER}",
]
"""

UNRESOLVED = """- **Gate status:** `{status}`

| ID | Question | Why | Who | Default | Status | Resolution |
|----|----------|-----|-----|---------|--------|------------|
| Q1 | q? | b. | analyst | d | `{q}` | r |
"""


def _repo(tmp_path: Path, **spec) -> Path:
    orchestration = spec.get("orchestration", True)
    venv = spec.get("venv", True)
    pyproject = spec.get("pyproject", GOOD_PYPROJECT)
    gate_status = spec.get("gate_status", "CLEARED")
    root = tmp_path / "repo"
    tdir = root / "mappings" / "demo_table"
    tdir.mkdir(parents=True)
    (tdir / "source-map.yaml").write_text("table: demo\n", encoding="utf-8")
    (tdir / "unresolved-questions.md").write_text(
        UNRESOLVED.format(
            status=gate_status, q="answered" if gate_status == "CLEARED" else "open"
        ),
        encoding="utf-8",
    )
    (tdir / "readiness-status.yaml").write_text(
        "stages: {}\napprovals: []\n", encoding="utf-8"
    )
    if orchestration:
        orch = root / "orchestration" / "dagster"
        orch.mkdir(parents=True)
        (orch / "pyproject.toml").write_text(pyproject, encoding="utf-8")
        if venv:
            scripts = orch / ".venv" / ("Scripts")
            scripts.mkdir(parents=True)
            (scripts / "python.exe").write_text("", encoding="utf-8")
    return root


def _ids(findings) -> set[str]:
    return {finding.id for finding in findings}


@pytest.fixture(autouse=True)
def _no_dsn(monkeypatch: pytest.MonkeyPatch):
    for key in list(dict(**__import__("os").environ)):
        if key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_"):
            monkeypatch.delenv(key, raising=False)


def test_missing_orchestration_project_is_a_blocker(tmp_path: Path) -> None:
    findings = doctor.run_doctor(_repo(tmp_path, orchestration=False))
    assert "DAG-PROJ-01" in _ids(findings)
    assert doctor.has_blockers(findings) is True


def test_missing_venv_is_a_blocker_with_the_install_remedy(tmp_path: Path) -> None:
    findings = doctor.run_doctor(_repo(tmp_path, venv=False))
    blocker = next(f for f in findings if f.id == "DAG-VENV-01")
    assert blocker.severity == "blocker"
    assert "uv pip install" in blocker.remedy


def test_pin_mismatch_is_a_blocker(tmp_path: Path) -> None:
    bad = GOOD_PYPROJECT.replace(PINNED_DAGSTER, "0.99.0")
    findings = doctor.run_doctor(_repo(tmp_path, pyproject=bad))
    assert "DAG-PAIR-01" in _ids(findings)


def test_open_gate_is_a_warning_not_a_blocker(tmp_path: Path) -> None:
    findings = doctor.run_doctor(_repo(tmp_path, gate_status="OPEN"))
    gate_findings = [f for f in findings if f.id == "DAG-GATE-01"]
    assert gate_findings and gate_findings[0].severity == "warning"
    assert "demo_table" in gate_findings[0].message


def test_uncommitted_gate_artifact_names_the_commit_remedy(tmp_path: Path) -> None:
    """The `_repo` fixture is deliberately NOT a git repo, so its CLEARED
    mirror reads as UNCOMMITTED (#334): the doctor must name the commit
    remedy instead of implying the reviewer still has to clear the gate."""
    findings = doctor.run_doctor(_repo(tmp_path))
    gate_findings = [f for f in findings if f.id == "DAG-GATE-01"]
    assert gate_findings
    assert "UNCOMMITTED" in gate_findings[0].message
    assert (
        "commit mappings/demo_table/unresolved-questions.md" in gate_findings[0].remedy
    )


def test_absent_dsn_is_a_warning_and_present_dsn_is_never_echoed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    findings = doctor.run_doctor(root)
    dsn_finding = next(f for f in findings if f.id == "DAG-DSN-01")
    assert dsn_finding.severity == "warning"
    assert doctor.has_blockers(findings) is False  # a green repo has no blockers

    secret = "postgresql://user:secretpw@host:5432/db"
    monkeypatch.setenv("DATABASE_URL", secret)
    findings = doctor.run_doctor(root)
    dsn_findings = [f for f in findings if f.id == "DAG-DSN-01"]
    assert not dsn_findings  # warning cleared
    assert all(secret not in f.message + f.remedy for f in findings)


def test_dbt_runtime_probe_reads_windows_metadata_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    metadata = (
        root
        / "orchestration"
        / "dagster"
        / ".venv"
        / "Lib"
        / "site-packages"
        / "dbt_core-1.12.0.dist-info"
        / "METADATA"
    )
    metadata.parent.mkdir(parents=True)
    metadata.write_text("Name: dbt-core\n", encoding="utf-8")
    monkeypatch.setattr(
        doctor,
        "orchestration_python",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("doctor looked up an executable probe")
        ),
    )

    assert doctor._dbt_runtime_present(root) is True


def test_dbt_runtime_probe_reads_posix_metadata_without_an_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path, venv=False)
    metadata = (
        root
        / "orchestration"
        / "dagster"
        / ".venv"
        / "lib"
        / "python3.13"
        / "site-packages"
        / "dbt_core-1.12.0.dist-info"
        / "METADATA"
    )
    metadata.parent.mkdir(parents=True)
    metadata.write_text("Name: dbt-core\n", encoding="utf-8")
    monkeypatch.setattr(
        doctor,
        "orchestration_python",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("doctor looked up an executable probe")
        ),
    )

    assert doctor._dbt_runtime_present(root) is True


def test_dbt_runtime_probe_is_false_without_metadata(tmp_path: Path) -> None:
    assert doctor._dbt_runtime_present(_repo(tmp_path)) is False


def test_live_readiness_reports_engine_driver_and_credentials_without_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "postgresql://reader:never-print@db.internal/warehouse"
    monkeypatch.setenv("DATABASE_URL", secret)
    monkeypatch.setattr(doctor, "_driver_metadata_present", lambda engine: True)

    findings = doctor.live_readiness_findings(_repo(tmp_path))

    assert {finding.id for finding in findings} >= {
        "DAG-LIVE-ENGINE-00",
        "DAG-LIVE-CRED-00",
        "DAG-LIVE-DRIVER-00",
        "DAG-LIVE-00",
    }
    assert all(secret not in finding.message + finding.remedy for finding in findings)
    assert next(f for f in findings if f.id == "DAG-LIVE-00").state == "available"


def test_live_readiness_is_pending_without_credentials_or_driver(
    tmp_path: Path,
) -> None:
    findings = doctor.live_readiness_findings(_repo(tmp_path))

    assert next(f for f in findings if f.id == "DAG-LIVE-CRED-01").state == "missing"
    assert next(f for f in findings if f.id == "DAG-LIVE-00").state == "pending_live"


def test_live_readiness_invalid_engine_never_connects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANALYTICS_DB_ENGINE", "unknown-engine")
    from seshat.dialect import PostgresDialect

    monkeypatch.setattr(
        PostgresDialect,
        "connect",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not connect")),
    )

    findings = doctor.live_readiness_findings(_repo(tmp_path))

    overall = next(f for f in findings if f.id == "DAG-LIVE-00")
    assert overall.state == "invalid"
    assert "unknown-engine" not in overall.message
