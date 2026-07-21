"""Tests for the read-only orchestration-adoption assessment engine (issue #401).

The engine reads ONLY committed state (``mappings/*/readiness-status.yaml``, the
presence of a dbt / dagster project) and emits a recommend-then-decide document:
per-adapter signals, a categorical recommendation, open questions the tool CANNOT
answer from committed state (deferred to the human), and the concrete opt-in
command for each path. It never installs, runs, or approves an adapter, and it
never emits a numeric score (Principle V, hard rule #9).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.orchestration_assess import build_orchestration_assessment

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str, body: str) -> None:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _gold_ready(table: str) -> str:
    return f"""\
table: "silver.{table}"
current_stage: "gold_ready"
stages:
  source_ready: {{status: "pass", evidence: ["profile"]}}
  mapping_ready: {{status: "pass", evidence: ["map"]}}
  silver_ready: {{status: "pass", evidence: ["silver"]}}
  gold_ready: {{status: "pass", evidence: ["gold live-validated"]}}
"""


def _mapping_ready(table: str) -> str:
    return f"""\
table: "silver.{table}"
current_stage: "mapping_ready"
stages:
  source_ready: {{status: "pass", evidence: ["profile"]}}
  mapping_ready: {{status: "pass", evidence: ["map"]}}
"""


def _gold_stage_blocked(table: str) -> str:
    """current_stage LABEL is gold_ready, but the gold_ready stage is BLOCKED --
    the table has NOT reached gold. Counting the bare label as gold would be the
    #401-review bug."""
    return f"""\
table: "silver.{table}"
current_stage: "gold_ready"
stages:
  source_ready: {{status: "pass", evidence: ["profile"]}}
  mapping_ready: {{status: "pass", evidence: ["map"]}}
  silver_ready: {{status: "pass", evidence: ["silver"]}}
  gold_ready: {{status: "blocked", evidence: []}}
"""


# ---------------------------------------------------------------------------
# Shape / invariants
# ---------------------------------------------------------------------------


def test_empty_repo_recommends_neither_and_is_read_only(tmp_path: Path) -> None:
    result = build_orchestration_assessment(tmp_path)
    assert result["read_only_proof"] is True
    assert result["table_count"] == 0
    assert result["recommendation"]["dbt"] == "not_recommended"
    assert result["recommendation"]["dagster"] == "not_recommended"


def test_result_never_emits_a_numeric_score(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    result = build_orchestration_assessment(tmp_path)
    import json

    dumped = json.dumps(result).lower()
    for banned in ("score", "confidence", "health", "maturity", "completeness"):
        assert banned not in dumped


def test_recommendation_values_are_categorical_never_a_decision(tmp_path: Path) -> None:
    """The tool RECOMMENDS; it never records an adoption DECISION. Values are a
    fixed categorical vocabulary, and the document is explicit that the human
    decides."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    result = build_orchestration_assessment(tmp_path)
    # No "recommended" tier: a state-derived signal is capped at "consider"
    # (never an assertion that the customer must adopt).
    allowed = {"consider", "not_recommended", "already_adopted"}
    assert result["recommendation"]["dbt"] in allowed
    assert result["recommendation"]["dagster"] in allowed
    assert result["decision_owner"] == "human"


def test_gold_ready_label_with_blocked_stage_is_not_counted_as_gold(
    tmp_path: Path,
) -> None:
    """A table whose `current_stage` LABEL is `gold_ready` but whose `gold_ready`
    stage is `blocked` has NOT reached gold. It must not be counted as
    gold-validated -- counting the bare label would falsely emit the stronger
    single-table "already Gold-validated -> orchestration NOT required" headline
    for a build that has not passed (#401 review)."""
    _write_status(tmp_path, "orders", _gold_stage_blocked("orders"))
    result = build_orchestration_assessment(tmp_path)
    assert result["table_count"] == 1
    # A blocked gold stage is NOT counted toward gold readiness.
    assert result["gold_ready_count"] == 0
    # The headline must NOT assert the build is already Gold-validated.
    assert "Gold-validated" not in result["recommended_action"]


def test_engine_is_read_only(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    build_orchestration_assessment(tmp_path)
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


# ---------------------------------------------------------------------------
# The C086 case: one table, gold-validated -> orchestration NOT required
# ---------------------------------------------------------------------------


def test_single_gold_table_recommends_neither_plainly(tmp_path: Path) -> None:
    _write_status(tmp_path, "sales_c086_raw", _gold_ready("sales_c086_raw"))
    result = build_orchestration_assessment(tmp_path)
    assert result["table_count"] == 1
    assert result["recommendation"]["dbt"] == "not_recommended"
    assert result["recommendation"]["dagster"] == "not_recommended"
    # The plain-language headline names the actual situation, not ceremony.
    headline = result["recommended_action"].lower()
    assert "not required" in headline or "not recommended" in headline
    # A concrete "revisit when" trigger is surfaced (the issue's exact ask).
    assert "revisit" in headline


def test_single_table_reports_a_reason_against_each_adapter(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    result = build_orchestration_assessment(tmp_path)
    dbt = result["adapters"]["dbt"]
    assert dbt["recommendation"] == "not_recommended"
    assert any(
        "single" in s.lower() or "one table" in s.lower() for s in dbt["against"]
    )


# ---------------------------------------------------------------------------
# Multiple tables -> dbt becomes a "consider", dagster surfaces open questions
# ---------------------------------------------------------------------------


def test_multiple_tables_moves_dbt_to_consider(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _write_status(tmp_path, "customers", _gold_ready("customers"))
    _write_status(tmp_path, "products", _mapping_ready("products"))
    result = build_orchestration_assessment(tmp_path)
    assert result["table_count"] == 3
    assert result["recommendation"]["dbt"] == "consider"
    dbt = result["adapters"]["dbt"]
    assert any("table" in s.lower() for s in dbt["for"])


def test_dagster_recommendation_defers_scheduling_to_the_human(tmp_path: Path) -> None:
    """Whether unattended/scheduled runs are needed is an INTENTION the tool
    cannot read from committed state -- it must be an open question, never a
    fabricated verdict."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _write_status(tmp_path, "customers", _gold_ready("customers"))
    result = build_orchestration_assessment(tmp_path)
    dagster = result["adapters"]["dagster"]
    # dagster is never asserted as "recommended" from state alone.
    assert dagster["recommendation"] in {"consider", "not_recommended"}
    joined = " ".join(dagster["open_questions"]).lower()
    assert "schedul" in joined or "unattended" in joined


# ---------------------------------------------------------------------------
# Opt-in commands are surfaced but never executed
# ---------------------------------------------------------------------------


def test_each_adapter_surfaces_its_concrete_opt_in_command(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    result = build_orchestration_assessment(tmp_path)
    assert "seshat-bi[dbt]" in result["adapters"]["dbt"]["opt_in_command"]
    assert "dagster init" in result["adapters"]["dagster"]["opt_in_command"]


def test_already_adopted_adapter_is_reported_as_present(tmp_path: Path) -> None:
    """If a dbt project is already committed, the tool reports it as present and
    does not re-recommend adopting it."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    (tmp_path / "dbt").mkdir(parents=True)
    (tmp_path / "dbt" / "dbt_project.yml").write_text(
        "name: shadow\n", encoding="utf-8"
    )
    result = build_orchestration_assessment(tmp_path)
    dbt = result["adapters"]["dbt"]
    assert dbt["already_present"] is True
    assert dbt["recommendation"] == "already_adopted"


def test_dagster_project_presence_is_detected(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    proj = tmp_path / "orchestration" / "dagster"
    proj.mkdir(parents=True)
    (proj / "pyproject.toml").write_text("[project]\nname='o'\n", encoding="utf-8")
    result = build_orchestration_assessment(tmp_path)
    dagster = result["adapters"]["dagster"]
    assert dagster["already_present"] is True
    assert dagster["recommendation"] == "already_adopted"


# ---------------------------------------------------------------------------
# Robustness: malformed / partial committed state must not crash
# ---------------------------------------------------------------------------


def test_malformed_status_file_is_skipped_not_fatal(tmp_path: Path) -> None:
    _write_status(tmp_path, "good", _gold_ready("good"))
    _write_status(tmp_path, "bad", "this: is: not: valid: yaml: [")
    result = build_orchestration_assessment(tmp_path)
    # The good table still counts; the bad one is skipped, not a crash.
    assert result["table_count"] == 1
