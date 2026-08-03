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

from dataclasses import dataclass, field
from decimal import Decimal


class ReportError(Exception):
    """Any report-surface failure. Never used to describe business meaning."""


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
