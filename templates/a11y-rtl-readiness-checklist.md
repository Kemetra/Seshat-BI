# A11y / RTL readiness checklist -- `<subject-area>` / `<page-id>`

<!--
  GENERIC TEMPLATE (roadmap rule 7). Copy this blank into a per-subject-area
  working set (mappings/<subject>/design/) and fill the placeholders. This is
  the reviewable evidence artifact that records a Dashboard-Ready (Stage 6)
  page was reviewed for WCAG contrast, colorblind-safe palette separation, and
  RTL/Arabic layout readiness -- three required dimensions, never silently
  skipped.

  On-disk spec: specs/102-dashboard-a11y-rtl-gate  |  Roadmap feature: TBD
  (a new roadmap F-number, if assigned, is a roadmap-ledger edit at plan time;
  this template does not invent one).

  Authority category: Product Module / artifact-writing.

  THE BOUNDARY (verbatim from templates/module-contract.md -- do not drift):
    A Product Module MUST NOT create truth: it cannot define business meaning,
    approve a metric or mapping, or move a readiness stage to `pass`. Those are
    Core Authority operations owned by a named human (Principle V). A Module
    reads, summarizes, visualizes, MAY write derived evidence (if
    `artifact-writing` or `execution-capable`), and MAY execute an approved
    step against the LOCAL committed working set (if `execution-capable`). If
    it would connect to a DB / external service or publish, it is an Execution
    Adapter, not a Module -- use templates/adapter-contract.md instead.

  This checklist pins `artifact-writing`, NOT `execution-capable`: it reads
  already-committed design/theme/layout artifacts and the current CT1
  (`design_contrast.py`) result, and WRITES this checklist as derived
  evidence. It renders nothing, opens nothing, publishes nothing, and connects
  to no live semantic model. Materialize/publish is the deferred, gated F016
  Execution Adapter -- not this artifact.

  C086 IS AN EXAMPLE, NEVER INLINED HERE. Do NOT copy any C086/pharmacy or
  retail_store_sales specifics (real token hex values, real theme colors, real
  page layout facts, real Arabic text) into this file. The worked instance is
  CITED, never inlined: see a filled instance under
  `mappings/<subject>/design/a11y-rtl-readiness-checklist.md`. ASCII +
  UTF-8 no BOM; only `--` and `->`; no literal Arabic string in this generic
  template (a real Arabic example, if any, lives only in a filled per-page
  instance); no real connection host or secret (Principle IX).
-->

## What this checklist is (and is not)

This checklist records, once per dashboard page, that the page's declared
static design/theme/layout artifacts were reviewed for three dimensions:
WCAG contrast, colorblind-safe palette separation, and RTL/Arabic layout
readiness. It is a REQUIRED `evidence[]` item on the EXISTING `dashboard_ready`
gate (`docs/readiness/dashboard-ready.md`) -- an ADDITIVE evidence item,
following the F034 "design approved vs page implemented" precedent: no new
status, no new readiness stage, and no new `retail check` rule id.

It is NOT a re-derivation of contrast math (CT1 already computes that; this
checklist CITES CT1's registered result -- see the `contrast` dimension
below), NOT a CVD-simulation score, and NOT a render/open/publish/connect
step. It VERIFIES already-committed static text; it never renders a report,
opens Power BI Desktop, publishes, or connects to a live semantic model
(F016 remains gated and unbuilt).

Use the four readiness statuses for the rolled-up `overall_status`, never a
number: `not_started` / `blocked` / `warning` / `pass`. Each of the three
dimensions is recorded as `reviewed-clean` / `not-applicable-with-reason` /
`blocked` ONLY -- there is NO numeric / maturity / confidence / completeness
score anywhere in this checklist (hard rule #9). This checklist never
self-grants `dashboard_ready: pass` -- that stays the BI / report owner's
recorded design-review action; this checklist is evidence FOR that sign-off,
never a substitute for it.

## Header

| Field | Value |
|-------|-------|
| `subject_area` | `<schema.table or model name>` |
| `page_id` | `<which report page this checklist covers>` |
| `filled_by` | `<analyst_or_agent>` |
| `filled_at` | `<YYYY-MM-DD>` |

## Dimension 1 -- `contrast` (cites CT1; never re-derived)

The contrast dimension is a pure CITATION of the already-shipped CT1 rule
(`src/retail/rules/design_contrast.py`) result for the page's design-tokens
file. It NEVER independently computes or asserts a contrast ratio, and it
can NEVER contradict CT1's registered finding.

| Field | Value |
|-------|-------|
| `token_file` | `<*-design-tokens.yaml file already associated with this page's design mapping, resolved via the SAME co-location convention templates/visual-implementation-trace.md already uses -- no new lookup mechanism>` |
| `ct1_result` | `<clean \| open-error: <finding text> \| parse-failure: <finding text> \| file-not-found>` |
| `disposition` | `<reviewed-clean \| blocked>` -- derived from `ct1_result`, never set independently |
| `reason` | `<required when disposition is blocked -- restate the CT1 finding verbatim, do not invent a different reason>` |
| `citation` | `[<token_file path>, "retail check CT1 result for that path, captured <YYYY-MM-DD>"]` |

**Derivation rule (never violate)**: `ct1_result: clean` -> `disposition:
reviewed-clean`. `ct1_result: open-error` / `parse-failure` / `file-not-found`
-> `disposition: blocked` (the contrast dimension MUST NOT be marked
`reviewed-clean` while CT1 reports an open finding). `not-applicable-with-
reason` is NOT a valid disposition for this dimension -- every page has some
text/background pairing, so contrast always applies.

**Invariant**: `disposition: reviewed-clean` implies `ct1_result: clean`.
These two fields MUST NEVER disagree. A filled checklist asserting
`reviewed-clean` while CT1 reports an open ERROR for the same token file is a
defect in the checklist, not a valid fill.

## Dimension 2 -- `colorblind_safe` (reviewed against fixed, generic criteria)

The colorblind-safe dimension reviews the page's declared multi-series
`dataColors` (or category palette) against the ONE fixed, generic criteria
list documented once at
`docs/powerbi/visual-design-system.md#colorblind-safe-palette-separation`
(never restated or reinvented per page). This is a documented HUMAN/agent-read
judgment against fixed criteria, NOT a numeric CVD-simulation score.

| Field | Value |
|-------|-------|
| `palette_source` | `<the committed theme/palette file whose dataColors or category palette this dimension reviews, e.g. themes/<name>.theme.json>` |
| `criteria_ref` | `docs/powerbi/visual-design-system.md#colorblind-safe-palette-separation` |
| `disposition` | `<reviewed-clean \| not-applicable-with-reason \| blocked>` |
| `reason` | `<required when disposition is not-applicable-with-reason -- e.g. "no multi-series dataColors/category palette declared on this page" (Edge Cases)>` |
| `finding_detail` | `<required when disposition is blocked -- name the specific colors/series that fail separation and propose the accessible alternative; never silently overridden, never silently complied with>` |
| `citation` | `[<palette_source path>]` |

`not-applicable-with-reason` is valid ONLY when the page genuinely declares no
multi-series palette (e.g. a single-series page) -- it is never used to skip a
page that does have one.

## Dimension 3 -- `rtl_arabic_layout` (reviewed against fixed, generic criteria)

The RTL/Arabic layout dimension reviews the page's layout artifact (text
direction, mirrored visual/axis alignment where direction carries meaning,
Arabic numeral/date formatting expectations) against the ONE fixed, generic
criteria list documented once at
`docs/powerbi/visual-design-system.md#rtl-arabic-layout-readiness` (never
restated or reinvented per page).

| Field | Value |
|-------|-------|
| `layout_source` | `<the page blueprint/layout artifact reviewed, e.g. mappings/<subject>/design/dashboard-layout.md>` |
| `criteria_ref` | `docs/powerbi/visual-design-system.md#rtl-arabic-layout-readiness` |
| `disposition` | `<reviewed-clean \| not-applicable-with-reason \| blocked>` |
| `scope_ruling_citation` | `<REQUIRED when disposition is not-applicable-with-reason -- see the OPEN Q-FR014-SCOPE stop-and-ask below; an assumed default alone is NOT a valid citation, this field MUST name an explicit named-human LTR-only ruling FOR THIS SPECIFIC PAGE>` |
| `finding_detail` | `<required when disposition is blocked -- name the specific mirroring/direction/formatting defect and propose the RTL-correct alternative; never silently overridden, never silently complied with>` |
| `citation` | `[<layout_source path>]` |

## Staleness (review-discipline obligation -- no automated detector)

When the cited `token_file`, `palette_source`, or `layout_source` changes
after this checklist was filled, this checklist becomes STALE evidence. There
is NO automated timestamp/hash/diff detector for this (FR-008 forbids a new
`retail check` rule) -- staleness is a human REVIEW-DISCIPLINE obligation
checked at the next `dashboard_ready` design-review sign-off. A reviewer
re-confirming a `pass` claim is responsible for noticing a cited file changed
and re-filling this checklist before relying on it for a fresh claim.

## Roll-up -- `overall_status` (worst of the three dimensions; never a number)

| Field | Value |
|-------|-------|
| `overall_status` | `<not_started \| blocked \| warning \| pass>` -- the WORST of the three dimension dispositions, mapped onto the four readiness statuses |
| `evidence` | `[<contrast citation>, <colorblind_safe citation>, <rtl_arabic_layout citation>]` |
| `blocking_reasons` | `[]` -- required whenever any dimension (or the overall status) is `blocked` |

Any dimension `blocked` -> overall at minimum `warning` (escalation to
`blocked` is the OPEN Q-FR014-SEVERITY question below -- do not resolve it
here); all three dimensions `reviewed-clean` or `not-applicable-with-reason`
(each with a valid citation) -> the checklist contributes toward `pass` for
this evidence item. This checklist NEVER itself sets `dashboard_ready: pass`
-- it produces evidence FOR that existing, separately-recorded sign-off.

## FORBIDDEN operations (standing guardrail -- do NOT fill; these always hold)

These hold for EVERY copy of this checklist, regardless of subject area (the
authority matrix says NO -- Product Module / artifact-writing):

- MUST NOT create truth: no defining business meaning, no approving a
  metric/mapping.
- MUST NOT grant approval or move a readiness stage to `pass` (named-human /
  Core Authority only); MUST NOT self-grant `dashboard_ready: pass`.
- MUST NOT render, open, or publish a Power BI report, and MUST NOT connect
  to Power BI Desktop or a live semantic model (those are Execution Adapter
  capabilities -- the deferred, gated F016).
- MUST NOT re-derive a contrast ratio that could contradict CT1's registered
  finding for the cited `token_file` (the `contrast` dimension is a pure
  citation, never an independent judgment).
- MUST NOT mark `rtl_arabic_layout.disposition: not-applicable-with-reason`
  without an explicit named-human LTR-only ruling citation for that specific
  page (an assumed default is not a valid citation -- see Q-FR014-SCOPE
  below).
- MUST NOT emit a numeric / maturity / confidence / completeness score
  anywhere in this checklist (hard rule #9).
- MUST NOT commit a real connection host, DSN, or secret (Principle IX).
- MUST NOT leave any dimension's `disposition` field blank or a
  `<placeholder>` -- a genuinely inapplicable dimension is filled as
  `not-applicable-with-reason` (with a valid citation), never silently
  omitted.

## Stop-and-ask: two OPEN Principle-V questions (carried forward, not answered)

These are business-policy / audience-scope decisions the agent MUST NOT
settle alone (Principle V). They are recorded here VERBATIM from
`specs/102-dashboard-a11y-rtl-gate/spec.md`'s `## Clarifications` section and
remain OPEN in every copy of this checklist until a named human rules.

- **Q-FR014-SCOPE (RTL-dimension applicability default)** -- OPEN. Is every
  dashboard page presumed IN-SCOPE for the RTL/Arabic layout dimension by
  default, requiring an explicit human LTR-only ruling before a page may be
  marked `not-applicable-with-reason` -- or is the reverse true (out-of-scope
  by default unless a human explicitly flags a page as serving an
  Arabic-reading audience)? RECORDED PENDING DEFAULT (not yet ratified): every
  page is presumed IN-SCOPE unless a named human explicitly marks that
  specific page LTR-only/English-only with a recorded reason. Until the owner
  rules, no page in this checklist may be marked `not-applicable-with-reason`
  for the `rtl_arabic_layout` dimension on the strength of an assumed default
  alone -- `scope_ruling_citation` must name an explicit human ruling.
- **Q-FR014-SEVERITY (block-vs-warning pass-bar)** -- OPEN. When any dimension
  surfaces an open finding (an open CT1 error, an unreviewed/failing
  colorblind-safe palette, or a genuine RTL/mirroring defect), does that make
  `dashboard_ready` `blocked`, or does it only downgrade the stage to
  `warning` -- the way a contrast note is treated as a `warning`-class design
  note in `dashboard-qa.md` / `screenshot-review.md` today? UNDECIDED pending
  a named-human ruling. Until the owner rules, an open finding in any
  dimension MUST be recorded as AT LEAST a `warning`-class finding cited in
  `blocking_reasons[]` or an equivalent warning-evidence entry -- it is never
  silently dropped, and this checklist does not unilaterally escalate it to
  `blocked` on its own authority.

## How it handles a missing input (Principle V; stop-and-ask)

When a required cited file (`token_file`, `palette_source`, or
`layout_source`) is missing, when CT1 cannot run (parse failure) for the
cited token file, or when a dimension's disposition is a genuine judgment
call this checklist's fixed criteria do not resolve, this checklist SURFACES
it as a blocking reason and STOPS -- it never fabricates the input,
self-approves, or proceeds past the missing evidence. A genuine RTL/mirroring
or colorblind-safety defect this checklist surfaces is recorded as a
`warning`- or `blocked`-class finding (per the OPEN Q-FR014-SEVERITY ruling
above) with the proposed accessible/RTL-correct alternative -- it is never
silently overridden and never silently complied with.

## See also

- The mechanical rule this checklist cites (never duplicates):
  `src/retail/rules/design_contrast.py` (CT1).
- The ONE committed home for the fixed colorblind-safe and RTL/Arabic
  criteria: `docs/powerbi/visual-design-system.md`
  (`#colorblind-safe-palette-separation`, `#rtl-arabic-layout-readiness`).
- The gate this checklist evidences (never re-decides): `docs/readiness/
  dashboard-ready.md`, `docs/readiness/readiness-model.md`.
- The structural precedent this checklist mirrors (additive evidence item, no
  new status/gate/rule): `templates/visual-implementation-trace.md` and its
  "Evidence item: 'design approved' vs 'page implemented'" section in
  `docs/readiness/dashboard-ready.md` (F034).
- The authority category + matrix: `docs/architecture/product-modules.md`;
  the copy-me declaration: `templates/module-contract.md`.
- The theme-json purity linter this checklist stays distinct from (a
  forbidden-key scan, not a legibility review): spec 060.
- The deferred execution/publish adapter (named, never invoked): F016.
- The worked instance (CITED, never inlined):
  `mappings/<subject>/design/a11y-rtl-readiness-checklist.md` (worked example:
  `mappings/retail_store_sales/design/a11y-rtl-readiness-checklist.md`).
