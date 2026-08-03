"""The immutable fact package the surfaces are allowed to present.

Ported from ``Khepri/src/khepri/rra/bundle.py`` (``CitedFigure``,
``ReportBundle``). ``fact_id`` became ``contract_id``: in this kit a figure's
provenance is the APPROVED METRIC CONTRACT it came from, which is what makes
"every figure traces to an approved contract" a checkable property rather than a
convention.

``renderings`` is the point of :class:`CitedFigure`. A surface is handed the text
and may only reproduce it, so "did the workbook round this differently from the
PDF?" cannot arise -- neither of them rounded anything.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal


class ReportError(Exception):
    """Any report-surface failure. Never used to describe business meaning."""


# Reading direction. Named rather than inferred, so a surface laying out a page
# right-to-left has not done it by accident.
DIRECTION_LTR = "ltr"
DIRECTION_RTL = "rtl"

# Three chart kinds, deliberately. A fourth adds a branch to every dispatching
# function in `charts`, and each geometry function is kept at its own low
# complexity by a lookup rather than an if-chain.
CHART_BAR = "bar"
CHART_GROUPED_BAR = "grouped_bar"
CHART_LINE = "line"
GOVERNED_CHART_KINDS = frozenset({CHART_BAR, CHART_GROUPED_BAR, CHART_LINE})

# Figure labels that are governed vocabulary rather than customer text. A label in
# this set is an internal identifier the surface must translate; anything else is
# the customer's own category and is final. Treating a governed label as final put
# an English identifier on an Arabic axis in Khepri.
GOVERNED_FIGURE_LABELS = frozenset({"period_over_period", "prior_period", "budget"})


@dataclass(frozen=True, slots=True)
class BundleIdentity:
    table: str
    journey: str
    generated_for: str


@dataclass(frozen=True, slots=True)
class CitedFigure:
    figure_id: str
    citation_id: str
    contract_id: str
    metric: str
    unit_kind: str
    kind: str
    section: str
    label: str | None
    value: Decimal | None
    renderings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.figure_id:
            raise ReportError("figure_id is required")
        if not self.contract_id:
            raise ReportError(
                f"figure {self.figure_id!r} has no approved contract id; an "
                "unattributed figure refuses the render"
            )
        if not self.renderings:
            raise ReportError(
                f"figure {self.figure_id!r} carries no rendering; a surface may "
                "only reproduce text, so the text must already exist"
            )


@dataclass(frozen=True, slots=True)
class StatedCaveat:
    caveat_id: str
    section: str
    renderings: dict[str, str]


@dataclass(frozen=True, slots=True)
class ChartSpec:
    """What a chart plots, named in figure identifiers and nothing else.

    A spec carries no geometry and no values. It says which governed figures a
    chart is drawn from, so the chart inherits the contract tracing those figures
    already have instead of needing a parallel mechanism of its own.
    """

    kind: str
    figure_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind not in GOVERNED_CHART_KINDS:
            raise ReportError(
                f"chart kind {self.kind!r} is outside the governed set "
                f"{sorted(GOVERNED_CHART_KINDS)}"
            )
        if not self.figure_ids:
            raise ReportError("a chart spec must name at least one figure")


@dataclass(frozen=True, slots=True)
class Section:
    section_id: str
    order: int
    figure_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportBundle:
    identity: BundleIdentity
    figures: tuple[CitedFigure, ...]
    caveats: tuple[StatedCaveat, ...]
    sections: tuple[Section, ...]

    def __post_init__(self) -> None:
        self._require_ordered_sections()
        self._require_sections_index_the_figures()

    @property
    def section_ids(self) -> tuple[str, ...]:
        """The ordered sections this bundle declares."""
        return tuple(
            section.section_id
            for section in sorted(self.sections, key=lambda item: item.order)
        )

    def _require_ordered_sections(self) -> None:
        orders = [section.order for section in self.sections]
        if orders != sorted(orders):
            raise ReportError(f"sections are not in declared order: {orders}")

    def _require_sections_index_the_figures(self) -> None:
        known = {figure.figure_id for figure in self.figures}
        indexed: set[str] = set()
        for section in self.sections:
            for figure_id in section.figure_ids:
                if figure_id not in known:
                    raise ReportError(
                        f"section {section.section_id!r} indexes unknown figure "
                        f"{figure_id!r}"
                    )
                indexed.add(figure_id)
        orphans = sorted(known - indexed)
        if orphans:
            raise ReportError(f"figures with no declared section: {orphans}")


def declares_a_rate(contract: Mapping[str, object]) -> bool:
    """True when the contract states its aggregate IS a rate.

    The signal is the contract's explicit ``definition.expected_value.aggregation:
    ratio``, NOT the structural presence of a numerator and a denominator. The
    distinction is load-bearing and easy to get backwards:

    ``DiscountedTransactionRate`` divides one count by another and IS a rate, shown
    as ``50.37%``. ``AvgTransactionValue`` also divides -- a sum by a count -- and is
    NOT a rate: it is money per transaction, shown as ``123.42``. Reading "computed
    by division" as "displayed as a percentage" would render the average as
    ``1.23%``.

    So a contract that does not declare a rate constrains nothing here, and its
    unit_kind stays the authored one. Which unit a non-rate carries is spec 103
    FR-014, an open owner question this predicate deliberately does not answer.
    """
    definition = contract.get("definition")
    if not isinstance(definition, Mapping):
        return False
    expected = definition.get("expected_value")
    if not isinstance(expected, Mapping):
        return False
    return expected.get("aggregation") == "ratio"
