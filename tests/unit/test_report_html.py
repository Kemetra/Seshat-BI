from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

pytest.importorskip("jinja2", reason="requires the `report` extra")

_REPO = Path(__file__).parents[2]

_LAYOUT_TEXT = """\
version: 1
cover_title_code: cover.board_pack
sections:
  - section_id: overview
    order: 1
    heading_code: section.overview
    visual_ids: [v1, v2]
    page_break_before: false
    chart_kind: bar
"""


def _artifacts(tmp_path: Path, label: str = "Region A"):
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(_LAYOUT_TEXT, encoding="utf-8")
    layout = load_layout(path)
    bundle = build_bundle(
        table="retail_store_sales",
        generated_for="board",
        design=ApprovedDesign(layout=layout, contracts={"TotalSales": "x.yaml"}),
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": label,
                "value": Decimal("1552071"),
            },
            {
                "visual_id": "v2",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": "Region B",
                "value": Decimal("840000"),
            },
        ],
    )
    return bundle, layout


def test_environment_escapes_and_is_strict() -> None:
    from jinja2 import StrictUndefined

    from seshat.report.html import build_environment

    env = build_environment()
    assert env.autoescape is True
    assert env.undefined is StrictUndefined


def test_document_reproduces_the_bundle_text(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path)
    surface = HtmlReportRenderer().render(bundle, layout, "en")
    assert "1,552,071.00" in surface.document
    assert "840,000.00" in surface.document


def test_each_figure_cites_its_contract(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path)
    document = HtmlReportRenderer().render(bundle, layout, "en").document
    assert document.count('data-contract="TotalSales"') == 2


def test_hostile_label_is_escaped(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path, label="<script>alert(1)</script>")
    document = HtmlReportRenderer().render(bundle, layout, "en").document
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document


def test_hostile_chart_axis_label_is_escaped(tmp_path: Path) -> None:
    """A chart's labels are customer values and escape like any table cell."""
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path, label="<script>x</script>")
    document = HtmlReportRenderer().render(bundle, layout, "en").document
    assert "<svg" in document  # the macro did write elements
    assert "<script>x</script>" not in document


def test_the_chart_macro_writes_elements(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path)
    document = HtmlReportRenderer().render(bundle, layout, "en").document
    assert "<rect" in document
    assert 'viewBox="0 0 640.0000 320.0000"' in document


def test_no_safe_filter_or_markup_in_any_template() -> None:
    """One |safe makes escaping a convention rather than a guarantee.

    Jinja comments are stripped first: a comment explaining the rule is inert,
    and only real usage would defeat the escaping.
    """
    import re

    templates = _REPO / "src/seshat/report/templates"
    found = list(templates.glob("*.j2"))
    assert found, "no templates to scan"
    for template in found:
        text = re.sub(
            r"\{#.*?#\}", "", template.read_text(encoding="utf-8"), flags=re.S
        )
        assert "|safe" not in text, template.name
        assert "| safe" not in text, template.name
        assert "Markup(" not in text, template.name


def test_no_surface_module_imports_markup() -> None:
    package = _REPO / "src/seshat/report"
    for module in package.glob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "Markup" not in text, module.name


def test_renderer_refuses_a_missing_language(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer, SurfaceRenderFailed

    bundle, layout = _artifacts(tmp_path)
    with pytest.raises(SurfaceRenderFailed, match="rendering"):
        HtmlReportRenderer().render(bundle, layout, "ar")


def test_direction_follows_the_language() -> None:
    from seshat.report.html import direction_for

    assert direction_for("en") == "ltr"
    assert direction_for("ar") == "rtl"


def test_section_without_a_chart_kind_renders_tables_only(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer
    from seshat.report.layout import load_layout

    bundle, _ = _artifacts(tmp_path)
    plain = tmp_path / "plain.yaml"
    plain.write_text(
        _LAYOUT_TEXT.replace("    chart_kind: bar\n", ""), encoding="utf-8"
    )
    document = HtmlReportRenderer().render(bundle, load_layout(plain), "en").document
    assert "<svg" not in document
    assert "1,552,071.00" in document


def test_two_charts_get_distinct_accessible_titles(tmp_path: Path) -> None:
    """A shared `title-bar` id makes every aria-labelledby resolve to the first
    chart, so a screen reader announces the wrong name for the rest."""
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.html import HtmlReportRenderer
    from seshat.report.layout import load_layout

    path = tmp_path / "layout.yaml"
    path.write_text(
        """\
version: 1
cover_title_code: cover.x
sections:
  - section_id: first
    order: 1
    heading_code: section.first
    visual_ids: [a1, a2]
    page_break_before: false
    chart_kind: bar
  - section_id: second
    order: 2
    heading_code: section.second
    visual_ids: [b1, b2]
    page_break_before: false
    chart_kind: bar
""",
        encoding="utf-8",
    )
    layout = load_layout(path)
    observations = [
        {
            "visual_id": vid,
            "contract_id": "TotalSales",
            "metric": "TotalSales",
            "unit_kind": "currency",
            "label": vid,
            "value": Decimal(amount),
        }
        for vid, amount in (("a1", "10"), ("a2", "20"), ("b1", "30"), ("b2", "40"))
    ]
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(layout=layout, contracts={"TotalSales": "x.yaml"}),
        observations=observations,
    )
    document = HtmlReportRenderer().render(bundle, layout, "en").document
    assert 'id="title-first"' in document
    assert 'id="title-second"' in document
    assert document.count('aria-labelledby="title-first"') == 1
    assert "title-bar" not in document
