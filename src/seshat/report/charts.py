"""Governed chart geometry as an exact view model.

PORTED from ``Khepri/src/khepri/rra/rendering/charts.py`` at commit ``7a1e3fd``.
Adaptation: the chart vocabulary and ``CitedFigure`` come from
:mod:`seshat.report.model`; Khepri's narrative and comparison-mode coupling is
dropped. The geometry, the ``Decimal`` discipline, and the geometry-not-markup
rule are unchanged -- they are the reviewed part, and the reasons are kept below.

**This module returns geometry, not markup.** An earlier Khepri design had it
return an SVG fragment as a ``str``, and these templates cannot render one.
``build_environment()`` sets ``autoescape=True`` unconditionally and nothing
reachable from the bundle is ever marked safe, because a page with one ``|safe``
in it has an escaping convention rather than an escaping guarantee. A
``{{ section.chart_svg }}`` holding markup reaches the reader as ``&lt;svg ...``,
so the page would display chart source as text -- on the web surface and, through
template inheritance, on the printed one.

So the boundary moves instead. This module resolves geometry to strings and a
Jinja macro writes the elements. Tags come from template source, which is trusted
because it is source; labels pass through the same autoescaping as every table
cell, which is what makes a value named ``<script>`` inert here for the same
reason it is inert there. **Nothing in this module escapes anything.**

**It invents no prose either.** ``title_code`` and ``description_code`` are
governed codes, for the same reason the coordinates are not markup: the wording a
reader sees belongs in the per-language tables the surfaces already keep. Composing
a sentence here would put untranslated English on an Arabic page. They carry the
``_code`` suffix so that inserting one straight into a ``<title>`` cannot happen
quietly -- the environment uses ``StrictUndefined``, so a template reaching for
``view.title`` raises rather than printing an identifier at a reader.

**The canvas travels with the view.** ``width`` and ``height`` are on
:class:`ChartView` because a template with ``viewBox="0 0 640 320"`` written in
literally keeps drawing to the old canvas after this module changes it, and every
mark silently overflows.

**Geometry is ``Decimal`` throughout, and becomes a string only when a mark is
built.** A float coordinate would mean binary floating point reached the surface of
a governed figure.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from seshat.report.model import (
    CHART_BAR,
    CHART_GROUPED_BAR,
    CHART_LINE,
    DIRECTION_RTL,
    GOVERNED_FIGURE_LABELS,
    ChartSpec,
    CitedFigure,
)

# One canvas for every chart in a report. Two charts drawn to different scales sit
# on one page inviting a comparison their geometry does not support.
CHART_WIDTH = Decimal(640)
CHART_HEIGHT = Decimal(320)

# The extent of a point on a line. A line's marks are drawn as areas like any
# other, because a surface renders marks uniformly; the mark's *top edge* is the
# value, the same convention a bar follows.
POINT_SIZE = Decimal(8)

# How much of its slot a bar occupies. A plain bar leaves a gap so each reads as
# its own category; a grouped bar fills the slot so neighbours read as one group.
BAR_FILL = Decimal("0.6")
GROUPED_FILL = Decimal(1)

# Places kept in a coordinate string. Four, so a quantized division never has to
# be rounded again by a renderer.
COORDINATE_PRECISION = 4

_SCALE = Decimal(1).scaleb(-COORDINATE_PRECISION)


@dataclass(frozen=True, slots=True)
class ChartLabel:
    """What a mark is called, and whether the surface must translate it.

    Two kinds of text reach an axis and they must not be confused. A bucket figure
    carries the customer's own product or branch name, which is final and only
    needs escaping. A scalar figure has no category, and its *metric* identifies
    the bar; that name is governed wording, so it is a code the surface looks up.

    A bare string could not tell those apart, and a surface guessing would either
    print ``metric.total_sales`` at a reader or run a customer's product name
    through a translation table.
    """

    value: str
    localize: bool
    x: str
    y: str


@dataclass(frozen=True, slots=True)
class ChartMark:
    """One drawn thing, addressed in canvas units as exact decimal strings."""

    x: str
    y: str
    width: str
    height: str


@dataclass(frozen=True, slots=True)
class ChartView:
    """What a macro needs to draw one chart, and nothing it could misread."""

    kind: str
    title_code: str
    description_code: str
    width: str
    height: str
    marks: tuple[ChartMark, ...]
    labels: tuple[ChartLabel, ...]
    polyline: str


@dataclass(frozen=True, slots=True)
class _Domain:
    """The value range a chart is drawn against, always including zero.

    ``zero`` is where the baseline falls from the top of the canvas, which is what
    lets a negative bar hang from it rather than being drawn as a positive one.
    """

    low: Decimal
    high: Decimal

    @property
    def span(self) -> Decimal:
        return self.high - self.low

    def offset(self, value: Decimal) -> Decimal:
        """How far below the top of the canvas this value sits."""
        return CHART_HEIGHT * (self.high - value) / self.span

    @property
    def zero(self) -> Decimal:
        return self.offset(Decimal(0))


@dataclass(frozen=True, slots=True)
class _Plot:
    """One resolved, drawable series: its values, its domain, and its direction."""

    values: tuple[Decimal, ...]
    domain: _Domain
    mirrored: bool

    @property
    def slot(self) -> Decimal:
        return CHART_WIDTH / len(self.values)


def build_chart(
    spec: ChartSpec,
    figures: tuple[CitedFigure, ...],
    *,
    direction: str,
) -> ChartView | None:
    """The geometry for one chart, or nothing when the series cannot be drawn.

    There is deliberately no ``language`` parameter: this module produces codes and
    customer values, and a parameter it does not use would imply otherwise.
    Direction stays, because mirroring is geometry.
    """
    resolved = _resolve(spec, figures)
    if resolved is None:
        return None
    plot = _plot(resolved, mirrored=direction == DIRECTION_RTL)
    if plot is None:
        return None
    marks = _GEOMETRY[spec.kind](plot)
    return ChartView(
        kind=spec.kind,
        title_code=f"chart_title.{resolved[0].section}",
        description_code=f"chart_description.{spec.kind}",
        width=_coordinate(CHART_WIDTH),
        height=_coordinate(CHART_HEIGHT),
        marks=marks,
        labels=tuple(
            _label(figure, mark) for figure, mark in zip(resolved, marks, strict=True)
        ),
        polyline=_polyline(spec.kind, marks),
    )


def _label(figure: CitedFigure, mark: ChartMark) -> ChartLabel:
    """A mark's category if it has one, otherwise the code for its metric.

    Placed under the mark it names, at the foot of the canvas. The horizontal
    centre is read off the mark, the same derivation ``_polyline`` uses, so a label
    and its bar cannot disagree about where they are.
    """
    placed = {"x": _coordinate(_centre(mark)), "y": _coordinate(CHART_HEIGHT)}
    if figure.label in GOVERNED_FIGURE_LABELS:
        # A governed label is an internal identifier, not customer text.
        return ChartLabel(value=f"label.{figure.label}", localize=True, **placed)
    if figure.label is not None:
        return ChartLabel(value=figure.label, localize=False, **placed)
    return ChartLabel(value=f"metric.{figure.metric}", localize=True, **placed)


def _resolve(
    spec: ChartSpec,
    figures: tuple[CitedFigure, ...],
) -> tuple[CitedFigure, ...] | None:
    """The spec's figures in the order it named them, or nothing if one is missing.

    Fail closed rather than skipping: a chart drawn from the figures it happened to
    find would plot a series the section never authorized, and the section's own
    text would still reconcile.
    """
    known = {figure.figure_id: figure for figure in figures}
    found = [known.get(figure_id) for figure_id in spec.figure_ids]
    if any(figure is None for figure in found):
        return None
    return tuple(figure for figure in found if figure is not None)


def _plot(resolved: tuple[CitedFigure, ...], *, mirrored: bool) -> _Plot | None:
    """A drawable series, or nothing.

    Four refusals, all silent by design. One point is a number the table states
    better. A missing value is a governed gap, and a chart may not render it as a
    zero. A domain of no width has nothing to scale by, and a flat axis implies a
    measurement it does not have.

    And mixed units, because one axis states one dimension. A count of 25 beside a
    ratio of 0.1818 scales the ratio to invisibility, and a reader sees a governed
    figure that looks like nothing at all.
    """
    if len(resolved) < 2:
        return None
    if any(figure.value is None for figure in resolved):
        return None
    if len({figure.unit_kind for figure in resolved}) != 1:
        return None
    values = tuple(figure.value for figure in resolved if figure.value is not None)
    domain = _Domain(low=min(*values, Decimal(0)), high=max(*values, Decimal(0)))
    if domain.span == 0:
        return None
    return _Plot(values=values, domain=domain, mirrored=mirrored)


def _bars(plot: _Plot) -> tuple[ChartMark, ...]:
    """One bar per value, each centred in its slot with a gap either side."""
    return _columns(plot, fill=BAR_FILL)


def _grouped_bars(plot: _Plot) -> tuple[ChartMark, ...]:
    """Bars filling their slots, so neighbours read as one group."""
    return _columns(plot, fill=GROUPED_FILL)


def _line(plot: _Plot) -> tuple[ChartMark, ...]:
    """Points at rank positions, sized so a surface drawing areas draws something.

    Zero-extent marks were the earlier design, and a consumer rendering every mark
    as a rectangle drew a curve of nothing at all. The top edge carries the value,
    as a bar's does. What joins them is ``ChartView.polyline``, because points
    alone are a scatter however they are sized.
    """
    return tuple(
        ChartMark(
            x=_coordinate(
                _mirror(plot, _rank(plot, index) - POINT_SIZE / 2, POINT_SIZE)
            ),
            y=_coordinate(plot.domain.offset(value)),
            width=_coordinate(POINT_SIZE),
            height=_coordinate(POINT_SIZE),
        )
        for index, value in enumerate(plot.values)
    )


def _rank(plot: _Plot, index: int) -> Decimal:
    """Where the kth cumulative point sits: at the rank fraction it speaks for.

    A cumulative share curve's kth point states what the top ``(k + 1) / n`` of
    ranked values hold, so that fraction is its horizontal position. Slot centres
    were the earlier placement and they shift every percentile left by half a slot.

    The last point therefore sits on the right edge and its mark is half outside
    the viewBox. That is a clipped half-dot; the alternative was a curve that
    misstated every percentile it plotted.
    """
    return CHART_WIDTH * Decimal(index + 1) / len(plot.values)


def _columns(plot: _Plot, *, fill: Decimal) -> tuple[ChartMark, ...]:
    """Rectangles rising from, or hanging beneath, the zero line."""
    width = plot.slot * fill
    return tuple(
        ChartMark(
            x=_coordinate(
                _mirror(plot, plot.slot * index + (plot.slot - width) / 2, width)
            ),
            y=_coordinate(_top(plot, value)),
            width=_coordinate(width),
            height=_coordinate(_height(plot, value)),
        )
        for index, value in enumerate(plot.values)
    )


def _top(plot: _Plot, value: Decimal) -> Decimal:
    """Where a rectangle starts: at the value if it rises, at zero if it hangs."""
    if value < 0:
        return plot.domain.zero
    return plot.domain.offset(value)


def _height(plot: _Plot, value: Decimal) -> Decimal:
    """Always positive: the distance between the value and the zero line."""
    return abs(plot.domain.zero - plot.domain.offset(value))


def _mirror(plot: _Plot, x: Decimal, width: Decimal) -> Decimal:
    """The same left edge, measured from the other side when the page reads so.

    Only the category axis mirrors. Flipping the value axis as well would render
    every proportion upside down while every number beside it stayed correct.
    """
    if plot.mirrored:
        return CHART_WIDTH - x - width
    return x


def _centre(mark: ChartMark) -> Decimal:
    """The middle of a mark's top edge: the point its value is stated at."""
    return Decimal(mark.x) + Decimal(mark.width) / 2


def _polyline(kind: str, marks: tuple[ChartMark, ...]) -> str:
    """The points a line is drawn through, or nothing for another kind.

    Read back off the marks rather than recomputed from the plot. A coordinate
    string parses to the exact ``Decimal`` it was written from, so this is
    derivation and not duplication -- there is no second calculation that could
    place a point somewhere the rectangle beside it is not.
    """
    if kind != CHART_LINE:
        return ""
    return " ".join(f"{_coordinate(_centre(mark))},{mark.y}" for mark in marks)


def _coordinate(value: Decimal) -> str:
    return str(value.quantize(_SCALE))


# Dispatch by kind rather than through an if-chain: a lookup keeps each geometry
# function at its own low complexity, where a chain would add every branch to one.
_GEOMETRY = {
    CHART_BAR: _bars,
    CHART_GROUPED_BAR: _grouped_bars,
    CHART_LINE: _line,
}
