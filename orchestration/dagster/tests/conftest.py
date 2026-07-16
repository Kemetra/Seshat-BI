"""Fixture repos for the in-process orchestration tests (spec 134 US1-US3).

Builds a generic tmp repo shaped like the real one: ``mappings/<table>/`` gate
artifacts, ``warehouse/migrations/`` SQL, ``data/raw/<table>.csv``. Table name
is deliberately generic (Principle VII).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

TABLE = "demo_table"

UNRESOLVED_TEMPLATE = """# Unresolved questions -- `{table}`

- **Table id:** `{table}`
- **Gate status:** `{gate_status}`

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | A question? | It blocks. | analyst | default | `{q1_status}` | {q1_resolution} |
"""

READINESS_TEMPLATE = """table: "bronze.{table}"
stages:
  mapping_ready:
    status: "pass"
    evidence: []
    blocking_reasons: []
  semantic_model_ready:
    status: "{semantic_status}"
    evidence: []
    blocking_reasons: []
  publish_ready:
    status: "{publish_status}"
    evidence: []
    blocking_reasons: []
approvals:
{approvals}
"""

APPROVAL_ROW = """  - stage: "{stage}"
    owner: "Named Human ({role})"
    at: "2026-06-25"
    note: "recorded by a named human"
"""


def make_fixture_repo(
    tmp_path: Path,
    *,
    gate_cleared: bool = True,
    semantic_approved: bool = True,
    publish_status: str = "not_started",
) -> Path:
    root = tmp_path / "repo"
    table_dir = root / "mappings" / TABLE
    table_dir.mkdir(parents=True)
    (table_dir / "source-map.yaml").write_text(f"table: {TABLE}\n", encoding="utf-8")
    (table_dir / "source-profile.md").write_text("# profile\nrows: 3\n", encoding="utf-8")
    (table_dir / "unresolved-questions.md").write_text(
        UNRESOLVED_TEMPLATE.format(
            table=TABLE,
            gate_status="CLEARED" if gate_cleared else "OPEN",
            q1_status="answered" if gate_cleared else "open",
            q1_resolution="resolved 2026-01-01" if gate_cleared else "",
        ),
        encoding="utf-8",
    )
    approvals = APPROVAL_ROW.format(stage="mapping_ready", role="data_owner")
    if semantic_approved:
        approvals += APPROVAL_ROW.format(stage="semantic_model_ready", role="metric_owner")
    (table_dir / "readiness-status.yaml").write_text(
        READINESS_TEMPLATE.format(
            table=TABLE,
            semantic_status="pass" if semantic_approved else "not_started",
            publish_status=publish_status,
            approvals=approvals,
        ),
        encoding="utf-8",
    )
    (table_dir / "metrics").mkdir()
    (table_dir / "metrics" / "a-metric.yaml").write_text("metric: A\n", encoding="utf-8")
    (table_dir / "design").mkdir()
    (table_dir / "design" / "layout.md").write_text("# layout\n", encoding="utf-8")
    (table_dir / "handoff").mkdir()
    (table_dir / "handoff" / "pack.md").write_text("# pack\n", encoding="utf-8")

    migrations = root / "warehouse" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / f"0001_create_silver_{TABLE}.sql").write_text(
        "SELECT 1;\n", encoding="utf-8"
    )
    (migrations / f"0002_create_gold_{TABLE}_star.sql").write_text(
        "SELECT 1;\n", encoding="utf-8"
    )

    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / f"{TABLE}.csv").write_text("id,amount\n1,10\n2,20\n", encoding="utf-8")
    return root


def mappings_digest(root: Path) -> str:
    """One hash over every byte under mappings/ -- the no-authored-truth probe."""
    digest = hashlib.sha256()
    for path in sorted((root / "mappings").rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.fixture
def green_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_fixture_repo(tmp_path)
    monkeypatch.setenv("SESHAT_REPO_ROOT", str(root))
    monkeypatch.setenv("SESHAT_DAGSTER_RUN_ID", "testrun-001")
    monkeypatch.delenv("SESHAT_DAGSTER_TABLES", raising=False)
    monkeypatch.delenv("SESHAT_RAW_LANDING_DIR", raising=False)
    return root


def stub_green_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend a healthy DB + green gate commands (never a real connection)."""
    from tower_bi_orchestration import commands, db

    monkeypatch.setattr(db, "resolve_dsn", lambda: "postgresql://stub")
    monkeypatch.setattr(db, "apply_sql_file", lambda dsn, path: None)
    monkeypatch.setattr(db, "load_csv", lambda dsn, table, path: 2)
    monkeypatch.setattr(
        commands, "run_gate_command", lambda argv, cwd: (0, "0 violations")
    )
