# powerbi-handoff (surface 4: implementation handoff)

Surface 4 of the four-surface router (`../SKILL.md`). This workflow is the LAST
step of a design: it gathers the artifacts the other three surfaces produced and
turns them into implementation NOTES a human (later, an F016 adapter) uses to
build the report in Power BI Desktop. It is the bundle, not the build -- the
router opens it for "build / implement in Power BI".

## Scope (read first)

This workflow ASSEMBLES and HANDS OFF; it does not author anything in Power BI.
It produces notes only. It edits no PBIP/PBIR file, generates no DAX, changes no
SQL, edits no semantic-model file, and runs no pbi-cli automation. Execution
(PBIP/PBIR authoring, pbi-cli, workspace publish) is F016's job; this workflow
stops at the handoff boundary and names F016 as that owner.

It defines no metric (that is F009) and designs no specific dashboard (that is the
F011/012 `dashboard-design` verb). It only restates, in build-ready order, what
the upstream design artifacts already decided -- referencing each by name, never
re-deriving it.

## What this workflow consumes

The handoff is downstream of every other surface. Gather these inputs first; if
one is missing, the handoff is `blocked` until it exists (do not invent it):

| Input | What it provides | Where it comes from |
|-------|------------------|---------------------|
| Approved metric contracts | the metric each data-bound visual binds to, BY NAME -- never an inline formula | F009 (planned); the metric-contract store |
| Governed semantic model contract | the model + the mapped fields each visual uses, referenced by relative path | F010; the governed PBIP model |
| Dashboard page blueprint | page = one business question; sections; visual list; mobile notes | `../../../../templates/dashboard-page-blueprint.yaml` (filled: `../../../../reports/blueprints/<page>.yaml`) |
| Theme JSON | the palette/fonts/defaults to import in Desktop | `../../../../themes/tower-retail.theme.json` |
| Background specs | the static canvas/background asset per page + its import instructions | `../../../../templates/background-spec.yaml` |
| Visual specs | one spec per visual (type, contract, mapped fields, position, formatting, tooltip, sorting, number format) | `../../../../templates/visual-spec.yaml` |
| QA checklist | the anti-pattern review the page must pass before handoff | `dashboard-qa.md` |

Reference each input BY NAME or relative path -- the handoff inlines no metric
formula, no DAX, and no concrete subject-area values. Contracts and fields stay
placeholders (e.g. `<sales_amount>`, `<branch>`, `<period>`) in this generic
workflow.

## Gate check before assembling (data-bound pages)

If the bundle includes any data-bound page (surface 1), confirm the inherited
gate is satisfied before assembling: the subject area's `semantic_model_ready`
MUST be `pass`, every data-bound visual MUST cite one approved metric contract by
name and a mapped semantic-model field, and the QA checklist (`dashboard-qa.md`)
MUST have no open blocking anti-pattern. If any fails, record the blocking reason
(`orphan visual: no contract for <question>`, `unmapped field: <field>`, or
`semantic_model_ready is not pass`) and STOP -- do not assemble a handoff around a
missing contract. A pure-styling bundle (theme + background only, no metric) is
not gated.

## Output: implementation notes for Power BI Desktop

Produce a single, readable handoff note (committed text, no PBIP edit) in this
order -- the order a human would build the report:

1. **Prerequisites** -- the governed semantic model is open/connected (by relative
   path, never an absolute/remote ref, never a real host); `semantic_model_ready`
   is `pass`; the approved metric contracts exist. List them by name.
2. **Import the theme** -- import `../../../../themes/tower-retail.theme.json` in
   Power BI Desktop (View -> Themes -> Browse). Note that it is a STARTER theme to
   be VALIDATED in Desktop (see `../../../../themes/README.md`); colors/fonts/
   defaults come from the theme, not per-visual overrides.
3. **Set each page's canvas + background** -- per page, set the canvas size and
   apply the static background asset from its background spec as the page
   background/image layer; keep all live visuals editable ABOVE it. The background
   carries layout structure only (safe zones, containers, grid) -- no KPI value,
   no dynamic title.
4. **Place the visuals** -- per page, in the blueprint's section order (header /
   KPI strip / main insight / diagnostic / exception-detail / filter rail /
   footer-status), create each visual from its visual spec: visual type, the
   metric contract it binds to (by name -- in Desktop this is selecting the
   existing measure, NOT writing a new one), the mapped semantic-model fields,
   position, formatting, sorting, number format, and tooltip behavior.
5. **Slicers + interactions** -- add slicers as mapped dimension controls (off to
   the side, not dominating); set visual interactions per the blueprint (default
   cross-highlight; cross-filter only where the blueprint justifies it).
6. **Mobile layout** -- apply the phone layout from the blueprint's mobile notes
   (KPI strip + top insight survive to mobile; desktop-only detail is dropped).
   See `mobile-layout.md`.
7. **Final QA pass** -- run `dashboard-qa.md` against the built page before
   handoff sign-off; record any `warning`-class deviation with its reason.

For each visual, the note says "bind to contract `<name>`, field `<field>`" -- it
NEVER contains the metric's formula or any DAX. Writing the measure is selecting
an existing approved contract in Desktop, not authoring a definition here.

## No-data-edit / handoff boundary

This slice edits no PBIP/PBIR file, generates no DAX, changes no SQL, edits no semantic-model file,
and adds no pbi-cli automation. The handoff stops at implementation NOTES and names F016 as the
owner of any execution step (PBIP/PBIR authoring, pbi-cli, workspace publish).

The note describes WHAT to build and in what order; a human (later, the F016
adapter) performs the build. This workflow never crosses into authoring or
publishing.

## Future adapter NOTES (F016 -- deferred, described not built)

Record, as PROSE for the deferred owner, what a future F016 PBIP/pbi-cli adapter
WOULD automate from this handoff -- so the design captures intent without adding
any automation now:

- An adapter would read the page blueprints + visual specs + theme + background
  specs and emit the PBIP/PBIR project a human assembles by hand today.
- It would bind each visual to its already-approved metric contract and mapped
  field (still no metric invented -- the contract is the source of truth).
- It would set the model reference as a RELATIVE path (the same constraint
  `seshat check` R1 enforces) -- never an absolute/remote ref, never a real host.
- It would remain GATED on the same gate: no data-bound generation before
  `semantic_model_ready` is `pass` and the design-review sign-off is recorded.

These are NOTES describing a deferred capability. Do not write a pbi-cli command
sequence, a runnable script, or any automation here -- F016 owns that, and adding
it now is a scope violation.

## Known limitations (record with the handoff)

- **Manual build until F016.** Every step above is performed by a human in Power
  BI Desktop today; there is no automation in this slice.
- **Theme schema is treated as UNCERTAIN.** `../../../../themes/tower-retail.theme.json`
  is a conservative STARTER that MUST be validated in Power BI Desktop before use
  (see `../../../../themes/README.md`); some keys may need adjustment for the
  installed Desktop version.
- **Background assets are external.** They are designed and exported outside Power
  BI (surface 2) and must already exist at the paths the background specs name.
- **Handoff readiness is recorded, not granted.** Record `dashboard_ready` with
  the four statuses (`not_started` / `blocked` / `warning` / `pass`) plus
  `evidence[]` and `blocking_reasons[]`; never a numeric score. Never self-grant
  `dashboard_ready: pass` -- that is the F011/012 verb owner's recorded
  design-review.

## Stop-and-ask (Principle V)

STOP and surface to a human rather than self-answering when:

- a required input (a contract, a mapped field, the governed model, a blueprint,
  a spec) is missing -- record the blocking reason and STOP, do not invent it;
- a user asks to "just build it in Power BI" or to run pbi-cli -- produce the
  implementation notes only and name F016 as the owner of any execution step;
- the design-review sign-off has not been recorded -- the handoff may be assembled
  as a `warning`-class draft, but `dashboard_ready: pass` is the verb owner's call.

## See also

- The router + the four-surface table: `../SKILL.md`.
- The page being handed off: `page-blueprint.md`; arrange the visuals:
  `visual-design-system.md`; the phone layout: `mobile-layout.md`.
- The QA checklist run before handoff: `dashboard-qa.md`.
- The blueprint blank + filled instances: `templates/dashboard-page-blueprint.yaml`,
  `reports/blueprints/<page>.yaml`.
- The visual + background spec blanks: `templates/visual-spec.yaml`,
  `templates/background-spec.yaml`.
- The starter theme + its validate-in-Desktop note: `themes/tower-retail.theme.json`,
  `themes/README.md`.
- The deferred execution owner: F016 (PBIP/PBIR authoring, pbi-cli, publish).
- The gate to inherit + the four statuses: `docs/readiness/dashboard-ready.md`,
  `docs/readiness/readiness-model.md`.
