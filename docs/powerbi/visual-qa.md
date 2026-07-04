# Power BI Visual QA -- the anti-pattern reference

The PROSE home of the visual-QA anti-pattern reference. This doc explains, in
readable terms, each anti-pattern a Power BI dashboard can fall into, and names
the design principle it violates. It is reference material an agent (and a human
reviewer) consults; it does not itself run a critique.

> **Two QA homes, kept in sync (plan.md Structure Decision #4).** This doc is the
> readable reference. The PROCEDURE that USES it is the
> `powerbi-dashboard-design` skill workflow
> `.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md`. The two
> carry the SAME anti-pattern list -- prose explanations here, the run-it-as-a-check
> procedure there. If you add, remove, or rename an anti-pattern in one, change
> the other in the same edit so they never drift.

## How to read this doc

Each entry below is one anti-pattern. For each: what it looks like, why it hurts
the reader, the design principle it violates (from
`docs/powerbi/visual-design-system.md`), and the fix. The screenshot-critique
procedure (`.claude/skills/powerbi-dashboard-design/workflows/screenshot-review.md`)
walks a page against this list and outputs findings + recommended fixes + the
forbidden-changes list.

This is generic retail-BI guidance, not a ruling about any one subject area or
worked example. It carries placeholders, never a concrete business metric.

## The four surfaces (context for the last three anti-patterns)

Power BI dashboard design is four separate surfaces. Route every request to exactly ONE; never blend them.

| # | Surface | What it is | Authoring tool | The rule that keeps it clean |
|---|---------|------------|----------------|------------------------------|
| 1 | Report visuals | cards, charts, slicers, tables/matrices, tooltips, bookmarks, titles, interactions, mobile layout | Power BI Desktop (later; F016) | every visual binds to a metric contract + a semantic model field; nothing invented |
| 2 | External background/canvas | PNG/SVG/JPG backgrounds, grids, safe zones, static layout containers, exported assets | Figma / Canva / PowerPoint / Illustrator (outside Power BI) | background is STATIC STRUCTURE, never data -- no KPI value, no dynamic title baked in |
| 3 | Theme JSON | color palette, fonts, visual defaults, page/wallpaper defaults, filter-pane defaults, sentiment colors | a JSON file imported into Power BI | theme controls DEFAULTS, never business meaning -- no DAX, no metric, no relationship |
| 4 | Implementation handoff | the bundle a human (later, an adapter) uses to build the report in Power BI Desktop | notes only in this slice | this slice STOPS at the handoff boundary -- no PBIP/PBIR edit, no pbi-cli automation |

The last three anti-patterns below (#11 background containing dynamic values,
and the theme/contract/field entries) are surface-boundary violations: they are a
sign that two surfaces have been blended.

## The anti-patterns

### 1. Too many visuals on one page

**Looks like**: a page crammed with a dozen or more charts, cards, and tables, so
no single object draws the eye and the reader must hunt for the answer.

**Why it hurts**: cognitive overload. An executive page that tries to say
everything says nothing; the one decision the page exists to support gets buried.

**Principle violated**: *executive pages use fewer visuals* and *every page
answers ONE business question*. A page is a question, not a data dump.

**Fix**: cut to the visuals that answer the page's one business question. Move the
rest to a diagnostic/detail page or a drill-through. Keep an executive page within
the conservative max-visuals guidance in
`design/tokens/tower-retail-design-tokens.yaml`.

### 2. KPI without comparison/context

**Looks like**: a card showing a bare number -- a total or a count -- with no prior
period, target, variance, or trend beside it.

**Why it hurts**: a number alone is not insight. The reader cannot tell whether it
is good, bad, up, or down, so the card cannot drive a decision.

**Principle violated**: *every KPI has comparison/context*. A KPI without a
reference point is decoration.

**Fix**: pair the value with at least one of: prior-period delta, target/variance,
or a sparkline/trend. The comparison itself must trace to an approved metric
contract (see #10) -- do not invent the comparison at design time.

### 3. Unclear date context

**Looks like**: numbers on the page with no visible "as of" date, period label, or
date slicer state -- the reader cannot tell what time range the figures cover.

**Why it hurts**: an undated number is unreadable and unauditable. "Sales are 12k"
means nothing without the period; two readers will assume different windows.

**Principle violated**: *every page answers a business question* (a question is
always scoped in time). Date context is part of the answer, not optional chrome.

**Fix**: show the active period explicitly -- a header "as of" / period label, a
visible date slicer, or a date in the subtitle. Make the time grain match the
question's grain.

### 4. Wrong number formats

**Looks like**: currency shown without a symbol or with too many decimals,
percentages shown as raw ratios, large counts without thousands separators, or the
same measure formatted differently on two visuals.

**Why it hurts**: misread values and lost trust. Inconsistent formatting makes the
page look unmaintained and forces the reader to decode each number.

**Principle violated**: *consistent number formats*. A measure should look the same
everywhere it appears.

**Fix**: apply the number-format defaults from
`design/tokens/tower-retail-design-tokens.yaml` (currency, percent, count,
decimal places) consistently. Note: number formatting is a presentation default
(theme/visual format), NOT a metric definition -- the metric's meaning lives in
its contract (F009).

### 5. Slicers taking too much space

**Looks like**: a wall of slicers/filters taking a large share of the canvas,
crowding out the visuals that actually answer the question.

**Why it hurts**: the page becomes a filter form instead of an answer. Reader
attention goes to controls, not insight; the most valuable canvas space is spent
on plumbing.

**Principle violated**: *slicers don't dominate* and *executive pages use fewer
visuals*. Filters serve the answer; they are not the answer.

**Fix**: collapse slicers into a compact filter rail, use the filter pane for
secondary filters, and keep only the few slicers the page's question needs in the
canvas. Reserve the prime canvas for the insight visuals.

### 6. Table used as the main executive visual

**Looks like**: a large detail table or matrix as the centerpiece of an executive
page, where a card or chart should carry the headline.

**Why it hurts**: a table makes the reader compute the insight themselves.
Executives need the conclusion (the trend, the comparison, the exception), not
rows to scan.

**Principle violated**: *tables are for detail, not executive insight* and
*executive pages use fewer visuals*. Detail belongs on a diagnostic/detail page or
a drill-through.

**Fix**: lead with KPI cards and a focused chart that states the conclusion; move
the table to a diagnostic page, an exception-detail section, or a drill-through for
readers who need the rows.

### 7. No visual hierarchy

**Looks like**: every visual the same size and weight, no clear top-left headline,
no grouping -- the page reads as a flat grid with no entry point.

**Why it hurts**: the reader does not know where to look first. A page with no
hierarchy makes the reader build the priority order themselves, every time.

**Principle violated**: *executive pages use fewer visuals* and the page/section
vocabulary in `docs/powerbi/dashboard-blueprints.md` (header -> KPI strip -> main
insight -> diagnostic -> exception-detail), which encodes the intended reading
order. The most important answer should be the most prominent object.

**Fix**: establish a clear reading order -- headline KPI strip at the top, the main
insight largest and top-left of the body, diagnostics secondary, detail last. Use
size, position, and grouping to encode importance.

### 8. Inconsistent branch/category colors

**Looks like**: the same category, branch, or segment drawn in one color on one
visual and a different color on another, so the eye cannot track an entity across
the page.

**Why it hurts**: color is a tracking cue; when it shifts, the reader loses the
thread and may misattribute values. It also reads as careless.

**Principle violated**: *colors carry meaning* and *consistent branch/category
colors where applicable*. A category's color should be stable across the report.

**Fix**: assign each recurring category/branch a fixed color (data colors in the
theme, see `themes/tower-retail.theme.json` and the tokens) and reuse it on every
visual. Keep the palette within the conservative token set.

### 9. No tooltip explanation

**Looks like**: a chart with a non-obvious measure, calculation, or abbreviation
and no tooltip or note explaining what the reader is seeing.

**Why it hurts**: the reader has to guess the definition, or misreads it. A
self-serve dashboard with undocumented measures generates support questions and
mistrust.

**Principle violated**: *colors carry meaning* and *accessible contrast* -- the
principles that a visual should be self-explanatory to its reader. Context belongs
on the visual.

**Fix**: add a tooltip (or a small info note) that states what the measure means
in plain terms. The explanation must match the metric contract's intent -- do not
write a new definition here; reference the contract (F009).

### 10. Visual using a metric with no contract

**Looks like**: a card or chart whose value is a metric that has no approved metric
contract (F009) -- the number was defined at design time to fill the visual.

**Why it hurts**: this is the central failure the readiness system exists to
prevent -- an invented metric, unreviewed, presented as fact. It is the orphan
visual.

**Principle violated**: the **inherited gate** (rule 5) and *every visual binds to
a metric contract*. A visual with no backing contract MUST NOT be emitted.

**Fix**: do NOT emit the visual. Record `orphan visual: no contract for
<question>` as a blocking reason, and route the metric to F009 (metric-contract
store) to be defined and approved first. The foundation never invents a metric to
fill a card.

### 11. Visual using an unmapped field

**Looks like**: a visual bound to a column/field that is not present in the
governed semantic model (F010) -- a field that does not exist in the model the
report references.

**Why it hurts**: the visual cannot resolve, or silently binds to the wrong thing.
It also means design ran ahead of the model.

**Principle violated**: the contract/field requirement -- *every data-bound visual
traces to a field present in the governed semantic model* (FR-002). Visuals bind
only to mapped fields.

**Fix**: do NOT emit the visual. Record `unmapped field: <field>` as a blocking
reason and STOP. The field must be added to the governed model and reach
`semantic_model_ready: pass` upstream before the visual can bind.

### 12. Background containing dynamic values

**Looks like**: a KPI number, a dynamic title, a date, or any other
data/refreshing content baked into the static background image (surface 2) instead
of being a live Power BI visual (surface 1) sitting above it.

**Why it hurts**: a value baked into an image NEVER refreshes -- it is frozen at
export time and will silently go stale and wrong. It also mixes two surfaces.

**Principle violated**: the **surface-2 purity rule** -- *background is STATIC
STRUCTURE, never data*. No KPI value, no dynamic title, no other dynamic content
in a static background.

**Fix**: keep the background to layout structure only (safe zones, containers,
grid -- see `docs/powerbi/background-assets.md`). Put every value, title, and date
in a live Power BI visual placed editable ABOVE the background.

### 13. Theme colors overridden randomly per visual

**Looks like**: individual visuals each setting their own ad-hoc colors instead of
inheriting the theme defaults, so the palette drifts visual-by-visual and the same
category gets different colors (see also #8).

**Why it hurts**: the theme stops being the single source of styling defaults; the
page looks inconsistent and is unmaintainable (a palette change no longer
propagates). It is also the surface-3 boundary being eroded.

**Principle violated**: the **surface-3 purity rule** -- *theme JSON controls
DEFAULTS* -- and *colors carry meaning* / *consistent category colors*. Per-visual
overrides should be the rare, deliberate exception, not the norm.

**Fix**: let visuals inherit the theme's data colors and visual defaults
(`themes/tower-retail.theme.json`). Reserve per-visual color overrides for a
deliberate, documented reason (e.g. a single emphasis), never as the default way to
color a chart. Remember: a sentiment COLOR belongs in the theme; the sentiment
THRESHOLD/RULE is a metric contract (F009), not a styling choice.

## Surface-boundary anti-patterns: why the last three are gravest

Anti-patterns #10-#13 are not just readability problems -- they are blends of two
surfaces or breaches of the inherited gate, the exact drift this foundation
exists to prevent:

- **#10 / #11** breach the gate (rule 5): a visual bound to an invented metric or
  an unmapped field is design running ahead of approved contracts. The fix is to
  STOP and route upstream, not to redesign the visual.
- **#12** blends surface 1 into surface 2 (data into a static background).
- **#13** erodes surface 3 (defaults) into per-visual business styling.

For #10 and #11 the response is always: do not emit the visual, record the
blocking reason, point upstream. For #12 and #13 the response is: move the content
back to the surface it belongs to.

## Readiness wiring

A QA pass records its outcome with the readiness vocabulary
(`docs/readiness/readiness-model.md`): exactly four statuses --
`not_started` / `blocked` / `warning` / `pass` -- plus `evidence[]` and
`blocking_reasons[]`. NEVER a numeric confidence score (roadmap rule 9).

- A readability/severity anti-pattern (e.g. #1, #6, #7) is typically a
  `warning`-class design note: record it with the reason and the recommended fix;
  it does not by itself fail the stage.
- A gate breach (#10, #11) is a `blocking_reason` -- design STOPS until the
  upstream contract/model exists.
- This doc, and the QA procedure that uses it, NEVER self-grant
  `dashboard_ready: pass`. That status is the verb's design-review sign-off, owned
  by `docs/readiness/dashboard-ready.md` + the F011/012 `dashboard-design` verb.
  This foundation documents and reuses that gate; it does not re-define it.

When the surface an issue belongs to is ambiguous, or whether a readability
deviation is acceptable is a judgment call, STOP and ask (Principle V) rather than
self-answering.

## See also

- `.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md` -- the
  PROCEDURE that uses this list (keep the two in sync).
- `.claude/skills/powerbi-dashboard-design/workflows/screenshot-review.md` -- the
  screenshot-critique procedure (findings + fixes + forbidden changes).
- `docs/powerbi/visual-design-system.md` -- the four surfaces + the design
  principles each anti-pattern violates.
- `docs/powerbi/background-assets.md` -- the surface-2 background rules (#12).
- `docs/powerbi/theme-json.md` -- the surface-3 theme do/don't list (#13).
- `docs/powerbi/dashboard-blueprints.md` -- the page section vocabulary (#7).
- `docs/readiness/dashboard-ready.md` -- the inherited gate and the design-review
  sign-off (#10, #11).
- `docs/readiness/readiness-model.md` -- the four-status readiness vocabulary.
- `templates/screenshot-review.md` -- the critique-output template.
