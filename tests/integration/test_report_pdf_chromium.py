"""The one test that runs a real browser.

Every other PDF test drives :class:`seshat.report.pdf.PagePrinter` with a
hand-written fake, which is what makes the printed surface verifiable in a
checkout with no browser. That design has one hole: a fake can be made to return
whatever ``assert_publishable`` wants to see, so the fakes prove the *assertions*
work without ever proving that **Chromium's actual output satisfies them**.

This module closes that hole, and is skipped -- not failed -- wherever the
``report-pdf`` extra or the browser binary is absent.

**What is asserted where, and why the split is not laziness.** Chromium subsets
its embedded fonts and encodes glyph ids rather than characters, so a figure's
text is genuinely not greppable in the output bytes. Rather than take on a
PDF-parsing dependency to recover it, this module asserts each property at the
seam where it is exactly observable:

* *figure text* against the HTML handed to the browser -- the last point at which
  the surface is responsible for it, and the point a regression would appear;
* *document structure* against the produced bytes -- tags, embedded fonts,
  ``/ToUnicode`` maps, page count, and the absence of script.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

pytest.importorskip("jinja2", reason="requires the `report` extra")
pytest.importorskip("playwright.sync_api", reason="requires the `report-pdf` extra")

_REPO = Path(__file__).parents[2]
_FIXTURE = _REPO / "tests/fixtures/report/board_pack.yaml"

# What Playwright says when the package is present but the binary was never
# downloaded. Matched so that case skips, while a browser that is installed and
# genuinely failing still fails.
_NOT_INSTALLED = "executable doesn't exist"


class _SpyPrinter:
    """The real printer, plus a record of the HTML it was handed.

    Wrapping rather than replacing: the bytes below are Chromium's, and the
    captured page is the genuine input that produced them.
    """

    def __init__(self) -> None:
        from seshat.report.chromium import ChromiumPrinter

        self._printer = ChromiumPrinter()
        self.html = ""

    def print_to_pdf(self, page) -> bytes:
        self.html = page.html
        return self._printer.print_to_pdf(page)


def _artifacts(tmp_path: Path):
    from seshat.report.bundle import build_bundle
    from seshat.report.layout import load_layout

    payload = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
    layout_path = tmp_path / "report-layout.yaml"
    layout_path.write_text(
        yaml.safe_dump(payload["layout"], sort_keys=False), encoding="utf-8"
    )
    bundle = build_bundle(
        table=payload["table"],
        generated_for=payload["generated_for"],
        layout=load_layout(layout_path),
        contracts=payload["contracts"],
        observations=[
            {**entry, "value": Decimal(str(entry["value"]))}
            for entry in payload["observations"]
        ],
    )
    return bundle, load_layout(layout_path)


@pytest.fixture(scope="module")
def printed(tmp_path_factory) -> tuple[bytes, str]:
    """One real Chromium render, shared by every assertion below.

    Skipping happens here rather than at import: probing for the binary
    beforehand means opening and abandoning a driver connection, and the only
    reliable answer comes from the launch itself.
    """
    from seshat.report.model import ReportError
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path_factory.mktemp("chromium"))
    printer = _SpyPrinter()
    try:
        surface = PdfReportRenderer(printer).render(bundle, layout, "en")
    except ReportError as exc:  # pragma: no cover - environment dependent
        if _NOT_INSTALLED in str(exc).lower():
            pytest.skip("chromium is absent; run `playwright install chromium`")
        raise
    return surface.pdf_bytes, printer.html


def test_chromium_output_is_publishable(printed) -> None:
    """The assertion the fakes could only ever pretend to satisfy."""
    from seshat.report.pdf import assert_publishable

    pdf_bytes, _ = printed
    assert assert_publishable(pdf_bytes) is None
    assert pdf_bytes.startswith(b"%PDF")


def test_chromium_tags_the_document(printed) -> None:
    """Untagged, a screen reader has no structure tree and cannot read the page."""
    pdf_bytes, _ = printed
    assert b"/StructTreeRoot" in pdf_bytes
    assert b"/Marked" in pdf_bytes


def test_chromium_embeds_a_font_program(printed) -> None:
    """Without one, Arabic renders in whatever the opening machine happens to have."""
    pdf_bytes, _ = printed
    assert b"/FontFile" in pdf_bytes


def test_the_embedded_text_is_recoverable(printed) -> None:
    """A ``/ToUnicode`` map is what makes a tagged PDF's text extractable.

    Tagging alone marks structure; without this map, assistive technology reads
    subset glyph ids rather than characters.
    """
    pdf_bytes, _ = printed
    assert b"/ToUnicode" in pdf_bytes
    assert b"/Lang" in pdf_bytes


def test_the_structure_tree_carries_real_semantics(printed) -> None:
    """A heading, the section tables, and the chart with its alternative text."""
    pdf_bytes, _ = printed
    assert b"/S /H1" in pdf_bytes
    assert b"/S /Table" in pdf_bytes
    assert b"/S /Figure" in pdf_bytes
    assert b"/Alt" in pdf_bytes


def test_the_page_break_produced_more_than_one_page(printed) -> None:
    """The fixture breaks before `mix`, so a single-page output means print CSS
    never applied -- which a fake printer can never detect."""
    pdf_bytes, _ = printed
    pages = pdf_bytes.count(b"/Type /Page") + pdf_bytes.count(b"/Type/Page")
    assert pages > 1


def test_the_document_carries_no_script_and_fetches_nothing(printed) -> None:
    """`set_content` and no navigation, verified in the artifact rather than trusted."""
    pdf_bytes, _ = printed
    assert b"/JavaScript" not in pdf_bytes
    assert b"/URI" not in pdf_bytes


def test_the_figures_reached_the_browser_verbatim(printed) -> None:
    """Text correctness, asserted where it is still observable.

    These are the renderings `bundle.py` produced. Chromium subsets fonts, so this
    is the last point the surface is answerable for the characters.
    """
    _, html = printed
    for text in ("1,552,071.00", "12,575", "50.37%", "612,480.25"):
        assert text in html


def test_the_printed_page_cites_its_contracts(printed) -> None:
    _, html = printed
    assert 'data-contract="TotalSales"' in html
    assert 'data-contract="DiscountedTransactionRate"' in html


def test_the_chartable_section_was_drawn(printed) -> None:
    """`by_region` is same-unit, so geometry exists; the KPI rows stay tables."""
    _, html = printed
    assert "<svg" in html
    assert html.count("<rect") == 3
