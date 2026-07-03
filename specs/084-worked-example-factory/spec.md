# Feature Specification: Worked-Example Factory

**Feature Branch**: `spec/worked-example-factory` (spec dir: `specs/084-worked-example-factory/`)

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "Define a REPEATABLE PROCESS for creating additional
GENERIC worked examples (e.g. inventory, customer loyalty) to move beyond a single
worked example. Generic examples only, no client-specific data, no C086
resurrection. Must define acceptance criteria for what qualifies as a complete
worked example. Must distinguish docs/example maturity from runtime capability.
Must not fabricate metrics, KPI contracts, or approvals."

## Why this feature exists

Seshat BI ships exactly one worked example today, `retail_store_sales`
(`docs/worked-examples/retail-store-sales.md`), which traverses the full
seven-stage readiness spine to Dashboard Ready (Publish Ready honestly held at
`warning`). It is cited everywhere as "an example, never the universal schema"
(Constitution Principle VII), but the repo has never written down **how a second
one gets made** -- what domain makes a good candidate, which artifacts a
"complete" example must produce, and where the line sits between "the docs got
richer" and "the tool gained a feature." Without that process, each future
worked example would be authored ad hoc, at risk of (a) silently narrowing scope
until it stops proving genericity, (b) fabricating approvals or metrics to look
"done," or (c) blurring into a claim that the runtime itself grew a capability
it did not.

This feature defines that process, as documentation: a repeatable recipe plus a
completeness contract. It does not execute the recipe. It does not build an
inventory or loyalty example. It defines what "complete" means so a future
author (human or agent) -- and a future reviewer -- can tell.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author picks and starts a new worked-example domain (Priority: P1)

An author (agent or analyst) wants to add the repo's second worked example -- say,
inventory or customer loyalty -- to demonstrate the kit's genericity on a
structurally different domain (different grain, different PII shape, a return
path retail_store_sales lacks, etc). Today they would have to reverse-engineer
the process from reading `retail-store-sales.md` and guessing what is essential
versus incidental to that one instance.

**Why this priority**: without a documented selection method and a starting
checklist, every future example either copies retail_store_sales too literally
(missing the point of proving genericity) or invents its own undocumented
process (drifting the kit's practice).

**Independent Test**: hand a fresh agent only this spec's `quickstart.md` and the
five mapping-gate templates (no other guidance) and confirm it can name a
candidate domain, state why it is a good genericity test, and identify the first
artifact to author -- without inventing new templates or reading
retail-store-sales.md as a copy-paste source.

**Acceptance Scenarios**:

1. **Given** the factory's domain-selection guidance (`research.md` Sec "What makes
   a good generic example domain"), **When** an author evaluates a candidate
   domain (e.g. inventory), **Then** they can state which existing-example axis
   it varies (grain, PII shape, returns, language, a business-rollup need) and
   confirm it introduces no client-specific fact.
2. **Given** the maturity ladder (`templates/maturity-report.md`, rungs L1/L2),
   **When** an author starts a second worked example, **Then** they can state
   that finishing it advances the reported rung from "L1: one worked example" to
   "L2: two worked examples" -- a milestone claim, never a percentage or score.

---

### User Story 2 - Reviewer judges whether a worked example is "complete" (Priority: P1)

A reviewer (human or a governance skill) is handed a candidate worked-example
directory (`mappings/<new-table>/` plus a narrative doc under
`docs/worked-examples/`) and must decide: is this a complete worked example, or
is it partial / premature / fabricated?

**Why this priority**: this feature exists primarily to make that judgment
checkable rather than a matter of taste. Without a written completeness
contract, "done" silently means "as far as the last author got," and a partial
example could be merged and then cited as proof of genericity it does not
provide.

**Independent Test**: apply the acceptance-criteria contract
(`contracts/worked-example-completeness.md`) to the existing
`mappings/retail_store_sales/` + `docs/worked-examples/retail-store-sales.md` set
and confirm it scores "complete" against every required item -- proving the
contract is calibrated to the one example the repo already trusts, not a
stricter or looser bar invented for this feature.

**Acceptance Scenarios**:

1. **Given** a candidate worked example missing a metric contract or a
   binding-map entry, **When** the completeness contract is applied, **Then**
   the reviewer can point at the specific missing artifact/section, not just say
   "not done."
2. **Given** a candidate worked example whose `readiness-status.yaml` shows a
   `mapping_ready` approval recorded by the authoring agent itself (no named
   human), **When** the completeness contract is applied, **Then** it is
   rejected on that fact alone -- a self-granted approval fails completeness
   regardless of how many artifacts exist (Principle V).
3. **Given** a candidate worked example that reaches Gold Ready with no live DB
   available, **When** the completeness contract is applied, **Then** it is
   scored against the **repo-only completeness tier** (artifacts authored,
   `retail check` clean, live legs explicitly `[PENDING LIVE PROFILE]`) rather
   than being rejected outright or silently marked complete.

---

### User Story 3 - Distinguish "we added an example" from "the kit gained a feature" (Priority: P1)

Someone reading `RELEASE_NOTES.md` or a PR description after a second worked
example lands must be able to tell that the kit's **capability surface**
(`src/retail/`, its rule set, its CLI verbs) did not change -- only the example
corpus grew. Conversely, someone must not be able to smuggle a claim like "the
kit now supports inventory tracking" or "returns handling is now supported" past
review just because a worked example happened to touch that domain.

**Why this priority**: this is the specific failure mode named in the task
(docs/example maturity vs runtime capability) and the sharpest way a
worked-example factory could quietly misrepresent what was built. It is a
governance property of the *process*, not of any one example, so it belongs in
this spec rather than being re-derived per example.

**Independent Test**: given a hypothetical release note draft that says "added
the inventory worked example; the kit can now track stock levels," an author
applying this feature's maturity-vs-capability rule can identify the sentence as
a violation and rewrite it to "added the inventory worked example (maturity: L1
-> L2 evidence); no `src/retail` change, no new CLI verb, no new rule."

**Acceptance Scenarios**:

1. **Given** a completed second worked example, **When** the maturity ladder
   (`templates/maturity-report.md`) is (re-)assessed, **Then** the reported rung
   moves from L1 to L2 **only if** the binary evidence test for L2 is met (>= 2
   worked-example tables with mapping artifacts under `mappings/`), and the
   report is worded as a milestone, never a score.
2. **Given** the same event, **When** any generated documentation describes it,
   **Then** it explicitly states "zero `src/retail` change, zero new CLI verb,
   zero new governance rule" if that is true -- the factory's output MUST NOT be
   silently read as a runtime-capability claim.

---

### Edge Cases

- What happens when a candidate domain turns out to need a genuinely new RC
  default or a new governance rule to model correctly (e.g. a domain with
  multi-currency amounts)? -> Out of scope for the example itself: the example
  is deferred or scoped down to what the *existing* RC defaults and rule set can
  express; proposing a new default/rule is a separate spec, never bundled into
  a worked-example PR (keeps "maturity" and "capability" changes in separate,
  separately-reviewable changes).
- What happens when no live database is reachable to run `retail validate` /
  populate `reconciliation-report.md` for the new example? -> The example stops
  at the repo-only completeness tier (Silver/Gold artifacts authored and
  `retail check`-clean; the live-gated stages marked `blocked` or
  `[PENDING LIVE PROFILE]` in `readiness-status.yaml`, never a fabricated
  `pass`).
- What happens when a candidate domain is structurally *identical* to
  retail_store_sales on every axis (same grain shape, no PII, no returns, no
  rollups)? -> It fails domain selection (research.md criteria): a second
  example that varies no axis proves nothing new and should not be started;
  pick a domain that stresses a different axis instead.
- What happens when an author is tempted to reuse retail_store_sales' actual
  approval records (dates, owner names) as a template shortcut? -> Forbidden.
  Every approval seam in a new example starts empty; only a named human can
  fill `approvals[]` for that example, never copied or invented (Principle V,
  and Non-Goal below).
- What happens when someone asks the factory to reconstruct or reference the
  archived C086 client example as a starting point? -> Refused. C086 was
  archived out specifically to keep the shipped example set generic
  (RELEASE_NOTES v0.1.0); the factory's guidance and templates MUST NOT cite or
  resurrect it, per Constitution Principle VII and this feature's explicit
  non-goal.
- What happens when a "complete" example later needs a correction (an approval
  retraction, like retail_store_sales' Sec 7)? -> Not a factory failure: the
  completeness contract's Publish Ready tier explicitly allows `warning` with a
  recorded reason as an honest terminal state, mirroring the precedent already
  shipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST document a repeatable, generic **process**
  (a sequence of steps referencing existing artifacts/gates) for producing a new
  worked example, usable for any future domain (inventory, customer loyalty, or
  otherwise) without per-domain special-casing baked into the process itself.
- **FR-002**: The feature MUST document **domain-selection guidance**: what
  makes a candidate domain a good addition (which genericity axis it stresses:
  grain shape, PII presence/absence, returns presence/absence, language,
  business-rollup need, file-vs-DB source, etc.), so a second example is chosen
  to prove breadth, not to duplicate the first.
- **FR-003**: The feature MUST define an explicit, checkable **acceptance-
  criteria contract** for "this worked example is complete," derived from and
  calibrated against the artifact set the existing `retail_store_sales` example
  already produced (the five mapping-gate artifacts, silver+gold migrations,
  metric contracts, governed TMDL model, dashboard design, handoff pack,
  readiness-status.yaml, and a narrative doc under `docs/worked-examples/`).
- **FR-004**: The completeness contract MUST define **two tiers**: a
  repo-only-achievable tier (artifacts authored and internally consistent,
  `retail check` exit 0, live-gated stages honestly marked pending) and a
  human/live-gated tier (named-human approvals recorded in `approvals[]`, a live
  `retail validate` run) -- and MUST state that the factory process can only ever
  produce the first tier; the second tier is always a separate, later, human
  and/or live-DB-dependent action.
- **FR-005**: The feature MUST state explicitly, in a load-bearing way (not a
  footnote), that a worked example maturing (e.g. the kit's maturity ladder
  moving from L1 "one worked example" to L2 "two worked examples", per
  `templates/maturity-report.md`) **is not** and **must never be reported as** a
  runtime capability gain -- no implied new `src/retail` behavior, CLI verb, or
  governance rule.
- **FR-006**: The feature MUST prohibit, as a hard constraint on the process
  itself, any invented/fabricated metric value, KPI contract, expected value, or
  approval record. Every numeric or approval artifact the process produces for a
  new example MUST either (a) be a structural placeholder pending real data, or
  (b) cite the specific evidence it derives from, exactly as
  `templates/metric-contract.yaml`, `templates/readiness-status.yaml`, and
  Constitution Principle V already require.
- **FR-007**: The feature MUST prohibit any client-specific fact (billing codes,
  segment rollups, insurance/other PII columns, or any other C086-sourced
  specific) from appearing in the process guidance, templates, or examples this
  feature produces (Constitution Principle VII). It MUST NOT reference C086's
  archived artifacts as a source to copy from.
- **FR-008**: The feature MUST identify the exact artifact set a "complete"
  worked example comprises (a data-model inventory), citing the existing
  templates in `templates/` verbatim rather than re-specifying their shape.
- **FR-009**: The feature MUST provide a quickstart usable by a future author
  (human or agent) to start a new worked example: which template to fill first,
  which gate must clear before the next artifact, and where the process
  legitimately stops absent a live DB or a named human reviewer.
- **FR-010**: The feature MUST state its relationship to the sibling
  `083-demo-harness` feature explicitly: the demo harness **runs** an existing,
  already-complete worked example (execution surface); this factory **defines
  how a worked example is produced** (authoring-process surface). Neither
  subsumes the other; a factory-produced example is what a demo harness would
  later run.
- **FR-011**: The feature MUST NOT itself author, scaffold, or partially fill any
  concrete new worked example (no inventory or loyalty artifacts, no draft
  `mappings/<new-table>/` directory, no draft narrative doc). It defines the
  recipe and the bar, not an instance.
- **FR-012**: The feature MUST state that proposing a new RC default or a new
  `retail check` governance rule is out of scope for any worked example built
  under this process; a domain that requires one is either deferred or narrowed
  to what already-shipped defaults/rules can express, and any new
  default/rule is its own, separately reviewed spec.

### Key Entities *(include if feature involves data)*

- **Worked-example candidate domain**: a proposed subject-matter area (e.g.
  inventory, customer loyalty) not yet built; characterized by which genericity
  axis it stresses relative to `retail_store_sales`, and whether it is
  expressible with already-shipped RC defaults and governance rules.
- **Worked-example artifact set**: the concrete files a complete example
  comprises -- the five mapping-gate artifacts (`source-profile.md`,
  `source-map.yaml`, `assumptions.md`, `unresolved-questions.md`,
  `reconciliation-report.md`) under `mappings/<table>/`, the silver+gold
  migrations, `metrics/*.yaml` contracts, the governed PBIP/TMDL model, the
  `design/` set (layout, visual list, binding map), the `handoff/` pack,
  `readiness-status.yaml`, and a narrative doc under `docs/worked-examples/`.
- **Completeness tier**: one of `repo-only` (artifacts authored,
  internally consistent, `retail check` clean, live legs pending) or
  `human/live-gated` (named-human approvals recorded, live `retail validate`
  run) -- a classification of how far a given example has progressed, never a
  numeric score.
- **Maturity rung**: one of the seven evidence-gated milestones (L0-L6) in
  `templates/maturity-report.md`; a worked example's completion is evidence for
  the L1/L2/L3 rungs specifically (worked-example count; silver/gold
  repeatability), never a rung on its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A future author, given only this spec's `quickstart.md` and the
  cited existing templates, can name a candidate domain, state which genericity
  axis it stresses, and identify the first artifact to fill -- without reading
  `retail-store-sales.md` as a copy source and without inventing a new artifact
  type.
- **SC-002**: Applying the acceptance-criteria contract
  (`contracts/worked-example-completeness.md`) to the existing
  `retail_store_sales` example set yields "complete" (repo-only tier fully met;
  human/live-gated tier met per its own recorded evidence) -- proving the
  contract is calibrated to, not stricter or looser than, the one trusted
  instance.
- **SC-003**: No file produced by this feature contains a fabricated metric
  value, expected value, or approval record; every numeric/approval placeholder
  is either an explicit `<placeholder>` or cites real, already-committed
  evidence.
- **SC-004**: No file produced by this feature references C086, its billing
  codes, its segment rollups, or any of its archived artifacts.
- **SC-005**: The spec, plan, and tasks documents contain an explicit,
  unambiguous statement (not implied) that this feature changes no file under
  `src/`, adds no `retail check` rule, and adds no CLI verb -- confirmed by the
  end-of-chain validation showing zero SUBSTANTIVE diffs outside
  `specs/084-worked-example-factory/`. (The sole permitted exception is the
  spec-kit bookkeeping pointer `.specify/feature.json`, which `/speckit.specify`
  repoints to the active feature dir; it is a tooling pointer, not a runtime or
  content artifact, and is never committed as part of this feature's product.)
- **SC-006**: The completeness contract explicitly names the four
  always-required human-approval seams (`mapping_ready`, `semantic_model_ready`,
  `dashboard_ready`, `publish_ready`) -- plus a fifth, conditional
  `source_ready` seam that applies only to a file (csv/excel) source, per
  `templates/readiness-status.yaml`'s own conditional comment -- as seams the
  factory process leaves empty, never fills.

## Non-Goals (explicit)

- Building, scaffolding, or partially drafting a second worked example
  (inventory, loyalty, or any other domain). This feature defines the recipe
  only.
- Resurrecting, citing, or copying any C086 artifact, code, or figure.
- Proposing, adding, or modifying any `retail check` / `retail validate` rule,
  any RC cleaning default, or any CLI verb.
- Granting, simulating, or pre-filling any named-human approval
  (`approvals[]` entry) for a future example.
- Fabricating a metric value, an "expected_value" for `retail value-check`, or
  any live-validation result.
- Defining a numeric maturity score (the maturity ladder is binary
  achieved/not-achieved per rung, per `templates/maturity-report.md`; this
  feature does not change that model).
- Running `retail check`, `retail validate`, or any DB connection as part of
  this spec's own production (research/validation commentary may reference what
  a future author would run, but this spec work does not run them against a
  real target).
- Superseding or duplicating `083-demo-harness`; see FR-010.

## Evidence Requirements

- Every claim this feature's plan/tasks make about "what retail_store_sales
  did" MUST cite `docs/worked-examples/retail-store-sales.md` or the specific
  `mappings/retail_store_sales/*` file, never restated from memory.
- Every claim about the maturity ladder's rung definitions MUST cite
  `templates/maturity-report.md` verbatim (rung table), never a re-derived
  rung set.
- Every claim about the readiness spine MUST cite `docs/readiness/readiness-
  model.md` or `docs/readiness/readiness-pipeline.md`.
- The final validation step (analyze/report) MUST record exact command output
  (or exact skip reason) for any check attempted -- never a claimed result that
  was not observed.

## Human-Approval Boundaries

- This spec, plan, tasks, and analyze chain requires no human approval to
  produce (it is documentation defining a process).
- Any future *use* of this factory to build a real second worked example will
  require, at minimum, the same four always-required named-human approval seams
  (`mapping_ready`, `semantic_model_ready`, `dashboard_ready`, `publish_ready`)
  that `retail_store_sales` required -- plus a fifth, conditional `source_ready`
  approval that applies only when the source is a file (csv/excel), per
  `templates/readiness-status.yaml` -- and this feature does not reduce,
  automate, or pre-clear any of them.
- This feature itself introduces no new approval seam and no new gate; it
  documents the existing ones as they apply to a not-yet-built second example.

## Safety Constraints

- No SUBSTANTIVE file outside `specs/084-worked-example-factory/` may be created
  or modified by this feature's production. The sole permitted exception is the
  spec-kit bookkeeping pointer `.specify/feature.json` (repointed to the active
  feature dir by `/speckit.specify`) -- a tooling pointer, not a runtime or
  content artifact; it is not part of this feature's committed product.
- No `src/**` change. No new/changed rule ID. No CI change. No new dependency.
- No commit, push, PR, or merge performed as part of producing this spec chain.
- No live DB connection, no `retail check` / `retail validate` execution
  against a real target, performed as part of producing this spec chain (a
  read-only, no-mutation `retail check --repo .` dry validation run at the end
  is permitted per the task's validation instructions and is reported with its
  exact exit code).

## Stop Conditions

- If, during plan/tasks authoring, a candidate domain example would require a
  new RC default or governance rule to be expressible at all, STOP describing
  that domain as a valid candidate in this spec's research and instead record it
  as an explicitly out-of-scope example class (see FR-012); do not silently
  design around it by inventing an ad hoc rule.
- If asked (by inference from the task or otherwise) to actually scaffold a
  second worked example's files, STOP -- that is implementation, forbidden by
  the Non-Goals and the task's absolute boundaries.
- If any acceptance-criteria item cannot be traced to an existing template,
  the readiness model, or the retail_store_sales precedent, STOP and record it
  as an Assumption or a `[NEEDS CLARIFICATION]` rather than inventing a new
  unbacked requirement.

## Assumptions

- **A-001**: The completeness bar for a "complete" worked example is the
  artifact set `retail_store_sales` actually produced (see Key Entities), taken
  as the calibration instance -- not a stricter or looser bar invented for this
  feature. Rationale: it is the only precedent the repo has validated end to
  end; inventing a different bar without a second data point would be
  arbitrary.
- **A-002**: "Generic" candidate domains suitable for illustration in this
  feature's `research.md` are limited to widely-recognized, structurally
  distinct retail-adjacent domains (e.g. inventory stock levels, customer
  loyalty/points) named only as *illustrative*, never drafted -- consistent with
  the task's explicit examples.
- **A-003**: A worked example may legitimately stop at the repo-only
  completeness tier (no live DB) and still be considered "complete for the
  static/documentation phase" as long as every live-gated stage is honestly
  marked pending/blocked rather than skipped or faked -- mirroring the kit's
  existing graceful-deferred-mode posture (AGENTS.md "Live DB steps").
- **A-004**: This feature's own production (the 4-step spec chain) does not
  require a live DB or any human approval to complete, since it produces no
  runtime artifact and grants no approval itself.
- **A-005**: The sibling `083-demo-harness` spec directory does not yet exist
  on this branch at the time of writing; this spec references it by name and
  role only (per the task's briefing), not by reading its (not-yet-created)
  spec.md.

## [NEEDS CLARIFICATION] (scope-changing unknowns only, max 3)

None. Every judgment call encountered (completeness bar, candidate-domain
scope, repo-only-vs-live tiering) has a direct precedent in already-shipped
artifacts (`retail_store_sales`, `templates/maturity-report.md`, AGENTS.md's
deferred-mode posture) and is recorded as an Assumption above rather than a
clarification question.
