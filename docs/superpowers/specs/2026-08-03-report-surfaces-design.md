# Report surfaces (HTML / Excel / PDF) — design

**Date:** 2026-08-03
**Status:** approved by owner (brainstorm session; four decisions recorded below)
**Capability id:** `report-surfaces`

## Why this exists

The kit's only output today is Power BI: a governed PBIP/TMDL semantic model, a
theme, and a contract-bound dashboard design. Clients also need a document they
can email to a board, a workbook a finance user can pivot, and a page a
stakeholder can open without a Power BI licence.

The naive way to provide those is to render each format from its own SQL. That
would create **a second engine producing numbers**, so a board pack could say
1.55M while the dashboard says 1.54M with nothing to arbitrate — reintroducing,
through the export door, exactly the failure the kit's contract-binding rules
exist to prevent.

## The four decisions this design rests on

| # | Decision | Rejected alternative |
|---|---|---|
| 1 | Numbers come from **one upstream bundle**; renderers only transcribe | Each format queries gold itself |
| 2 | **Port** Khepri's `rra/rendering` into Seshat with provenance headers | Shared package across both repos; or reimplement |
| 3 | Charts are **inline SVG** drawn from pre-computed bundle series | Native chart per surface; matplotlib/plotly images |
| 4 | Content comes from the **already-approved design** + a thin print overlay | A new per-surface report spec; or a raw contract dump |

## What Khepri gives us, and what it does not

`Khepri/src/khepri/rra/rendering/` already solved the hard part, and its stated
reasons match this kit's principles almost word for word:

- **`pdf.py`** — *"It presents figures; it never produces one."* The arithmetic
  happened once upstream in `bundle`; a `Decimal` the renderer could format is
  never in reach, and a test holds that by making the string and the `Decimal`
  disagree. Chromium is *"a port, not an import"*: rendering is expressed against
  a one-method `PagePrinter`, so the surface is verifiable with a fake and no
  browser. Bytes are inspected before a `PdfSurface` exists — untagged, or
  missing an embedded font program, is refused rather than discovered by a
  customer.
- **`excel.py`** — no arithmetic at all (a `SUM` in a totals row *"would look
  like diligence"*), no numeric cells (so money never round-trips through IEEE
  754), and every cell written through `write_string` with formula/URL/number
  coercion disabled, so a hostile label arrives verbatim and inert.
- **One template, two surfaces** — the print template *extends* the web template
  rather than forking it, so shared concerns cannot drift between HTML and PDF.

**What it does not give us: charts.** Khepri's report is tables and narrative.
The SVG writer is net-new work here, and it is the largest new piece.

Porting rather than sharing keeps Seshat a standalone kit whose only runtime
dependency is `pyyaml` — a documented product promise (spec 076 pure kit). Every
ported file names its Khepri source path and commit in a header, so divergence is
at least traceable. If a third consumer ever appears, revisit as a shared package.

## Architecture

```
approved contracts + report-intent.yaml + visual-contract-binding-map.md + data
                    │
                    ▼
              bundle.py          the ONLY place arithmetic happens
                    │            (Decimal in, exact strings out, immutable)
                    ▼
               view.py           strings only; no Decimal in reach downstream
        ┌───────────┼────────────┬───────────────┐
      html.py     pdf.py      excel.py         svg.py
                (extends the   (transcribes    (draws pre-computed
                 html template) only)           series only)
```

```
src/seshat/report/
  bundle.py      computes once from approved contracts; emits a fact package
  view.py        bundle -> view model of strings
  svg.py         charts: bar / line / sparkline. No dependencies.
  html.py        Jinja2 render of the web surface
  pdf.py         extends the HTML template + print CSS; PagePrinter port
  chromium.py    the ONE Playwright adapter; pdf.py never imports it
  excel.py       xlsxwriter; write_string only; no numeric cells
  layout.py      the print overlay: cover, sections, page breaks
  templates/     report.html.j2, report.pdf.html.j2, report.css, report.print.css
```

### Dependencies stay optional

The base kit keeps `pyyaml` as its only runtime dependency. Two extras, following
the established `db` / `stats` / `files` pattern:

| Extra | Adds | Enables |
|---|---|---|
| `seshat-bi[report]` | `jinja2`, `xlsxwriter` | HTML + Excel, **no browser** |
| `seshat-bi[report-pdf]` | `playwright` | PDF |

`svg.py` has no dependencies at all, so charts work wherever HTML does.

### The print overlay

A dashboard layout cannot express paging, so one thin new artifact:
`mappings/<table>/design/report-layout.yaml` — cover page, section order, page
breaks, and which visuals belong to which section. It references visual ids from
the existing `visual-list.md` and **cannot introduce a figure**. Meaning stays
governed by artifacts that are already approved; the overlay adds presentation
only.

## Gate and honest degradation

- **No `dashboard_ready: pass`** → refuse and name the blocker. These surfaces
  render an *approved design*; with no approved design there is nothing to render.
- **No data source** → refuse to invent a figure. Renders structure only, with
  explicit `[PENDING LIVE DATA]` in every figure slot. Useful for reviewing
  layout; not a report anyone can send.
- **No Chromium** → PDF is unavailable and says so. HTML and Excel still work,
  because they never needed a browser.
- **A figure with no approved contract id** → refuse the whole render, rather
  than emit one unattributed number.

## Invariants that get tests

Four are inherited from Khepri's stated reasons; the fifth and sixth are
Seshat-specific.

1. **Renderers never compute.** The view model carries strings. A test makes the
   string and the `Decimal` deliberately disagree and asserts every surface shows
   the string — so any renderer that started formatting the number would fail.
2. **Excel holds no arithmetic and no numeric cells.** Every figure is the exact
   decimal string the bundle produced.
3. **Formula injection is inert.** A label beginning `=`, `+`, `-`, or `@`
   reaches the cell verbatim and does not execute.
4. **PDF is tagged and embeds its fonts, or is refused.** Required for the RTL
   and accessibility checklist already in `design/`.
5. **Every figure traces to an approved contract id.** An untraceable figure
   refuses the render.
6. **No fabricated status or score in any surface** (hard rule #9), asserted with
   the existing truthfulness checks.

## Increments

**Increment A — the contract and all three surfaces, offline.** Bundle built from
committed governed artifacts plus a synthetic fixture, so the whole pipeline is
provable with no database and no browser: `svg.py`, `view.py`, `html.py`,
`excel.py`, `layout.py`, `pdf.py` + `chromium.py` behind the port, the six
invariants, the two extras, and `report-layout.yaml` + its template. Real PDF
bytes require `[report-pdf]`; tests use the fake `PagePrinter`.

**Increment B — live numbers.** `bundle.py` reads gold through the `db` extra and
a DSN, replacing the fixture source. Everything above is unchanged, which is the
point of putting the seam at the bundle.

## Scope

**In scope (A + B):** HTML, Excel and PDF for one table from an approved design;
bar, line and sparkline charts; the print overlay artifact; the CLI surface.

**Out of scope:** RDL paginated reports, Power BI embedding, scheduled or emailed
delivery, multi-table portfolio reports, and authoring new bilingual *content*
(the ported templates' RTL support comes along; writing Arabic copy does not).

## Risks

- **Charts are the largest new build** and have no Khepri precedent. Use the
  `dataviz` skill for form and palette rather than inventing them.
- **Chromium is heavy in CI.** Unit tests use the fake printer and need no
  browser; real-Chromium verification is a separate optional job, and the wheel
  ships no browser.
- **Offline output has no numbers.** That is deliberate — the alternative is a
  document with invented figures, which is worse than no document.

## References

- `Khepri/src/khepri/rra/rendering/{pdf,excel}.py` and `templates/` — the ported
  source, and the reasons quoted above.
- `mappings/retail_store_sales/design/` — the approved design artifacts this
  renders (`report-intent.yaml`, `visual-list.md`,
  `visual-contract-binding-map.md`, `a11y-rtl-readiness-checklist.md`).
- `mappings/retail_store_sales/metrics/` — the five approved contracts.
- `pyproject.toml` `[project.optional-dependencies]` — the extras pattern the two
  new extras follow.
- `docs/superpowers/specs/2026-08-03-adopter-sim-design.md` — the most recent
  design in this lane, and the source of the "text is never the only evidence"
  posture reused here.
