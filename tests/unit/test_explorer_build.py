from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.explorer.build import build_explorer_projection, render_explorer_html

pytestmark = pytest.mark.unit


def _write_table(
    root: Path,
    table: str = "orders",
    *,
    evidence: str = "evidence: [mappings/{table}/source-profile.md]",
    with_profile: bool = True,
) -> None:
    table_dir = root / "mappings" / table
    table_dir.mkdir(parents=True)
    if with_profile:
        (table_dir / "source-profile.md").write_text("profile\n", encoding="utf-8")
    (table_dir / "readiness-status.yaml").write_text(
        f"""\
table: {table}
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    {evidence.format(table=table)}
    blocking_reasons: []
  mapping_ready:
    status: blocked
    evidence: []
    blocking_reasons: [grain needs owner approval]
  silver_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  gold_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  semantic_model_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  dashboard_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  publish_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
blocking_reasons: [grain needs owner approval]
approvals:
  - stage: source_ready
    owner: Jordan Rivera (analyst)
    at: 2026-07-01
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def test_portfolio_aggregates_tables_in_stable_order(tmp_path: Path) -> None:
    _write_table(tmp_path, "zeta")
    _write_table(tmp_path, "alpha")
    projection = build_explorer_projection(tmp_path)
    assert [table["table_id"] for table in projection["tables"]] == ["alpha", "zeta"]
    assert projection["schema_version"] == "1.0"
    assert projection["disclosure"]["status"] == "pass"


def test_missing_evidence_is_explicitly_missing(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders", with_profile=False)
    projection = build_explorer_projection(tmp_path)
    evidence = projection["tables"][0]["stages"]["source_ready"]["evidence"]
    assert evidence[0]["state"] == "missing"


def test_pending_live_evidence_is_deferred_not_missing(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders", evidence='evidence: ["[PENDING LIVE PROFILE]"]')
    projection = build_explorer_projection(tmp_path)
    evidence = projection["tables"][0]["stages"]["source_ready"]["evidence"]
    assert evidence[0]["state"] == "deferred"


def test_malformed_readiness_file_is_an_input_defect_entry(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    broken = tmp_path / "mappings/broken"
    broken.mkdir(parents=True)
    (broken / "readiness-status.yaml").write_text(
        "stages: [not: valid: yaml\n", encoding="utf-8"
    )
    projection = build_explorer_projection(tmp_path)
    defects = [t for t in projection["tables"] if "input_defect" in t]
    assert len(defects) == 1
    assert defects[0]["table_id"] == "broken"
    html = render_explorer_html(projection, repo=tmp_path)
    assert "Input defect" in html


def test_no_inferred_pass_and_invariant_violations_block_disclosure(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path, "orders")
    status = tmp_path / "mappings/orders/readiness-status.yaml"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "  mapping_ready:\n    status: blocked\n    evidence: []\n"
            "    blocking_reasons: [grain needs owner approval]",
            "  mapping_ready:\n    status: pass\n    evidence: []\n"
            "    blocking_reasons: []",
        ),
        encoding="utf-8",
    )
    projection = build_explorer_projection(tmp_path)
    assert projection["disclosure"]["status"] == "blocked"
    assert any(
        finding["rule"] == "projection_pass_without_evidence"
        for finding in projection["disclosure"]["findings"]
    )


def test_approval_receipts_are_carried(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    projection = build_explorer_projection(tmp_path)
    receipt = projection["tables"][0]["approvals"][0]
    assert receipt["stage"] == "source_ready"
    assert receipt["valid_shape"] is True


def test_available_lineage_from_metric_contracts(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    metrics = tmp_path / "mappings/orders/metrics"
    metrics.mkdir()
    (metrics / "NetSales.yaml").write_text(
        'name: "NetSales"\nbinds_to:\n  gold_table: "gold.fct_orders"\n',
        encoding="utf-8",
    )
    projection = build_explorer_projection(tmp_path)
    lineage = projection["lineage"]
    kinds = {node["kind"] for node in lineage["nodes"]}
    assert kinds == {"metric_contract", "warehouse_table"}
    assert lineage["edges"][0]["relation"] == "binds_to"
    assert lineage["edges"][0]["evidence"] == "mappings/orders/metrics/NetSales.yaml"


def test_unreadable_metric_contract_is_explicit_never_inferred(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path, "orders")
    metrics = tmp_path / "mappings/orders/metrics"
    metrics.mkdir()
    (metrics / "Broken.yaml").write_text("[not: a: mapping\n", encoding="utf-8")
    projection = build_explorer_projection(tmp_path)
    assert projection["lineage"]["edges"] == []
    assert projection["lineage"]["nodes"][0]["kind"] == "input_defect"


def test_empty_workspace_renders_without_error(tmp_path: Path) -> None:
    projection = build_explorer_projection(tmp_path)
    assert projection["tables"] == []
    html = render_explorer_html(projection, repo=tmp_path)
    assert "Readiness explorer" in html
    assert "No metric lineage" in html


def test_projection_and_html_never_emit_a_score(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    projection = build_explorer_projection(tmp_path)
    payload = json.dumps(projection).lower()
    assert '"score"' not in payload
    assert '"confidence"' not in payload
    html = render_explorer_html(projection, repo=tmp_path).lower()
    assert "no readiness score" in html


def test_html_escapes_hostile_content(tmp_path: Path) -> None:
    _write_table(tmp_path, "orders")
    status = tmp_path / "mappings/orders/readiness-status.yaml"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "grain needs owner approval",
            "<script>alert('x')</script> needs approval",
        ),
        encoding="utf-8",
    )
    html = render_explorer_html(build_explorer_projection(tmp_path), repo=tmp_path)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
