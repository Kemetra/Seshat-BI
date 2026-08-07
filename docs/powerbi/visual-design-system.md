# Power BI Visual Design System

The committed design vocabulary the Dashboard Ready stage reasons WITH. It teaches
an agent to DISTINGUISH the artifacts of Power BI dashboard design -- design tokens,
theme JSON, background assets, page blueprint, visual specs, and the Power BI
implementation handoff -- and to route every request to exactly one of four
surfaces and never blend them. It does not design any specific dashboard (that is
the F011/012 `dashboard-design` verb's job) and it implements nothing in Power BI.
Native report mechanics belong to Microsoft's official report-authoring skill
after the gate; F016 is only the parked live semantic execution adapter.

## The four surfaces (route to exactly one)

Power BI dashboard design is four separate surfaces. Route every request to exactly ONE; never blend them.

| # | Surface | What it is | Authoring tool | The rule that keeps it clean |
|---|---------|------------|----------------|------------------------------|
| 1 | Report visuals | cards, charts, slicers, tables/matrices, tooltips, bookmarks, titles, interactions, mobile layout | Microsoft `powerbi-report-authoring` or Power BI Desktop after the gate | every visual binds to a metric contract + a semantic model field; nothing invented |
| 2 | External background/canvas | PNG/SVG/JPG backgrounds, grids, safe zones, static layout containers, exported assets | Figma / Canva / PowerPoint / Illustrator (outside Power BI) | background is STATIC STRUCTURE, never data -- no KPI value, no dynamic title baked in |
| 3 | Theme JSON | color palette, fonts, visual defaults, page/wallpaper defaults, filter-pane defaults, sentiment colors | a JSON file imported into Power BI | theme controls DEFAULTS, never business meaning -- no DAX, no metric, no relationship |
| 4 | Implementation handoff | the bundle an official executor or human uses to build the report | notes only in this slice | this slice STOPS at the handoff boundary -- no PBIP/PBIR edit |

Blending these is the failure mode. Baking a KPI number into a background image
mixes surface 1 into surface 2 (a number that never refreshes). Putting a metric
definition in theme JSON mixes surface 1 into surface 3 (business logic hidden in
a styling file). Editing a PBIP file here crosses into surface 4 (the execution
owner's territory). The discipline that keeps the four apart is the value.

## Distinguish the artifacts (which file is which, which surface it serves)

A design request produces different artifacts with different lifecycles and
different homes. Confusing them is how the surfaces get blended. Each artifact
below names exactly one home (its manifest path) and the surface it serves.

| Artifact | What it is (and what it is NOT) | Home (repo-relative) | Surface |
|----------|---------------------------------|----------------------|---------|
| Design tokens | the tool-agnostic SOURCE of the design language: colors, type scale, spacing, sentiment colors, KPI-card and number-format rules. NOT a Power BI file -- it is read BY the theme and the blueprints. | `design/tokens/tower-retail-design-tokens.yaml` | 3 (source of) |
| Theme JSON | the Power-BI-specific COMPILED default derived from the tokens: a JSON file imported into Power BI that sets palette/fonts/visual+page/wallpaper/filter-pane defaults and sentiment colors. NOT business meaning. | `themes/tower-retail.theme.json` (spec: `templates/theme-json-spec.md`; do/don't: `docs/powerbi/theme-json.md`) | 3 |
| Background assets | static layout STRUCTURE exported from a design tool (PNG/SVG/JPG), imported as a page background; safe zones, grids, containers. NOT data -- no KPI value or dynamic title in the image. | `design/backgrounds/README.md` (spec: `templates/background-spec.yaml`; workflow: `docs/powerbi/background-assets.md`) | 2 |
| Page blueprint | the per-page design INTENT: audience + the one business question + required contracts/model deps (as references) + sections + candidate visuals + QA rules. NOT inlined metric formulas or DAX. | `templates/dashboard-page-blueprint.yaml` (starters: `reports/blueprints/*.yaml`; how-to: `docs/powerbi/dashboard-blueprints.md`) | 1 |
| Visual specs | the per-visual design intent: id/type/business question + the metric contract (by name) + the mapped semantic-model fields + position/formatting/interactions/tooltip/sorting/number-format + anti-pattern checks. NOT an invented metric. | `templates/visual-spec.yaml` | 1 |
| Power BI implementation | the implementation NOTES the official report-authoring skill or a human uses to build the report; the design slice STOPS here. NOT a PBIP/PBIR edit, DAX, or SQL. | `.claude/skills/powerbi-dashboard-design/workflows/powerbi-handoff.md` | 4 |

### Tokens vs theme JSON -- the distinction readers confuse

Design tokens are the tool-agnostic SOURCE; the theme JSON is the Power-BI-specific
COMPILED default. The tokens
(`design/tokens/tower-retail-design-tokens.yaml`) state the design language once --
colors, type scale, spacing, sentiment colors, KPI-card and number-format rules --
independent of any tool. The theme
(`themes/tower-retail.theme.json`) is what Power BI actually imports: a JSON default
built FROM the tokens. Change the language in the tokens; recompile the theme from
it. Keeping them separate keeps the source single and the compiled output
disposable; folding the language into the theme would scatter it across a
tool-specific file. (Same source-vs-compiled split recorded in
`specs/017-powerbi-visual-foundation/plan.md` Structure Decision #2.)

Note: this reference doc is `docs/powerbi/visual-design-system.md`; the surface-1
agent procedure for arranging report visuals is the separate
`.claude/skills/powerbi-dashboard-design/workflows/visual-design-system.md`. They
share a name on purpose (prose reference vs. agent procedure); always cite the full
path so the two do not blur.

## Power BI design principles (generic guidance, not a C086 ruling)

These are the committed defaults a good retail dashboard follows. They are
GENERIC reference -- a deviation is allowed only when recorded as a `warning`-class
design note with a reason (Constitution Principle VI), never silently.

- **Every page answers a business question.** A page exists to answer one named
  question for one audience; if it does not, it is not a page -- it is a pile of
  visuals. State the question in the page blueprint before placing a single visual.
- **Every KPI has comparison and context.** A bare number is not insight. Every
  KPI card carries a comparison (vs. prior period / target / benchmark) and the
  date context it is measured over -- otherwise the reader cannot tell good from bad.
- **Executive pages use fewer visuals.** An executive summary is read in seconds;
  prefer a small KPI strip plus one or two main-insight visuals over a dense grid.
  Detail belongs on diagnostic pages, not the executive page.
- **Slicers should not dominate the page.** Filters are a rail, not the headline;
  a wall of slicers crowds out the answer. Keep the filter rail compact and put
  the insight first.
- **Tables are for detail, not executive insight.** A table answers "show me the
  rows"; it does not deliver a top-line message. Use a chart or KPI for the
  executive insight and reserve tables/matrices for diagnostic and exception detail.
- **Number formats are consistent.** The same measure uses the same format
  everywhere (currency symbol, decimals, thousands separators, percent vs. ratio);
  inconsistent formatting reads as a data error even when the data is correct.
- **Colors carry meaning.** Color encodes something (sentiment, category,
  emphasis) -- it is not decoration. Use sentiment colors for good/warning/bad and
  a stable category palette; do not recolor the same category differently per page.
- **Accessible contrast.** Text and data marks meet a readable contrast ratio
  against their background; avoid dark backgrounds behind dense charts and
  low-contrast pairings. Readability is a design requirement, not a preference.
- **Consistent branch/category colors where applicable.** When a page set compares
  the same branches or product categories, the same entity keeps the same color
  across every page so the eye tracks it without re-learning the legend.
- **Keep a Data Quality and Controls page for serious dashboards.** A dashboard
  people make decisions on carries a page that surfaces freshness, coverage,
  reconciliation, and known data-quality issues -- so a reader can trust (or
  distrust) the numbers on the other pages.

## What this doc does NOT do

- It does NOT define a gate. The hard gate (no data-bound dashboard design before
  the subject area's `semantic_model_ready` is `pass`) and the design-review
  sign-off are owned by `docs/readiness/dashboard-ready.md` and the F011/012
  `dashboard-design` verb. This doc documents and reuses them; it never re-defines
  them or self-grants `dashboard_ready: pass`.
- It does NOT reproduce the full visual-QA anti-pattern catalog -- that prose
  reference lives in `docs/powerbi/visual-qa.md`.
- It does NOT reproduce the theme do/don't list -- that lives in
  `docs/powerbi/theme-json.md`.
- It does NOT edit any PBIP/PBIR file, generate DAX, change SQL, edit any
  semantic-model file, or execute an upstream tool. `powerbi-workflows` selects
  the official report authoring owner or the parked F016 live semantic adapter.

## See also

- The router that classifies a request into one of the four surfaces:
  `.claude/skills/powerbi-dashboard-design/SKILL.md`.
- The other prose references for each surface: `docs/powerbi/background-assets.md`
  (surface 2), `docs/powerbi/theme-json.md` (surface 3),
  `docs/powerbi/dashboard-blueprints.md` (surface 1, page blueprints), and
  `docs/powerbi/visual-qa.md` (surface 1, the anti-pattern reference).
- The stage this foundation backs: `docs/readiness/dashboard-ready.md` (the gate
  to inherit) + `docs/readiness/readiness-model.md` (the four statuses, no score).
- The gated verb this foundation feeds: the F011/012 `dashboard-design` skill
  (spec-only today; see `specs/012-dashboard-design-skill/`).
- Native report execution owner: Microsoft `powerbi-report-authoring` when
  discoverable. Live semantic connection/refresh/query/publish: parked F016.
