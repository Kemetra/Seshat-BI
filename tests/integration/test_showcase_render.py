"""US1 (MVP) acceptance coverage: the showcase bundle renders truthfully,
offline, and read-only over both the real worked example and synthetic
fixtures (SC-001, SC-002, SC-008; FR-001/003/004/007/008/025/026/027)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.showcase.build import build_showcase_bundle, render_showcase_html

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO / "tests/fixtures/showcase"
_EXPLORER_ASSETS = _REPO / "src/seshat/explorer/assets"


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".seshat-output" not in path.parts
    }


def test_worked_example_renders_every_section_from_committed_evidence() -> None:
    """Independent test for US1: point the feature at the worked example
    (docs/worked-examples/retail-store-sales.md documents
    mappings/retail_store_sales/), open the bundle, and confirm every
    section is sourced from the shipped projection (SC-001)."""
    bundle = build_showcase_bundle(_REPO)
    table_ids = [table["table_id"] for table in bundle["tables"]]
    assert any("retail_store_sales" in table_id for table_id in table_ids)

    html = render_showcase_html(bundle, repo=_REPO)
    assert "retail_store_sales" in html
    assert "Metric lineage" in html
    assert "Disclosure manifest" in html
    assert "Publishing this bundle is a separate" in html
    # Self-contained: every external reference is inlined or a data URI: no
    # fetched stylesheet/script/image (the SVG xmlns attribute is not a
    # network reference).
    assert 'href="http' not in html
    assert 'src="http' not in html
    assert "data:image/svg+xml;base64," in html


def test_bundle_is_self_contained_with_no_external_fetch() -> None:
    bundle = build_showcase_bundle(_REPO)
    html = render_showcase_html(bundle, repo=_REPO)
    assert "<script>" in html and "<script src=" not in html
    assert "<style>" in html and 'rel="stylesheet"' not in html
    assert bundle["badge"]["svg"] in html


def test_all_missing_fixture_never_infers_a_pass(tmp_path: Path) -> None:
    shutil.copytree(_FIXTURES / "all_missing", tmp_path, dirs_exist_ok=True)
    bundle = build_showcase_bundle(tmp_path)
    table = bundle["tables"][0]
    assert table["table_id"] == "onboarding_candidate"
    statuses = {block["status"] for block in table["stages"].values()}
    assert statuses == {"not_started"}
    assert bundle["badge"]["passed_stage_count"] == 0
    assert "onboarding" in bundle["badge"]["label"].lower()

    html = render_showcase_html(bundle, repo=tmp_path)
    assert "No evidence recorded" in html


def test_mixed_state_fixture_shows_truthful_evidence_states(tmp_path: Path) -> None:
    shutil.copytree(_FIXTURES / "mixed_state", tmp_path, dirs_exist_ok=True)
    bundle = build_showcase_bundle(tmp_path)
    tables = {table["table_id"]: table for table in bundle["tables"]}

    orders = tables["orders"]
    source_evidence = orders["stages"]["source_ready"]["evidence"][0]
    assert source_evidence["state"] == "available"
    silver_evidence = orders["stages"]["silver_ready"]["evidence"][0]
    assert silver_evidence["state"] == "deferred"
    gold_evidence = orders["stages"]["gold_ready"]["evidence"][0]
    assert gold_evidence["state"] == "missing"

    assert "input_defect" in tables["broken_table"]

    defect_nodes = [
        node for node in bundle["lineage"]["nodes"] if node["kind"] == "input_defect"
    ]
    assert defect_nodes, "the malformed metric contract must render as a defect node"

    _assert_no_pass_without_evidence(bundle["tables"])


def _stage_pass_without_evidence(table: dict) -> str | None:
    """Return the offending "table.stage" name if any stage on this table is
    `pass` with no evidence, else ``None`` (INV-1 helper)."""
    if "input_defect" in table:
        return None
    for stage, block in table["stages"].items():
        if block["status"] == "pass" and not block["evidence"]:
            return f"{table['table_id']}.{stage}"
    return None


def _assert_no_pass_without_evidence(tables: list[dict]) -> None:
    # INV-1: no stage renders `pass` without at least one evidence item.
    offenders = [_stage_pass_without_evidence(table) for table in tables]
    offenders = [name for name in offenders if name is not None]
    assert not offenders, f"pass with no evidence: {offenders}"


def test_generation_and_rendering_write_nothing_to_source(tmp_path: Path) -> None:
    shutil.copytree(_FIXTURES / "mixed_state", tmp_path, dirs_exist_ok=True)
    before = _snapshot(tmp_path)
    explorer_before = {
        path.name: path.read_bytes() for path in _EXPLORER_ASSETS.glob("*")
    }

    bundle = build_showcase_bundle(tmp_path)
    render_showcase_html(bundle, repo=tmp_path)
    render_showcase_html(bundle, repo=tmp_path, rtl=True)

    assert _snapshot(tmp_path) == before
    explorer_after = {
        path.name: path.read_bytes() for path in _EXPLORER_ASSETS.glob("*")
    }
    assert explorer_after == explorer_before


def test_no_fabricated_score_confidence_grade_or_pass_anywhere(tmp_path: Path) -> None:
    shutil.copytree(_FIXTURES / "mixed_state", tmp_path, dirs_exist_ok=True)
    bundle = build_showcase_bundle(tmp_path)
    payload = json.dumps(bundle, default=str).lower()
    assert '"score"' not in payload
    assert '"confidence"' not in payload
    assert '"grade"' not in payload

    html = render_showcase_html(bundle, repo=tmp_path).lower()
    assert "confidence" not in html
    assert '"score"' not in html


def test_html_escapes_hostile_content(tmp_path: Path) -> None:
    shutil.copytree(_FIXTURES / "mixed_state", tmp_path, dirs_exist_ok=True)
    status = tmp_path / "mappings/orders/readiness-status.yaml"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "reconciliation report not yet produced",
            "<script>alert('x')</script> not yet produced",
        ),
        encoding="utf-8",
    )
    bundle = build_showcase_bundle(tmp_path)
    html = render_showcase_html(bundle, repo=tmp_path)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
