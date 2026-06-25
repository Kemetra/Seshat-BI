# Feature Specification: Power BI Visual Foundation (F011A) -- the design substrate the Dashboard Ready verb reasons with

**Feature**: F011A (roadmap F-number) | **Spec directory**: `017-powerbi-visual-foundation` (next free on-disk slot; the roadmap F-number is authoritative -- see `docs/roadmap/roadmap.md` numbering note)

**Feature Branch**: `017-powerbi-visual-foundation` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-25

**Status**: Implemented (commit `53d43f1`, F011A) -- shipped to `main`

**Input**: "F011A Power BI Visual Foundation. Layer 6 (Dashboard & Delivery). Advances readiness stage: Dashboard Ready. A docs/templates/skill FOUNDATION that teaches an agent to handle Power BI dashboard design across four SEPARATE surfaces -- (1) report visuals, (2) external background/canvas assets, (3) theme JSON, (4) later implementation handoff -- and never to blend them. Docs/templates/skill-only (roadmap rule 8). Generic to retail BI (rule 7). HARD GATES inherited from Dashboard Ready: no design before metric contracts + semantic model contracts exist (rule 5); no PBIP/PBIR edits and no pbi-cli automation in this slice (rule 6, F016 owns that)."

## Why this feature exists

The readiness spine defines Stage 6, **Dashboard Ready** (`docs/readiness/dashboard-ready.md`):
a report is designed AGAINST approved metric contracts, never before them. Feature F011
(on-disk `specs/012-dashboard-design-skill/`) already specs the **verb** that performs that
stage -- a gated skill that binds each visual to one approved contract and STOPS at the
publish boundary. But the verb has nothing to reason WITH. It assumes the agent already
knows the difference between a report visual and a background PNG, what a theme JSON may and
may not control, what a good executive page looks like, and how to critique a screenshot.
Today that knowledge is nowhere committed -- so an agent improvises it per request, which is
exactly the unreviewed drift this kit exists to prevent.

This feature fills that hole with the **design FOUNDATION**: the committed vocabulary,
templates, design tokens, starter theme JSON, page blueprints, and QA reference an agent
consults to design a Power BI dashboard well -- plus a router skill that classifies any
visual-design request into exactly one of four surfaces. It teaches the agent to
DISTINGUISH the surfaces; it does not design any specific dashboard (that is the verb's job)
and it does not implement anything in Power BI (that is F016's job).

It is the agent expression of the principle the whole readiness system rests on: a stage is
a **doc + template + reference** before it is a tool (roadmap rule 8, Principle VIII). The
verb is safe to run only when the agent has a non-improvised design vocabulary to run it
with; this feature is that vocabulary.

## The core idea: four separate surfaces, never blended

Power BI dashboard design is not one activity. It is four, with different artifacts,
different tools, and different rules. The single load-bearing behavior this feature teaches
is to **route each request to exactly one surface and never mix them**:

| # | Surface | What it is | Authoring tool | The rule that keeps it clean |
|---|---------|------------|----------------|------------------------------|
| 1 | **Report visuals** | cards, charts, slicers, tables/matrices, tooltips, bookmarks, titles, interactions, mobile layout -- the live, data-bound objects | Power BI Desktop (later; F016) | every visual binds to a metric contract + a semantic model field; nothing invented |
| 2 | **External background/canvas** | PNG/SVG/JPG backgrounds, grids, safe zones, static layout containers, exported assets | Figma / Canva / PowerPoint / Illustrator (outside Power BI) | background is STATIC STRUCTURE, never data -- no KPI value, no dynamic title baked in |
| 3 | **Theme JSON** | color palette, fonts, visual defaults, page/wallpaper defaults, filter-pane defaults, sentiment colors | a JSON file imported into Power BI | theme controls DEFAULTS, never business meaning -- no DAX, no metric, no relationship |
| 4 | **Implementation handoff** | the bundle a human (later, an adapter) uses to build the report in Power BI Desktop | notes only in this slice | this slice STOPS at the handoff boundary -- no PBIP/PBIR edit, no pbi-cli automation |

Blending these is the failure mode. Baking a KPI number into a background image (mixing 1
into 2) makes a number that never refreshes. Putting a metric definition in theme JSON
(mixing 1 into 3) hides business logic in a styling file. Editing a PBIP file in this slice
(crossing into 4) steps into the deferred adapter's territory. The feature's value is the
discipline that keeps the four apart.

## Relationship to F011 / on-disk 012 (the no-divergent-source-of-truth boundary)

This feature deliberately overlaps the ground of F011 (on-disk `012-dashboard-design-skill`).
The constitution forbids "a second, divergent source of truth" (Governance, amendment clause
4), so the boundary is stated here and MUST hold:

- **F011 / 012 is the VERB.** `.claude/skills/dashboard-design/SKILL.md` -- a gated procedure
  that, for one subject area whose `semantic_model_ready` is `pass`, authors a layout plan +
  visual list + visual->contract binding map and STOPS. It is the thing that designs a
  specific dashboard.
- **F011A is the FOUNDATION.** The committed vocabulary, templates, tokens, theme, blueprints,
  and QA reference that ANY dashboard design reads -- plus a router that classifies the four
  surfaces. It is the thing the verb reasons WITH.
- **F011A adds NO new gate.** Dashboard Ready's gate (rule 5: contracts first; the design
  review sign-off) and the publish boundary (rule 6: no pbi-cli/PBIP) are owned by the stage
  doc + F011/012 and are reused VERBATIM here. This feature documents them; it does not
  re-decide or duplicate them.
- **Open decision O-1 (recorded, not blocking): does F011A's router skill
  (`powerbi-dashboard-design`) sit ALONGSIDE 012's `dashboard-design`, or eventually absorb
  it?** Recommended reversible default: **alongside.** F011A's `powerbi-dashboard-design`
  is the broad design-surface router (the foundation's front door); it ROUTES the
  "design a dashboard from contracts" intent to 012's `dashboard-design` verb rather than
  re-implementing the gate. If review prefers a single skill, the merge is a later, separate
  decision recorded in tasks -- this slice does not pre-empt it. (Same posture 010 used for
  its storage-path O-1.)

## Architecture (a docs/templates/skill foundation; no codegen, no engine, no CLI)

The foundation is committed text only:

- **One router skill** -- `.claude/skills/powerbi-dashboard-design/SKILL.md` + a `workflows/`
  set of agent-procedure markdown. (Deviation from the literal `skills/` path in the input:
  this repo discovers skills only under `.claude/skills/` -- all 20 existing skills live
  there -- so the skill MUST go there to load. Recorded in plan.md Structure Decision.)
- **Reference docs** under `docs/powerbi/` -- the prose that explains the four surfaces, the
  design principles, and the theme-JSON do/don't list.
- **Generic templates** under `templates/` -- copy-me blanks for a page blueprint, a visual
  spec, a background spec, a theme-JSON spec, and a screenshot review.
- **Design system seed** under `design/` (tokens, grids, backgrounds README), a starter
  theme under `themes/`, and four starter page blueprints under `reports/blueprints/`.

There is NO codegen engine that emits a `.pbir`, NO theme generator, and NO `retail design`
CLI subcommand -- by design. The value is JUDGMENT (which surface a request belongs to, which
visual fits a contract's grain, whether a page answers a business question), and judgment is
what a human reviewer signs off. The agent reading the foundation and authoring reviewable
design text is the right grain (Principle VIII docs-first; roadmap rule 8).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Route a request to exactly one of the four surfaces (Priority: P1)

An analyst asks the agent something about a dashboard -- "redesign this page", "critique this
screenshot", "make a branded background", "pick our colors and fonts", "arrange these
cards". The agent reads the router skill and classifies the request into exactly ONE of the
four surfaces (report visuals / background-canvas / theme JSON / handoff) plus the right
intent, then opens the matching workflow. It never blends surfaces (e.g. it never proposes
baking a KPI into a background, never puts a metric in theme JSON).

**Why this priority**: routing is the feature. The four-surface distinction is the one new
load-bearing idea this slice adds; everything else is reference material the router points
at. If the agent cannot classify a request, the foundation does not function.

**Independent Test**: given a fixture set of ~10 generic design requests (at least two per
surface, plus deliberately ambiguous ones), the agent names the surface + intent + the
workflow file it would open for each; an auditor confirms each maps to exactly one surface,
the ambiguous ones are surfaced as a clarification (Principle V) not silently guessed, and
zero responses blend surfaces.

**Acceptance Scenarios**:

1. **Given** "design a new executive page", **When** the agent routes it, **Then** it opens
   `page-blueprint.md` (+ `visual-design-system.md` for arrangement) and treats it as
   surface 1, not 2/3.
2. **Given** "critique this dashboard screenshot", **When** the agent routes it, **Then** it
   opens `screenshot-review.md` and produces a critique, NOT a redesign or a new file.
3. **Given** "make a branded background for our pages", **When** the agent routes it, **Then**
   it opens `background-asset-design.md` (surface 2) and treats the output as static
   structure -- it never proposes putting a live KPI in the image.
4. **Given** "set our colors, fonts, and default formatting", **When** the agent routes it,
   **Then** it opens `theme-json-design.md` (surface 3) and never puts a metric definition,
   DAX, or relationship in the theme.
5. **Given** an ambiguous request ("make this look better"), **When** the agent routes it,
   **Then** it asks which surface is meant (Principle V) rather than inventing a blended plan.

### User Story 2 - Refuse to design when the upstream contracts do not exist (Priority: P1)

A request would design data-bound visuals (surface 1) for a subject area whose metric
contracts (F009) and `semantic_model_ready` (F010) are not yet `pass`. The foundation's hard
gate -- inherited verbatim from Dashboard Ready and F011/012 -- makes the agent REFUSE: no
visual is bound to an invented metric, no dashboard is designed before its contracts exist.
The agent records the blocking reason and STOPS, and the request is routed to the upstream
stage instead. Pure styling work that touches no metric (a background's safe-zones, a theme's
palette) is NOT gated and may proceed.

**Why this priority**: the gate is what makes any of this safe to automate (roadmap rule 5).
A foundation that taught great visual design but let the agent design before contracts exist
would defeat the readiness system. Refusing is as load-bearing as routing.

**Independent Test**: given a fixture subject area with `semantic_model_ready` in each
non-`pass` status, a "design the KPI visuals" request yields zero data-bound design + the
matching blocking reason; an identical-shaped "design the background safe zones" request
(no metric) is allowed; an auditor confirms the gate fired on the data-bound case and only
that case.

**Acceptance Scenarios**:

1. **Given** `semantic_model_ready` is not `pass` (no approved contracts), **When** a
   data-bound visual is requested, **Then** the agent designs no such visual, records the
   blocking reason ("no approved metric contracts -- Dashboard Ready gate, rule 5"), and
   points to the upstream stage.
2. **Given** a visual is proposed for a metric with no contract, **When** the agent drafts
   it, **Then** it does NOT emit the visual -- it records "orphan visual: no contract for
   <question>" (the foundation never invents a metric to fill a card).
3. **Given** a visual would use a field not present in the governed semantic model, **When**
   the agent drafts it, **Then** it records "unmapped field" and STOPS -- it binds visuals
   only to mapped semantic-model fields.
4. **Given** a request is pure styling with no metric (background grid, theme palette),
   **When** the agent routes it, **Then** it proceeds -- surfaces 2 and 3 carry structure and
   defaults, not data, so they are not gated on contracts.

### User Story 3 - Keep the four surfaces and their artifacts cleanly separated (Priority: P1)

The foundation's templates and reference docs each belong to exactly one surface and
encode that surface's rule. A page blueprint references (does not embed) its required metric
contracts and theme; a background spec lists forbidden dynamic content; a theme-JSON spec
lists what the theme must NOT control. The agent, following them, produces artifacts that
never blend a surface into another.

**Why this priority**: the separation is what the reference material exists to enforce. The
templates are the durable mechanism (the agent and a human both read them) that keeps
"background is structure not data" and "theme is defaults not meaning" from being
re-litigated per dashboard.

**Independent Test**: read each committed template; confirm the page blueprint references
contracts/theme/background by name (does not inline metric formulas or theme colors), the
background spec has an explicit "forbidden dynamic content" section, the theme-JSON spec has
an explicit "must NOT control" section, and no template carries C086/pharmacy specifics.

**Acceptance Scenarios**:

1. **Given** `templates/dashboard-page-blueprint.yaml`, **When** it is read, **Then** it
   carries readiness dependencies + required metric contracts + required semantic model
   contract as REFERENCES (names/paths), never inlined metric formulas or DAX.
2. **Given** `templates/background-spec.yaml`, **When** it is read, **Then** it has a
   "forbidden dynamic content" section that explicitly bans KPI values and dynamic titles in
   the static image.
3. **Given** `templates/theme-json-spec.md`, **When** it is read, **Then** it lists both what
   the theme controls (palette/fonts/defaults/filter pane) and what it must NOT control (DAX,
   metric definitions, relationships, source mapping, storytelling, validation).
4. **Given** the four starter `reports/blueprints/*.yaml`, **When** they are read, **Then**
   each names its required metric contracts and semantic-model dependencies as placeholders
   and invents no concrete business metric beyond a named placeholder.

### Edge Cases

- **A request spans two surfaces** ("design the page AND its background"). The agent splits
  it into two routed sub-tasks (surface 1 + surface 2), each with its own artifact, rather
  than producing one blended plan.
- **A screenshot critique implies a metric is wrong.** The critique surface (surface 1, QA)
  may FLAG that a visual seems to use an uncontracted metric, but it does not redefine the
  metric (that is F009) -- it records the finding and points upstream.
- **A user wants a dark, dense executive page.** The foundation records the readability
  concern (dark backgrounds behind dense charts) as a `warning`-class design note and
  proposes the accessible alternative; it does not silently override the user, nor silently
  comply against the documented principle.
- **A theme JSON the user supplies tries to encode a sentiment rule by metric.** The agent
  separates: sentiment COLORS belong in the theme (surface 3); the sentiment THRESHOLD/RULE
  is business logic that belongs in a metric contract (F009) -- it does not let the theme
  carry the rule.
- **No metric contracts exist yet for the subject area.** Surface-1 design is gated (US2);
  but the foundation's generic templates, tokens, theme, and blueprints are still authorable
  as GENERIC reference (they carry placeholders, not a specific subject area's metrics).
- **The user asks to "just build it in Power BI" / run pbi-cli.** The agent STOPS at the
  handoff boundary (surface 4): it produces implementation notes only and names F016 as the
  owner of any PBIP/PBIR edit or pbi-cli automation (rule 6).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The router skill MUST classify any visual-design request into exactly ONE of
  four surfaces -- report visuals, external background/canvas, theme JSON, implementation
  handoff -- plus its intent, and open the single matching workflow. It MUST NOT produce a
  plan that blends two surfaces (FR-001 is the core routing behavior).
- **FR-002**: The foundation MUST require that every data-bound visual trace to (a) an
  approved metric contract (F009) and (b) a field present in the governed semantic model
  (F010). A visual with no backing contract is an orphan and MUST NOT be emitted; a field not
  in the model is unmapped and MUST be recorded as a blocking reason.
- **FR-003**: The foundation MUST NOT invent, define, or alter a metric. Metric definition is
  F009's job; the foundation only references contracts that already exist and are approved.
- **FR-004**: The foundation MUST inherit the Dashboard Ready hard gate VERBATIM: no
  data-bound dashboard design before the subject area's `semantic_model_ready` is `pass`
  (rule 5). It MUST NOT define a new gate, a new readiness status meaning, or a competing
  copy of the gate (no divergent source of truth).
- **FR-005**: The foundation MUST document background/canvas assets as STATIC STRUCTURE, not
  data: it MUST forbid baking any KPI value, dynamic title, or other dynamic content into a
  static background image, and the background template MUST carry an explicit
  "forbidden dynamic content" section.
- **FR-006**: The foundation MUST document theme JSON as DEFAULTS ONLY: it controls palette,
  fonts, visual defaults, page/wallpaper defaults, filter-pane defaults, and sentiment
  colors; it MUST NOT control DAX, metric definitions, semantic-model relationships, source
  mapping, visual storytelling, or data validation -- and the theme spec MUST list both sides
  explicitly.
- **FR-007**: This slice MUST NOT edit any PBIP/PBIR file, generate DAX, change SQL, edit any
  semantic-model file, or add pbi-cli automation. The handoff workflow MUST stop at
  implementation NOTES and name F016 as the owner of any execution step (rule 6).
- **FR-008**: All foundation artifacts MUST be generic to retail BI (rule 7): no
  C086/pharmacy specifics in any skill, doc, template, token file, theme, or blueprint.
  Worked values belong only to a per-subject-area instance; C086 is an example, not the
  schema (Principle VII).
- **FR-009**: The foundation MUST stop at Principle V judgment calls -- which business
  question a page answers, whether a readability/grain deviation is acceptable, which surface
  an ambiguous request belongs to -- surfacing them for a human rather than self-answering.
- **FR-010**: The foundation MUST record design readiness consistent with the readiness model
  (`not_started` / `blocked` / `warning` / `pass` + `evidence[]` + `blocking_reasons[]`) and
  MUST NOT fabricate a confidence score (roadmap rule 9). It MUST NOT self-grant
  `dashboard_ready: pass` -- that needs the owner's design-review approval (owned by F011/012).
- **FR-011**: The router skill MUST explicitly distinguish the four surfaces in its own text
  (a named router table mapping request -> surface -> workflow), so the distinction is
  committed, not improvised per request.
- **FR-012**: The foundation's design principles MUST be committed as reference (every page
  answers a business question; every KPI has comparison/context; executive pages use fewer
  visuals; tables are for detail not executive insight; consistent number formats; colors
  carry meaning; accessible contrast; consistent branch/category colors where applicable; a
  Data Quality & Controls page for serious dashboards) -- as generic guidance, not a C086
  ruling.
- **FR-013**: The foundation MUST provide a visual-QA reference of anti-patterns (too many
  visuals; KPI without comparison; unclear date context; wrong number formats; slicers
  dominating; table as the main executive visual; no hierarchy; inconsistent category colors;
  no tooltip explanation; visual using a metric with no contract; visual using an unmapped
  field; background containing dynamic values; theme colors overridden randomly per visual)
  and a screenshot-critique procedure that outputs findings + recommended fixes + the
  forbidden-changes list.
- **FR-014**: All committed files MUST be ASCII, UTF-8 without BOM, with short repo-relative
  paths (`<= 200` chars), and MUST NOT bake in any real connection host or secret
  (Principle IX + G6).

### Key Entities

- **Surface (the central concept)**: one of four design domains -- report visuals,
  external background/canvas, theme JSON, implementation handoff -- each with its own tool,
  artifact, and rule. The router classifies every request into exactly one.
- **Router skill (output)**: `.claude/skills/powerbi-dashboard-design/SKILL.md` + its
  `workflows/` -- agent-procedure text whose front door is a request->surface->workflow
  table; it routes, it does not itself design a specific dashboard or implement anything.
- **Reference docs (output)**: `docs/powerbi/*.md` -- the prose that explains the surfaces,
  the design principles, the background workflow, and the theme do/don't list.
- **Generic templates (output)**: `templates/*` -- copy-me blanks (page blueprint, visual
  spec, background spec, theme-JSON spec, screenshot review), each encoding one surface's
  rule, each generic.
- **Design tokens (output)**: `design/tokens/tower-retail-design-tokens.yaml` -- a
  conservative executive retail palette/typography/spacing/KPI-card seed (no overdesigned
  SaaS styling), referenced by the theme.
- **Starter theme (output)**: `themes/tower-retail.theme.json` -- a minimal, conservative,
  starter Power BI theme that MUST be validated in Power BI Desktop before use (the exact
  theme schema is treated as uncertain and documented as such).
- **Starter page blueprints (output)**: four `reports/blueprints/*.yaml` (executive summary,
  branch performance, product mix, data-quality control room) -- each states audience +
  business question + required contracts/model deps (as placeholders) + sections +
  candidate visuals + QA rules, inventing no concrete metric.
- **Approved metric contract / governed semantic model (inputs, from F009/F010)**: the
  upstream artifacts every data-bound visual references. This feature consumes them; it never
  defines them.
- **Design readiness record (output)**: the `dashboard_ready` stage notes (status + evidence
  + blocking reasons), consistent with the readiness model, never a fabricated score, never a
  self-granted `pass`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixture set of generic design requests (>= 2 per surface + ambiguous
  ones), the router classifies 100% into exactly one surface + intent; 0 responses blend two
  surfaces; ambiguous requests are surfaced as a clarification, not silently guessed.
- **SC-002**: For every non-`pass` `semantic_model_ready` status, the foundation produces 0
  data-bound visual designs and records the matching blocking reason -- the hard gate (rule 5)
  holds in 100% of gated cases; pure-styling (surface 2/3, no metric) requests are NOT gated.
- **SC-003**: Across all runs the foundation emits 0 PBIP/PBIR edits, 0 DAX, 0 SQL changes, 0
  semantic-model edits, and 0 pbi-cli commands -- the handoff boundary (rule 6) and the
  no-data-edit guardrails hold 100% of the time.
- **SC-004**: 100% of data-bound visuals the foundation describes cite exactly one approved
  metric contract by name AND a mapped semantic-model field; 0 cite an invented metric or an
  unmapped field.
- **SC-005**: Every committed background template/spec carries an explicit "forbidden dynamic
  content" section banning KPI values and dynamic titles in static images; 0 foundation
  artifacts place a dynamic value inside a static background.
- **SC-006**: The theme-JSON spec lists both what the theme controls and what it must NOT
  control (DAX/metrics/relationships/source-mapping/storytelling/validation); 0 theme artifacts
  encode business logic.
- **SC-007**: 0 C086/pharmacy specifics appear in any committed foundation artifact (generic,
  rule 7); a reviewer scanning every file finds only generic placeholders.
- **SC-008**: `retail check` exits 0 with its rule count UNCHANGED after this slice (the
  foundation adds no rule and edits no governed PBIP/SQL/TMDL text); all files are ASCII +
  UTF-8 no BOM with paths `<= 200` chars.
- **SC-009**: The foundation defines `dashboard_ready` readiness with the four statuses +
  evidence + blockers and never a numeric score; it writes `dashboard_ready: pass` in 0% of
  runs (the `pass` is the verb's design-review, F011/012, not this foundation's).

## Assumptions

- **F009 (metric-contract store) and F010 (semantic-model-readiness) are the upstream
  dependencies.** Every data-bound visual references their outputs (approved contracts + a
  bound governed model). Surface-1 design is `not_started` for a subject area until they
  exist and `semantic_model_ready` is `pass`. Surfaces 2 and 3 (structure, defaults) are not
  gated on them. C086 is the first worked example, not the schema.
- **F011 / on-disk 012 (dashboard-design verb) is the consumer.** This foundation is the
  vocabulary that verb reads; the verb owns the design-review gate and the `dashboard_ready:
  pass`. F011A adds no second gate (the no-divergent-source-of-truth boundary above). O-1
  (router alongside vs. absorb 012) is recorded with a reversible default (alongside).
- **The deferred publishing/authoring engine is F016** (pbi-cli/PBIP adapter, the last and
  gated feature). This slice stops at the handoff boundary and never enters it (rule 6).
- **Skill location is `.claude/skills/`, not top-level `skills/`.** This repo discovers
  skills only there (all 20 existing skills live under `.claude/skills/`); the input's literal
  `skills/` path would be a non-loadable artifact. Recorded as a deliberate, reasoned
  deviation in plan.md.
- **Reuse over new surface (Principle II, YAGNI):** docs/templates/skill only -- no codegen
  engine, no theme generator, no `retail design` CLI, no new `retail check` rule. The new
  top-level dirs (`design/`, `themes/`, `reports/`) are justified in plan.md's Structure
  Decision.
- **The starter theme JSON schema is treated as UNCERTAIN.** `themes/tower-retail.theme.json`
  is a minimal conservative starter that MUST be validated in Power BI Desktop before use;
  the slice documents this rather than claiming schema completeness.
- **Generic templates carry no pharmacy specifics** (rule 7, Principle VII); worked values
  live only in a per-subject-area instance.
- **This is a planning + foundation-authoring slice consistent with the readiness roadmap**
  (Layer 6, Dashboard Ready). It changes no existing gate, moves no existing doc, and writes
  no runtime code.
