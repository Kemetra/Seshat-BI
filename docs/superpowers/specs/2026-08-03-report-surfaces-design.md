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
| 3 | Charts are **dependency-free SVG** over pre-computed series — as a geometry view model rendered by a Jinja macro, never a markup string (see correction below) | Native chart per surface; matplotlib/plotly images |
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

### Correction: Khepri does have charts, and its approach supersedes mine

An early read of the HTML template suggested Khepri's report was tables and
narrative only, and this design initially called the chart writer net-new work.
That was wrong. `rendering/charts.py` (409 lines) exists, and it documents having
already tried — and rejected — the "return an SVG string" approach this design
first proposed:

> *"An earlier design had it return an SVG fragment as a `str`, and these
> templates cannot render one. `build_environment()` sets `autoescape=True`
> unconditionally and `html.py` states the rule outright: nothing reachable from
> the bundle is ever marked safe, because a page with one `|safe` in it has an
> escaping convention rather than an escaping guarantee."*

So charts are ported too, and four of its rules are adopted verbatim:

- **Geometry, not markup.** The module resolves geometry to strings; a Jinja macro
  writes the elements. Tags come from trusted template source; axis labels — which
  are customer values — pass through the same autoescaping as every table cell,
  which is what makes a product named `<script>` inert. There is no `|safe` and no
  `Markup` anywhere on a bundle-reachable path.
- **Geometry is `Decimal` throughout**, becoming a string only when a mark is
  built. A float coordinate would put binary floating point on the surface of a
  governed figure.
- **No prose in the chart module.** `title_code` / `description_code` are governed
  codes resolved from per-language tables; composing a sentence there would put
  untranslated English on an Arabic page. The `_code` suffix plus
  `StrictUndefined` makes a template reaching for the wrong field raise rather
  than print an identifier at a reader.
- **The canvas travels with the view.** `width` / `height` live on the chart view,
  because a `viewBox` written literally in a template keeps drawing to the old
  canvas after the geometry changes and every mark silently overflows.

`fonts.py` + `typefaces/` also port across, and they are what make the
tagged-PDF-with-embedded-fonts rule satisfiable for Arabic.

The revised assessment: **this is a port throughout, and the new work is the
Seshat-side bundle and contract-tracing, not the rendering.**

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
  charts.py      chart GEOMETRY as an exact view model; no markup, no prose
  html.py        Jinja2 render of the web surface; autoescape always on
  pdf.py         extends the HTML template + print CSS; PagePrinter port
  chromium.py    the ONE Playwright adapter; pdf.py never imports it
  fonts.py       embedded font payloads (what makes tagged-PDF satisfiable)
  excel.py       xlsxwriter; write_string only; no numeric cells
  layout.py      the print overlay: cover, sections, page breaks
  templates/     report.html.j2, report.pdf.html.j2, report.css,
                 report.print.css, and the chart macro that writes SVG elements
  typefaces/     the font files themselves
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
7. **No `|safe` and no `Markup` on any bundle-reachable path.** A test renders a
   label named `<script>alert(1)</script>` as both a table cell and a chart axis
   label and asserts it arrives escaped in both.
8. **Chart geometry is `Decimal`, never `float`.** A test asserts the coordinate
   type before stringification, so a refactor cannot quietly introduce a float.

## Increments

**Increment A — the contract and all three surfaces, offline.** Bundle built from
committed governed artifacts plus a synthetic fixture, so the whole pipeline is
provable with no database and no browser: `view.py`, `charts.py`, `html.py`,
`excel.py`, `layout.py`, `fonts.py`, `pdf.py` + `chromium.py` behind the port, the
eight invariants, the two extras, and `report-layout.yaml` + its template. Real
PDF bytes require `[report-pdf]`; tests use the fake `PagePrinter`.

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

- **The port is larger than first assessed** — `charts.py`, `fonts.py`,
  `html.py`, `typefaces/` and the templates all come across, not just `pdf.py` and
  `excel.py`. The genuinely new work is the Seshat-side bundle, the
  contract-tracing invariant, and the print overlay. Use the `dataviz` skill for
  chart form and palette choices, which are presentation decisions the port does
  not settle.
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
