"""The HTML surface: a page that only transcribes a bundle.

Not a line-for-line port. Khepri's ``rendering/html.py`` is largely its narrative,
reconciliation and bilingual chrome, none of which has a counterpart here, so what
is adopted is the set of rules that surface's own docstrings argue for -- and those
rules are load-bearing:

**Escaping is a guarantee, not a convention.** ``build_environment()`` sets
``autoescape=True`` and ``undefined=StrictUndefined`` unconditionally, and nothing
reachable from the bundle is ever marked safe. One ``|safe`` on the path that
customer-derived labels travel would turn the guarantee into a habit. That is also
why :mod:`seshat.report.charts` returns geometry rather than markup: a chart's axis
labels *are* customer values, so they escape exactly like a table cell, and the
elements are written by a macro from trusted template source.

**A surface reproduces text; it never formats a number.** Every cell is
``figure.renderings[language]``. ``CitedFigure.value`` is deliberately not read
here -- a surface that formatted it would be a second place a figure is decided,
and a workbook and a page could then disagree.

**A missing language refuses rather than falls back.** Falling back to English
would put untranslated text on a page while every number beside it looked correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError

from seshat.report.charts import ChartView, build_chart
from seshat.report.layout import ReportLayout
from seshat.report.model import (
    DIRECTION_LTR,
    DIRECTION_RTL,
    ChartSpec,
    CitedFigure,
    ReportBundle,
    ReportError,
)
from seshat.report.vocabulary import Vocabulary

HTML_SURFACE_VERSION = "seshat.report.html.v1"
TEMPLATE_PACKAGE = "seshat.report"
TEMPLATE_DIRECTORY = "templates"
TEMPLATE_NAME = "report.html.j2"
STYLESHEET_NAME = "report.css"

# Languages whose pages read right to left. Named, so a surface laying out a page
# that way has not done it by accident.
_RTL_LANGUAGES = frozenset({"ar", "he", "fa", "ur"})


class SurfaceRenderFailed(RuntimeError):
    """The surface could not be produced. No partial page is ever returned."""


@dataclass(frozen=True, slots=True)
class FigureCell:
    """One cell: the text a reader sees and the contract it came from."""

    figure_id: str
    contract_id: str
    label: str | None
    text: str


@dataclass(frozen=True, slots=True)
class SectionView:
    section_id: str
    heading_code: str
    # The resolved wording a reader sees. The code stays alongside it as metadata,
    # because a surface that displayed the code was the defect this closes.
    heading: str
    page_break_before: bool
    cells: tuple[FigureCell, ...]
    chart: ChartView | None
    # Approved caveats for this section, already resolved. A section whose caveat
    # cannot reach the page publishes a materially misleading figure.
    caveats: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HtmlSurface:
    document: str
    language: str
    direction: str
    surface_version: str = HTML_SURFACE_VERSION


def build_environment() -> Environment:
    """The one environment. Autoescaping and strict undefined are not options."""
    return Environment(
        loader=PackageLoader(TEMPLATE_PACKAGE, TEMPLATE_DIRECTORY),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def direction_for(language: str) -> str:
    return DIRECTION_RTL if language in _RTL_LANGUAGES else DIRECTION_LTR


def _cell(figure: CitedFigure, language: str) -> FigureCell:
    try:
        text = figure.renderings[language]
    except KeyError as exc:
        raise SurfaceRenderFailed(
            f"figure {figure.figure_id!r} has no {language!r} rendering; a surface "
            "may only reproduce text, and falling back to another language would "
            "put untranslated text beside correct numbers"
        ) from exc
    return FigureCell(
        figure_id=figure.figure_id,
        contract_id=figure.contract_id,
        label=figure.label,
        text=text,
    )


def build_cells(bundle: ReportBundle, language: str) -> tuple[FigureCell, ...]:
    return tuple(_cell(figure, language) for figure in bundle.figures)


def build_sections(
    bundle: ReportBundle, layout: ReportLayout, vocabulary: Vocabulary
) -> tuple[SectionView, ...]:
    """The sections a surface renders, with every governed code already resolved.

    ``vocabulary`` carries the language, so there is one place the answer to "which
    language is this?" comes from rather than two that could disagree.
    """
    language = vocabulary.language
    by_id = {figure.figure_id: figure for figure in bundle.figures}
    direction = direction_for(language)
    views: list[SectionView] = []
    for section in layout.sections:
        figures = tuple(
            by_id[visual_id] for visual_id in section.visual_ids if visual_id in by_id
        )
        views.append(
            SectionView(
                section_id=section.section_id,
                heading_code=section.heading_code,
                heading=vocabulary.text(section.heading_code),
                page_break_before=section.page_break_before,
                cells=tuple(_cell(figure, language) for figure in figures),
                chart=_chart_of(section, figures, direction),
                caveats=tuple(vocabulary.text(code) for code in section.caveat_codes),
            )
        )
    return tuple(views)


def _chart_of(section, figures, direction: str) -> ChartView | None:
    """The section's chart, or nothing when it declared no form.

    `charts.build_chart` decides on its own whether the series is drawable, and
    returns None rather than a misleading picture.
    """
    if section.chart_kind is None or not figures:
        return None
    spec = ChartSpec(
        kind=section.chart_kind,
        figure_ids=tuple(figure.figure_id for figure in figures),
    )
    return build_chart(spec, figures, direction=direction)


def read_stylesheet(name: str) -> str:
    """A stylesheet from this package's own template directory.

    Inlined rather than linked so the document is a single file an adopter can
    email or open offline. The source is package data, not bundle content.
    """
    directory = resources.files(TEMPLATE_PACKAGE).joinpath(TEMPLATE_DIRECTORY)
    return directory.joinpath(name).read_text(encoding="utf-8")


def build_context(
    bundle: ReportBundle, layout: ReportLayout, vocabulary: Vocabulary
) -> dict[str, object]:
    return {
        "language": vocabulary.language,
        "direction": direction_for(vocabulary.language),
        "cover_title_code": layout.cover_title_code,
        "cover_title": vocabulary.text(layout.cover_title_code),
        "table": bundle.identity.table,
        "generated_for": bundle.identity.generated_for,
        "sections": build_sections(bundle, layout, vocabulary),
        "screen_stylesheet": read_stylesheet(STYLESHEET_NAME),
        "surface_version": HTML_SURFACE_VERSION,
    }


class HtmlReportRenderer:
    """Renders the web surface. Holds no state between renders."""

    def __init__(self, environment: Environment | None = None) -> None:
        self._environment = environment or build_environment()

    def render(
        self, bundle: ReportBundle, layout: ReportLayout, vocabulary: Vocabulary
    ) -> HtmlSurface:
        context = build_context(bundle, layout, vocabulary)
        try:
            template = self._environment.get_template(TEMPLATE_NAME)
            document = template.render(**context)
        except (TemplateError, ReportError) as exc:
            raise SurfaceRenderFailed(f"HTML surface failed: {exc}") from exc
        return HtmlSurface(
            document=document,
            language=vocabulary.language,
            direction=str(context["direction"]),
        )
