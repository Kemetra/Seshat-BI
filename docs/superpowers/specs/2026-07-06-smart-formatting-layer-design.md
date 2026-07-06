# Smart-formatting / design-intelligence layer -- design

- **Date:** 2026-07-06
- **Author:** agent (brainstorming, 7-agent explore->critique->synthesize workflow) + Ahmed Shaaban (decisions)
- **Surface:** the DEFINE side of dashboard design -- proposes a formatting plan the
  shipped PBIR adapter (A/B/C) applies. Routed by `powerbi-dashboard-design/SKILL.md`.
- **Status:** design, pending owner review before writing-plans.

## What this is (and the honest ceiling)

An Opus reasoning layer that **proposes a traceable formatting plan** for a report --
which theme, which per-visual formatting, which category colors -- from the kit's
committed design-QA rubric + tokens + the report's existing visuals/contracts. The 3
shipped `pbir-*` adapter verbs then **apply** the applyable subset; a new lint
**checks** the plan's shape; a **named human ratifies** it and is the only one who can
judge the rendered result good.

**The honest ceiling (owner-accepted):** this layer produces a **consistent,
theme-conformant, correctly-formatted** dashboard baseline -- NOT "brilliant/creative
automatically." It formats **blind** (the sandbox cannot render Power BI); it can
prove a formatting choice's citation *resolves*, never that the choice *serves* the
principle. "Brilliant" needs a human render + judgment. We state this exactly as
ADR 0015 already does ("great professional dashboards remains a separate concern,
explicitly NOT claimed"). This design does not overclaim it.

## Architecture -- three parts, along the kit's DEFINE / CHECK / execute grain

Mirrors the existing `theme-gen -> pbir-verbs` split. NO new core reasoning verb --
reasoning is a skill (non-deterministic LLM judgment); the core's contribution is the
deterministic lint.

| Role | Where | What | New? |
|------|-------|------|------|
| REASON (propose) | a new workflow in the `powerbi-dashboard-design` skill (Opus) | reads approved artifacts + rubric -> emits the ledger | new workflow |
| ARTIFACT | committed `mappings/<subject>/design/formatting-plan.md` | the git-reviewable ledger; `status: warning`, no score | new template |
| CHECK | a new **DL7** lint in `src/retail/rules/` (DL1-DL6 exist; DL7 is next free -- confirm against the live registry at build time) | validates ledger *well-formedness* only | new rule |
| EXECUTE (apply) | the existing 3 `pbir-*` verbs | apply a ratified plan | reused unchanged |
| APPROVE | the existing DL4 / RS1 / `dashboard-ready.md` gate | human sign-off | reused, no parallel gate |

**Consumes (all committed, read-only, by reference):** the design-QA rubric
(`docs/powerbi/visual-qa.md`); design tokens + a committed generated theme; the
approved visual-contract-binding-map + `visual-list.md` + `dashboard-layout.md`; each
existing `visual.json`; metric contracts (to READ names, never redefine).
**Precondition (inherited gate):** an APPROVED binding-map + `semantic_model_ready: pass`.
Refuses to run before it.

**Produces:** one `formatting-plan.md` ledger per subject. Writes no PBIR, touches no
model, invents no metric and no color.

**The ledger speaks the adapter's real nested shape -- no translator.** Rows author
`container -> group -> {property: value}` directly (the `pbir_visual_format.py` input),
never an invented flat shape -- a translator would be a third place formatting truth
lives and the natural home for a binding/geometry leak.

## The Formatting Plan ledger -- the anti-vibes artifact

One row per formatting decision. Every row MUST cite the rubric anti-pattern it
addresses AND the token it draws from -- a row missing either fails the lint and
cannot be applied. Words, never numbers (rule #9).

| field | meaning |
|-------|---------|
| `target` | `visual_id` (from the binding-map) or `page:<name>` |
| `container`/`group`/`property`/`value` | the adapter's real nested formatting shape |
| `principle_cited` | a resolvable `visual-qa.md` anti-pattern number |
| `token_cited` | a resolvable path in the tokens YAML |
| `apply_verb` | `A` theme / `B` format / `C` page-bg / `handoff-only` (no apply path) |
| `status` | `proposed` / `needs-owner-decision` / `blocked-orphan` |
| `rationale` | words-only why |

Footer: `readiness.status: warning` (never self-granted pass);
`blocking_reasons: [not rendered -- screenshot-review pending]`;
`ratification.ratified_by: ""` (the agent is structurally forbidden to fill it);
**no `score:`/`confidence:` field exists by design.**

### The 13 anti-patterns partition by apply-path -- this partition IS the design

- **APPLY-able** (property-level; a citation is meaningful): #4 number formats, #9
  tooltip presence, #12 background-carries-no-data, #13 theme-inheritance /
  documented per-visual override, #3 date-context *only when surfacing an existing
  date field via subtitle*, #8 category colors *(see caveat below)*.
- **DETECT-only, no apply-path** (geometry/type -- the verbs cannot write position,
  size, or `visualType`): #1, #5, #6, #7 -> emitted as `handoff-only` notes for a
  human / Desktop / a future increment D.
- **STOP-upstream** (binding or creation -- forbidden by constitution + adapter): #2
  KPI-without-comparison, #10 orphan, #11 unmapped-field, #3-as-adding-a-date-slicer.

The split axis for #2/#3: **surfacing an existing field** = applyable; **adding a new
field/slicer/comparison** = binding = STOP.

**#8 category-color caveat (owner decision):** safe pinning needs a committed
enumeration of category members. Absent that, #8 rows are emitted as
`needs-owner-decision`, never auto-`proposed` (they would be guessing). Owner ruled
(2026-07-06): include #8 in slice 1 under this downgrade.

## The blind-formatting gap -- handled honestly (owner chose the open loop)

The loop is **open** and named as such.

- **Verified PRE-apply (deterministic, in the lint):** every row's citations
  *resolve*; only allow-listed containers/groups are touched; the proposed change
  leaves `query`/`visualType` byte-identical (the adapter's FR-003 guarantee applied
  to the plan); no `apply_verb:B` row targets a non-binding-map visual; no numeric
  score; `ratified_by` not agent-filled.
- **NOT verified -- stated out loud:** the lint checks a citation *resolves*, never
  that the decision *serves* the principle. Opus can attach a plausible-but-wrong
  citation and pass. "Brilliant" is never earned here.
- **Two rules keep the open loop honest, not falsely closed:**
  1. An applyable row may NEVER cite a render-only anti-pattern (#1/#5/#6/#7) as
     *resolved* -- making a title bolder does not establish hierarchy (that is
     size+position = `handoff-only`). The lint forbids this category error.
  2. The stated ceiling is consistent / conformant, never brilliant-automatically.
- **The only path that earns "good":** propose -> lint -> (human renders in Desktop)
  -> the existing `screenshot-review.md` critique -> revise. The render edge is a
  human / F016 seam, never autonomous. F016 may later automate the render half; it
  never becomes the judge.
- **SVG preview: DEFERRED** (owner chose the open loop without it).

## Principle-V STOPs (stay the owner's; `needs-owner-decision`, never auto-proposed)

1. Which question is the headline, when the questions are not ranked.
2. Density beyond the token ceiling (`max_visuals_per_executive_page`) -- a warning
   the owner rules on, never an auto-cut.
3. Color that carries MEANING (brand palette; a sentiment threshold is F009). The
   layer proposes only generic-token colors.
4. Choosing a background image where more than one committed asset fits, or none vs an
   asset.
5. Surfacing a data-honesty caveat (verb B can write title/subtitle text, which makes
   this *more* acute) -- deciding to surface, where, and how prominently is a
   judgment -> `needs-owner-decision`.

**Hard NOs (flat refusals):** never touch a binding / metric meaning; never reword
contract text; never propose formatting for a visual absent from the binding-map
(`blocked-orphan`, route upstream); never self-grant a pass; never emit a score.

## Smallest first slice (owner-ruled) + explicit deferrals

**Build, in order, proven on the committed fixture
(`tests/fixtures/pbir/visual_fmt.Report`), shipped HELD:**
1. `templates/formatting-plan.md` -- the ledger schema.
2. the DL-family lint -- citations resolve, allow-list-only, binding byte-identical,
   no applyable row cites a render-only anti-pattern, no score, `ratified_by` unset.
3. a `powerbi-dashboard-design` workflow producing a **theme-selection + per-visual
   #4/#9/#13 + #8 category-colors** plan for one page, stopping at the ratify seam.
   (#8 rows are `needs-owner-decision` unless a committed member enumeration exists.)

**Shipped HELD / latent (repo precedent -- gap #6, increment C):** the real report
page has ZERO visuals; the only geometry+binding `visual.json` is the test fixture. So
the code ships and is proven on the fixture but is **latent until a filled report
lands** -- we do not claim it runs against the real report.

**Explicitly deferred:** theme *generation* from the plan (propose seed -> `theme-gen`);
background proposal (verb C rows); geometry/layout (increment D -- its own ADR +
allow-list); the SVG preview; auto-closing the render->critique->revise loop.

## The single sharpest risk that remains

Even a perfectly-partitioned, honestly-scoped layer formats **blind** -- its actual
quality is unverifiable in-sandbox, so the entire value is gated on a human actually
rendering and running `screenshot-review`. If that human step is skipped (and
"do recommended / without stop" pressure will push to skip it), we ship blind
formatting dressed in a resolvable-citation veneer: every row cites a principle, no
row is proven to *serve* one. This human-render dependency is the risk that survives
every fix -- it is the one thing the kit's DEFINE/CHECK identity structurally cannot
close on its own. The design's mitigations: the honest-ceiling wording, the
render-only-citation ban, and the `blocking_reasons: [not rendered]` footer that keeps
the plan at `warning` until a human render is recorded.

## See also

- The rubric it reasons from: `docs/powerbi/visual-qa.md` (13 anti-patterns).
- The critique output the human render feeds: `templates/screenshot-review.md`.
- The verbs that apply the plan: `src/retail/pbir_theme_apply.py`,
  `pbir_visual_format.py`, `pbir_page_background.py`.
- The authorization for agent-written PBIR: ADR 0015.
- Tokens / house style: `design/tokens/`.
- The gate it inherits (no parallel gate): `docs/readiness/dashboard-ready.md`.
