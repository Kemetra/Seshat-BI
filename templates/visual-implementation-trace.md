# Visual implementation trace -- `<subject-area>`

<!--
  GENERIC TEMPLATE (roadmap rule 7). Copy this blank into a per-subject-area
  working set (mappings/<subject>/design/) and fill the placeholders. This is the
  reviewable evidence artifact that proves a HUMAN-built PBIR page realizes the
  approved visual -> contract binding map 1:1 -- and nothing more.

  On-disk spec: specs/039-visual-implementation-mvp  |  Roadmap feature: F034
  (when the spec-dir number and the F-number disagree, the roadmap F-number wins).

  Authority category: Product Module / artifact-writing.

  THE BOUNDARY (verbatim from templates/module-contract.md -- do not drift):
    A Product Module MUST NOT create truth: it cannot define business meaning,
    approve a metric or mapping, or move a readiness stage to `pass`. Those are Core
    Authority operations owned by a named human (Principle V). A Module reads,
    summarizes, visualizes, MAY write derived evidence (if `artifact-writing` or
    `execution-capable`), and MAY execute an approved step against the LOCAL committed
    working set (if `execution-capable`). If it would connect to a DB / external
    service or publish, it is an Execution Adapter, not a Module -- use
    templates/adapter-contract.md instead (see the module-vs-adapter seam).

  This trace pins `artifact-writing`, NOT `execution-capable`: a human builds the page in
  Power BI Desktop; the agent only VERIFIES the committed page and WRITES this trace
  (it derives a committed artifact from committed evidence -- it executes nothing,
  connects to nothing, publishes nothing). Materialize/publish is the deferred,
  gated F016 Execution Adapter -- not this slice.

  C086 IS AN EXAMPLE, NEVER INLINED HERE. Do NOT copy any C086/pharmacy or
  retail_store_sales specifics (real measure names, real rates, segment rollups,
  grain keys) into this file. The worked instance is CITED, never inlined:
  see a filled worked example under docs/worked-examples/ and the per-subject-area trace it
  produces. ASCII + UTF-8 no BOM; only `--` and `->`; no real connection host or
  secret (Principle IX).
-->

## What this trace is (and is not)

This trace records, one row per built measure-bearing visual, that a HUMAN-built PBIR
page realizes the approved visual -> contract binding map. It VERIFIES a committed page;
it does not author one, does not generate PBIR, writes no DAX, edits no semantic-model
file, runs no pbi-cli / Power BI MCP command, and publishes nothing. The page is built by
a person in Power BI Desktop and saved as plain-text PBIR; the agent reads the committed
`<report>/definition/` and fills this trace as derived evidence.

It is NOT a design, a re-bind, or a metric definition: design + binding is F011/012's job,
metric definition is F009's. This trace consumes the approved binding map; it never
re-designs, re-binds, or invents a metric.

Use the four readiness statuses, never a number, for every row and for the overall roll-up.
The readiness vocabulary is exactly four statuses (`not_started` / `blocked` / `warning` /
`pass`) + `evidence[]` + `blocking_reasons[]`. There is NO numeric / maturity / confidence
score anywhere here (roadmap rule 9). This trace never self-grants `dashboard_ready: pass`
-- that stays the BI / report owner's recorded design-review action.

## Inherited gate (rule 5 -- not re-decided here; owned by docs/readiness/dashboard-ready.md + F011/012)

No implemented-page evidence is recorded before BOTH of these hold. This trace DEFINES no
new gate and is NOT a second source of truth -- the gate, the design-review sign-off, and
`dashboard_ready: pass` stay owned by `docs/readiness/dashboard-ready.md` and F011/012.

- `semantic_model_ready` is `pass` for this subject area, AND
- the design-review sign-off (visual -> contract binding) is recorded in `approvals[]`.

If either is missing, record NO row as `pass`, record the matching blocking reason, set the
overall status to `blocked`, and STOP -- point upstream:

- `semantic_model_ready` not `pass` -> `blocking_reason: "no approved contracts -- Dashboard Ready gate, rule 5"`.
- sign-off not recorded -> `blocking_reason: "design-review sign-off not recorded"`.

## Header

| Field | Value |
|-------|-------|
| Subject area | `<schema.table or model name>` |
| Built PBIR page | `<report>/definition/pages/<id>/` (a HUMAN Desktop save -- not agent-authored) |
| Governed model | `<relative path -- e.g. ../<Model>.SemanticModel; R1: relative, never absolute/remote>` |
| Approved binding map | `mappings/<subject>/design/visual-contract-binding-map.md` |
| `semantic_model_ready` | `pass` |
| design-review sign-off | `{stage: dashboard_ready, owner: <bi-report-owner>, at: <YYYY-MM-DD>}` |
| Traced by | `<analyst_or_agent>` |
| Trace date | `<YYYY-MM-DD>` |

## The 1:1 trace (one row per built MEASURE-BEARING visual)

Every measure-bearing visual on the built page maps to exactly ONE approved metric contract
(by name) from the approved binding map AND to a field present in the governed semantic
model. The status column admits the full readiness four-status set (never a number):

- `pass` -- the row binds 1:1 to exactly one approved contract by name AND a mapped model field.
- `blocked` -- an ORPHAN visual (not in the approved binding map) OR an UNMAPPED field (absent
  from the governed model). Record the reason; this row can NEVER be `pass`.
- `warning` -- a non-blocking divergence surfaced during/after the build (e.g. an accepted
  layout deviation, or a built visual whose map entry was re-approved upstream and now
  diverges) that must be visible but does not by itself retract the design approval.
- `not_started` -- an approved binding-map entry with NO built visual yet.

| visual_id | visual_type | bound_contract (approved, by name) | mapped_field(s) | status | blocking / divergence reason |
|-----------|-------------|------------------------------------|-----------------|--------|------------------------------|
| `v01` | `<card/bar/line/table>` | `<approved-contract-name>` | `<mapped field(s)>` | `<not_started \| blocked \| warning \| pass>` | `<reason, or "--" when pass>` |
| `v02` | `<...>` | `<approved-contract-name>` | `<...>` | `<...>` | `<...>` |

> An ORPHAN visual (a measure-bearing visual NOT in the approved binding map) forces
> `status: blocked` with `reason: "orphan visual: not in approved binding map"` -- never `pass`.
> A field absent from the governed semantic model forces `status: blocked` with
> `reason: "unmapped field"`.
>
> FILTER-RAIL SLICERS ARE DIMENSION CONTROLS, NOT trace rows. A slicer / dimension control
> binds no measure; it does not appear in the binding map and is NOT a row here. This trace
> governs measure-bearing visuals only (matching the F011/012 binding-map convention).

## Coverage check (every approved binding-map entry is accounted for)

The trace makes a post-build divergence visible -- it never silently accepts a stale page as
`pass`. Record any approved entry with no built visual, and any built visual no longer in a
re-approved map.

| approved binding-map entry | built on the page? | disposition |
|----------------------------|--------------------|-------------|
| `<approved-contract-name / visual_id>` | `<yes \| no>` | `<traced as v0N (pass) \| not_started: no built visual yet \| warning: map re-approved upstream, page diverges>` |

## Caveat carried to the page (generic -- placeholders only)

When an approved contract carries a caveat the visual MUST surface (e.g. an excluded
population, a floor/ceiling framing), name it here so the built visual and this trace agree.
This is the CONTRACT's caveat, restated -- never a redefinition (that is F009).

| visual_id | approved value framing | caveat surfaced on the visual |
|-----------|------------------------|-------------------------------|
| `<v0N>` | `<rate>` | `<excluded>` ; `<floor>` |

> Carry the APPROVED framing the contract records -- never a retracted/stale figure. The
> built visual and this row MUST agree. (Worked instance only -- generic placeholders here.)

## Readiness (roll up to the WORST row status)

The overall trace status is the worst status across all rows and the coverage check above:
any `blocked` row -> `blocked`; else any `warning` or `not_started` -> that; else `pass`.
A `pass` requires that all measure-bearing visuals trace cleanly AND every approved entry is
built. Recorded as evidence under the EXISTING Dashboard Ready owner -- never a self-grant.

- trace status: `<not_started \| blocked \| warning \| pass>`   # the worst row status
- evidence: `["built-page traces to the approved binding map; R1 passes", "<the binding map>", "<the built page diff>"]`
- blocking_reasons: `[]`   # required whenever any row or the overall status is `blocked`
- dashboard_ready evidence item (recorded by the owner, NOT by this trace):
  `evidence: "built-page traces to the approved binding map; R1 passes"`

## FORBIDDEN operations (standing guardrail -- do NOT fill; these always hold)

These hold for EVERY copy of this trace, regardless of subject area (the authority matrix
says NO -- Product Module / artifact-writing):

- MUST NOT create truth: no defining business meaning, no approving a metric/mapping.
- MUST NOT grant approval or move a readiness stage to `pass` (named-human / Core Authority
  only); MUST NOT self-grant `dashboard_ready: pass`.
- MUST NOT connect to a DB or external service, and MUST NOT publish a Power BI artifact
  (those are Execution Adapter capabilities -- the deferred, gated F016).
- MUST NOT generate PBIR, write DAX, change SQL, edit any semantic-model file, run any
  pbi-cli / Power BI MCP command, or publish. The ONLY PBIR change is the human's Desktop
  save of the built page; any generation/publish request STOPS and names F016 as the owner
  (rule 6). F034 is INDEPENDENT of F016 (rule 6 gates the automation, not the manual build).
- MUST NOT hand-edit Desktop-owned files (`report.json`, `diagramLayout.json`) or hand-author
  visual-container JSON -- the committed diff comes from a real Desktop save (FR-009).
- MUST NOT invent, define, re-bind, or re-design a metric (F009 defines; F011/012 designs).
- MUST NOT emit a numeric / maturity / confidence score (rule 9).
- MUST NOT commit a real connection host, DSN, or secret (Principle IX).

## How it handles a missing input (Principle V; stop-and-ask)

When the gate is not `pass`, the sign-off is not recorded, the binding map is missing, or a
built page faithfully-realizes / layout-deviation / sign-off-coverage question is a judgment
call, this trace SURFACES it as a blocking reason and STOPS -- it never fabricates the input,
self-approves, or proceeds past the missing gate. Building never DOWNGRADES a legitimately
approved design; a divergence found at build time is a new `warning` / `blocked` finding ON
THE PAGE, not a retraction of the design approval.

## See also

- The procedure that fills this template (forthcoming this feature, per O-1, ALONGSIDE
  `powerbi-handoff.md`): `.claude/skills/powerbi-dashboard-design/workflows/visual-implementation-review.md`.
- The approved binding map this verifies against: `templates/visual-contract-binding-map.md`.
- The input contract for the build order:
  `.claude/skills/powerbi-dashboard-design/workflows/powerbi-handoff.md`.
- The gate to inherit + the four statuses: `docs/readiness/dashboard-ready.md`,
  `docs/readiness/readiness-model.md`.
- The authority category + matrix: `docs/architecture/product-modules.md`; the copy-me
  declaration: `templates/module-contract.md`.
- Metric definitions live upstream (referenced, never redefined here): F009.
- The deferred execution/publish adapter (named, never invoked): F016.
- The worked instance (CITED, never inlined): a filled worked example under `docs/worked-examples/`.
