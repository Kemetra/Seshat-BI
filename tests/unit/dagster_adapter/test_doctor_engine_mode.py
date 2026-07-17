"""US4 (FR-010): `seshat dagster doctor` reports the resolved build engine per
table and, under `dbt`, dbt availability -- truthfully, categorically, no score.

A table on the default engine reports `migrations` and asserts nothing about
dbt. A table configured `engine: dbt` reports the dbt engine plus a deferred/
enable finding when the dbt runtime or DSN is absent. A table whose two layers
resolve to MIXED engines produces a WARNING naming the mix (plan-review R2 /
FR-015). No numeric score is ever emitted and the DSN is never echoed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dagster_adapter import doctor

pytestmark = pytest.mark.unit

UNRESOLVED = """- **Gate status:** `CLEARED`

| ID | Question | Why | Who | Default | Status | Resolution |
|----|----------|-----|-----|---------|--------|------------|
| Q1 | q? | b. | analyst | d | `answered` | r |
"""

GOOD_PYPROJECT = """[project]
name = "tower-bi-orchestration"
dependencies = [
    "dagster==1.13.14",
]
"""


def _repo(tmp_path: Path, engines: dict[str, str] | None) -> Path:
    root = tmp_path / "repo"
    tdir = root / "mappings" / "demo_table"
    tdir.mkdir(parents=True)
    (tdir / "source-map.yaml").write_text("table: demo\n", encoding="utf-8")
    (tdir / "unresolved-questions.md").write_text(UNRESOLVED, encoding="utf-8")
    (tdir / "readiness-status.yaml").write_text(
        "stages: {}\napprovals: []\n", encoding="utf-8"
    )
    if engines is not None:
        body = "".join(f"{layer}: {value}\n" for layer, value in engines.items())
        (tdir / "build-engine.yaml").write_text(body, encoding="utf-8")
    orch = root / "orchestration" / "dagster"
    orch.mkdir(parents=True)
    (orch / "pyproject.toml").write_text(GOOD_PYPROJECT, encoding="utf-8")
    scripts = orch / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("", encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def _no_dsn(monkeypatch: pytest.MonkeyPatch):
    import os

    for key in list(dict(**os.environ)):
        if key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_"):
            monkeypatch.delenv(key, raising=False)


def _engine_findings(findings) -> list:
    return [f for f in findings if f.id.startswith("DAG-ENG")]


def test_default_engine_reports_migrations_and_asserts_nothing_about_dbt(
    tmp_path: Path,
) -> None:
    findings = doctor.run_doctor(_repo(tmp_path, engines=None))
    eng = _engine_findings(findings)
    assert eng, "expected a per-table engine-mode finding"
    finding = next(f for f in eng if "demo_table" in f.message)
    assert "migrations" in finding.message
    assert finding.severity == "info"
    assert "dbt" not in finding.message.replace("migrations", "")


def test_dbt_engine_reports_the_engine_and_a_deferred_finding_when_dsn_absent(
    tmp_path: Path,
) -> None:
    findings = doctor.run_doctor(
        _repo(tmp_path, engines={"silver": "dbt", "gold": "dbt"})
    )
    eng = _engine_findings(findings)
    messages = " ".join(f.message for f in eng)
    assert "demo_table" in messages
    assert "dbt" in messages
    # a concrete deferred/enable finding under dbt when the DSN is absent
    assert any(f.severity in {"warning", "info"} and "dbt" in f.message for f in eng)
    assert all(not _looks_like_a_score(f.message) for f in findings)


def test_mixed_engines_emit_a_warning_naming_the_mix(tmp_path: Path) -> None:
    findings = doctor.run_doctor(
        _repo(tmp_path, engines={"silver": "dbt", "gold": "migrations"})
    )
    eng = _engine_findings(findings)
    mixed = [f for f in eng if f.severity == "warning" and "mixed" in f.message.lower()]
    assert mixed, "a mixed-engine table must emit a WARNING naming the mix"
    assert "demo_table" in mixed[0].message
    assert "dbt" in mixed[0].message and "migrations" in mixed[0].message


def test_doctor_never_echoes_the_dsn_under_the_dbt_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "postgresql://user:secretpw@host:5432/db"
    monkeypatch.setenv("DATABASE_URL", secret)
    findings = doctor.run_doctor(
        _repo(tmp_path, engines={"silver": "dbt", "gold": "dbt"})
    )
    assert all(secret not in f.message + f.remedy for f in findings)


def _looks_like_a_score(text: str) -> bool:
    # a numeric health/confidence/maturity score is forbidden (hard rule #9)
    import re

    return bool(re.search(r"\b\d+\s*(/\s*\d+|%|score|points)\b", text.lower()))
