"""The one adapter that needs a browser.

Isolated here on purpose. :mod:`seshat.report.pdf` expresses the whole printed
surface against its ``PagePrinter`` protocol and imports nothing from this module,
so the surface is verifiable with a hand-written fake and no browser at all. Only
an operator actually producing a PDF reaches this file, and only they need the
``report-pdf`` extra installed.

Ported in spirit from ``Khepri/src/khepri/rra/rendering/chromium.py`` at commit
``7a1e3fd``: content is set on the page rather than navigated to, so the browser
fetches nothing, and JavaScript is never executed.
"""

from __future__ import annotations

from seshat.report.model import ReportError
from seshat.report.pdf import PagePrinter, PrintablePage

# A4 at the print stylesheet's margins. Set here rather than in CSS because the
# browser owns the paper, and a page box in two places drifts.
_PDF_OPTIONS = {
    "format": "A4",
    "print_background": True,
    "prefer_css_page_size": True,
    "tagged": True,
}


class ChromiumPrinter:
    """Prints a page with headless Chromium, fetching nothing.

    ``tagged=True`` is what makes the output pass
    :func:`seshat.report.pdf.assert_publishable`; the assertion stays in ``pdf.py``
    regardless, because a printer claiming to have tagged its output is not
    evidence that it did.
    """

    def __init__(self, *, timeout_ms: int = 30_000) -> None:
        self._timeout_ms = timeout_ms

    def print_to_pdf(self, page: PrintablePage) -> bytes:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - exercised by the CLI path
            raise ReportError(
                "PDF output needs a browser. Install the extra with "
                '`pip install "seshat-bi[report-pdf]"` and then '
                "`playwright install chromium`. HTML and Excel need no browser."
            ) from exc
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    tab = browser.new_page()
                    # set_content, never goto: nothing is fetched from anywhere.
                    tab.set_content(page.html, timeout=self._timeout_ms)
                    tab.emulate_media(media="print")
                    return tab.pdf(**_PDF_OPTIONS)
                finally:
                    browser.close()
        except Exception as exc:  # pragma: no cover - needs a real browser
            raise ReportError(f"Chromium could not print the page: {exc}") from exc


def build_printer() -> PagePrinter:
    return ChromiumPrinter()
