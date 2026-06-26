# visual-implementation-review (surface 4: verify the built page)

Surface 4 of the four-surface router (`../SKILL.md`), ALONGSIDE `powerbi-handoff.md`.
Where the handoff produces the build NOTES a human follows, this workflow VERIFIES
the result: it reads the committed plain-text PBIR a human built in Power BI Desktop
and produces the implementation TRACE proving the page realizes the approved
visual -> contract binding map 1:1 -- and nothing more. It is the review, not the
build. (On-disk spec: `specs/039-visual-implementation-mvp`; roadmap feature: F034 --
the roadmap F-number is authoritative when it disagrees with the spec-dir number.)

## Scope (read first)

This workflow READS a committed page and WRITES a derived trace; it authors nothing
in Power BI. It edits no PBIP/PBIR file, generates no PBIR, writes no DAX, changes no
SQL, edits no semantic-model file, hand-edits no Desktop-owned file
(`report.json` / `diagramLayout.json`), hand-authors no visual-container JSON, runs
no pbi-cli / Power BI MCP command, and publishes nothing. Execution (PBIR authoring,
pbi-cli, workspace publish) is F016's job; this workflow stops at the review boundary
and names F016 as that owner. F034 is INDEPENDENT of F016 -- rule 6 gates the
automation, not the manual build (see the boundary section below).

It defines no metric (that is F009) and designs/re-binds no dashboard (that is the
F011/012 `dashboard-design` verb). It only verifies that the page a human built
matches what those upstream artifacts already approved -- referencing each by name,
never re-deriving it.

## What this workflow consumes

The review is downstream of the build. Gather these inputs first; if one is missing,
the review is `blocked` until it exists (do not invent it):

| Input | What it provides | Where it comes from |
|-------|------------------|---------------------|
| The committed PBIR page | the BUILT visuals to verify -- one visual container per built visual, in plain text | a human's Desktop save under `<report>/definition/pages/<id>/` |
| Approved visual -> contract binding map | the 1:1 source of truth: each measure-bearing visual -> exactly one approved contract by name + mapped field | F011/012 (`mappings/<subject>/design/visual-contract-binding-map.md`) |
| The design-review sign-off | the recorded approval the build realizes | `approvals[]` in `mappings/<subject>/readiness-status.yaml` |
| The trace template | the copy-me blank this workflow fills | `../../../../templates/visual-implementation-trace.md` |
| F011A handoff notes | the build order the page should reflect (restated, never re-derived) | `powerbi-handoff.md` |

Reference each input BY NAME or relative path. This generic workflow inlines no
concrete subject-area value: contracts/fields stay placeholders (e.g.
`<ApprovedContract>`, `<dim[col]>`). Worked values live only in the per-subject
filled trace instance.

## Gate check before reviewing (inherited VERBATIM from Dashboard Ready, rule 5)

Confirm the inherited gate is satisfied BEFORE recording any implemented-page
evidence -- this workflow re-decides nothing; the gate is owned by
`docs/readiness/dashboard-ready.md` + F011/012:

- the subject area's `semantic_model_ready` MUST be `pass`, AND
- the design-review sign-off MUST be recorded in `approvals[]`, AND
- the approved binding map MUST exist.

If any fails, record the blocking reason and STOP -- record NO implemented-page
evidence, do not bless a build whose design is not approved:

- `semantic_model_ready` not `pass` -> `blocking_reason: "no approved contracts -- Dashboard Ready gate, rule 5"`.
- sign-off not recorded -> `blocking_reason: "design-review sign-off not recorded"`.
- binding map missing -> `blocking_reason: "approved binding map missing"`.

A page may be built before the gate clears, but it is never BLESSED as implemented
evidence until the gate holds.

## Output: the implementation trace (read the page, fill the template)

Copy `../../../../templates/visual-implementation-trace.md` to the subject area's
design dir (`mappings/<subject>/design/visual-implementation-trace.md`) and fill it
by READING the committed page, in this order:

1. **Enumerate the built measure-bearing visuals** -- read each visual container in
   `<report>/definition/pages/<id>/` (and its `visuals/` if Desktop split them). A
   filter-rail dimension SLICER binds no measure -- it is NOT a trace row (the trace
   governs measure-bearing visuals only, matching the F011/012 binding-map convention).
2. **Trace each visual 1:1 to the approved binding map** -- one row per built
   measure-bearing visual: the contract it binds to (BY NAME) and the mapped
   semantic-model field(s). The binding map is the source of truth, never the visual's
   on-page caption.
3. **Status each row** from the readiness four-status set (never a number):
   - `pass` -- binds 1:1 to exactly one approved contract by name AND a mapped model field.
   - `blocked` -- an ORPHAN visual (not in the approved binding map) OR an UNMAPPED field
     (absent from the governed model). Record the reason; this row can never be `pass`.
   - `warning` -- a non-blocking divergence to surface (an accepted layout deviation, or a
     built visual whose map entry was re-approved upstream and now diverges) that does not
     by itself retract the design approval.
   - `not_started` -- an approved binding-map entry with NO built visual yet.
4. **Run the coverage check** -- every approved binding-map entry is accounted for: built
   (`pass`), `not_started` (no built visual yet), or `warning` (map re-approved, page now
   diverges). A built visual NOT in the approved map is an orphan -> `blocked`.
5. **Carry any contract caveat** the visual must surface (an excluded population, a
   floor/ceiling framing) -- restate the CONTRACT's approved framing, never a redefinition
   (F009) and never a retracted/stale figure.
6. **Roll up to the WORST row status** -- any `blocked` -> `blocked`; else any `warning` or
   `not_started` -> that; else `pass`. Record `evidence[]` + `blocking_reasons[]`.

For each visual, the trace row says "binds to contract `<name>`, field `<field>`" -- it
NEVER contains the metric's formula or any DAX. Verifying a binding is matching the visual's
selected measure to an existing approved contract, not authoring a definition here.

## The git-diff review checklist (a reviewer runs this on the committed PBIR)

The page is reviewed in git like code -- the reviewer reads plain text, never an opaque
`.pbix`. Confirm, on the committed diff:

- [ ] The change is a real Power BI Desktop SAVE (committed `definition/` text), not
      hand-authored visual-container JSON and not an edit to `report.json` /
      `diagramLayout.json` (FR-009; Desktop owns those files).
- [ ] No opaque `.pbix` is committed -- the page is plain-text PBIR (FR-002).
- [ ] The PBIR references the governed semantic model by a RELATIVE path -- never an
      absolute/remote ref, never a real host (FR-007; the same constraint `retail check`
      R1 enforces).
- [ ] One visual container per approved measure-bearing visual; no visual the binding map
      did not approve (no orphan).
- [ ] The filled `visual-implementation-trace.md` accompanies the page diff, and its
      overall status matches the rows.
- [ ] Committed files are ASCII, UTF-8 without BOM; the nested `definition/pages/<id>/...`
      paths stay under the Windows 260-char limit (FR-014).
- [ ] A contract caveat (e.g. a discount rate's excluded/floor framing) is surfaced on the
      visual and agrees with the trace -- the APPROVED framing, never a retracted/stale one.

## The 1:1 trace check (the load-bearing rule)

Every measure-bearing visual on the built page maps to EXACTLY ONE approved metric contract
(by name) from the approved binding map AND to a field present in the governed semantic
model. A measure reused across visuals is still ONE contract bound multiple ways (allowed);
a visual with NO approved contract behind it is an orphan and forbidden. The page cannot
silently introduce an unapproved metric, an orphan visual, or an unmapped field -- any of
those forces the trace `blocked`, never `pass`.

## No-author / review boundary (and the F016 line)

This workflow READS a committed page and WRITES a derived trace; it authors no PBIR.
It edits no PBIP/PBIR/semantic-model file, generates no PBIR, writes no DAX, changes no SQL,
runs no pbi-cli / Power BI MCP command, and publishes nothing. The build itself is a HUMAN
action in Power BI Desktop; this workflow's role is to VERIFY the committed result and
produce the reviewable trace.

- **F016 is EXECUTION AUTOMATION** (a future adapter that would generate the PBIR and publish
  it without a human in Desktop) -- deferred, gated (rule 6), and named here as the owner of
  any generation/publish step.
- **F034 is a HUMAN MANUAL BUILD reviewed in git** -- a person builds in Desktop and commits
  plain-text PBIR; the only "tooling" is git diff + this read-only trace. It is INDEPENDENT
  of F016: rule 6 gates the automation, not the manual build, and no readiness stage depends
  on F016.

If a user asks to "just generate the report", "run pbi-cli", or "publish to the workspace",
STOP at the review boundary, produce or verify only the committed PBIR a human built, and
name F016 as the owner of any generation or publish step.

## Readiness (recorded, not granted)

Record `dashboard_ready` with the four statuses (`not_started` / `blocked` / `warning` /
`pass`) plus `evidence[]` and `blocking_reasons[]`; never a numeric score (rule 9). The
implemented-page result is recorded ONLY as an `evidence[]` item under the EXISTING Dashboard
Ready owner (`evidence: built-page traces to the approved binding map; R1 passes`). Building
the page never DOWNGRADES a legitimately approved design; a build-time divergence is a new
`warning` / `blocked` finding on the page, not a retraction of the design approval. NEVER
self-grant `dashboard_ready: pass` -- that stays the F011/012 verb owner's recorded
design-review action.

## Stop-and-ask (Principle V)

STOP and surface to a human rather than self-answering when:

- a required input (the committed page, the binding map, the governed model, the sign-off)
  is missing -- record the blocking reason and STOP, do not invent it;
- a user asks to generate the PBIR, run pbi-cli/MCP, or publish -- verify only the committed
  page and name F016 as the owner of any execution step;
- whether a built page FAITHFULLY realizes the approved design, whether a layout deviation
  discovered at build time is acceptable, or whether the design-review sign-off COVERS the
  built page is a judgment call -- surface it to the BI owner; never self-answer or
  self-grant `dashboard_ready: pass`.

## See also

- The router + the four-surface table: `../SKILL.md`.
- The build NOTES this verifies the result of: `powerbi-handoff.md` (the input contract).
- The trace template this fills: `../../../../templates/visual-implementation-trace.md`.
- The approved binding map verified against: `mappings/<subject>/design/visual-contract-binding-map.md`.
- The QA catalog a built page also passes: `dashboard-qa.md`.
- The gate to inherit + the four statuses: `docs/readiness/dashboard-ready.md`,
  `docs/readiness/readiness-model.md`.
- The deferred execution/publish owner (named, never invoked): F016.
