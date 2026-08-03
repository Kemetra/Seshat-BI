from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.unit._report_helpers import vocabulary as _vocab

pytestmark = pytest.mark.unit

pytest.importorskip("jinja2", reason="requires the `report` extra")

_REPO = Path(__file__).parents[2]

# Minimal payloads: tagged with an embedded font, and each failing variant.
_GOOD = (
    b"%PDF-1.7\n/MarkInfo<</Marked true>>/StructTreeRoot 1 0 R\n/FontFile2 2 0 R\n%%EOF"
)
_UNTAGGED = b"%PDF-1.7\n/FontFile2 2 0 R\n%%EOF"
_NO_FONT = b"%PDF-1.7\n/MarkInfo<</Marked true>>/StructTreeRoot 1 0 R\n%%EOF"
_NOT_PDF = b"<html>nope</html>"

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
  - section_id: detail
    order: 2
    heading_code: section.detail
    visual_ids: [v3]
    page_break_before: true
"""


class FakePrinter:
    """The whole browser, for test purposes: HTML in, bytes out."""

    def __init__(self, payload: bytes = _GOOD) -> None:
        self.payload = payload
        self.pages: list[object] = []

    def print_to_pdf(self, page) -> bytes:
        self.pages.append(page)
        return self.payload


def _artifacts(tmp_path: Path):
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(_LAYOUT_TEXT, encoding="utf-8")
    layout = load_layout(path)
    observations = [
        {
            "visual_id": visual_id,
            "contract_id": "TotalSales",
            "metric": "TotalSales",
            "unit_kind": "currency",
            "label": label,
            "value": Decimal(amount),
        }
        for visual_id, label, amount in (
            ("v1", "Region A", "1552071"),
            ("v2", "Region B", "840000"),
            ("v3", "Region C", "120000"),
        )
    ]
    bundle = build_bundle(
        table="retail_store_sales",
        generated_for="board",
        design=ApprovedDesign(layout=layout, contracts={"TotalSales": "x.yaml"}),
        observations=observations,
    )
    return bundle, layout


def test_pdf_module_imports_neither_chromium_nor_playwright() -> None:
    """The browser is a port, not an import: the surface stays browser-free."""
    source = (_REPO / "src/seshat/report/pdf.py").read_text(encoding="utf-8")
    body = source.split('"""', 2)[-1]
    assert "chromium" not in body.lower()
    assert "playwright" not in body.lower()


def test_render_uses_the_injected_printer(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    surface = PdfReportRenderer(printer).render(bundle, layout, _vocab("en"))
    assert surface.pdf_bytes == _GOOD
    assert len(printer.pages) == 1


def test_printed_html_carries_the_bundle_text(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    PdfReportRenderer(printer).render(bundle, layout, _vocab("en"))
    html = str(printer.pages[0])
    assert "1,552,071.00" in html
    assert "840,000.00" in html


def test_printed_surface_extends_the_web_template(tmp_path: Path) -> None:
    """One template, two surfaces: the cover and footer come from the base."""
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    PdfReportRenderer(printer).render(bundle, layout, _vocab("en"))
    html = str(printer.pages[0])
    assert 'class="cover"' in html
    assert 'class="provenance"' in html
    assert "<!doctype html>" in html


def test_print_stylesheet_is_inlined(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    PdfReportRenderer(printer).render(bundle, layout, _vocab("en"))
    html = str(printer.pages[0])
    assert "@page" in html  # the print sheet reached the page
    assert ".figures" in html  # and so did the shared one


def test_page_break_reaches_the_marked_section(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    PdfReportRenderer(printer).render(bundle, layout, _vocab("en"))
    html = str(printer.pages[0])
    # The attribute wraps across lines in the template, so match each part.
    assert 'class="section page-break"' in html
    assert 'id="detail"' in html
    assert 'class="section"' in html
    assert 'id="overview"' in html
    # Only the section the overlay marked gets the break. Counted on the class
    # attribute, since the inlined print stylesheet also names the selector.
    assert html.count('class="section page-break"') == 1


def test_chart_macro_is_available_to_the_printed_surface(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    PdfReportRenderer(printer).render(bundle, layout, _vocab("en"))
    assert "<rect" in str(printer.pages[0])


def test_untagged_pdf_is_refused(tmp_path: Path) -> None:
    from seshat.report.model import ReportError
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    with pytest.raises(ReportError, match="no structure tree"):
        PdfReportRenderer(FakePrinter(_UNTAGGED)).render(bundle, layout, _vocab("en"))


def test_pdf_without_an_embedded_font_is_refused(tmp_path: Path) -> None:
    from seshat.report.model import ReportError
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    with pytest.raises(ReportError, match="font"):
        PdfReportRenderer(FakePrinter(_NO_FONT)).render(bundle, layout, _vocab("en"))


def test_non_pdf_bytes_are_refused(tmp_path: Path) -> None:
    from seshat.report.model import ReportError
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    with pytest.raises(ReportError, match="not a PDF"):
        PdfReportRenderer(FakePrinter(_NOT_PDF)).render(bundle, layout, _vocab("en"))


def test_missing_language_refuses_before_printing(tmp_path: Path) -> None:
    from seshat.report.html import SurfaceRenderFailed
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    with pytest.raises(SurfaceRenderFailed):
        PdfReportRenderer(printer).render(bundle, layout, _vocab("ar"))
    assert printer.pages == []  # nothing was sent to the browser


def test_chromium_adapter_reports_a_missing_browser_clearly() -> None:
    """Without the extra, the message must name the fix, not raise ImportError."""
    source = (_REPO / "src/seshat/report/chromium.py").read_text(encoding="utf-8")
    assert "seshat-bi[report-pdf]" in source
    assert "set_content" in source
    # Content is SET on the page, never navigated to, so nothing is fetched. A
    # mention in a comment is inert; only a real call would defeat this.
    assert ".goto(" not in source


def test_a_marked_false_pdf_is_refused(tmp_path: Path) -> None:
    """`/Marked false` is a printer stating it did NOT mark the content.

    Reading it as tagged accepts an inaccessible document on the strength of the
    word appearing in the bytes.
    """
    from seshat.report.model import ReportError
    from seshat.report.pdf import assert_publishable

    lying = (
        b"%PDF-1.7\n/StructTreeRoot 1 0 R\n/MarkInfo<</Marked false>>/FontFile2 2 0 R"
    )
    with pytest.raises(ReportError, match="does not declare its content marked"):
        assert_publishable(lying)


def test_a_structure_tree_alone_is_not_enough(tmp_path: Path) -> None:
    from seshat.report.model import ReportError
    from seshat.report.pdf import assert_publishable

    with pytest.raises(ReportError, match="does not declare its content marked"):
        assert_publishable(b"%PDF-1.7\n/StructTreeRoot 1 0 R\n/FontFile2 2 0 R")


def test_a_marked_flag_alone_is_not_enough() -> None:
    """The flag is a claim; the structure tree is the thing being claimed."""
    from seshat.report.model import ReportError
    from seshat.report.pdf import assert_publishable

    with pytest.raises(ReportError, match="no structure tree"):
        assert_publishable(b"%PDF-1.7\n/MarkInfo<</Marked true>>/FontFile2 2 0 R")
