"""The one place a report's arithmetic and formatting happen.

Every surface downstream transcribes :attr:`CitedFigure.renderings`. That is why
this module exists: a figure is computed and formatted exactly once, so a workbook
and a PDF cannot round the same number differently -- neither of them rounds
anything.

``observations`` is the seam Increment B replaces with a gold query. Its shape does
not change when that happens, which is the point of putting the seam here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from seshat.report.layout import ReportLayout
from seshat.report.model import (
    BundleIdentity,
    CitedFigure,
    ReportBundle,
    ReportError,
    Section,
    declares_a_rate,
)

UNIT_KINDS = ("currency", "count", "ratio")

# What a figure slot says when no data source was reachable. Never a number:
# a document with invented figures is worse than a document with none.
PENDING = "[PENDING LIVE DATA]"

_CENTS = Decimal("0.01")


def render_value(value: Decimal, unit_kind: str) -> str:
    """The single formatting rule. Surfaces reproduce this string verbatim."""
    if unit_kind not in UNIT_KINDS:
        raise ReportError(
            f"unknown unit_kind {unit_kind!r}; expected one of {list(UNIT_KINDS)}"
        )
    if unit_kind == "currency":
        return f"{value.quantize(_CENTS, rounding=ROUND_HALF_UP):,}"
    if unit_kind == "count":
        return f"{value.quantize(Decimal(1), rounding=ROUND_HALF_UP):,}"
    percent = (value * 100).quantize(_CENTS, rounding=ROUND_HALF_UP)
    return f"{percent}%"


@dataclass(frozen=True, slots=True)
class ApprovedDesign:
    """What an owner approved, travelling together.

    The overlay says what appears and in what order, the contracts say what a
    figure is allowed to cite, the bindings say WHICH contract each visual cites,
    and the definitions say what kind of quantity each contract is. They are one
    argument because they are one decision, and a bundle built from some of them is
    not built from an approved design.

    ``bindings`` and ``definitions`` are optional so a caller with neither still
    gets the older, weaker guarantees rather than a crash -- but their absence
    costs something specific, named at each use below.
    """

    layout: ReportLayout
    contracts: Mapping[str, str]
    # visual_id -> the ONE contract the design review bound it to.
    bindings: Mapping[str, str] | None = None
    # contract_id -> its parsed contract, for the facts a figure must not restate.
    definitions: Mapping[str, Mapping[str, object]] | None = None


def build_bundle(
    *,
    table: str,
    generated_for: str,
    design: ApprovedDesign,
    observations: Sequence[Mapping[str, object]],
) -> ReportBundle:
    """Compute and format every figure once, then freeze it."""
    layout = design.layout
    declared = {
        visual_id: section.section_id
        for section in layout.sections
        for visual_id in section.visual_ids
    }
    entries = _complete(observations, declared, design)
    figures = tuple(
        _figure(entry, declared=declared, design=design) for entry in entries
    )
    sections = tuple(
        Section(
            section_id=section.section_id,
            order=section.order,
            figure_ids=tuple(
                figure.figure_id
                for figure in figures
                if figure.section == section.section_id
            ),
        )
        for section in layout.sections
    )
    return ReportBundle(
        identity=BundleIdentity(
            table=table, journey="report", generated_for=generated_for
        ),
        figures=figures,
        caveats=(),
        sections=sections,
    )


def _complete(
    observations: Sequence[Mapping[str, object]],
    declared: Mapping[str, str],
    design: ApprovedDesign,
) -> list[Mapping[str, object]]:
    """Exactly one entry per declared visual, or a refusal.

    Two failures this closes, both silent before:

    A repeated ``visual_id`` produced two conflicting figures, and the surfaces
    index figures by id, so whichever came last won and the other vanished. A
    duplicated query row could publish the wrong governed number with nothing
    refusing.

    An OMITTED visual simply did not appear, so a partial observations file
    rendered an apparently complete board pack with approved KPIs missing. Where
    the governed bindings are available each omission becomes an explicit
    ``[PENDING LIVE DATA]`` figure -- the visual is on the page, stating that its
    number is not. Without bindings there is no approved contract to attribute such
    a figure to, so the omission refuses instead.
    """
    seen = _one_entry_per_visual(observations)
    missing = [visual_id for visual_id in declared if visual_id not in seen]
    if not missing:
        return list(observations)
    if design.bindings is None:
        raise ReportError(
            f"the layout declares {sorted(missing)} but no figure was supplied for "
            "them, and no approved binding map was available to mark them pending. A "
            "partial report would look complete with approved KPIs missing -- supply "
            "them, or remove them from the overlay."
        )
    return list(observations) + [_pending(visual_id, design) for visual_id in missing]


def _one_entry_per_visual(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, Mapping[str, object]]:
    """The observations keyed by visual, refusing a repeat rather than keeping one."""
    seen: dict[str, Mapping[str, object]] = {}
    for entry in observations:
        visual_id = _text(entry, "visual_id")
        if visual_id in seen:
            raise ReportError(
                f"visual {visual_id!r} is observed more than once. Every surface "
                "indexes figures by id, so one of these would silently replace the "
                "other and publish the wrong governed number."
            )
        seen[visual_id] = entry
    return seen


def _pending(visual_id: str, design: ApprovedDesign) -> Mapping[str, object]:
    """A declared visual nobody observed, stated as pending rather than dropped.

    ``unit_kind`` is never consulted: a figure with no value renders as
    :data:`PENDING`, and every chart refuses a series containing one.
    """
    bindings = design.bindings or {}
    contract_id = bindings.get(visual_id)
    if contract_id is None:
        raise ReportError(
            f"visual {visual_id!r} was not observed and the approved binding map does "
            "not bind it, so there is no contract to attribute a pending figure to"
        )
    return {
        "visual_id": visual_id,
        "contract_id": contract_id,
        "unit_kind": "count",
        "label": None,
        "value": None,
    }


def _figure(
    entry: Mapping[str, object],
    *,
    declared: Mapping[str, str],
    design: ApprovedDesign,
) -> CitedFigure:
    visual_id = _text(entry, "visual_id")
    contract_id = _text(entry, "contract_id")
    _assert_attributable(visual_id, contract_id, declared=declared, design=design)
    unit_kind = _governed_unit_kind(entry, contract_id, design)
    value = _exact_value(entry)
    return CitedFigure(
        figure_id=visual_id,
        citation_id=f"{contract_id}#{visual_id}",
        contract_id=contract_id,
        metric=_governed_metric(entry, contract_id, design),
        unit_kind=unit_kind or "count",
        kind="total",
        section=declared[visual_id],
        label=_label(entry),
        value=value,
        renderings={"en": _rendering(value, unit_kind)},
    )


def _assert_attributable(
    visual_id: str,
    contract_id: str,
    *,
    declared: Mapping[str, str],
    design: ApprovedDesign,
) -> None:
    """A figure has to be asked for, attributable, and attributed CORRECTLY."""
    if visual_id not in declared:
        raise ReportError(
            f"observation for visual {visual_id!r} is not in the layout; the "
            "overlay decides what appears"
        )
    if contract_id not in design.contracts:
        raise ReportError(
            f"visual {visual_id!r} cites {contract_id!r}, which is not an approved "
            "contract; an unattributed figure refuses the render"
        )
    _assert_the_signed_pair(visual_id, contract_id, design)


def _assert_the_signed_pair(
    visual_id: str, contract_id: str, design: ApprovedDesign
) -> None:
    """The exact visual-to-contract pair the design review signed off.

    Membership alone let a TotalSales visual be populated and labelled as
    TotalQuantity while still advertising governed provenance. A visual the map does
    not bind (or no map at all) keeps the older, weaker membership guarantee.
    """
    governed = (design.bindings or {}).get(visual_id)
    if governed is None or governed == contract_id:
        return
    raise ReportError(
        f"visual {visual_id!r} cites {contract_id!r}, but the approved binding "
        f"map binds it to {governed!r}. Citing SOME approved contract is not the "
        "same as citing the one this visual was signed off against."
    )


def _governed_metric(
    entry: Mapping[str, object], contract_id: str, design: ApprovedDesign
) -> str:
    """The metric name, taken from the contract rather than from the observation.

    An observation could previously name any metric it liked beside a correct
    contract id, so a figure could be labelled as measuring something it did not.
    """
    contract = (design.definitions or {}).get(contract_id)
    if isinstance(contract, Mapping):
        name = contract.get("name")
        if isinstance(name, str) and name:
            return name
    return _text(entry, "metric") or contract_id


def _governed_unit_kind(
    entry: Mapping[str, object], contract_id: str, design: ApprovedDesign
) -> str:
    """The declared unit kind, with the one fact the contract can settle enforced.

    A ratio rendered as a total, or a total rendered as a ratio, is wrong by orders
    of magnitude: a `TotalSales` observation declaring `unit_kind: ratio` published
    `155207100.00%` while still citing an approved contract.

    Only the ratio axis is derivable. Whether a base aggregate is currency or a
    count depends on the source-map's declared unit, and how to treat an undeclared
    one is spec 103 FR-014 -- an open owner question this module must not settle.
    """
    declared = _text(entry, "unit_kind")
    contract = (design.definitions or {}).get(contract_id)
    if isinstance(contract, Mapping):
        _assert_the_ratio_axis_agrees(declared, entry, contract_id, contract)
    return declared


def _assert_the_ratio_axis_agrees(
    declared: str,
    entry: Mapping[str, object],
    contract_id: str,
    contract: Mapping[str, object],
) -> None:
    """Rate or not, checked against the contract's own declaration."""
    is_rate = declares_a_rate(contract)
    if is_rate and declared != "ratio":
        raise ReportError(
            f"visual {_text(entry, 'visual_id')!r} declares unit_kind {declared!r}, "
            f"but {contract_id!r} declares itself a rate; rendering a rate as a total "
            "misstates it by orders of magnitude"
        )
    if declared == "ratio" and not is_rate:
        raise ReportError(
            f"visual {_text(entry, 'visual_id')!r} declares unit_kind 'ratio', but "
            f"{contract_id!r} does not declare itself a rate; its value would be "
            "multiplied by 100 and shown as a percentage"
        )


def _text(entry: Mapping[str, object], key: str) -> str:
    return str(entry.get(key) or "")


def _exact_value(entry: Mapping[str, object]) -> Decimal | None:
    """Only an exact ``Decimal`` counts as data.

    Anything else -- a float that already lost precision, a string, a missing key
    -- reads as no observation, which renders as :data:`PENDING` rather than a
    number nobody computed.
    """
    raw = entry.get("value")
    return raw if isinstance(raw, Decimal) else None


def _label(entry: Mapping[str, object]) -> str | None:
    label = entry.get("label")
    return label if isinstance(label, str) else None


def _rendering(value: Decimal | None, unit_kind: str) -> str:
    return PENDING if value is None else render_value(value, unit_kind)
