---
name: powerbi-dashboard-design
description: >-
  The Power BI VISUAL/DESIGN layer of the Tower BI Readiness System. Use when
  someone asks about dashboard design, page layout, a background/canvas asset, a
  theme/colors choice, a screenshot critique, a mobile layout, or a Power BI
  handoff in the Seshat BI repo. This skill ROUTES a design request
  into exactly ONE of four surfaces (report visuals, external background/canvas,
  theme JSON, implementation handoff) and opens the matching workflow. It is a
  router and a vocabulary, not a builder: it never edits a PBIP/PBIR file, never
  generates DAX, and never invents a metric. The gated "design a dashboard from
  approved contracts" intent it hands off to the F011/012 dashboard-design verb.
---

# powerbi-dashboard-design

The front door of the Power BI design FOUNDATION. The readiness spine defines
Stage 6, **Dashboard Ready** (`docs/readiness/dashboard-ready.md`): a report is
designed AGAINST approved metric contracts, never before them. This skill is the
committed design vocabulary that stage reasons WITH -- it classifies any
visual-design request into one of four separate surfaces and opens the right
workflow, so the four-surface distinction is committed once here instead of being
improvised per request.

This skill ROUTES and INSTRUCTS; it does not itself design a specific dashboard
and it implements nothing in Power BI. Designing a specific dashboard from
approved contracts is the F011/012 `dashboard-design` verb's job; executing it in
Power BI (PBIP/PBIR authoring, pbi-cli, workspace publish) is F016's job.

## The four surfaces (route to exactly one)

Power BI dashboard design is four separate surfaces. Route every request to exactly ONE; never blend them.

| # | Surface | What it is | Authoring tool | The rule that keeps it clean |
|---|---------|------------|----------------|------------------------------|
| 1 | Report visuals | cards, charts, slicers, tables/matrices, tooltips, bookmarks, titles, interactions, mobile layout | Power BI Desktop (later; F016) | every visual binds to a metric contract + a semantic model field; nothing invented |
| 2 | External background/canvas | PNG/SVG/JPG backgrounds, grids, safe zones, static layout containers, exported assets | Figma / Canva / PowerPoint / Illustrator (outside Power BI) | background is STATIC STRUCTURE, never data -- no KPI value, no dynamic title baked in |
| 3 | Theme JSON | color palette, fonts, visual defaults, page/wallpaper defaults, filter-pane defaults, sentiment colors | a JSON file imported into Power BI | theme controls DEFAULTS, never business meaning -- no DAX, no metric, no relationship |
| 4 | Implementation handoff | the bundle a human (later, an adapter) uses to build the report in Power BI Desktop | notes only in this slice | this slice STOPS at the handoff boundary -- no PBIP/PBIR edit, no pbi-cli automation |

Blending these is the failure mode. Baking a KPI number into a background image
mixes surface 1 into surface 2 (a number that never refreshes). Putting a metric
definition in theme JSON mixes surface 1 into surface 3 (business logic hidden in
a styling file). Editing a PBIP file here crosses into surface 4 (the deferred
adapter's territory). The discipline that keeps the four apart is the value.

## Router: request -> workflow

Classify the request, then open the single matching workflow under `workflows/`.

| Request | Surface | Open this workflow |
|---------|---------|--------------------|
| New dashboard / page design | 1 | `workflows/page-blueprint.md` |
| Existing screenshot critique | 1 | `workflows/screenshot-review.md` |
| Background / canvas request | 2 | `workflows/background-asset-design.md` |
| Colors / fonts / default formatting | 3 | `workflows/theme-json-design.md` |
| Chart / card / slicer arrangement | 1 | `workflows/visual-design-system.md` + `workflows/page-blueprint.md` |
| Final review | 1 | `workflows/dashboard-qa.md` |
| Mobile-specific layout | 1 | `workflows/mobile-layout.md` |
| Build / implement in Power BI | 4 | `workflows/powerbi-handoff.md` |
| Review / verify a built PBIR page | 4 | `workflows/visual-implementation-review.md` |

Routing rules:

- **Exactly one surface per request.** Name the surface + the intent + the
  workflow file before doing anything else. Never produce a plan that blends two
  surfaces.
- **A request that spans two surfaces** ("design the page AND its background")
  splits into two routed sub-tasks (surface 1 + surface 2), each with its own
  artifact -- never one blended plan.
- **An ambiguous request** ("make this look better") is a Principle V STOP: ask
  which surface is meant rather than inventing a blended plan.

## Hard rules (carry into every workflow)

- **Metrics come from metric contracts only.** The foundation never invents,
  defines, or alters a metric -- metric definition is F009's job. A data-bound
  visual with no backing approved contract is an orphan and MUST NOT be emitted.
- **Visuals map to semantic-model fields.** Every data-bound visual binds to a
  field present in the governed semantic model (F010). A field not in the model
  is unmapped and is recorded as a blocking reason -- not designed around.
- **Background = structure, not data** (surface 2). Never bake a KPI value, a
  dynamic title, or any other dynamic content into a static background image.
- **Theme = defaults, not meaning** (surface 3). The theme controls palette,
  fonts, visual/page/wallpaper/filter-pane defaults, and sentiment COLORS only;
  it MUST NOT control DAX, metric definitions, relationships, source mapping,
  storytelling, or validation. (A sentiment COLOR is the theme's; the sentiment
  THRESHOLD/RULE is a metric contract, F009.)
- **PBIP/pbi-cli implementation is later (F016)** unless a request explicitly
  scopes it -- and even then this slice produces NOTES only.
- **STOP before editing any PBIP/PBIR file.** This skill edits no PBIP/PBIR,
  generates no DAX, changes no SQL, and edits no semantic-model file.

## The inherited gate

No data-bound dashboard design before the subject area semantic_model_ready is pass (roadmap
rule 5). This feature DEFINES NO new gate and is NOT a second source of truth: the gate, the
design-review sign-off, and the dashboard_ready: pass are owned by docs/readiness/dashboard-ready.md
and the F011/012 dashboard-design verb. This feature documents and reuses them.

The gate applies to data-bound work (surface 1). Pure-styling work that touches
no metric -- a background's safe zones (surface 2), a theme's palette (surface 3)
-- is NOT gated and may proceed. Record readiness with the four statuses only
(`not_started` / `blocked` / `warning` / `pass`) plus `evidence[]` and
`blocking_reasons[]`; never a numeric score, and never self-grant
`dashboard_ready: pass` (that is the verb owner's recorded design-review).

**Routing the gated intent:** the "design a dashboard from approved contracts"
intent routes to the F011/012 `dashboard-design` verb (it sits O-1 alongside this
router). This skill points that intent at the verb; it does not re-implement the
gate or design the specific dashboard itself.

## See also

- The prose reference for each surface: `docs/powerbi/*.md` (visual-design-system,
  background-assets, theme-json, dashboard-blueprints, visual-qa).
- The stage this foundation backs: `docs/readiness/dashboard-ready.md` (the gate
  to inherit) + `docs/readiness/readiness-model.md` (the four statuses, no score).
- The gated verb this router hands off to: the F011/012 `dashboard-design` skill
  (`.claude/skills/dashboard-design/SKILL.md`; spec at `specs/012-dashboard-design-skill/`).
- The deferred execution owner: F016 (PBIP/PBIR authoring, pbi-cli, publish).
- The design-foundation idea lane: `docs/roadmap/idea-backlog.md` `## Design Foundation`
  -- the categorical cohort where design-layer ideas (`strengthens_layer = design-system`)
  land in the idea bank (exploratory, not a roadmap).
