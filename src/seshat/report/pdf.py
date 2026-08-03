"""The tagged PDF surface of one report bundle.

Discipline ported from ``Khepri/src/khepri/rra/rendering/pdf.py`` at commit
``7a1e3fd``. Its three arguments are adopted unchanged:

**One template, two surfaces.** This module renders no page of its own. It calls
the same :func:`seshat.report.html.build_context` the web surface calls, adds a
print stylesheet to that context, and renders a template that *extends* the web
template rather than replacing it. A forked print template would be a second place
for the shared structure to drift.

**It presents figures; it never produces one.** Inherited from the web surface and
true for the same reason: the view model carries text, the arithmetic happened once
in :mod:`seshat.report.bundle`, and a ``Decimal`` this renderer could format is
never in reach.

**The browser is a port, not an import.** A browser is a large external binary
that a build, a container, or an air-gapped checkout may not have. Rendering is
therefore expressed against :class:`PagePrinter` -- one method, HTML in, PDF bytes
out -- so the whole surface is verifiable with a hand-written fake and no browser
at all. ``chromium.py`` holds the one adapter that needs Playwright, and **this
module does not import it.**

**What a PDF has to be before it is published.** A tagged, readable PDF -- and
neither property is visible in the object a renderer returns, because ``bytes`` is
``bytes``. So the bytes are inspected before a :class:`PdfSurface` can exist. An
untagged PDF carries no structure tree and is unreadable to a screen reader; a PDF
with no embedded font program renders in whatever the opening machine happens to
have, which for Arabic is frequently nothing. Both are refused here rather than
discovered by a customer.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Protocol

from jinja2 import TemplateError

from seshat.report.html import (
    STYLESHEET_NAME,
    TEMPLATE_DIRECTORY,
    TEMPLATE_PACKAGE,
    SurfaceRenderFailed,
    build_context,
    build_environment,
)
from seshat.report.layout import ReportLayout
from seshat.report.model import ReportBundle, ReportError
from seshat.report.vocabulary import Vocabulary

PDF_SURFACE_VERSION = "seshat.report.pdf.v1"
PRINT_TEMPLATE_NAME = "report.pdf.html.j2"
PRINT_STYLESHEET_NAME = "report.print.css"

# The structure tree itself. A screen reader has nothing to navigate without it,
# so this is required on its own rather than as one of a set of alternatives:
# `/Marked` is a claim, `/StructTreeRoot` is the thing being claimed.
_STRUCTURE_MARKERS = (b"/StructTreeRoot",)
# The marked-content flag, which has to be TRUE. `/Marked false` is a printer
# stating that it did NOT mark the content, and reading it as tagged would accept
# an inaccessible document on the strength of the word appearing in the bytes.
_MARKED_MARKERS = (b"/Marked true", b"/Marked  true", b"/Marked\ntrue")
# Markers an embedded font program carries, in any of the accepted forms.
_FONT_MARKERS = (b"/FontFile", b"/FontFile2", b"/FontFile3")

# Each requirement is satisfied by ANY of its markers, and its refusal says what
# the reader would have lost. Kept as data so adding a requirement is one entry
# rather than another branch in the assertion.
_REQUIREMENTS: tuple[tuple[tuple[bytes, ...], str], ...] = (
    (
        _STRUCTURE_MARKERS,
        "PDF carries no structure tree (/StructTreeRoot): a screen reader has "
        "nothing to navigate. Refusing rather than shipping it.",
    ),
    (
        _MARKED_MARKERS,
        "PDF does not declare its content marked (/Marked true): the structure "
        "tree is present but the document does not claim to use it, which is how "
        "a regressed printer produces an inaccessible PDF that looks tagged.",
    ),
    (
        _FONT_MARKERS,
        "PDF embeds no font program: it would render in whatever the opening "
        "machine happens to have, which for Arabic is frequently nothing.",
    ),
)


@dataclass(frozen=True, slots=True)
class PrintablePage:
    """The HTML a printer is asked to render, and nothing it could misread."""

    html: str
    language: str
    direction: str

    def __str__(self) -> str:
        return self.html


class PagePrinter(Protocol):
    """The single thing a browser does for this surface.

    One method, deliberately. Everything else a browser can do -- navigate,
    execute script, fetch a subresource -- is something this surface has no use for
    and would rather not have available.
    """

    def print_to_pdf(self, page: PrintablePage) -> bytes: ...


@dataclass(frozen=True, slots=True)
class PdfSurface:
    pdf_bytes: bytes
    language: str
    direction: str
    surface_version: str = PDF_SURFACE_VERSION


def _stylesheet(name: str) -> str:
    directory = resources.files(TEMPLATE_PACKAGE).joinpath(TEMPLATE_DIRECTORY)
    return directory.joinpath(name).read_text(encoding="utf-8")


def assert_publishable(pdf_bytes: bytes) -> None:
    """Refuse a PDF that a reader could not use, before it becomes a surface."""
    if not pdf_bytes.startswith(b"%PDF"):
        raise ReportError("printer returned bytes that are not a PDF")
    for markers, refusal in _REQUIREMENTS:
        if not any(marker in pdf_bytes for marker in markers):
            raise ReportError(refusal)


class PdfReportRenderer:
    """Renders the printed surface through an injected printer."""

    def __init__(self, printer: PagePrinter) -> None:
        self._printer = printer
        self._environment = build_environment()

    def render(
        self, bundle: ReportBundle, layout: ReportLayout, vocabulary: Vocabulary
    ) -> PdfSurface:
        context = build_context(bundle, layout, vocabulary)
        context["screen_stylesheet"] = _stylesheet(STYLESHEET_NAME)
        context["print_stylesheet"] = _stylesheet(PRINT_STYLESHEET_NAME)
        context["surface_version"] = PDF_SURFACE_VERSION
        try:
            template = self._environment.get_template(PRINT_TEMPLATE_NAME)
            html = template.render(**context)
        except (TemplateError, ReportError) as exc:
            raise SurfaceRenderFailed(f"PDF surface failed: {exc}") from exc
        page = PrintablePage(
            html=html,
            language=vocabulary.language,
            direction=str(context["direction"]),
        )
        pdf_bytes = self._printer.print_to_pdf(page)
        assert_publishable(pdf_bytes)
        return PdfSurface(
            pdf_bytes=pdf_bytes,
            language=vocabulary.language,
            direction=page.direction,
        )
