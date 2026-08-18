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


# ---------------------------------------------------------------------------
# Power BI MCP + core-only targets (D1'). The 3-value vocabulary is UNCHANGED:
# there is deliberately no "recommended" tier (see the module's own comment), so
# these targets are assessed with the same consider / not_recommended /
# already_adopted signals the dbt and dagster paths use.
# ---------------------------------------------------------------------------


def _pbip_model(tmp_path: Path, name: str = "Retail") -> None:
    """A committed PBIP semantic model: a `<name>.SemanticModel/` folder."""
    model = tmp_path / "powerbi" / f"{name}.SemanticModel" / "definition"
    model.mkdir(parents=True, exist_ok=True)
    (model.parent / "definition.pbism").write_text("{}", encoding="utf-8")


def test_pbi_mcp_not_recommended_without_a_committed_pbip_model(tmp_path: Path) -> None:
    """With no PBIP model there is nothing for read-only diagnostics to inspect."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))

    doc = build_orchestration_assessment(tmp_path)

    assert doc["recommendation"]["pbi_mcp"] == "not_recommended"


def test_pbi_mcp_consider_when_a_pbip_semantic_model_is_committed(
    tmp_path: Path,
) -> None:
    """A committed PBIP model gives read-only diagnostics a real target."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)

    doc = build_orchestration_assessment(tmp_path)

    assert doc["recommendation"]["pbi_mcp"] == "consider"
    assert doc["adapters"]["pbi_mcp"]["for"] != []


def test_pbi_mcp_already_adopted_when_mcp_config_present(tmp_path: Path) -> None:
    """A .mcp.json configuring a POWER BI server is the already-adopted signal.

    Originally this fixture was a bare `{}`, which asserted the defect PR #537's
    review caught: an empty or unrelated config is not Power BI adoption. The
    fixture is now a real Power BI server entry; the `absent` / `unparseable`
    cases are covered separately below.
    """
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        '{"mcpServers": {"powerbi": {"command": "pbi", "args": ["--readonly"]}}}',
        encoding="utf-8",
    )

    doc = build_orchestration_assessment(tmp_path)

    assert doc["recommendation"]["pbi_mcp"] == "already_adopted"
    assert doc["adapters"]["pbi_mcp"]["already_present"] is True


def test_pbi_mcp_opt_in_is_read_only_and_never_offers_mutation(
    tmp_path: Path,
) -> None:
    """The opt-in path is the read-only doctor family, never a write mode.

    ADR 0018 is ratified (2026-08-18) but slice 5 (mutations) is unbuilt, so no
    write path exists. An assessment that advertised write mode would be
    advising a capability that is not built.
    """
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)

    block = build_orchestration_assessment(tmp_path)["adapters"]["pbi_mcp"]

    assert "doctor" in block["opt_in_command"]
    haystack = " ".join(
        [block["opt_in_command"], *block["for"], *block["against"]]
    ).lower()
    for forbidden in ("write mode", "readwrite", "publish", "mutation"):
        assert forbidden not in haystack


def test_core_only_is_sufficient_when_no_adapter_is_advised(tmp_path: Path) -> None:
    """One direct-built table needs no adapter -- core-only is the honest answer."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))

    doc = build_orchestration_assessment(tmp_path)

    assert doc["core_only_sufficient"] is True


def test_core_only_is_not_sufficient_once_an_adapter_is_considered(
    tmp_path: Path,
) -> None:
    """When any adapter is worth weighing, core-only is no longer the whole answer."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)

    doc = build_orchestration_assessment(tmp_path)

    assert doc["recommendation"]["pbi_mcp"] == "consider"
    assert doc["core_only_sufficient"] is False


def test_existing_dbt_and_dagster_keys_are_unchanged(tmp_path: Path) -> None:
    """Backward compatibility: the pre-existing document keys keep their shape."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))

    doc = build_orchestration_assessment(tmp_path)

    assert set(doc["recommendation"]) == {"dbt", "dagster", "pbi_mcp"}
    assert doc["decision_owner"] == "human"
    assert doc["read_only_proof"] is True
    for key in ("dbt", "dagster"):
        assert set(doc["adapters"][key]) == {
            "recommendation",
            "for",
            "against",
            "open_questions",
            "opt_in_command",
            "already_present",
        }


# ---------------------------------------------------------------------------
# Review fixes (PR #537, Codex P2 x3).
# ---------------------------------------------------------------------------


def _mcp_config(tmp_path: Path, payload: str) -> None:
    (tmp_path / ".mcp.json").write_text(payload, encoding="utf-8")


def test_unrelated_mcp_server_is_not_power_bi_adoption(tmp_path: Path) -> None:
    """An .mcp.json holding only a NON-Power-BI server is not adoption.

    Presence of any MCP client config said nothing about Power BI;
    `pbi_mcp.detect.classify_mcp_config` is the authority and returns `absent`
    when no Power BI-shaped server exists.
    """
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)
    _mcp_config(tmp_path, '{"mcpServers": {"docs": {"command": "docs-server"}}}')

    doc = build_orchestration_assessment(tmp_path)

    assert doc["recommendation"]["pbi_mcp"] == "consider"
    assert doc["adapters"]["pbi_mcp"]["already_present"] is False


def test_unparseable_mcp_config_is_not_adoption(tmp_path: Path) -> None:
    """A malformed .mcp.json cannot evidence adoption."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)
    _mcp_config(tmp_path, "{not json")

    doc = build_orchestration_assessment(tmp_path)

    assert doc["adapters"]["pbi_mcp"]["already_present"] is False


def test_power_bi_mcp_server_is_adoption(tmp_path: Path) -> None:
    """A real Power BI-shaped server entry IS the already-adopted signal."""
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)
    _mcp_config(
        tmp_path,
        '{"mcpServers": {"powerbi": {"command": "pbi", "args": ["--readonly"]}}}',
    )

    doc = build_orchestration_assessment(tmp_path)

    assert doc["recommendation"]["pbi_mcp"] == "already_adopted"
    assert doc["adapters"]["pbi_mcp"]["already_present"] is True


def test_state_changing_config_is_warned_about(tmp_path: Path) -> None:
    """A config requesting a state-changing mode is adopted BUT flagged.

    ADR 0018 is ratified but slice 5 is unbuilt, so a local stdio server without
    `--readonly` is worth naming as a caution -- warning about the reader's own
    config is the opposite of advertising the mode.
    """
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)
    _mcp_config(tmp_path, '{"mcpServers": {"powerbi": {"command": "pbi"}}}')

    block = build_orchestration_assessment(tmp_path)["adapters"]["pbi_mcp"]

    assert block["recommendation"] == "already_adopted"
    assert block["against"] != []
    assert "0018" in " ".join(block["against"])


def test_recommended_action_cannot_contradict_core_only(tmp_path: Path) -> None:
    """The headline must not say "nothing needed" while an adapter is advised.

    With one Gold table and no dbt/dagster the headline used to report that
    orchestration is not required, even when `core_only_sufficient` was false
    because a PBIP model made pbi_mcp `consider`.
    """
    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)

    doc = build_orchestration_assessment(tmp_path)

    assert doc["core_only_sufficient"] is False
    assert "power bi" in doc["recommended_action"].lower()


def test_text_render_shows_the_power_bi_block_and_core_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default (non-JSON) path must not hide the new verdict."""
    from seshat.cli import main

    _write_status(tmp_path, "orders", _gold_ready("orders"))
    _pbip_model(tmp_path)

    rc = main(["orchestration-assess", "--repo", str(tmp_path)])

    out = capsys.readouterr().out.lower()
    assert rc == 0
    assert "pbi_mcp" in out or "power bi" in out
    assert "core_only" in out or "core-only" in out
