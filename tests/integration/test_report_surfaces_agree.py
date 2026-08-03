"""The invariant that makes one bundle worth having.

If a renderer ever starts formatting `CitedFigure.value` itself, there are two
places a figure is decided and a workbook can disagree with a page. The sentinel
test below makes that impossible to introduce quietly: it sets a figure's rendering
to text the `Decimal` could not produce, and asserts every surface shows the text.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from seshat.report.html import SurfaceRenderFailed
from tests.unit._report_helpers import vocabulary as _vocab

pytestmark = pytest.mark.integration

pytest.importorskip("jinja2", reason="requires the `report` extra")
pytest.importorskip("xlsxwriter", reason="requires the `report` extra")

_GOOD_PDF = (
    b"%PDF-1.7\n/MarkInfo<</Marked true>>/StructTreeRoot 1 0 R\n/FontFile2 2 0 R\n%%EOF"
)

_LAYOUT_TEXT = """\
version: 1
cover_title_code: cover.board_pack
sections:
  - section_id: headline
    order: 1
    heading_code: section.headline
    visual_ids: [v1, v2]
    page_break_before: false
    chart_kind: bar
"""


class FakePrinter:
    def __init__(self) -> None:
        self.html = ""

    def print_to_pdf(self, page) -> bytes:
        self.html = str(page)
        return _GOOD_PDF


def _artifacts(tmp_path: Path):
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
                "label": "Region A",
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


def _workbook_xml(workbook_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        return "".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
            if name.endswith(".xml")
        )


def _render_all(bundle, layout, language: str = "en") -> tuple[str, str, str]:
    from seshat.report.excel import ExcelReportRenderer
    from seshat.report.html import HtmlReportRenderer
    from seshat.report.pdf import PdfReportRenderer

    printer = FakePrinter()
    html = HtmlReportRenderer().render(bundle, layout, _vocab(language)).document
    workbook = _workbook_xml(
        ExcelReportRenderer().render(bundle, layout, _vocab(language)).workbook_bytes
    )
    PdfReportRenderer(printer).render(bundle, layout, _vocab(language))
    return html, workbook, printer.html


def test_all_three_surfaces_show_the_same_text(tmp_path: Path) -> None:
    bundle, layout = _artifacts(tmp_path)
    for document in _render_all(bundle, layout):
        assert "1,552,071.00" in document
        assert "840,000.00" in document


def test_no_surface_formats_the_decimal_itself(tmp_path: Path) -> None:
    """Make the rendering and the Decimal disagree; every surface shows the text.

    A renderer that formatted `value` would print 1,552,071.00 here and fail.
    """
    bundle, layout = _artifacts(tmp_path)
    lying = replace(bundle.figures[0], renderings={"en": "SENTINEL-42"})
    bundle = replace(bundle, figures=(lying, bundle.figures[1]))
    for document in _render_all(bundle, layout):
        assert "SENTINEL-42" in document
        assert "1,552,071.00" not in document


def test_every_surface_records_the_approved_contract(tmp_path: Path) -> None:
    bundle, layout = _artifacts(tmp_path)
    for document in _render_all(bundle, layout):
        assert "TotalSales" in document


def test_no_surface_emits_a_score_or_a_readiness_pass(tmp_path: Path) -> None:
    bundle, layout = _artifacts(tmp_path)
    for document in _render_all(bundle, layout):
        assert not re.search(
            r"\b(?:score|confidence)\s*[:=]\s*\d", document, re.IGNORECASE
        )
        assert not re.search(
            r"\b(?:readiness_)?state\s*[:=]\s*['\"]?pass", document, re.IGNORECASE
        )


def test_a_hostile_label_is_inert_in_every_surface(tmp_path: Path) -> None:
    """Escaped on the page, and non-executing in the workbook."""
    bundle, layout = _artifacts(tmp_path)
    hostile = replace(bundle.figures[0], label='=HYPERLINK("http://evil")')
    bundle = replace(bundle, figures=(hostile, bundle.figures[1]))
    html, workbook, printed = _render_all(bundle, layout)
    assert "<f>" not in workbook  # no formula cell
    assert "HYPERLINK" in workbook  # verbatim, and dead
    for page in (html, printed):
        assert "&#34;" in page or "&quot;" in page  # the quotes were escaped


def test_a_pending_figure_says_so_in_every_surface(tmp_path: Path) -> None:
    """No data source must never become an invented number, on any surface."""
    from seshat.report.bundle import PENDING, ApprovedDesign, build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(_LAYOUT_TEXT, encoding="utf-8")
    layout = load_layout(path)
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(layout=layout, contracts={"TotalSales": "x.yaml"}),
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": "Region A",
                "value": None,
            },
            {
                "visual_id": "v2",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": "Region B",
                "value": None,
            },
        ],
    )
    for document in _render_all(bundle, layout):
        assert PENDING in document
        # And no chart was drawn from values that do not exist.
        assert "<rect" not in document


# --- governed wording and required caveats ----------------------------------

_CAVEATED_LAYOUT = """\
version: 1
cover_title_code: cover.board_pack
sections:
  - section_id: headline
    order: 1
    heading_code: section.headline
    visual_ids: [v1, v2]
    page_break_before: false
    caveat_codes: [caveat.demo]
"""


def _caveated(tmp_path: Path):
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "caveated.yaml"
    path.write_text(_CAVEATED_LAYOUT, encoding="utf-8")
    layout = load_layout(path)
    bundle = build_bundle(
        table="retail_store_sales",
        generated_for="board",
        design=ApprovedDesign(layout=layout, contracts={"TotalSales": "x.yaml"}),
        observations=[
            {
                "visual_id": vid,
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": vid,
                "value": Decimal(amount),
            }
            for vid, amount in (("v1", "10"), ("v2", "20"))
        ],
    )
    return bundle, layout


def test_no_surface_displays_a_governed_code_as_visible_text(tmp_path: Path) -> None:
    """`section.headline` in a heading was the defect. The code stays as metadata."""
    bundle, layout = _caveated(tmp_path)
    html, workbook, printed = _render_all(bundle, layout)
    for page in (html, printed):
        assert 'data-code="section.headline"' in page  # metadata, kept
        assert ">section.headline<" not in page  # never the visible text
        assert ">Headline<" in page  # the resolved wording


def test_an_approved_caveat_reaches_every_surface(tmp_path: Path) -> None:
    """The binding map REQUIRES v04's caveat. A bundle that could not carry one
    published a materially misleading percentage."""
    bundle, layout = _caveated(tmp_path)
    for document in _render_all(bundle, layout):
        assert "A stated caveat." in document


def test_a_caveat_with_no_wording_refuses_rather_than_dropping_it(
    tmp_path: Path,
) -> None:
    """A silently dropped caveat is exactly the failure this closes."""
    from seshat.report.html import HtmlReportRenderer
    from seshat.report.model import ReportError
    from seshat.report.vocabulary import Vocabulary

    bundle, layout = _caveated(tmp_path)
    bare = Vocabulary(
        language="en", terms={"section.headline": "H", "cover.board_pack": "C"}
    )
    with pytest.raises((ReportError, SurfaceRenderFailed)):
        HtmlReportRenderer().render(bundle, layout, bare)
