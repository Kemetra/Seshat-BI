# Feature Specification: Visual Implementation MVP (F034) -- turn an approved blueprint into a real PBIR page, by hand, reviewed in git

**Feature**: F034 (roadmap F-number) | **Spec directory**: `039-visual-implementation-mvp` (next free on-disk slot -- the script numbers from the current max `038`, not the first gap; the roadmap F-number is authoritative -- see `docs/roadmap/roadmap.md` numbering note)

**Feature Branch**: `039-visual-implementation-mvp` (located via `.specify/feature.json`)

**Created**: 2026-06-25

**Status**: Finalized -- authoring slice shipped 2026-06-26. The three GENERIC artifacts
exist: the trace template (`templates/visual-implementation-trace.md`) and the Dashboard
Ready evidence-item edit (`docs/readiness/dashboard-ready.md`) landed with the Tier-5 batch
(`aba74c8`); the implementation-review procedure
(`.claude/skills/powerbi-dashboard-design/workflows/visual-implementation-review.md`) landed
2026-06-26, completing the rule-8 authoring slice. **The built-page worked example (US-1,
SC-001, SC-007, FR-013) remains UNMET by design** -- it requires a human building the page in
Power BI Desktop and committing the PBIR (FR-008/FR-009 forbid agent-generated PBIR; Desktop
is also absent on the authoring machine). That step is deferred to the BI owner; the agent's
procedure + trace + verification are ready for it. The gate (FR-006) is satisfied for
`retail_store_sales` (`semantic_model_ready: pass` + design-review sign-off recorded
2026-06-25), so the build is unblocked whenever the owner performs it.

**Input**: "Visual Implementation MVP (F034). Layer 6 (Dashboard & Delivery). Advances readiness stage: Dashboard Ready -- specifically, it advances `dashboard_ready` from 'design approved on paper' to 'the approved design is realized as visuals on a real PBIR page'. A human builds the approved dashboard blueprint as visuals in Power BI Desktop, saves the report as plain-text PBIR (PBIP), and the page is reviewed in git like code. Docs/templates/skill-only authoring slice (roadmap rule 8); generic to retail BI (rule 7). INDEPENDENT of F016: it is a MANUAL Desktop build with git-diff review, not execution automation, so it crosses no automation boundary (rule 6 gates only the F016 adapter). HARD GATES inherited from Dashboard Ready: no implementation before `semantic_model_ready` is `pass` and the design-review sign-off exists (rule 5); NO pbi-cli / Power BI MCP automation, NO publish (rule 6, F016 owns that). It adds NO new readiness stage and NO new `retail check` rule -- only an evidence item under the existing Dashboard Ready owner."

## Clarifications

### Session 2026-06-25

- Q: The trace template records a per-visual status, but the spec only names `pass` and `blocked`, while the readiness model defines four statuses (`not_started` / `blocked` / `warning` / `pass`) and the Edge Cases describe a post-build divergence as a `warning` finding. Which status set does the trace template's status column admit? -> A: The trace status column admits the full readiness four-status set verbatim (`not_started` / `blocked` / `warning` / `pass`), never a fabricated score. A measure-bearing row is `pass` only when it binds 1:1 to exactly one approved contract by name AND a mapped model field; `blocked` for an orphan visual (not in the approved binding map) or an unmapped field; `warning` for a non-blocking divergence surfaced during/after the build (e.g. an accepted layout deviation, or a built visual whose map entry was re-approved upstream and now diverges) that must be visible but does not by itself retract design approval; `not_started` for an approved binding-map entry with no built visual yet. The overall trace rolls up to the worst row status. This reuses the readiness model verbatim and adds no fifth status (FR-005, FR-012).

- Q: O-1 asks whether the implementation-verification procedure ships as a new workflow alongside `powerbi-handoff.md` or as a thin standalone verb skill. Does this slice ratify the recorded reversible default for the artifacts authored here? -> A: Yes -- for THIS slice the procedure ships as a new workflow `visual-implementation-review.md` ALONGSIDE `powerbi-handoff.md` under `.claude/skills/powerbi-dashboard-design/workflows/` (the recorded reversible default). The build is the natural continuation of F011A surface 4 and reuses its handoff notes verbatim as the input contract; this adds no new top-level directory and no new skill (Principle II reuse, YAGNI). Promoting it to a standalone verb skill remains a later, separate, reversible decision and is NOT pre-empted here. O-1's disposition is now "default ratified for this slice"; it is not a blocking open item.

## Why this feature exists

The readiness spine defines Stage 6, **Dashboard Ready** (`docs/readiness/dashboard-ready.md`):
a report is designed AGAINST approved metric contracts, and the BI owner signs off the
visual->contract binding review. Feature F011/012 (the `dashboard-design` verb) authors that
design -- a layout plan, a visual list, and a visual->contract binding map -- and F011A (the
`powerbi-dashboard-design` foundation) is the vocabulary it reasons with. Both are SHIPPED.

But today, when those finish, `dashboard_ready` can read `pass` while **no report page has
ever been built**. The status is granted on DESIGN artifacts plus a design-review sign-off,
not on a realized page. The live proof of the gap is in the repo right now:
`powerbi/RetailStoreSales.Report` has a single empty "Page 1" with zero visual containers,
while `mappings/retail_store_sales/design/` holds a complete, owner-approved design -- a
7-region layout, a 10-visual list, and a visual->contract binding map -- bound to 5 approved
contracts at `semantic_model_ready: pass`. The approved design has simply never been turned
into visuals on the page.

That last step -- **blueprint -> visuals on a real PBIR page** -- is genuinely unspecced. It
is the unclaimed seam between the F011/012 verb (which STOPS at the binding map) and F016
(which is deferred, execution-only, and gated). An analyst who wants the dashboard they
approved has, today, only the option to improvise the build with no committed procedure and
no reviewable trace -- exactly the unreviewed drift this kit exists to prevent.

This feature fills that seam with the **manual implementation MVP**: a committed procedure by
which a human builds the approved blueprint as visuals in Power BI Desktop, saves the report
as plain-text PBIR (the `pbip-workflow` the repo already endorses), and the result is reviewed
in git like code -- visual by visual, each traced back to the approved binding map. It is the
agent expression of rule 8 (a stage is a doc + procedure before it is automation) for the one
Dashboard Ready step that had neither.

## The core idea: a manual build with a reviewable, traced result -- not automation

The single load-bearing behavior this feature adds is **closing the loop between the approved
binding map and the built page, with a git-reviewable trace, while crossing no automation
boundary**. Three properties hold together:

| Property | What it means | Why it matters |
|----------|---------------|----------------|
| **Human-built in Desktop** | a person creates each visual in Power BI Desktop from the visual spec; no tool generates PBIR | the build stays inside the blessed `pbip-workflow`; Desktop owns `report.json`/`diagramLayout.json` |
| **Saved as plain-text PBIR (PBIP)** | the report is saved in PBIP form so `definition/` is committed as reviewable text | a page becomes a git diff a reviewer reads like code, not an opaque `.pbix` |
| **Traced 1:1 to the approved binding map** | every built measure-bearing visual maps to exactly one approved metric contract from the binding map; no visual is added that the design did not approve | the page cannot silently introduce an unapproved metric or an orphan visual |

The failure mode this feature exists to prevent is an **ad-hoc build**: someone opens Desktop,
adds visuals from memory, and ships a `.pbix` no one can diff. That reintroduces an
unapproved metric, an unmapped field, or a number that contradicts the approved contract
(the discount-rate trap below) -- with no committed procedure and no trace to catch it.

## Relationship to F016 (the it-is-NOT-execution-automation boundary)

This feature deliberately sits next to F016 (the deferred Power BI EXECUTION adapter -- the
official Power BI MCP / connection; `pbi-cli` no longer preferred). The roadmap's hard rule 6
makes F016 LAST and gated. So the boundary MUST be stated and MUST hold, or this feature would
be read as pre-empting the deferred adapter:

- **F016 is EXECUTION AUTOMATION.** A future adapter that programmatically MATERIALIZES and
  PUBLISHES an already-approved model: it would emit the PBIR project, bind visuals, set the
  model reference, and push to a workspace -- without a human in Desktop. Rule 6 gates THAT
  because automated generation/publish before semantic-model readiness is dangerous.
- **F034 is a HUMAN MANUAL BUILD reviewed in git.** A person builds in Desktop and commits
  plain-text PBIR; the only "tooling" is git diff. This is the repo's already-endorsed
  `pbip-workflow` -- neither generation nor publish.
- **F034 is therefore INDEPENDENT of F016, not blocked by it.** Rule 6 forbids the automation,
  not the manual build. "No current readiness stage depends on F016" (roadmap) -- so the manual
  implementation does not wait on it. F034 explicitly does NOT add any pbi-cli/MCP command,
  any generation script, or any publish step; if asked to, it STOPS and names F016 as the
  owner (the same boundary the `powerbi-handoff` workflow already draws).
- **F034 adds NO new gate and NO new readiness stage.** Dashboard Ready's gate (rule 5:
  contracts first; the design-review sign-off) is owned by the stage doc + F011/012 and is
  reused VERBATIM. This feature adds only an EVIDENCE ITEM under the existing Dashboard Ready
  owner (see FR-005) -- it does not re-decide the gate or create a second source of truth
  (constitution Governance, amendment clause: no divergent source of truth).

## Relationship to F011/012 and F011A (consumes, never re-designs)

- **F011/012 (the verb) is the PRODUCER of the design.** It authors the layout plan + visual
  list + visual->contract binding map and records the design-review sign-off. F034 CONSUMES
  those artifacts; it never re-designs, never re-binds, never invents a metric.
- **F011A (the foundation) is the VOCABULARY.** Its `powerbi-handoff` workflow (surface 4)
  already produces the build NOTES in build order and explicitly says "Manual build until
  F016 -- every step is performed by a human in Power BI Desktop today." F034 is the spec that
  turns those notes into a committed, gated, traced READINESS STEP with a verification that
  the built page matches the binding map. F034 does not duplicate the handoff notes; it
  consumes them as its input contract.
- **Open decision O-1 (default RATIFIED for this slice, see Clarifications 2026-06-25): does the
  implementation verification live as a new workflow under
  `.claude/skills/powerbi-dashboard-design/workflows/` (alongside `powerbi-handoff.md`), or as a
  thin new verb skill?** Disposition: **a new workflow alongside `powerbi-handoff.md`**
  (`visual-implementation-review.md`) -- ratified for the artifacts THIS slice authors, because the
  build is the natural continuation of surface 4 and reuses its inputs verbatim (adds no new
  top-level directory and no new skill). Promoting it to a standalone verb skill remains a later,
  separate, reversible decision recorded in tasks -- this slice does not pre-empt it. (Same posture
  F011A used for its router-vs-verb O-1.)

## Architecture (a docs/templates/skill authoring slice; no codegen, no engine, no CLI)

The slice is committed text plus the worked-example page; no automation:

- **One agent-procedure workflow** -- the manual-build + git-review procedure (per O-1, a
  `workflows/visual-implementation-review.md` alongside `powerbi-handoff.md`): it (a) restates
  the build order from the handoff notes, (b) defines the git-diff review checklist a reviewer
  runs on the committed PBIR, and (c) defines the 1:1 trace check (every measure-bearing
  visual on the page maps to exactly one contract in the binding map; the page adds no visual
  the map did not approve).
- **One generic template** -- `templates/visual-implementation-trace.md`: a copy-me blank that,
  for any subject area, lists each built visual, the contract it binds to (by name), the mapped
  field(s), and a PASS/blocking-reason column -- the reviewable evidence artifact.
- **Dashboard Ready doc edit** -- `docs/readiness/dashboard-ready.md` gains an explicit
  distinction between "design approved" and "page implemented" as an EVIDENCE ITEM (not a new
  status, not a new gate): a `pass` may record `evidence: built-page traces to the approved
  binding map; R1 passes`.
- **First worked example** -- the `retail_store_sales` empty Page 1 is built into the approved
  10-visual page in Power BI Desktop, saved as PBIR, committed, and reviewed -- producing a
  filled `visual-implementation-trace.md` instance under `mappings/retail_store_sales/design/`.

There is NO PBIR generator, NO pbi-cli command, and NO publish step -- by design (rule 6). The
value is the committed procedure + the reviewable trace; the build itself is a human action in
Desktop and the review is a human reading a git diff. The agent's role is to produce the
procedure and the trace template, and to VERIFY (read-only) that a committed page matches its
binding map -- never to author or publish the PBIR itself.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the approved blueprint as a real PBIR page, reviewed in git (Priority: P1)

A BI owner has an approved dashboard design for a subject area whose `dashboard_ready` records
a design-review sign-off (visual->contract binding map approved). They want the dashboard that
was approved -- a real page, not just a plan. Following the committed procedure, a human builds
each visual in Power BI Desktop from the visual specs, saves the report as plain-text PBIR
(PBIP), and commits `definition/`. The agent then produces the implementation trace (each built
visual -> its one approved contract -> mapped field) and the reviewer reads the git diff of the
page plus the trace, confirming the built page realizes the approved binding map and nothing
more.

**Why this priority**: this is the feature. Turning an approved design into a reviewable built
page is the one Dashboard Ready step that had no committed procedure. Everything else is the
guardrail around it. If the build cannot be performed and reviewed against the approved map,
the seam stays open.

**Independent Test**: take the `retail_store_sales` approved design (10 visuals, binding map
approved, `semantic_model_ready: pass`); build its page in Power BI Desktop, save as PBIR,
commit; produce the filled trace; an auditor confirms the committed `definition/pages/...`
contains the approved visuals, each row of the trace maps a built measure-bearing visual to
exactly one approved contract and a mapped field, the diff is plain-text reviewable, and R1
(`retail check`) still passes (PBIR references the model by relative path).

**Acceptance Scenarios**:

1. **Given** an approved binding map and `semantic_model_ready: pass`, **When** the human
   builds the page in Desktop and saves as PBIR, **Then** the committed `definition/` contains
   one visual container per approved measure-bearing visual and the report still references the
   model by a relative path (R1 passes).
2. **Given** the committed page, **When** the agent produces `visual-implementation-trace.md`,
   **Then** every measure-bearing visual on the page appears as one row binding to exactly one
   approved contract by name plus its mapped field(s), and the trace's status is `pass` only if
   all rows trace cleanly.
3. **Given** the trace and the page diff, **When** the reviewer reads them in git, **Then** the
   review is performed on plain text (no opaque `.pbix`), and the sign-off is recorded as a
   Dashboard Ready `evidence[]` item ("built-page traces to approved binding map; R1 passes").

### User Story 2 - Refuse to build (or to bless a build) when the design is not approved (Priority: P1)

A request would build the page (or record the implemented-page evidence) for a subject area
whose `semantic_model_ready` is not `pass`, or whose design-review sign-off is not recorded, or
whose binding map is missing. The procedure's hard gate -- inherited VERBATIM from Dashboard
Ready and F011/012 -- makes the agent REFUSE: no page is blessed as implemented before the
design it implements is approved. The agent records the blocking reason and STOPS, pointing to
the upstream stage. A built page that introduces a visual NOT in the approved binding map is an
orphan and fails the trace.

**Why this priority**: the gate is what keeps the implementation honest (rule 5). A feature that
let a page be built and blessed before its design was approved -- or let the build add unapproved
visuals -- would defeat the readiness system. Refusing is as load-bearing as building.

**Independent Test**: for a fixture subject area with `semantic_model_ready` in each non-`pass`
status, and one with `pass` but no recorded design-review sign-off, an "implement the page"
request yields zero implemented-page evidence + the matching blocking reason; a built page
carrying a visual absent from the approved binding map yields a `trace: blocked` with an
"orphan visual: not in approved binding map" reason; an auditor confirms the gate fired in each
case and only those.

**Acceptance Scenarios**:

1. **Given** `semantic_model_ready` is not `pass`, **When** an implementation is requested,
   **Then** the agent records no built-page evidence, records the blocking reason ("no approved
   contracts -- Dashboard Ready gate, rule 5"), and points upstream.
2. **Given** `semantic_model_ready: pass` but no recorded design-review sign-off, **When** an
   implementation is requested, **Then** the agent does not bless any built page (the
   implemented-page evidence requires the design-review sign-off to exist first) and records
   "design-review sign-off not recorded".
3. **Given** a built page contains a measure-bearing visual that is not in the approved binding
   map, **When** the trace is produced, **Then** that visual is recorded as "orphan visual: not
   in approved binding map" and the trace status is `blocked`, never `pass`.
4. **Given** a built visual uses a field not present in the governed semantic model, **When**
   the trace is produced, **Then** it is recorded as "unmapped field" and the trace status is
   `blocked`.

### User Story 3 - Stay strictly inside the manual / no-publish boundary (Priority: P1)

A user asks to "just generate the report", "run pbi-cli", or "publish it to the workspace".
The procedure STOPS at the manual-build + git-review boundary: it produces or verifies the
committed PBIR a human built, and it names F016 as the owner of any generation or publish step.
The slice edits no semantic-model file, writes no DAX, runs no pbi-cli/MCP command, and pushes
nothing to a workspace.

**Why this priority**: this is the boundary that keeps F034 from being read as pre-empting the
deferred, gated F016 (rule 6). A manual build is allowed; automating or publishing it is not.
The separation is what makes the MVP safe to ship before F016 exists.

**Independent Test**: across a fixture set of requests including "generate the PBIR", "run
pbi-cli", and "publish to workspace", the procedure produces zero automation/publish output and
names F016 in each case; an auditor confirms zero pbi-cli/MCP commands, zero generated PBIR,
zero publish actions, and zero semantic-model/DAX/SQL edits.

**Acceptance Scenarios**:

1. **Given** a request to "generate the report automatically", **When** the agent responds,
   **Then** it produces only the manual-build procedure / trace and names F016 as the owner of
   any generation -- it emits no PBIR-generating command or script.
2. **Given** a request to "publish to the workspace", **When** the agent responds, **Then** it
   STOPS and names F016 -- it performs no publish and records the boundary.
3. **Given** the slice's committed artifacts, **When** they are inspected, **Then** they contain
   zero pbi-cli/MCP commands, zero DAX/SQL, zero semantic-model edits, and the only PBIR change
   is the human-built page committed as plain text (a Desktop save), not an agent-authored file.

### Edge Cases

- **The approved design changes after the page is built.** The binding map is re-approved
  upstream (F011/012); the page must be rebuilt to match and the trace re-run. The trace's job
  is to make the divergence visible (a built visual no longer in the map, or a map entry with
  no built visual) -- it does not silently accept a stale page as `pass`.
- **Desktop owns `report.json` / `diagramLayout.json`.** The human builds visuals IN Desktop
  and commits Desktop's save; the procedure forbids hand-editing visual-container JSON or those
  Desktop-owned files (it can break the project, per `pbip-workflow`). The reviewable diff comes
  from a real Desktop save, not hand-authored JSON.
- **Windows path / encoding limits.** The nested PBIR `definition/pages/<id>/...` folders plus
  short project/table names must stay under the 260-char path limit; committed text is UTF-8
  without BOM (CLAUDE.md hard rules). A build that breaks either is not committable.
- **A slicer / dimension control is on the page.** Filter-rail slicers are dimension controls,
  not measure-bound visuals; they do not appear in the binding map and are not trace rows (the
  trace governs measure-bearing visuals only) -- matching the F011/012 binding-map convention.
- **The discount-rate trap (worked example honesty).** The `retail_store_sales` discount visual
  MUST show the APPROVED `DiscountedTransactionRate` = 50.37% (discounted / known-status) and
  surface the contract caveat (33.39% unknown status excluded; 33.55% floor if unknowns were
  treated as not-discounted). The built page and the trace MUST reflect the corrected 50.37%
  framing -- never the retracted/stale figure -- or it republishes a known-bad number.
- **`dashboard_ready` is already `pass` on design alone.** Building the page must not DOWNGRADE
  a legitimately-approved design; it ADDS the implemented-page evidence item. If the build
  reveals a divergence from the map, that is a new `warning`/`blocked` finding on the page, not
  a retraction of the design approval.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The procedure MUST define a committed, ordered manual build of the approved
  blueprint into a real PBIR page in Power BI Desktop, consuming the F011A `powerbi-handoff`
  notes as its input contract -- restating, never re-deriving, the build order (theme ->
  background -> visuals -> slicers/interactions -> mobile -> QA).
- **FR-002**: The report MUST be saved as plain-text PBIR (PBIP) so the page is committed as
  reviewable text under `<report>/definition/`; the slice MUST treat the page as a git diff a
  reviewer reads, never an opaque `.pbix`.
- **FR-003**: Every measure-bearing visual on the built page MUST trace to exactly one approved
  metric contract (by name) from the approved binding map AND to a field present in the governed
  semantic model. A visual not in the approved binding map is an orphan and MUST make the trace
  `blocked`; a field absent from the model is unmapped and MUST be recorded as a blocking reason.
- **FR-004**: The slice MUST NOT invent, define, or alter a metric, and MUST NOT re-design or
  re-bind. Metric definition is F009's job, design/binding is F011/012's; this slice only
  realizes and verifies an already-approved design.
- **FR-005**: The slice MUST record the implemented-page result as an EVIDENCE ITEM under the
  EXISTING Dashboard Ready owner (`evidence: built-page traces to approved binding map; R1
  passes`). It MUST NOT add a new readiness stage, a new readiness status meaning, a new
  `retail check` rule, or a second/divergent gate (no divergent source of truth).
- **FR-006**: The slice MUST inherit the Dashboard Ready hard gate VERBATIM: no implemented-page
  evidence is recorded before the subject area's `semantic_model_ready` is `pass` AND the
  design-review sign-off is recorded (rule 5). If either is missing, the agent records the
  blocking reason and STOPS.
- **FR-007**: The PBIR MUST reference the governed semantic model by a RELATIVE path (the same
  constraint `retail check` R1 enforces) -- never an absolute/remote ref, never a real host.
- **FR-008**: This slice MUST NOT generate PBIR, write DAX, change SQL, edit any semantic-model
  file, run any pbi-cli / Power BI MCP command, or publish to a workspace. Any such request is
  STOPPED and F016 is named as the owner (rule 6). The only PBIR change is the human's Desktop
  save of the built page, committed as plain text.
- **FR-009**: The build MUST be a HUMAN action in Power BI Desktop; the procedure MUST forbid
  hand-editing Desktop-owned files (`report.json`, `diagramLayout.json`) or hand-authoring
  visual-container JSON, so the committed diff comes from a real Desktop save and the project
  stays openable.
- **FR-010**: All generic artifacts (the workflow, the trace template, the Dashboard Ready doc
  edit) MUST be generic to retail BI (rule 7): no C086/pharmacy or other subject-area specifics
  in any committed generic file. Worked values live only in the per-subject-area instance.
- **FR-011**: The slice MUST stop at Principle V judgment calls -- whether a built page
  faithfully realizes an approved design, whether a layout deviation discovered during the build
  is acceptable, whether the design-review sign-off covers the built page -- surfacing them to
  the BI owner rather than self-answering or self-granting `dashboard_ready: pass`.
- **FR-012**: The slice MUST record readiness consistent with the readiness model (`not_started`
  / `blocked` / `warning` / `pass` + `evidence[]` + `blocking_reasons[]`) and MUST NOT fabricate
  a confidence score (rule 9). It MUST NOT self-grant `dashboard_ready: pass` -- that is the BI
  owner's recorded design-review action.
- **FR-013**: The worked example (`retail_store_sales`) MUST realize the approved 10-visual
  design and MUST reflect the corrected `DiscountedTransactionRate` = 50.37% (discounted /
  known-status) with the contract caveats (33.39% unknown excluded; 33.55% floor) -- never the
  retracted/stale figure -- on both the built discount visual and its trace row.
- **FR-014**: All committed files MUST be ASCII, UTF-8 without BOM, with short repo-relative
  paths (`<= 200` chars), honoring the Windows 260-char PBIR path limit, and MUST NOT bake in
  any real connection host or secret (Principle IX + G6).

### Key Entities

- **Built PBIR page (the central artifact)**: the realized report page -- visual containers a
  human created in Power BI Desktop from the approved visual specs, saved as plain-text PBIR
  under `<report>/definition/pages/<id>/`, committed and reviewed in git. It is built, not
  generated; reviewed, not published.
- **Implementation trace (output)**: `templates/visual-implementation-trace.md` (generic blank)
  and its per-subject-area filled instance -- one row per built measure-bearing visual mapping
  it to exactly one approved contract by name, the mapped field(s), and a status drawn from the
  readiness four-status set (`not_started` / `blocked` / `warning` / `pass`) plus a
  blocking/divergence reason; the overall trace rolls up to the worst row status. The reviewable
  evidence that the page realizes the approved binding map.
- **Implementation review workflow (output)**: the agent-procedure markdown (per O-1, a
  `visual-implementation-review.md` alongside `powerbi-handoff.md`) -- restates build order,
  defines the git-diff review checklist, and defines the 1:1 trace check. It verifies a
  committed page; it does not author or publish one.
- **Dashboard Ready evidence item (output)**: the `docs/readiness/dashboard-ready.md` edit that
  distinguishes "design approved" from "page implemented" as an EVIDENCE ITEM under the existing
  owner -- no new status, no new gate, no new rule.
- **Approved binding map / visual list / layout plan (inputs, from F011/012)**: the design
  artifacts the build realizes and the trace checks against. This feature consumes them; it never
  re-designs or re-binds.
- **F011A handoff notes (input, from F011A)**: the `powerbi-handoff` build notes in build order;
  this feature's input contract for the manual build. Consumed, never duplicated.
- **F016 (the deferred boundary, NOT an input)**: the execution adapter that WOULD generate and
  publish. Named as the owner of any automation/publish; never invoked by this slice.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the `retail_store_sales` worked example, the approved 10-visual design is
  realized as a committed PBIR page; the committed `definition/` contains one visual container
  per approved measure-bearing visual; R1 (`retail check`) passes (relative model path); the
  page diff is plain-text reviewable (0 opaque `.pbix` committed).
- **SC-002**: 100% of measure-bearing visuals on a built page trace to exactly one approved
  contract by name AND a mapped semantic-model field; 0 visuals on a `pass` page are orphans
  (absent from the approved binding map) and 0 cite an unmapped field.
- **SC-003**: For every non-`pass` `semantic_model_ready` status and for a `pass`-but-no-sign-off
  fixture, 0 implemented-page evidence items are recorded and the matching blocking reason is
  present -- the hard gate (rule 5) holds in 100% of gated cases.
- **SC-004**: Across all runs the slice emits 0 generated PBIR, 0 pbi-cli / Power BI MCP
  commands, 0 publish actions, 0 DAX, 0 SQL changes, and 0 semantic-model edits -- the
  manual/no-publish boundary (rule 6) holds 100% of the time; the only PBIR change is the
  human's Desktop save.
- **SC-005**: The slice adds 0 new readiness stages, 0 new readiness statuses, and 0 new
  `retail check` rules; the implemented-page result is recorded ONLY as an `evidence[]` item
  under the existing Dashboard Ready owner. `retail check` exits 0 with its rule count UNCHANGED.
- **SC-006**: 0 C086/pharmacy or other subject-area specifics appear in any committed GENERIC
  artifact (the workflow, the trace template, the Dashboard Ready doc edit); a reviewer scanning
  every generic file finds only placeholders.
- **SC-007**: The `retail_store_sales` built discount visual and its trace row show the approved
  `DiscountedTransactionRate` = 50.37% with the caveats (33.39% unknown excluded; 33.55% floor);
  0 occurrences of the retracted/stale rate appear in the built page or the trace.
- **SC-008**: The slice writes `dashboard_ready: pass` in 0 runs as a self-grant -- the
  implemented-page evidence is recorded, but `pass` remains the BI owner's recorded design-review
  action; readiness is the four statuses + evidence + blockers, never a numeric score.
- **SC-009**: All committed files are ASCII + UTF-8 no BOM with repo-relative paths `<= 200`
  chars; the PBIR page folders stay under the Windows 260-char path limit; 0 real hosts/secrets
  appear in any committed file.

## Assumptions

- **F011/012 (the dashboard-design verb) and F011A (the foundation) are the upstream
  dependencies and are SHIPPED.** The build realizes F011/012's approved binding map using
  F011A's `powerbi-handoff` notes as the input contract. This feature consumes them; it never
  re-designs, re-binds, or duplicates them.
- **Dashboard Ready's gate and owner are unchanged.** The gate (rule 5: contracts first + the
  design-review sign-off) and the `dashboard_ready: pass` owner (the BI/report owner, per
  `docs/readiness/dashboard-ready.md`) stay as they are. F034 adds an EVIDENCE ITEM, not a gate
  (the no-divergent-source-of-truth boundary above).
- **The deferred execution/publish engine is F016** (the official Power BI MCP / connection;
  `pbi-cli` no longer preferred -- the last, gated feature). A manual Desktop build with
  git-diff review is NOT F016 and does not wait on it (rule 6 gates the automation, not the
  manual build). This slice stops at the manual-build + review boundary and never enters F016's
  territory.
- **The build is performed by a human in Power BI Desktop.** PBIP is a preview feature enabled
  in Desktop (CLAUDE.md). The agent produces the procedure and the trace and VERIFIES (read-only)
  a committed page; it does not author or publish the PBIR. Desktop owns `report.json` /
  `diagramLayout.json`; the procedure forbids hand-editing them.
- **The first worked example is `retail_store_sales`**, whose empty Page 1 + approved 10-visual
  design already exist in the repo. C086 is the prior worked example, not the schema (rule 7,
  Principle VII); generic artifacts carry placeholders only.
- **Reuse over new surface (Principle II, YAGNI):** docs/templates/skill + the human-built
  worked-example page only -- no PBIR generator, no theme/page codegen, no `retail` CLI
  subcommand, no new `retail check` rule. O-1 (workflow-alongside vs standalone verb skill) is
  recorded with a reversible default (alongside).
- **This is a planning + authoring slice consistent with the readiness roadmap** (Layer 6,
  Dashboard Ready). It changes no existing gate, moves no existing doc's authority, and writes no
  runtime code; the one PBIR change is a human Desktop save committed as reviewable text.
