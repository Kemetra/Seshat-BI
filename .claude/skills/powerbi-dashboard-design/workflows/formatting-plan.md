# formatting-plan (the smart-formatting proposer)

The procedure that PROPOSES a formatting plan for an already-approved dashboard page
-- which theme, and which per-visual formatting -- as a git-reviewable
`formatting-plan.md` ledger. The 3 shipped `pbir-*` verbs later APPLY a *ratified*
ledger; the DL7 lint CHECKS the ledger's shape; a named human RATIFIES it and renders.
This workflow WRITES ONLY the ledger. It never writes PBIR, never binds data, never
self-ratifies.

## The honest ceiling (state it; do not exceed it)

This produces a **consistent, theme-conformant, correctly-formatted** baseline -- NOT
"brilliant/creative automatically." It formats **blind**: the sandbox cannot render
Power BI, so the plan can prove a choice's citation *resolves*, never that the choice
*serves* the principle or looks good. "Brilliant" needs a human render + judgment. Do
not claim it. (Same stance as ADR 0015: "great professional dashboards remains a
separate concern, explicitly NOT claimed.")

## Precondition -- refuse to run before the gate

Do NOT propose a formatting plan for a subject area unless BOTH hold (cite
`docs/readiness/dashboard-ready.md`):

- the subject's `readiness-status.yaml` records `semantic_model_ready: pass`, AND
- the visual-contract-binding-map is APPROVED (a data-bound page designed before its
  contracts is the inherited-gate breach the kit exists to prevent).

If either is missing, STOP and record a blocking reason; do not propose formatting for
a page that is not yet gated.

## What it reads (all committed, by reference)

- the design-QA rubric: `docs/powerbi/visual-qa.md` (the 13 anti-patterns).
- the design tokens: `design/tokens/*.yaml`; a committed generated theme (`themes/`).
- the subject's approved `visual-contract-binding-map.md` + `visual-list.md`
  (which visual answers which question, and its bound contract) + `dashboard-layout.md`
  (reading order).
- each existing `visual.json` under the subject's `*.Report/`.
- metric contracts -- to READ names only, NEVER redefine.

## Procedure

### 1. Confirm the surface + the gate

Confirm this is a formatting-proposal request (not a redesign, a new page, or a metric
change). Confirm the precondition above. Read the rubric + tokens + binding-map.

### 2. Emit one ledger row per formatting decision

Copy `templates/formatting-plan.md`. For each APPLY-able anti-pattern, author rows in
the adapter's real `container / group / property / value` shape (the
`pbir_visual_format.py` input) -- never an invented flat shape. Every row MUST cite
the `visual-qa.md` anti-pattern it addresses AND the token it draws from, or DL7
rejects it.

Slice-1 applyable set:

- **#4 number formats** -- consistent currency/percent/decimals per
  `tokens.number_format`; `apply_verb: B`.
- **#9 tooltip presence** -- a non-obvious measure's visual carries a tooltip;
  `apply_verb: B`.
- **#13 theme-inheritance** -- visuals inherit theme data colors / defaults; a
  per-visual override is recorded with a reason (never the default); `apply_verb: A`
  (theme) or `B` (a documented override).
- **#3 date-context** -- ONLY when *surfacing an existing date field* via a subtitle
  (`apply_verb: B`). Adding a NEW date slicer/field is binding -> STOP (see step 4).
- **#8 category colors** -- pin a recurring category/branch to a fixed data color for
  consistency. SAFE pinning needs a committed enumeration of category members. If none
  exists, emit the #8 rows at `status: needs-owner-decision` (never auto-`proposed`);
  the layer must not guess members.

### 2b. Emit a background row as `needs-owner-decision` -- never choose the asset

If the page could carry a static page background (**#12** background-carries-no-data),
emit ONE verb-C row proposing the *slot*, never the choice of asset:

- `target: page:<name>`, `container: background`, `group: canvas`, `property: image`,
  `value:` the committed asset's registered name IF and only if exactly the intended
  asset is already unambiguous from a committed source; otherwise leave it as the
  placeholder the owner fills.
- `principle_cited: #12`, `token_cited:` the background token path, `apply_verb: C`.
- `status: needs-owner-decision` -- **always**, in this slice. Choosing a background
  image where more than one committed asset fits (or none vs one) is a Principle-V call
  (step 5); the layer proposes the slot + the citation, never the asset. Do not emit a
  background row at `proposed` unless a committed owner ruling authorizes a specific
  asset (no such ruling exists in this slice).
- `rationale:` words only -- e.g. "static structure only, carries no KPI value; asset
  choice is the owner's (one of N committed assets fits, or none)".

This mirrors the #8 category-color hold (step 2): the mechanism ships (`pbir-set-page-
background`), but the meaning-carrying choice stays the owner's until a ruling exists.

### 3. Emit detect-only findings as `handoff-only`

The render-only anti-patterns -- **#1** too many visuals, **#5** slicers dominating,
**#6** table-as-headline, **#7** no hierarchy -- are GEOMETRY/type. The `pbir-*` verbs
cannot write position, size, or `visualType`, so these have NO apply path. Record them
as `apply_verb: handoff-only` notes for a human / Desktop / a future increment D.
NEVER cite one as `resolved` from an applyable row (DL7 forbids it -- bolding a title
does not establish hierarchy).

### 4. STOP-upstream for binding/creation

**#2** KPI-without-comparison, **#10** orphan (no contract), **#11** unmapped field,
and #3-as-adding-a-new-date-slicer are BINDING or CREATION -- forbidden by the
constitution and outside the adapter. Do NOT emit a formatting row for them; record a
blocking reason and route upstream (a comparison measure -> F009; an unmapped field ->
the model). The layer never invents a metric to fill a card.

### 5. The Principle-V STOPs (never auto-`proposed`; use `needs-owner-decision`)

- which question is the page's HEADLINE, when the questions are not ranked;
- density beyond `tokens.layout.max_visuals_per_executive_page` (a warning the owner
  rules, never an auto-cut);
- any color that carries MEANING (a brand palette; a sentiment *threshold* is F009 --
  the color is a token, the rule is a contract). Propose only generic-token colors;
- choosing a background image where more than one committed asset fits, or none vs one;
- surfacing a data-honesty caveat (verb B can write title/subtitle text) -- deciding
  to surface it, where, and how prominently is a judgment.

### 6. Write the ledger footer + STOP at the ratify seam

Write the ledger at `readiness.status: warning`,
`blocking_reasons: [not rendered -- screenshot-review pending]`, and
`ratification.ratified_by:` **EMPTY** -- you are structurally forbidden to fill it.
Then STOP and print:

> Run `seshat check` (DL7 validates this ledger's shape). Then a named owner must
> ratify it, apply it with the `pbir-*` verbs, render the report in Power BI Desktop,
> and run `screenshot-review` to judge the result. Do NOT self-ratify. Do NOT apply.

## FORBIDDEN (standing guardrail)

- Do NOT write any PBIR file -- the `pbir-*` verbs apply only a *ratified* plan.
- Do NOT bind data, define/redefine a metric, or reword contract text.
- Do NOT emit a numeric score / confidence (rule #9); use words.
- Do NOT self-ratify (`ratified_by` stays empty -- Principle V).
- Do NOT propose formatting for a visual absent from the binding-map (`blocked-orphan`,
  route upstream).
- Do NOT claim "brilliant/creative" -- the honest ceiling is consistent/conformant.

## See also

- The ledger template: `templates/formatting-plan.md`.
- The shape check: DL7 (`src/seshat/rules/formatting_plan.py`).
- The rubric: `docs/powerbi/visual-qa.md`; the human render critique:
  `templates/screenshot-review.md` + `workflows/screenshot-review.md`.
- The verbs that apply a ratified plan: `retail pbir-apply-theme` /
  `pbir-format-visual` / `pbir-set-page-background`.
- The authorization: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`.
- The gate it inherits: `docs/readiness/dashboard-ready.md`.
