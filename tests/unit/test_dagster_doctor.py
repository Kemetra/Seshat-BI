"""Unit tests for `seshat dagster doctor` findings (spec 134, T022/T023)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dagster_adapter import PINNED_DAGSTER, PINNED_DAGSTER_DBT, doctor

pytestmark = pytest.mark.unit


GOOD_PYPROJECT = f"""[project]
name = "tower-bi-orchestration"
dependencies = [
    "dagster=={PINNED_DAGSTER}",
    "dagster-dbt=={PINNED_DAGSTER_DBT}",
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
    bad = GOOD_PYPROJECT.replace(PINNED_DAGSTER_DBT, "0.99.0")
    findings = doctor.run_doctor(_repo(tmp_path, pyproject=bad))
    assert "DAG-PAIR-01" in _ids(findings)


def test_open_gate_is_a_warning_not_a_blocker(tmp_path: Path) -> None:
    findings = doctor.run_doctor(_repo(tmp_path, gate_status="OPEN"))
    gate_findings = [f for f in findings if f.id == "DAG-GATE-01"]
    assert gate_findings and gate_findings[0].severity == "warning"
    assert "demo_table" in gate_findings[0].message


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
