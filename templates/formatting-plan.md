# Formatting Plan -- `<subject-area>` / `<page-id>`

> **GENERIC, copy-me template.** This is the DEFINE-side ledger of the smart-
> formatting layer: one row per formatting decision, each citing a
> `docs/powerbi/visual-qa.md` anti-pattern and a design token. It is proposed by
> the `powerbi-dashboard-design` skill's `workflows/formatting-plan.md` workflow
> and validated for well-formedness by rule `DL7`. The shipped `pbir-*` verbs
> (`pbir-apply-theme`, `pbir-format-visual`, `pbir-set-page-background`) apply
> the applyable subset of a RATIFIED plan; a named human ratifies + renders and
> is the only one who judges the rendered result good. This template writes no
> PBIR itself.
>
> Copy this file to `mappings/<subject>/design/formatting-plan.md`, replace
> every `<placeholder>`, and fill one row per decision.

## Honest ceiling -- read this before filling a row

This plan proposes a **consistent, theme-conformant, correctly-formatted**
baseline. It does **not**, and cannot, produce "brilliant" automatically: it
formats **blind** (nothing in this repo renders Power BI), so it can prove a
citation *resolves* -- never that the choice *serves* the principle it cites.
"Brilliant" needs a human to actually render the page and run
`docs/powerbi/visual-qa.md` / `templates/screenshot-review.md` critique against
the rendered result. Every row below states a citation, not a verdict.

## Principle-VII note (generic, no tenant specifics)

This template carries no tenant, client, or subject-area specifics. Any
resemblance to a real table, column, branch name, or metric in the example
rows below is coincidental placeholder text, not a filled instance. A filled
copy of this file lives under `mappings/<subject>/design/`, never here.

## The column contract

Each row is one formatting decision. Columns, in order, with a one-line
meaning each:

- `target` -- the `visual_id` (from the subject's approved binding-map) this
  row formats, or `page:<name>` for a page/theme-level decision.
- `container` -- the adapter's real top-level JSON key the value lands under:
  `objects` (chart-content), `visualContainerObjects` (chrome), `background`
  (page canvas), or `themeCollection` (report theme). Empty only for a
  page/theme-level row whose `apply_verb` is `A` or `C`.
- `group` -- the property group inside the container (e.g. `title`, `border`,
  `dataPoint`, `legend`) -- the adapter's real nested shape, never an invented
  flat key.
- `property` -- the single setting inside the group (e.g. `show`, `fontSize`,
  `color`).
- `value` -- the literal value this row proposes for that property.
- `principle_cited` -- a resolvable `docs/powerbi/visual-qa.md` anti-pattern
  number, `#1` through `#13`. Every row must cite one; a row that fixes
  nothing is not a formatting decision, it is vibes.
- `token_cited` -- the design token this value was drawn from (a path into
  `design/tokens/`), never an invented literal.
- `apply_verb` -- which mechanism can apply this row: `A` (`pbir-apply-theme`),
  `B` (`pbir-format-visual`), `C` (`pbir-set-page-background`), or
  `handoff-only` (no apply path exists; a human/Desktop/a future increment
  handles it).
- `status` -- `proposed`, `needs-owner-decision`, or `blocked-orphan`. Never
  `resolved` -- resolution is a human render + critique outcome, not something
  this ledger can self-declare.
- `rationale` -- words-only, why this value for this citation. Never a number.

## The apply-path partition -- this partition is the design

The 13 `docs/powerbi/visual-qa.md` anti-patterns split into three groups by
whether a `pbir-*` verb can act on them at all:

- **Applyable** (property-level; a citation here is meaningful and an
  `A`/`B`/`C` row may claim it): `#3` date-context (only when *surfacing* an
  existing date field via a subtitle -- adding a new slicer is a bind, see
  below), `#4` number formats, `#8` category colors (see the caveat below),
  `#9` tooltip presence, `#12` background carries no data, `#13`
  theme-inheritance / a documented per-visual override.
- **Detect-only, no apply path** (geometry or type -- no verb writes position,
  size, or `visualType`): `#1` too many visuals, `#5` slicers dominate, `#6`
  table as the main executive visual, `#7` no visual hierarchy. These are
  emitted as `handoff-only` rows for a human, Desktop, or a future increment --
  never claimed `resolved` by an `A`/`B`/`C` row. Bolding a title does not
  establish hierarchy; that is geometry, not a property this layer can set.
- **Stop-upstream** (binding or creation -- forbidden here): `#2`
  KPI-without-comparison, `#10` orphan metric, `#11` unmapped field, and `#3`
  when it means *adding* a new date slicer rather than surfacing an existing
  field. A row that would need a new binding is `blocked-orphan`; route it to
  the owning gate (metric contract / semantic model), never design around it.

**`#8` caveat:** pinning a category's color safely needs a committed
enumeration of that category's members. Absent one, an `#8` row is
`needs-owner-decision`, never auto-`proposed` -- proposing a color pin without
knowing the members would be guessing.

## Example rows (one per `apply_verb` value -- obvious placeholders only)

| target | container | group | property | value | principle_cited | token_cited | apply_verb | status | rationale |
|--------|-----------|-------|----------|-------|------------------|-------------|------------|--------|-----------|
| `page:overview` | `themeCollection` | `baseTheme` | `name` | `<theme-name>` | `#13` | `design/tokens/<subject>-design-tokens.yaml#palette` | A | proposed | inherit the committed theme instead of a per-visual ad-hoc color |
| `<visual_id_1>` | `objects` | `labels` | `displayUnits` | `<unit-format-literal>` | `#4` | `design/tokens/<subject>-design-tokens.yaml#number_format.count` | B | proposed | consistent count format per the token, matches every other count visual on the page |
| `page:overview` | `background` | `canvas` | `image` | `<registered-asset-name>` | `#12` | `design/tokens/<subject>-design-tokens.yaml#background` | C | proposed | static structure only, carries no KPI value baked in |
| `<visual_id_2>` | `visualContainerObjects` | `title` | `show` | `true` | `#8` | `design/tokens/<subject>-design-tokens.yaml#data_colors` | B | needs-owner-decision | category color pin needs a committed member enumeration -- absent one, owner decides |
| `<visual_id_3>` | (none) | (none) | (none) | (none) | `#7` | `design/tokens/<subject>-design-tokens.yaml#layout` | handoff-only | proposed | no clear top-left headline on this page; geometry fix needs a human/Desktop, no property this layer can set |

## Footer -- readiness + ratification (Principle V)

Every filled plan closes with this footer, verbatim in shape:

- `readiness.status: warning` -- never self-granted `pass`. A formatting plan
  cannot pass itself; only a human render + critique moves it forward.
- `blocking_reasons: [not rendered -- screenshot-review pending]` -- the
  standing reason this plan stays at `warning` until a human actually renders
  the page and runs the critique in `templates/screenshot-review.md`.
- `ratification.ratified_by: ""` -- **the agent is structurally forbidden to
  fill this field.** It is left empty for a named human to sign after review.
  An agent-shaped value here (containing "agent", "claude", "llm", or
  "assistant") is a self-ratify and `DL7` errors on it.

no `score:`/`confidence:` field exists here BY DESIGN (rule #9) -- a
formatting plan is words-only, never a numeric confidence.

## See also

- Rubric: `docs/powerbi/visual-qa.md` (the 13 anti-patterns this ledger cites).
- Lint: `DL7` in `src/retail/rules/formatting_plan.py` (validates this
  ledger's shape; does not and cannot judge whether a choice is good).
- Workflow that fills this template: the `formatting-plan.md` workflow under
  `.claude/skills/powerbi-dashboard-design/`.
- Apply verbs: `retail pbir-apply-theme`, `retail pbir-format-visual`,
  `retail pbir-set-page-background` (`docs/integrations/pbir-adapter.md`).
- Critique output once rendered: `templates/screenshot-review.md`.
- Sister templates: `templates/theme-json-spec.md` (surface 3),
  `templates/visual-spec.yaml` (surface 1).
- The gate this plan inherits (no parallel gate):
  `docs/readiness/dashboard-ready.md`.
