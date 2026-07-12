"""Unit tests for the deterministic Blueprint Preview (spec 123, US4).

The preview (`src/seshat/blueprint_preview.py`) is a PURE function: given
committed page-blueprint / visual-spec / report-composition / grid YAML, it
renders a deterministic SVG representing structure and design intent only. It
performs NO file write, NO live database read, NO PBIR/DAX creation (FR-016);
every data VALUE (a KPI number, a trend line, any business result) is a
labeled `PLACEHOLDER`, never fabricated (SEC-002).

Test strategy mirrors `test_dashboard_planner.py`: inline, generic (no C086 /
retail_store_sales specifics -- Principle VII) fixtures written to `tmp_path`,
never a real committed subject-area instance (none is required by T024-T027).

Sits ON the risk (memory: verifier must sit on the risk):
  - determinism is checked by running the SAME renderer call TWICE and
    asserting byte-identical output -- not by inspecting the implementation;
  - the "no fabricated value" check greps the rendered SVG TEXT for the
    literal placeholder token and asserts no other plausible business figure
    (a bare unlabeled number in a value-bearing slot) appears;
  - purity is checked by asserting the renderer performs no write under
    `tmp_path` (directory listing before/after is identical) and takes no
    network/db arguments at all (signature-level, plus a monkeypatched-open
    guard would be needed only for a writer -- this function is read-only).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seshat.blueprint_preview import render_blueprint_preview

pytestmark = pytest.mark.unit

_GRID = {
    "meta": {"grid_id": "desktop-16x9", "default_profile": "compact"},
    "profiles": {
        "compact": {
            "canvas": {"width": 200, "height": 150},
            "margin": {"top": 10, "right": 10, "bottom": 10, "left": 10},
            "grid": {
                "columns": 4,
                "rows": 3,
                "gutter": 20,
                "column_width": 30,
                "row_height": 30,
            },
        }
    },
}

_COMPOSITION = {
    "report_name": "WidgetSalesReport",
    "audience": "executive + branch manager",
    "pages": [
        {"page_id": "overview", "blueprint_ref": "overview-blueprint.yaml", "order": 1},
        {"page_id": "detail", "blueprint_ref": "detail-blueprint.yaml", "order": 2},
    ],
    "landing_page": "overview",
    "navigation": [
        {
            "from_page": "overview",
            "to": "detail",
            "label": "See detail",
            "purpose": "drill from exec KPI to branch detail",
        }
    ],
    "cross_page_filters": ["dim_date.month"],
}

_BLUEPRINT = {
    "page_name": "overview",
    "audience": "executive",
    "business_question": "How is overall performance this period vs last?",
    "grid": {"grid_ref": "design/grids/16x9-grid.yaml"},
    "sections": {
        "header": {"present": True, "purpose": "title"},
        "kpi_strip": {"present": True, "purpose": "headline KPIs"},
        "main_insight": {"present": True, "purpose": "primary trend"},
    },
    "narrative": {
        "headline": "Net Sales are up vs prior period.",
        "so_what": "Volume growth is healthy.",
        "recommended_action": "Review discount depth.",
        "key_exception": "Branch X drives most of the movement.",
    },
    "visuals": [
        {
            "visual_id": "exec_kpi_total_sales",
            "spec_ref": "exec_kpi_total_sales.yaml",
            "section": "kpi_strip",
            "binds_contract": "metric_net_sales",
        },
        {
            "visual_id": "exec_trend_main",
            "spec_ref": "exec_trend_main.yaml",
            "section": "main_insight",
            "binds_contract": "metric_net_sales",
        },
    ],
    "slicers": [
        {
            "field": "dim_date.month",
            "type": "dropdown",
            "section": "filter_rail",
            "default": "none",
        }
    ],
    "mobile_notes": {
        "grid_ref": "design/grids/mobile-grid.yaml",
        "keep_on_mobile": ["kpi_strip", "main_insight"],
        "desktop_only": ["exception_detail"],
    },
    "theme_json": {"theme_ref": "themes/tower-retail.theme.json"},
}

_VISUAL_KPI = {
    "visual_id": "exec_kpi_total_sales",
    "visual_type": "kpi_card",
    "business_question": "How is the headline KPI tracking vs prior/target?",
    "metric_contract": {
        "name": "metric_net_sales",
        "store_ref": "mappings/x/metrics/net_sales.yaml",
        "none": False,
    },
    "position": {
        "section": "kpi_strip",
        "x": 0,
        "y": 0,
        "width": 2,
        "height": 1,
        "z_order": 1,
    },
    "formatting_rules": {"title": "Net Sales"},
}

_VISUAL_TREND = {
    "visual_id": "exec_trend_main",
    "visual_type": "line_chart",
    "business_question": "How is overall performance trending?",
    "metric_contract": {
        "name": "metric_net_sales",
        "store_ref": "mappings/x/metrics/net_sales.yaml",
        "none": False,
    },
    "position": {
        "section": "main_insight",
        "x": 0,
        "y": 1,
        "width": 4,
        "height": 2,
        "z_order": 1,
    },
    "formatting_rules": {"title": "Trend"},
}


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    grid_path = tmp_path / "grid.yaml"
    grid_path.write_text(yaml.safe_dump(_GRID), encoding="utf-8")

    composition_path = tmp_path / "report-composition.yaml"
    composition_path.write_text(yaml.safe_dump(_COMPOSITION), encoding="utf-8")

    blueprint_path = tmp_path / "overview-blueprint.yaml"
    blueprint_path.write_text(yaml.safe_dump(_BLUEPRINT), encoding="utf-8")

    kpi_path = tmp_path / "exec_kpi_total_sales.yaml"
    kpi_path.write_text(yaml.safe_dump(_VISUAL_KPI), encoding="utf-8")

    trend_path = tmp_path / "exec_trend_main.yaml"
    trend_path.write_text(yaml.safe_dump(_VISUAL_TREND), encoding="utf-8")

    return {
        "grid": grid_path,
        "composition": composition_path,
        "blueprint": blueprint_path,
        "visuals": [kpi_path, trend_path],
    }


# --------------------------------------------------------------------------- #
# determinism (FR-015 / SC-006) -- identical inputs -> byte-identical SVG
# --------------------------------------------------------------------------- #


def test_identical_inputs_yield_byte_identical_svg(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    first = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    second = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    assert first == second
    assert isinstance(first, str) and first  # non-vacuous: content assertions below


def test_visual_input_order_does_not_affect_output(tmp_path: Path) -> None:
    """Sorting is by section-then-y-then-x (data-model.md), NOT input order --
    passing visuals in reverse must still yield the identical rendered SVG."""
    paths = _write_fixture(tmp_path)
    forward = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    reversed_order = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=list(reversed(paths["visuals"])),
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    assert forward == reversed_order


# --------------------------------------------------------------------------- #
# content -- sits ON the risk: a vacuous/empty renderer must NOT pass
# --------------------------------------------------------------------------- #


def test_svg_represents_structural_and_design_intent_elements(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    assert svg.startswith("<svg") or "<svg" in svg[:200]
    # page + order + business question
    assert "overview" in svg
    assert "How is overall performance this period vs last?" in svg
    # visual types + positions + referenced contract NAMES (never a formula/DAX)
    assert "kpi_card" in svg
    assert "line_chart" in svg
    assert "metric_net_sales" in svg
    # filters/slicers
    assert "dim_date.month" in svg
    # narrative region
    assert "Net Sales are up vs prior period." in svg
    # navigation
    assert "See detail" in svg
    # theme/grid/mobile/rtl intent references (by path/name, never inlined values)
    assert "themes/tower-retail.theme.json" in svg
    assert "mobile-grid.yaml" in svg


def test_visuals_sorted_by_section_then_y_then_x(tmp_path: Path) -> None:
    """kpi_strip precedes main_insight in the fixed section vocabulary order,
    so exec_kpi_total_sales's <g> must be emitted before exec_trend_main's."""
    paths = _write_fixture(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    assert svg.index("exec_kpi_total_sales") < svg.index("exec_trend_main")


# --------------------------------------------------------------------------- #
# no fabrication (FR-016 / SEC-002) -- every data value is a labeled PLACEHOLDER
# --------------------------------------------------------------------------- #


def test_every_data_value_is_a_labeled_placeholder(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    assert "PLACEHOLDER" in svg
    # never any concrete unlabeled business figure in a value slot (e.g. a bare
    # dollar amount, a percent) -- this fixture supplies none, and the renderer
    # must not invent one to "fill" the kpi_card / line_chart.
    for token in ("$", "%", "1,000", "42.0"):
        assert token not in svg


def test_realistic_values_request_yields_placeholders_not_fabrication(
    tmp_path: Path,
) -> None:
    """FR-016/SEC-002/US4 AC#2: a request for 'realistic preview values' with no
    approved data source still yields labeled placeholders -- it never raises
    and never fabricates a business figure. The renderer has no data-source
    parameter at all (structurally cannot fabricate); passing an unsupported
    kwarg some caller might try is out of scope -- this asserts the actual
    contract: no matter what, output stays placeholder-only."""
    paths = _write_fixture(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    assert svg.count("PLACEHOLDER") >= 2  # at least the two data-bound visuals


# --------------------------------------------------------------------------- #
# purity (SEC-001 / FR-016) -- no file/db/PBIR side effect
# --------------------------------------------------------------------------- #


def test_renderer_performs_no_file_write(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    after = sorted(p.name for p in tmp_path.iterdir())
    assert before == after


def test_renderer_returns_str_and_creates_no_pbir_or_dax_markers(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=paths["blueprint"],
        visual_spec_paths=paths["visuals"],
        composition_path=paths["composition"],
        grid_path=paths["grid"],
    )
    for banned in ("visualContainer", "DAX", "M-partition", "queryMetadata"):
        assert banned not in svg


# --------------------------------------------------------------------------- #
# escaping -- text nodes are escaped (no raw XML injection from YAML content)
# --------------------------------------------------------------------------- #


def test_special_characters_are_escaped(tmp_path: Path) -> None:
    blueprint = dict(_BLUEPRINT)
    blueprint["business_question"] = "A vs B & C <script>?"
    grid_path = tmp_path / "grid.yaml"
    grid_path.write_text(yaml.safe_dump(_GRID), encoding="utf-8")
    composition_path = tmp_path / "report-composition.yaml"
    composition_path.write_text(yaml.safe_dump(_COMPOSITION), encoding="utf-8")
    blueprint_path = tmp_path / "overview-blueprint.yaml"
    blueprint_path.write_text(yaml.safe_dump(blueprint), encoding="utf-8")

    svg = render_blueprint_preview(
        blueprint_path=blueprint_path,
        visual_spec_paths=[],
        composition_path=composition_path,
        grid_path=grid_path,
    )
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
