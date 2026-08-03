# Report Surfaces — Increment A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render one governed report as HTML, Excel and PDF from a single bundle, where every figure traces to an approved metric contract and no renderer performs arithmetic.

**Architecture:** A Seshat-side `bundle.py` computes each figure once from approved metric contracts and pre-renders its display text; `view.py`, `charts.py`, `html.py`, `excel.py` and `pdf.py` transcribe those strings and never touch a `Decimal`. The rendering layer is a **port** of `Khepri/src/khepri/rra/rendering/`, whose decisions this repo adopts wholesale; the new work is the bundle, the contract-tracing invariant, and the print overlay.

**Tech Stack:** Python 3.13, `jinja2`, `xlsxwriter`, `playwright` (optional extras only), stdlib `Decimal`, `pytest` markers `unit` / `integration`.

**Spec:** `docs/superpowers/specs/2026-08-03-report-surfaces-design.md`

## Global Constraints

- **Base install keeps `pyyaml` as its only runtime dependency.** New libraries go in extras: `report` = `jinja2` + `xlsxwriter`; `report-pdf` = `playwright`. Follow the existing `db` / `stats` / `files` pattern in `pyproject.toml`.
- **Renderers never compute.** The view model carries strings. A `Decimal` must not be reachable from any surface module.
- **No `|safe`, no `Markup`, ever, on a bundle-reachable path.** `build_environment()` sets `autoescape=True` and `undefined=StrictUndefined` unconditionally.
- **Chart geometry is `Decimal`**, stringified only when a mark is built. `COORDINATE_PRECISION = 4`.
- **No fabricated status or score** in any surface (hard rule #9).
- **Every figure carries an approved contract id** or the render refuses.
- **Excel:** every cell via `write_string`; no numeric cells; formula/URL/number coercion disabled.
- **PDF:** tagged with embedded fonts, or refused.
- **Ported files carry a provenance header** naming the Khepri source path and commit.
- **ASCII-only in printed output** (`[OK]`, `[FAIL]`) — Windows `charmap`.
- **File size:** 200–400 lines typical, 800 hard max.
- **Every test module** sets `pytestmark = pytest.mark.unit` (or `integration`).
- **Commit style:** `<type>: <description>`, types `feat|fix|refactor|docs|test|chore|perf|ci`.

## Port map

Khepri commit for every provenance header: run `git -C ../Khepri rev-parse --short HEAD` once and reuse that value.

| Khepri source | Seshat destination | Adaptation |
|---|---|---|
| `rra/bundle.py` (`CitedFigure`, `ReportBundle` only) | `src/seshat/report/model.py` | Keep field names. `fact_id` becomes the **approved contract id**. Drop `narrative`, `NarrativeDraft`, benchmark/telemetry concerns. |
| `rra/rendering/charts.py` | `src/seshat/report/charts.py` | Imports `CitedFigure` from `..report.model`. Otherwise unchanged. |
| `rra/rendering/html.py` | `src/seshat/report/html.py` | `TEMPLATE_PACKAGE = "seshat.report"`. Drop narrative passages. |
| `rra/rendering/excel.py` | `src/seshat/report/excel.py` | Unchanged apart from imports. |
| `rra/rendering/pdf.py` | `src/seshat/report/pdf.py` | Unchanged apart from imports. |
| `rra/rendering/chromium.py` | `src/seshat/report/chromium.py` | Unchanged. |
| `rra/rendering/fonts.py` + `typefaces/` | `src/seshat/report/fonts.py` + `typefaces/` | Unchanged. |
| `rra/rendering/templates/*` | `src/seshat/report/templates/*` | Remove narrative blocks; keep the chart macro, print CSS and page box. |

New, with no Khepri counterpart: `bundle.py` (contract-traced figure construction), `layout.py` + `templates/report-layout.yaml`, `cli/commands/report.py`.

---

### Task 1: Bundle model with contract tracing

**Files:**
- Create: `src/seshat/report/__init__.py`
- Create: `src/seshat/report/model.py`
- Test: `tests/unit/test_report_model.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ReportError(Exception)`; frozen slotted `CitedFigure(figure_id: str, citation_id: str, contract_id: str, metric: str, unit_kind: str, kind: str, section: str, label: str | None, value: Decimal | None, renderings: dict[str, str])`; frozen slotted `BundleIdentity(table: str, journey: str, generated_for: str)`; frozen slotted `StatedCaveat(caveat_id: str, section: str, renderings: dict[str, str])`; frozen slotted `Section(section_id: str, order: int, figure_ids: tuple[str, ...])`; frozen slotted `ReportBundle(identity, figures, caveats, sections)` with `section_ids` property.

`contract_id` replaces Khepri's `fact_id`: it is the approved metric contract a figure came from, and it is what makes invariant 5 checkable.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_report_model.py
from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.report.model import (
    BundleIdentity,
    CitedFigure,
    ReportBundle,
    ReportError,
    Section,
)

pytestmark = pytest.mark.unit


def _figure(figure_id: str = "f1", contract_id: str = "TotalSales", **over) -> CitedFigure:
    fields = {
        "figure_id": figure_id,
        "citation_id": "c1",
        "contract_id": contract_id,
        "metric": "TotalSales",
        "unit_kind": "currency",
        "kind": "total",
        "section": "s1",
        "label": None,
        "value": Decimal("1552071.00"),
        "renderings": {"en": "1,552,071.00"},
    }
    fields.update(over)
    return CitedFigure(**fields)


def _bundle(*figures: CitedFigure) -> ReportBundle:
    return ReportBundle(
        identity=BundleIdentity(
            table="retail_store_sales", journey="first-hour", generated_for="board"
        ),
        figures=figures or (_figure(),),
        caveats=(),
        sections=(Section(section_id="s1", order=1, figure_ids=("f1",)),),
    )


def test_bundle_exposes_ordered_section_ids() -> None:
    assert _bundle().section_ids == ("s1",)


def test_figure_without_contract_id_is_refused() -> None:
    with pytest.raises(ReportError, match="contract"):
        _figure(contract_id="")


def test_figure_without_a_rendering_is_refused() -> None:
    """A surface may only reproduce text, so text must exist."""
    with pytest.raises(ReportError, match="rendering"):
        _figure(renderings={})


def test_section_must_index_a_known_figure() -> None:
    with pytest.raises(ReportError, match="unknown figure"):
        ReportBundle(
            identity=BundleIdentity("t", "j", "board"),
            figures=(_figure(),),
            caveats=(),
            sections=(Section("s1", 1, ("missing",)),),
        )


def test_every_figure_must_belong_to_a_declared_section() -> None:
    with pytest.raises(ReportError, match="no declared section"):
        ReportBundle(
            identity=BundleIdentity("t", "j", "board"),
            figures=(_figure(), _figure(figure_id="f2")),
            caveats=(),
            sections=(Section("s1", 1, ("f1",)),),
        )


def test_sections_must_be_ordered() -> None:
    with pytest.raises(ReportError, match="order"):
        ReportBundle(
            identity=BundleIdentity("t", "j", "board"),
            figures=(_figure(),),
            caveats=(),
            sections=(
                Section("s2", 2, ("f1",)),
                Section("s1", 1, ()),
            ),
        )


def test_figure_is_immutable() -> None:
    with pytest.raises(Exception):
        _figure().figure_id = "other"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_report_model.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.report'`

- [ ] **Step 3: Write the implementation**

```python
# src/seshat/report/__init__.py
"""Governed report surfaces: HTML, Excel and PDF over one bundle."""
```

```python
# src/seshat/report/model.py
"""The immutable fact package the surfaces are allowed to present.

Ported from Khepri/src/khepri/rra/bundle.py (CitedFigure, ReportBundle) at
commit <KHEPRI_SHA>. `fact_id` became `contract_id`: in this kit a figure's
provenance is the APPROVED METRIC CONTRACT it came from, which is what makes
"every figure traces to an approved contract" a checkable property.

`renderings` is the point of `CitedFigure`. A surface is handed the text and may
only reproduce it, so "did the workbook round this differently from the PDF?"
cannot arise -- neither of them rounded anything.
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
        return tuple(s.section_id for s in sorted(self.sections, key=lambda s: s.order))

    def _require_ordered_sections(self) -> None:
        orders = [s.order for s in self.sections]
        if orders != sorted(orders):
            raise ReportError(f"sections are not in declared order: {orders}")

    def _require_sections_index_the_figures(self) -> None:
        known = {f.figure_id for f in self.figures}
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_model.py -q --no-cov`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/report tests/unit/test_report_model.py
git commit -m "feat: report bundle model with contract-traced figures"
```

---

### Task 2: The print overlay artifact and loader

**Files:**
- Create: `templates/report-layout.yaml`
- Create: `src/seshat/report/layout.py`
- Test: `tests/unit/test_report_layout.py`

**Interfaces:**
- Consumes: `ReportError` (Task 1).
- Produces: frozen `LayoutSection(section_id: str, order: int, heading_code: str, visual_ids: tuple[str, ...], page_break_before: bool)`; frozen `ReportLayout(cover_title_code: str, sections: tuple[LayoutSection, ...])`; `load_layout(path: Path) -> ReportLayout`; `LAYOUT_TEMPLATE_NAME = "report-layout.yaml"`.

The overlay adds presentation only: it references visual ids and **cannot introduce a figure**, which the loader enforces by rejecting any key that names a metric or value.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_report_layout.py
from __future__ import annotations

from pathlib import Path

import pytest

from seshat.report.layout import load_layout
from seshat.report.model import ReportError

pytestmark = pytest.mark.unit

_VALID = """\
version: 1
cover_title_code: cover.board_pack
sections:
  - section_id: overview
    order: 1
    heading_code: section.overview
    visual_ids: [v1, v2]
    page_break_before: false
  - section_id: detail
    order: 2
    heading_code: section.detail
    visual_ids: [v3]
    page_break_before: true
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "report-layout.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_layout_loads(tmp_path: Path) -> None:
    layout = load_layout(_write(tmp_path, _VALID))
    assert layout.cover_title_code == "cover.board_pack"
    assert [s.section_id for s in layout.sections] == ["overview", "detail"]
    assert layout.sections[1].page_break_before is True


def test_out_of_order_sections_are_refused(tmp_path: Path) -> None:
    text = _VALID.replace("order: 1", "order: 5")
    with pytest.raises(ReportError, match="order"):
        load_layout(_write(tmp_path, text))


def test_layout_may_not_introduce_a_figure(tmp_path: Path) -> None:
    """Presentation only: a value or metric in the overlay is a governance leak."""
    text = _VALID + "    value: 1234\n"
    with pytest.raises(ReportError, match="cannot introduce"):
        load_layout(_write(tmp_path, text))


def test_layout_may_not_carry_prose(tmp_path: Path) -> None:
    """Headings are governed codes, so no untranslated English reaches a page."""
    text = _VALID.replace("heading_code: section.overview", 'heading: "Overview"')
    with pytest.raises(ReportError, match="heading_code"):
        load_layout(_write(tmp_path, text))


def test_section_needs_at_least_one_visual(tmp_path: Path) -> None:
    text = _VALID.replace("visual_ids: [v3]", "visual_ids: []")
    with pytest.raises(ReportError, match="visual_ids"):
        load_layout(_write(tmp_path, text))


def test_shipped_template_loads() -> None:
    repo = Path(__file__).parents[2]
    layout = load_layout(repo / "templates" / "report-layout.yaml")
    assert layout.sections
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_report_layout.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.report.layout'`

- [ ] **Step 3: Write the blank template**

```yaml
# templates/report-layout.yaml
# The PRINT OVERLAY for a governed report. Presentation only.
#
# This file adds what a dashboard layout cannot express -- a cover page, section
# order, page breaks. It references visual ids from design/visual-list.md and
# CANNOT introduce a figure: no `value`, no `metric`, no prose. Meaning stays
# governed by the approved metric contracts and visual-contract-binding-map.md.
#
# Headings are governed CODES, not text, so a code resolves per language and no
# untranslated English reaches an Arabic page.
version: 1
cover_title_code: cover.<fill_in>
sections:
  - section_id: overview
    order: 1
    heading_code: section.overview
    visual_ids: []
    page_break_before: false
```

- [ ] **Step 4: Write the loader**

```python
# src/seshat/report/layout.py
"""The print overlay: paging and section order, and nothing about meaning.

A dashboard layout has no page boxes, so this artifact supplies them. It is
deliberately unable to state a figure: the loader refuses any key that names a
value or a metric, because the moment an overlay can carry a number there are two
places a report's figures come from.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.report.model import ReportError

LAYOUT_TEMPLATE_NAME = "report-layout.yaml"

# Keys that would let presentation state meaning.
_FORBIDDEN_KEYS = ("value", "metric", "figure", "contract", "measure", "dax", "sql")
# Keys that would put untranslated prose on a page.
_PROSE_KEYS = ("heading", "title", "caption", "text", "label")


@dataclass(frozen=True, slots=True)
class LayoutSection:
    section_id: str
    order: int
    heading_code: str
    visual_ids: tuple[str, ...]
    page_break_before: bool


@dataclass(frozen=True, slots=True)
class ReportLayout:
    cover_title_code: str
    sections: tuple[LayoutSection, ...]


def load_layout(path: Path) -> ReportLayout:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read layout {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ReportError(f"layout {path} is not a mapping")
    cover = raw.get("cover_title_code")
    if not isinstance(cover, str) or not cover:
        raise ReportError(f"layout {path} has no cover_title_code")
    raw_sections = raw.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ReportError(f"layout {path} declares no sections")
    sections = tuple(_section(entry, path) for entry in raw_sections)
    orders = [s.order for s in sections]
    if orders != sorted(orders):
        raise ReportError(f"layout {path} sections are out of order: {orders}")
    return ReportLayout(cover_title_code=cover, sections=sections)


def _reject_meaning(entry: dict, section_id: str) -> None:
    for key in entry:
        lowered = str(key).lower()
        if any(bad in lowered for bad in _FORBIDDEN_KEYS):
            raise ReportError(
                f"section {section_id!r} key {key!r}: the print overlay cannot "
                "introduce a figure -- meaning belongs to the approved contracts"
            )
        if lowered in _PROSE_KEYS:
            raise ReportError(
                f"section {section_id!r} key {key!r}: use heading_code, not prose, "
                "so the wording resolves per language"
            )


def _section(entry: object, path: Path) -> LayoutSection:
    if not isinstance(entry, dict):
        raise ReportError(f"layout {path} has a non-mapping section")
    section_id = entry.get("section_id")
    if not isinstance(section_id, str) or not section_id:
        raise ReportError(f"layout {path} has a section with no section_id")
    _reject_meaning(entry, section_id)
    order = entry.get("order")
    if not isinstance(order, int):
        raise ReportError(f"section {section_id!r} needs an int order")
    heading = entry.get("heading_code")
    if not isinstance(heading, str) or not heading:
        raise ReportError(f"section {section_id!r} needs a heading_code")
    visuals = entry.get("visual_ids")
    if not isinstance(visuals, list) or not visuals:
        raise ReportError(f"section {section_id!r} needs a non-empty visual_ids")
    if not all(isinstance(v, str) for v in visuals):
        raise ReportError(f"section {section_id!r} visual_ids must all be strings")
    return LayoutSection(
        section_id=section_id,
        order=order,
        heading_code=heading,
        visual_ids=tuple(visuals),
        page_break_before=bool(entry.get("page_break_before", False)),
    )
```

Note the shipped template's single section has `visual_ids: []`, which the loader refuses. Fix the template to carry one placeholder id so `test_shipped_template_loads` passes:

```yaml
    visual_ids: [replace-with-a-visual-id-from-visual-list]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_layout.py -q --no-cov`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add templates/report-layout.yaml src/seshat/report/layout.py tests/unit/test_report_layout.py
git commit -m "feat: report print overlay artifact and fail-closed loader

The overlay adds paging and section order only; the loader refuses any key that
could state a figure, and requires governed heading codes rather than prose."
```

---

### Task 3: Fixture-driven bundle builder

**Files:**
- Create: `src/seshat/report/bundle.py`
- Create: `tests/fixtures/report/board_pack.yaml`
- Test: `tests/unit/test_report_bundle.py`

**Interfaces:**
- Consumes: Task 1 types, `ReportLayout` (Task 2).
- Produces: `UNIT_KINDS = ("currency", "count", "ratio")`; `render_value(value: Decimal, unit_kind: str) -> str`; `build_bundle(*, table: str, generated_for: str, layout: ReportLayout, contracts: Mapping[str, str], observations: Sequence[Mapping[str, object]]) -> ReportBundle`.

`build_bundle` is **the only place arithmetic and formatting happen**. `observations` is the fixture stand-in for Increment B's gold query; each entry names a `contract_id`, a `visual_id`, an optional `label` and a `Decimal` `value`. A `contract_id` absent from `contracts` refuses the build — that is invariant 5 at its source.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_report_bundle.py
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from seshat.report.bundle import build_bundle, render_value
from seshat.report.layout import load_layout
from seshat.report.model import ReportError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]


def _layout(tmp_path: Path) -> object:
    path = tmp_path / "report-layout.yaml"
    path.write_text(
        "version: 1\n"
        "cover_title_code: cover.board_pack\n"
        "sections:\n"
        "  - section_id: overview\n"
        "    order: 1\n"
        "    heading_code: section.overview\n"
        "    visual_ids: [v1]\n"
        "    page_break_before: false\n",
        encoding="utf-8",
    )
    return load_layout(path)


_OBS = [
    {
        "visual_id": "v1",
        "contract_id": "TotalSales",
        "metric": "TotalSales",
        "unit_kind": "currency",
        "label": None,
        "value": Decimal("1552071"),
    }
]


def test_currency_renders_to_two_places_with_grouping() -> None:
    assert render_value(Decimal("1552071"), "currency") == "1,552,071.00"


def test_count_renders_without_decimals() -> None:
    assert render_value(Decimal("12575"), "count") == "12,575"


def test_ratio_renders_as_a_percentage_to_two_places() -> None:
    assert render_value(Decimal("0.5037"), "ratio") == "50.37%"


def test_unknown_unit_kind_is_refused() -> None:
    with pytest.raises(ReportError, match="unit_kind"):
        render_value(Decimal("1"), "furlongs")


def test_bundle_carries_the_rendered_text(tmp_path: Path) -> None:
    bundle = build_bundle(
        table="retail_store_sales",
        generated_for="board",
        layout=_layout(tmp_path),
        contracts={"TotalSales": "mappings/retail_store_sales/metrics/TotalSales.yaml"},
        observations=_OBS,
    )
    figure = bundle.figures[0]
    assert figure.renderings["en"] == "1,552,071.00"
    assert figure.contract_id == "TotalSales"
    assert figure.value == Decimal("1552071")


def test_observation_without_an_approved_contract_is_refused(tmp_path: Path) -> None:
    rogue = [{**_OBS[0], "contract_id": "InventedMetric"}]
    with pytest.raises(ReportError, match="not an approved contract"):
        build_bundle(
            table="t",
            generated_for="board",
            layout=_layout(tmp_path),
            contracts={"TotalSales": "x.yaml"},
            observations=rogue,
        )


def test_observation_for_an_undeclared_visual_is_refused(tmp_path: Path) -> None:
    rogue = [{**_OBS[0], "visual_id": "v99"}]
    with pytest.raises(ReportError, match="not in the layout"):
        build_bundle(
            table="t",
            generated_for="board",
            layout=_layout(tmp_path),
            contracts={"TotalSales": "x.yaml"},
            observations=rogue,
        )


def test_missing_value_renders_as_pending_not_a_number(tmp_path: Path) -> None:
    """No data source must never become an invented figure."""
    pending = [{**_OBS[0], "value": None}]
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=_layout(tmp_path),
        contracts={"TotalSales": "x.yaml"},
        observations=pending,
    )
    assert bundle.figures[0].renderings["en"] == "[PENDING LIVE DATA]"
    assert bundle.figures[0].value is None


def test_shipped_fixture_builds(tmp_path: Path) -> None:
    import yaml

    payload = yaml.safe_load(
        (_REPO / "tests/fixtures/report/board_pack.yaml").read_text(encoding="utf-8")
    )
    observations = [
        {**entry, "value": Decimal(str(entry["value"]))} for entry in payload["observations"]
    ]
    layout_path = tmp_path / "report-layout.yaml"
    layout_path.write_text(
        yaml.safe_dump(payload["layout"], sort_keys=False), encoding="utf-8"
    )
    bundle = build_bundle(
        table=payload["table"],
        generated_for=payload["generated_for"],
        layout=load_layout(layout_path),
        contracts=payload["contracts"],
        observations=observations,
    )
    assert len(bundle.figures) == len(observations)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_report_bundle.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.report.bundle'`

- [ ] **Step 3: Write the fixture**

```yaml
# tests/fixtures/report/board_pack.yaml
# Synthetic observations standing in for Increment B's gold query. Invented
# values; not client data. The five contract ids match the approved contracts
# under mappings/retail_store_sales/metrics/.
table: retail_store_sales
generated_for: board
contracts:
  TotalSales: mappings/retail_store_sales/metrics/TotalSales.yaml
  TotalQuantity: mappings/retail_store_sales/metrics/TotalQuantity.yaml
  TransactionCount: mappings/retail_store_sales/metrics/TransactionCount.yaml
  AvgTransactionValue: mappings/retail_store_sales/metrics/AvgTransactionValue.yaml
  DiscountedTransactionRate: mappings/retail_store_sales/metrics/DiscountedTransactionRate.yaml
layout:
  version: 1
  cover_title_code: cover.board_pack
  sections:
    - section_id: headline
      order: 1
      heading_code: section.headline
      visual_ids: [kpi_total_sales, kpi_transactions, kpi_avg_value]
      page_break_before: false
    - section_id: mix
      order: 2
      heading_code: section.mix
      visual_ids: [kpi_quantity, kpi_discount_rate]
      page_break_before: true
observations:
  - visual_id: kpi_total_sales
    contract_id: TotalSales
    metric: TotalSales
    unit_kind: currency
    label: null
    value: "1552071"
  - visual_id: kpi_transactions
    contract_id: TransactionCount
    metric: TransactionCount
    unit_kind: count
    label: null
    value: "12575"
  - visual_id: kpi_avg_value
    contract_id: AvgTransactionValue
    metric: AvgTransactionValue
    unit_kind: currency
    label: null
    value: "123.42"
  - visual_id: kpi_quantity
    contract_id: TotalQuantity
    metric: TotalQuantity
    unit_kind: count
    label: null
    value: "66276"
  - visual_id: kpi_discount_rate
    contract_id: DiscountedTransactionRate
    metric: DiscountedTransactionRate
    unit_kind: ratio
    label: null
    value: "0.5037"
```

- [ ] **Step 4: Write the builder**

```python
# src/seshat/report/bundle.py
"""The one place a report's arithmetic and formatting happen.

Every surface downstream transcribes `CitedFigure.renderings`. That is why this
module exists: a figure is computed and formatted exactly once, so a workbook and
a PDF cannot round the same number differently -- neither of them rounds anything.

`observations` is the seam Increment B replaces with a gold query. Its shape does
not change when that happens, which is the point of putting the seam here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal

from seshat.report.layout import ReportLayout
from seshat.report.model import (
    BundleIdentity,
    CitedFigure,
    ReportBundle,
    ReportError,
    Section,
)

UNIT_KINDS = ("currency", "count", "ratio")
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


def build_bundle(
    *,
    table: str,
    generated_for: str,
    layout: ReportLayout,
    contracts: Mapping[str, str],
    observations: Sequence[Mapping[str, object]],
) -> ReportBundle:
    declared = {
        visual_id: section.section_id
        for section in layout.sections
        for visual_id in section.visual_ids
    }
    figures = tuple(
        _figure(entry, declared=declared, contracts=contracts)
        for entry in observations
    )
    sections = tuple(
        Section(
            section_id=section.section_id,
            order=section.order,
            figure_ids=tuple(
                f.figure_id for f in figures if f.section == section.section_id
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


def _figure(
    entry: Mapping[str, object],
    *,
    declared: Mapping[str, str],
    contracts: Mapping[str, str],
) -> CitedFigure:
    visual_id = str(entry.get("visual_id") or "")
    contract_id = str(entry.get("contract_id") or "")
    if visual_id not in declared:
        raise ReportError(
            f"observation for visual {visual_id!r} is not in the layout; the "
            "overlay decides what appears"
        )
    if contract_id not in contracts:
        raise ReportError(
            f"visual {visual_id!r} cites {contract_id!r}, which is not an "
            "approved contract; an unattributed figure refuses the render"
        )
    unit_kind = str(entry.get("unit_kind") or "")
    raw = entry.get("value")
    value = raw if isinstance(raw, Decimal) else None
    text = PENDING if value is None else render_value(value, unit_kind)
    label = entry.get("label")
    return CitedFigure(
        figure_id=visual_id,
        citation_id=f"{contract_id}#{visual_id}",
        contract_id=contract_id,
        metric=str(entry.get("metric") or contract_id),
        unit_kind=unit_kind or "count",
        kind="total",
        section=declared[visual_id],
        label=str(label) if isinstance(label, str) else None,
        value=value,
        renderings={"en": text},
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_bundle.py -q --no-cov`
Expected: PASS (9 tests)

- [ ] **Step 6: Commit**

```bash
git add src/seshat/report/bundle.py tests/fixtures/report tests/unit/test_report_bundle.py
git commit -m "feat: report bundle builder -- the only place arithmetic happens

Refuses an observation citing an unapproved contract or an undeclared visual, and
renders a missing value as [PENDING LIVE DATA] rather than inventing a figure."
```

---

### Task 4: Port `charts.py` (geometry, never markup)

**Files:**
- Create: `src/seshat/report/charts.py` (port of `Khepri/src/khepri/rra/rendering/charts.py`)
- Test: `tests/unit/test_report_charts.py`

**Interfaces:**
- Consumes: `CitedFigure` (Task 1).
- Produces: `CHART_WIDTH: Decimal`, `CHART_HEIGHT: Decimal`, `COORDINATE_PRECISION = 4`; frozen slotted `ChartLabel`, `ChartMark`, `ChartView(width, height, marks, labels, title_code, description_code)`; `build_chart(figures: Sequence[CitedFigure], *, kind: str, mirrored: bool = False) -> ChartView | None`.

**Port procedure:** copy the source file, replace its `bundle` import with `from seshat.report.model import CitedFigure, ReportError`, drop any benchmark/telemetry references, and prepend the provenance header. Do not re-derive the geometry maths — it is the reviewed part.

- [ ] **Step 1: Capture the provenance sha**

Run: `git -C ../Khepri rev-parse --short HEAD`
Record the value; every ported file's header uses it.

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/test_report_charts.py
from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.report.charts import CHART_HEIGHT, CHART_WIDTH, build_chart
from seshat.report.model import CitedFigure

pytestmark = pytest.mark.unit


def _figure(figure_id: str, value: str, label: str) -> CitedFigure:
    return CitedFigure(
        figure_id=figure_id,
        citation_id=f"c#{figure_id}",
        contract_id="TotalSales",
        metric="TotalSales",
        unit_kind="currency",
        kind="series",
        section="s1",
        label=label,
        value=Decimal(value),
        renderings={"en": value},
    )


_SERIES = (
    _figure("a", "100", "Jan"),
    _figure("b", "250", "Feb"),
    _figure("c", "175", "Mar"),
)


def test_bar_chart_produces_one_mark_per_figure() -> None:
    view = build_chart(_SERIES, kind="bar")
    assert view is not None
    assert len(view.marks) == 3


def test_canvas_travels_with_the_view() -> None:
    """A viewBox written literally in a template would drift from the geometry."""
    view = build_chart(_SERIES, kind="bar")
    assert (view.width, view.height) == (CHART_WIDTH, CHART_HEIGHT)


def test_geometry_is_decimal_never_float() -> None:
    view = build_chart(_SERIES, kind="bar")
    for mark in view.marks:
        for coordinate in (mark.x, mark.y, mark.width, mark.height):
            assert isinstance(coordinate, (Decimal, str)), type(coordinate)
            assert not isinstance(coordinate, float)


def test_view_returns_no_markup() -> None:
    """The module returns geometry; a Jinja macro writes the elements."""
    view = build_chart(_SERIES, kind="bar")
    rendered = repr(view)
    assert "<svg" not in rendered
    assert "<rect" not in rendered


def test_titles_are_codes_not_prose() -> None:
    view = build_chart(_SERIES, kind="bar")
    assert view.title_code.endswith((".bar", ".comparison", ".series")) or "." in view.title_code
    assert " " not in view.title_code


def test_labels_come_from_the_figures_verbatim() -> None:
    view = build_chart(_SERIES, kind="bar")
    assert {label.text for label in view.labels} >= {"Jan", "Feb", "Mar"}


def test_empty_series_yields_no_chart() -> None:
    assert build_chart((), kind="bar") is None


def test_figures_without_values_yield_no_chart() -> None:
    pending = _figure("a", "0", "Jan")
    object.__setattr__(pending, "value", None)
    assert build_chart((pending,), kind="bar") is None
```

- [ ] **Step 3: Port the module**

```bash
cp ../Khepri/src/khepri/rra/rendering/charts.py src/seshat/report/charts.py
```

Then edit `src/seshat/report/charts.py`:

1. Prepend, above the existing docstring's first line, a provenance note:

```python
"""Governed chart geometry as an exact view model.

PORTED from Khepri/src/khepri/rra/rendering/charts.py at commit <KHEPRI_SHA>.
Adaptation: imports CitedFigure from seshat.report.model. The geometry, the
Decimal discipline, and the geometry-not-markup rule are unchanged -- they are
the reviewed part, and the reasons are preserved below.
"""
```

2. Replace the Khepri bundle import with:

```python
from seshat.report.model import CitedFigure, ReportError
```

3. Replace any `KhepriError` / RRA-specific exception with `ReportError`.
4. Remove any import or reference to Khepri telemetry, benchmark or persistence.
5. Leave `CHART_WIDTH`, `CHART_HEIGHT`, `COORDINATE_PRECISION`, `_SCALE`, and every private geometry helper exactly as they are.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_charts.py -q --no-cov`
Expected: PASS (8 tests). If `build_chart`'s signature differs from this plan's `Interfaces` block, adjust the test call to the real signature and keep the assertions — the assertions are the contract, the signature is the port's.

- [ ] **Step 5: Commit**

```bash
git add src/seshat/report/charts.py tests/unit/test_report_charts.py
git commit -m "feat: port Khepri chart geometry -- view model, never markup

Geometry stays Decimal until a mark is built, the canvas travels with the view,
and titles are governed codes so no untranslated prose reaches a page."
```

---

### Task 5: Port `html.py` and the templates

**Files:**
- Create: `src/seshat/report/html.py` (port)
- Create: `src/seshat/report/templates/report.html.j2`, `report.css` (port; chart macro included)
- Test: `tests/unit/test_report_html.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 4.
- Produces: `TEMPLATE_PACKAGE = "seshat.report"`, `TEMPLATE_DIRECTORY = "templates"`, `TEMPLATE_NAME = "report.html.j2"`, `STYLESHEET_NAME = "report.css"`; `SurfaceRenderFailed(RuntimeError)`; frozen slotted `FigureCell`, `HtmlSurface(document: str, ...)`; `build_environment() -> Environment`; `build_cells(bundle: ReportBundle, language: str) -> tuple[FigureCell, ...]`; `build_context(...) -> dict`; `HtmlReportRenderer.render(bundle, layout, language) -> HtmlSurface`.

**Port procedure:** copy `html.py` and the two template files; repoint the template package; delete narrative blocks (this kit has no narrative generator); keep `autoescape=True` and `StrictUndefined` **unconditionally**.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_report_html.py
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

jinja2 = pytest.importorskip("jinja2", reason="requires the `report` extra")


def _bundle_and_layout(tmp_path: Path):
    from seshat.report.bundle import build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(
        "version: 1\n"
        "cover_title_code: cover.board_pack\n"
        "sections:\n"
        "  - section_id: overview\n"
        "    order: 1\n"
        "    heading_code: section.overview\n"
        "    visual_ids: [v1]\n"
        "    page_break_before: false\n",
        encoding="utf-8",
    )
    layout = load_layout(path)
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=layout,
        contracts={"TotalSales": "x.yaml"},
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": "<script>alert(1)</script>",
                "value": Decimal("1552071"),
            }
        ],
    )
    return bundle, layout


def test_environment_escapes_and_is_strict() -> None:
    from seshat.report.html import build_environment

    env = build_environment()
    assert env.autoescape is True
    assert env.undefined.__name__ == "StrictUndefined"


def test_document_reproduces_the_bundle_text(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _bundle_and_layout(tmp_path)
    surface = HtmlReportRenderer().render(bundle, layout, "en")
    assert "1,552,071.00" in surface.document


def test_hostile_label_is_escaped(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _bundle_and_layout(tmp_path)
    surface = HtmlReportRenderer().render(bundle, layout, "en")
    assert "<script>alert(1)</script>" not in surface.document
    assert "&lt;script&gt;" in surface.document


def test_no_safe_filter_on_a_bundle_path() -> None:
    """One |safe makes escaping a convention rather than a guarantee."""
    templates = Path(__file__).parents[2] / "src/seshat/report/templates"
    for template in templates.glob("*.j2"):
        text = template.read_text(encoding="utf-8")
        assert "|safe" not in text, template.name
        assert "| safe" not in text, template.name
        assert "Markup(" not in text, template.name


def test_renderer_refuses_a_missing_language(tmp_path: Path) -> None:
    from seshat.report.html import HtmlReportRenderer, SurfaceRenderFailed

    bundle, layout = _bundle_and_layout(tmp_path)
    with pytest.raises(SurfaceRenderFailed):
        HtmlReportRenderer().render(bundle, layout, "ar")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_report_html.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.report.html'` (or a skip if `jinja2` is absent; install the extra first with `pip install -e ".[report]"`)

- [ ] **Step 3: Port**

```bash
cp ../Khepri/src/khepri/rra/rendering/html.py src/seshat/report/html.py
mkdir -p src/seshat/report/templates
cp ../Khepri/src/khepri/rra/rendering/templates/report.html.j2 src/seshat/report/templates/
cp ../Khepri/src/khepri/rra/rendering/templates/report.css src/seshat/report/templates/
```

Then edit:

1. Provenance header naming `Khepri/src/khepri/rra/rendering/html.py` at `<KHEPRI_SHA>`.
2. `TEMPLATE_PACKAGE = "seshat.report"`.
3. Imports: `from seshat.report.model import CitedFigure, ReportBundle, ReportError` and `from seshat.report.charts import build_chart`.
4. Delete `NarrativePassage`, `_passages`, and every narrative reference in the module and the template — this kit generates no narrative.
5. Replace Khepri's section-heading language tables with a `heading_code` lookup driven by `ReportLayout`.
6. Keep `build_environment()` exactly: `autoescape=True`, `undefined=StrictUndefined`, `PackageLoader(TEMPLATE_PACKAGE, TEMPLATE_DIRECTORY)`.
7. Keep the chart macro in the template unchanged; it is what turns geometry into elements.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_html.py -q --no-cov`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/report/html.py src/seshat/report/templates tests/unit/test_report_html.py
git commit -m "feat: port the HTML report surface with unconditional autoescaping

No |safe and no Markup on any bundle-reachable path, asserted by a test that
scans every template."
```

---

### Task 6: Port `excel.py`

**Files:**
- Create: `src/seshat/report/excel.py` (port)
- Test: `tests/unit/test_report_excel.py`

**Interfaces:**
- Consumes: Tasks 1, 3.
- Produces: `GOVERNED_LABELS: tuple[str, ...]`; frozen slotted `ExcelSurface(workbook_bytes: bytes, ...)`; `ExcelReportRenderer.render(bundle, layout, language) -> ExcelSurface`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_report_excel.py
from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

pytest.importorskip("xlsxwriter", reason="requires the `report` extra")


def _render(tmp_path: Path, label: str = "Region A"):
    from seshat.report.bundle import build_bundle
    from seshat.report.excel import ExcelReportRenderer
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(
        "version: 1\n"
        "cover_title_code: cover.board_pack\n"
        "sections:\n"
        "  - section_id: overview\n"
        "    order: 1\n"
        "    heading_code: section.overview\n"
        "    visual_ids: [v1]\n"
        "    page_break_before: false\n",
        encoding="utf-8",
    )
    layout = load_layout(path)
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=layout,
        contracts={"TotalSales": "x.yaml"},
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": label,
                "value": Decimal("1552071"),
            }
        ],
    )
    return ExcelReportRenderer().render(bundle, layout, "en")


def _sheet_xml(workbook_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        name = next(n for n in archive.namelist() if n.endswith("sheet1.xml"))
        return archive.read(name).decode("utf-8")


def test_workbook_is_produced(tmp_path: Path) -> None:
    surface = _render(tmp_path)
    assert surface.workbook_bytes[:2] == b"PK"


def test_figure_is_a_string_cell_not_a_number(tmp_path: Path) -> None:
    """Money as a numeric cell would round-trip through IEEE 754."""
    xml = _sheet_xml(_render(tmp_path).workbook_bytes)
    assert "1,552,071.00" in xml
    assert 't="n"' not in xml


def test_formula_prefix_is_inert(tmp_path: Path) -> None:
    xml = _sheet_xml(_render(tmp_path, label="=HYPERLINK(\"http://evil\")").workbook_bytes)
    assert "<f>" not in xml
    assert "HYPERLINK" in xml


def test_no_totals_row_arithmetic(tmp_path: Path) -> None:
    """A SUM would look like diligence and be a second source of numbers."""
    xml = _sheet_xml(_render(tmp_path).workbook_bytes)
    assert "SUM(" not in xml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_report_excel.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.report.excel'`

- [ ] **Step 3: Port**

```bash
cp ../Khepri/src/khepri/rra/rendering/excel.py src/seshat/report/excel.py
```

Edit: provenance header; imports repointed to `seshat.report.model` / `seshat.report.layout`; drop narrative and Khepri-specific sheet names; keep `write_string`, the disabled coercion options, `GOVERNED_LABELS`, and the no-arithmetic discipline exactly.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_excel.py -q --no-cov`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/report/excel.py tests/unit/test_report_excel.py
git commit -m "feat: port the governed Excel surface

Every cell a string, no numeric cells, no totals-row arithmetic, and a formula
prefix arrives verbatim and inert."
```

---

### Task 7: Port `pdf.py`, `chromium.py`, `fonts.py`

**Files:**
- Create: `src/seshat/report/pdf.py`, `chromium.py`, `fonts.py` (ports)
- Create: `src/seshat/report/typefaces/` (copied font files)
- Create: `src/seshat/report/templates/report.pdf.html.j2`, `report.print.css` (ports)
- Test: `tests/unit/test_report_pdf.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 5.
- Produces: `PrintablePage`; `PagePrinter` Protocol with `print_to_pdf(self, page: PrintablePage) -> bytes`; frozen slotted `PdfSurface(pdf_bytes: bytes, ...)`; `PdfReportRenderer(printer: PagePrinter).render(bundle, layout, language) -> PdfSurface`; `chromium.ChromiumPrinter` implementing the protocol.

`pdf.py` must not import `chromium.py` — that is what keeps the surface testable without a browser.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_report_pdf.py
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

pytest.importorskip("jinja2", reason="requires the `report` extra")

# A minimal PDF that is tagged and declares an embedded font program.
_GOOD = b"%PDF-1.7\n/MarkInfo<</Marked true>>/StructTreeRoot 1 0 R\n/FontFile2 2 0 R\n%%EOF"
_UNTAGGED = b"%PDF-1.7\n/FontFile2 2 0 R\n%%EOF"
_NO_FONT = b"%PDF-1.7\n/MarkInfo<</Marked true>>/StructTreeRoot 1 0 R\n%%EOF"


class FakePrinter:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.pages: list[object] = []

    def print_to_pdf(self, page) -> bytes:
        self.pages.append(page)
        return self.payload


def _bundle_and_layout(tmp_path: Path):
    from seshat.report.bundle import build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(
        "version: 1\n"
        "cover_title_code: cover.board_pack\n"
        "sections:\n"
        "  - section_id: overview\n"
        "    order: 1\n"
        "    heading_code: section.overview\n"
        "    visual_ids: [v1]\n"
        "    page_break_before: false\n",
        encoding="utf-8",
    )
    layout = load_layout(path)
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=layout,
        contracts={"TotalSales": "x.yaml"},
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": None,
                "value": Decimal("1552071"),
            }
        ],
    )
    return bundle, layout


def test_pdf_module_does_not_import_chromium() -> None:
    """Chromium is a port, not an import: the surface stays browser-free."""
    source = (
        Path(__file__).parents[2] / "src/seshat/report/pdf.py"
    ).read_text(encoding="utf-8")
    assert "chromium" not in source.lower()
    assert "playwright" not in source.lower()


def test_render_uses_the_injected_printer(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _bundle_and_layout(tmp_path)
    printer = FakePrinter(_GOOD)
    surface = PdfReportRenderer(printer).render(bundle, layout, "en")
    assert surface.pdf_bytes == _GOOD
    assert len(printer.pages) == 1


def test_untagged_pdf_is_refused(tmp_path: Path) -> None:
    from seshat.report.model import ReportError
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _bundle_and_layout(tmp_path)
    with pytest.raises(ReportError, match="tag"):
        PdfReportRenderer(FakePrinter(_UNTAGGED)).render(bundle, layout, "en")


def test_pdf_without_an_embedded_font_is_refused(tmp_path: Path) -> None:
    from seshat.report.model import ReportError
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _bundle_and_layout(tmp_path)
    with pytest.raises(ReportError, match="font"):
        PdfReportRenderer(FakePrinter(_NO_FONT)).render(bundle, layout, "en")


def test_printed_html_carries_the_bundle_text(tmp_path: Path) -> None:
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _bundle_and_layout(tmp_path)
    printer = FakePrinter(_GOOD)
    PdfReportRenderer(printer).render(bundle, layout, "en")
    assert "1,552,071.00" in str(printer.pages[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_report_pdf.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.report.pdf'`

- [ ] **Step 3: Port**

```bash
cp ../Khepri/src/khepri/rra/rendering/pdf.py src/seshat/report/pdf.py
cp ../Khepri/src/khepri/rra/rendering/chromium.py src/seshat/report/chromium.py
cp ../Khepri/src/khepri/rra/rendering/fonts.py src/seshat/report/fonts.py
cp -r ../Khepri/src/khepri/rra/rendering/typefaces src/seshat/report/typefaces
cp ../Khepri/src/khepri/rra/rendering/templates/report.pdf.html.j2 src/seshat/report/templates/
cp ../Khepri/src/khepri/rra/rendering/templates/report.print.css src/seshat/report/templates/
```

Edit each: provenance header; imports repointed to `seshat.report.*`; Khepri exceptions replaced with `ReportError`; narrative removed. Keep the tagged-PDF and embedded-font inspection, the `PagePrinter` protocol, and the template's `{% extends %}` of the web template exactly.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_report_pdf.py -q --no-cov`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/report/pdf.py src/seshat/report/chromium.py src/seshat/report/fonts.py src/seshat/report/typefaces src/seshat/report/templates tests/unit/test_report_pdf.py
git commit -m "feat: port the PDF surface with Chromium behind a one-method port

Untagged or missing-embedded-font output is refused rather than shipped, and
pdf.py imports neither chromium nor playwright so the surface tests browser-free."
```

---

### Task 8: CLI, extras, packaging, and the cross-surface invariant

**Files:**
- Create: `src/seshat/cli/commands/report.py`
- Modify: `pyproject.toml` (extras + force-include of templates/typefaces)
- Modify: `src/seshat/cli/parser.py` (register the subcommand)
- Test: `tests/unit/test_report_cli.py`, `tests/integration/test_report_surfaces_agree.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `report_main(args: argparse.Namespace) -> int`; exit codes `0` ok, `1` harness error, `2` gate refused.

- [ ] **Step 1: Write the failing cross-surface test**

```python
# tests/integration/test_report_surfaces_agree.py
"""The invariant that makes one bundle worth having."""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

pytest.importorskip("jinja2", reason="requires the `report` extra")
pytest.importorskip("xlsxwriter", reason="requires the `report` extra")

_GOOD = b"%PDF-1.7\n/MarkInfo<</Marked true>>/StructTreeRoot 1 0 R\n/FontFile2 2 0 R\n%%EOF"


class FakePrinter:
    def __init__(self) -> None:
        self.html = ""

    def print_to_pdf(self, page) -> bytes:
        self.html = str(page)
        return _GOOD


def _artifacts(tmp_path: Path):
    from seshat.report.bundle import build_bundle
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(
        "version: 1\n"
        "cover_title_code: cover.board_pack\n"
        "sections:\n"
        "  - section_id: overview\n"
        "    order: 1\n"
        "    heading_code: section.overview\n"
        "    visual_ids: [v1]\n"
        "    page_break_before: false\n",
        encoding="utf-8",
    )
    layout = load_layout(path)
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=layout,
        contracts={"TotalSales": "x.yaml"},
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": None,
                "value": Decimal("1552071"),
            }
        ],
    )
    return bundle, layout


def _sheet_xml(workbook_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        name = next(n for n in archive.namelist() if n.endswith("sheet1.xml"))
        return archive.read(name).decode("utf-8")


def test_all_three_surfaces_show_the_same_text(tmp_path: Path) -> None:
    from seshat.report.excel import ExcelReportRenderer
    from seshat.report.html import HtmlReportRenderer
    from seshat.report.pdf import PdfReportRenderer

    bundle, layout = _artifacts(tmp_path)
    printer = FakePrinter()
    html = HtmlReportRenderer().render(bundle, layout, "en").document
    workbook = _sheet_xml(ExcelReportRenderer().render(bundle, layout, "en").workbook_bytes)
    PdfReportRenderer(printer).render(bundle, layout, "en")
    for document in (html, workbook, printer.html):
        assert "1,552,071.00" in document


def test_no_surface_formats_the_decimal_itself(tmp_path: Path) -> None:
    """Make the rendering and the Decimal disagree; every surface must show the
    rendering. A renderer that formatted `value` would fail here."""
    from seshat.report.excel import ExcelReportRenderer
    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path)
    lying = replace(bundle.figures[0], renderings={"en": "SENTINEL-42"})
    bundle = replace(bundle, figures=(lying,))
    html = HtmlReportRenderer().render(bundle, layout, "en").document
    workbook = _sheet_xml(ExcelReportRenderer().render(bundle, layout, "en").workbook_bytes)
    for document in (html, workbook):
        assert "SENTINEL-42" in document
        assert "1,552,071.00" not in document


def test_no_surface_emits_a_score_or_status(tmp_path: Path) -> None:
    import re

    from seshat.report.html import HtmlReportRenderer

    bundle, layout = _artifacts(tmp_path)
    document = HtmlReportRenderer().render(bundle, layout, "en").document
    assert not re.search(r"\b(?:score|confidence)\s*[:=]\s*\d", document, re.IGNORECASE)
    assert not re.search(r"\breadiness_state\s*[:=]\s*['\"]?pass", document, re.IGNORECASE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_report_surfaces_agree.py -q --no-cov`
Expected: FAIL — the renderers do not exist yet if Tasks 5–7 are incomplete; otherwise FAIL on the sentinel test if any surface formats `value` itself.

- [ ] **Step 3: Write the CLI test**

```python
# tests/unit/test_report_cli.py
from __future__ import annotations

import pytest

from seshat.cli.commands.report import build_report_parser

pytestmark = pytest.mark.unit


def test_parser_requires_a_table() -> None:
    with pytest.raises(SystemExit):
        build_report_parser().parse_args([])


def test_format_choices_are_the_three_surfaces() -> None:
    args = build_report_parser().parse_args(["--table", "t", "--format", "html"])
    assert args.format == "html"
    for surface in ("html", "xlsx", "pdf"):
        assert build_report_parser().parse_args(
            ["--table", "t", "--format", surface]
        ).format == surface


def test_unknown_format_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_report_parser().parse_args(["--table", "t", "--format", "docx"])


def test_output_defaults_below_seshat_output() -> None:
    args = build_report_parser().parse_args(["--table", "t", "--format", "html"])
    assert str(args.output).startswith(".seshat-output")
```

- [ ] **Step 4: Write the CLI**

```python
# src/seshat/cli/commands/report.py
"""`seshat report` -- render an approved design as HTML, Excel or PDF.

Gated: rendering requires `dashboard_ready: pass`, because these surfaces present
an APPROVED design. With no approved design there is nothing to render, and
inventing one here would be a second place a report's content is decided.
"""

from __future__ import annotations

import argparse
from pathlib import Path

_FORMATS = ("html", "xlsx", "pdf")
_DEFAULT_OUTPUT = Path(".seshat-output") / "report"


def build_report_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seshat report")
    parser.add_argument("--table", required=True)
    parser.add_argument("--format", required=True, choices=_FORMATS)
    parser.add_argument("--language", default="en")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    return parser


def report_main(args: argparse.Namespace) -> int:
    from seshat.report.model import ReportError

    try:
        return _render(args)
    except ReportError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return 2


def _render(args: argparse.Namespace) -> int:
    from seshat.report.model import ReportError

    raise ReportError(
        f"dashboard_ready is not pass for {args.table!r}: these surfaces render an "
        "approved design, so the design must be approved first. Run the dashboard "
        "design and review flow, then retry."
    )
```

The gate refusal is the whole v1 CLI behaviour: Increment A proves the renderers, and wiring a real table's artifacts into the CLI is the first task of Increment B. The refusal is honest and testable rather than a stub that pretends to work.

- [ ] **Step 5: Add the extras and package data**

In `pyproject.toml` under `[project.optional-dependencies]`, after the `files` extra:

```toml
# Report surfaces. `report` covers HTML + Excel and needs no browser;
# `report-pdf` adds the browser Chromium is reached through. Neither is in the
# base install, which keeps the static core dependency-light.
report = [
    "jinja2>=3.1,<4",
    "xlsxwriter>=3.2,<4",
]
report-pdf = [
    "playwright>=1.61,<2",
]
```

In `[tool.hatch.build.targets.wheel.force-include]`, so templates and fonts ship with the package:

```toml
"src/seshat/report/templates" = "seshat/report/templates"
"src/seshat/report/typefaces" = "seshat/report/typefaces"
```

- [ ] **Step 6: Register the subcommand**

In `src/seshat/cli/parser.py`, follow the existing subcommand registrations and add `report` wired to `seshat.cli.commands.report.report_main`, with the same `--table` / `--format` / `--language` / `--output` arguments as `build_report_parser`.

- [ ] **Step 7: Run the full verification**

```bash
pip install -e ".[report]"
python -m pytest tests/unit -k report tests/integration/test_report_surfaces_agree.py -q --no-cov
python -m ruff format --check src tests scripts
python -m ruff check src tests scripts
python -m seshat.cli check
```

Expected: all report tests PASS; ruff clean; `seshat check` exit 0.

- [ ] **Step 8: Prove the templates and fonts ship**

```bash
python -m build --wheel --outdir dist-check
python - <<'PY'
import pathlib, zipfile
wheel = sorted(pathlib.Path("dist-check").glob("*.whl"))[-1]
names = zipfile.ZipFile(wheel).namelist()
need = ("seshat/report/templates/report.html.j2", "seshat/report/typefaces")
missing = [n for n in need if not any(x.startswith(n) for x in names)]
print("MISSING:", missing or "[OK] templates and fonts ship")
assert not missing, missing
PY
rm -rf dist-check
```

Expected: `[OK] templates and fonts ship`

- [ ] **Step 9: Commit**

```bash
git add src/seshat/cli/commands/report.py src/seshat/cli/parser.py pyproject.toml tests/unit/test_report_cli.py tests/integration/test_report_surfaces_agree.py
git commit -m "feat: seshat report CLI, report extras, and the cross-surface invariant

The sentinel test makes a figure's rendering and its Decimal disagree and asserts
every surface shows the rendering, so a renderer that started formatting numbers
fails immediately. The CLI refuses honestly until dashboard_ready is pass."
```

---

## Self-Review

**Spec coverage.** Decision 1 (one bundle, transcribe only) → Tasks 1, 3, 8's sentinel test. Decision 2 (port with provenance) → Tasks 4–7, each with a provenance step. Decision 3 (geometry not markup) → Task 4, plus the no-`|safe` scan in Task 5. Decision 4 (approved design + print overlay) → Tasks 2, 3. Invariants 1–8 → Tasks 1 (5), 3 (5), 5 (7), 6 (2, 3), 7 (4), 8 (1, 6), 4 (8). Extras and packaging → Task 8. `[PENDING LIVE DATA]` → Task 3.

**Known gaps, deliberate:**

1. **The CLI does not render a real table.** `_render` refuses with the gate message; wiring `mappings/<table>/design/` into the bundle is Increment B's first task. This is stated rather than stubbed, and its test asserts the refusal.
2. **Only `en` renderings.** `build_bundle` emits `{"en": ...}`. The ported templates keep their RTL support, but a second language needs a per-language rendering pass, which is out of Increment A's scope.
3. **No live gold query.** By design — that is the whole of Increment B.
4. **Chart kinds** depend on what the ported `build_chart` supports; Task 4's test asserts the contract and instructs adapting the call to the real signature rather than guessing it.

**Placeholder scan.** No TBD/TODO. The `<KHEPRI_SHA>` token is filled by Task 4 Step 1, which is an explicit command. Port steps name exact source paths and exact edits rather than "adapt as needed".

**Type consistency.** `ReportError` defined once (Task 1), imported everywhere. `CitedFigure.contract_id` used consistently (never Khepri's `fact_id`). `ReportLayout` / `LayoutSection` field names match between Task 2 and their uses in Tasks 3, 5–8. `render(bundle, layout, language)` is the signature for all three renderers. `workbook_bytes` and `pdf_bytes` and `document` are the surface payload attribute names used in Tasks 5–8.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-03-report-surfaces-increment-a.md`.
