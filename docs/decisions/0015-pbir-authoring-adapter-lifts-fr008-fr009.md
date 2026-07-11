# 0015 -- The PBIR-authoring adapter lifts FR-008/FR-009 (F034 completion)

- **Date:** 2026-07-05
- **Status:** **Accepted -- RATIFIED by Ahmed Shaaban (owner) on 2026-07-05.** This
  ADR records the owner's decision to permit agent-authored PBIR *through one bounded
  companion adapter only*. The adapter itself (skill, contract, runtime) is
  ENUMERATED as future work under spec `106-pbir-authoring-adapter` and ships NO PBIR
  writer in this decision -- this ADR is the terms of entry, not the build.
- **Roadmap feature:** F034 (Visual Implementation MVP) -- its authoring slice
  shipped (PR #43); this ADR authorizes the previously-forbidden execution half.
  Related: F016 (live publish) remains separately parked (see decision 6).
- **Authority category (F024):** Execution / **Authoring** Adapter, `local-file`
  (NOT DB-connected, NOT publish-capable). Declared against
  `docs/architecture/product-modules.md`, the F029/F030 companion-adapter pattern.
- **Context:** spec-001 **FR-008/FR-009 forbid agent-generated PBIR**;
  `dashboard-design/SKILL.md:78` says "STOP before authoring PBIR via automation,"
  and F034's built page was deliberately left as a human Power BI Desktop action.
  The owner's goal (2026-07-05) is a tool that authors report formatting -- the card/
  chart settings a human sets by hand in the Power BI UI (which *are* edits to the
  PBIR JSON on disk). The theme generator (Slice 1, PR #204) supplies the styling;
  the open question this ADR closes: **may an agent write those settings into the
  committed PBIR, and under what boundary?** This ADR records the terms.

## Decision

### 1. FR-008/FR-009 are lifted ONLY for one bounded authoring adapter

Agent-authored PBIR is permitted **exclusively** through the companion adapter
specified in `specs/106-pbir-authoring-adapter/` and bound by its FR-001..FR-011.
The static DEFINE/CHECK core (`src/seshat/` rules, `retail check`) **remains
forbidden** from writing any PBIR/report file. The lift is a narrow carve-out, not
a general permission: outside this adapter, FR-008/FR-009 stand unchanged.

### 2. Formatting-only -- an allow-list, never meaning

> The adapter MUST edit ONLY a declared, guard-tested allow-list of visual/page
> FORMATTING properties (card fill/border/title/font/alignment, data-label and
> gridline defaults, data colors, page-background reference). It MUST NOT write
> data bindings, measures, DAX, relationships, meaning-changing filters, or any
> semantic-model content.

This keeps the adapter a *styler*, not an author of truth. A property not on the
allow-list is not writable; growing the allow-list is a reviewed change, never
silent. Creating a data-bound visual with no backing approved contract (the
surface-1 orphan rule) stays forbidden.

### 3. The evidence-not-approval rule (the governance hinge)

> A successful adapter write is EVIDENCE that formatting was applied; it MUST NOT
> move `dashboard_ready` (or any stage) to `pass` and MUST NOT emit a numeric
> confidence/health/maturity score (hard rule #9). The design-review sign-off and
> any readiness `pass` remain the verb owner's recorded human decision.

As with dbt (ADR 0009 decision 3), conflating "the tool did it" with "it is
approved" is how an adapter rots into the brain. The adapter writes formatting; a
named human still approves the dashboard.

### 4. Self-contained -- no external dependency

> The adapter MUST NOT use pbi-cli, the Power BI MCP, a live Power BI/workspace
> connection, or any network call. It operates on local committed files only,
> dependency-light (JSON is stdlib).

This is the owner's explicit "the tool complete in itself" constraint. pbi-cli is
installed on the build machine but is NOT the path; the adapter reads and writes the
PBIR JSON directly.

### 5. Deterministic, validated, reversible

> Every write MUST be deterministic (byte-identical on re-run), produce a reviewable
> git diff, validate the result (valid JSON + round-trip stable + R1 model-reference
> integrity green + a new `retail check` authoring-lint), and be all-or-nothing per
> report (stage -> validate -> commit or roll back). Path inputs are traversal-
> guarded; no overwrite without explicit intent.

A file-writing adapter that can corrupt a report is worse than none; safety is co-
primary with the capability (spec-106 US3).

### 6. Authoring, NOT publishing -- it stops at the committed PBIR

The adapter writes the committed PBIR files on disk and stops. Publishing/refreshing
a live Power BI workspace is the parked **F016** execution adapter, gated separately
on Semantic Model Ready. This adapter and F016 are different categories and never
overlap (Principle III).

### 7. Consumes the generated theme; backgrounds are surface-2 references

The adapter's formatting source of truth is a `retail theme-gen` (Slice 1) output;
it invents no colors/fonts outside the supplied theme. It may set a page background
to a committed surface-2 asset (per `background-spec.yaml`), honoring the surface-2
purity rule; it does NOT generate the image itself (that stays external).

### 8. Docs-first; this decision ships NO PBIR writer

Consistent with Principle VIII, this ADR + spec 106 enumerate the future shape; the
adapter skill, contract, allow-list, and authoring-lint are built under spec 106's
plan/tasks AFTER this ratification. No PBIR is written by this decision.

## Consequences

- The kit gains a reviewable, self-contained report-authoring capability: the owner
  can have card/chart formatting applied programmatically, as a git diff, without a
  live Power BI or any external tool.
- The constitutional boundary shifts from **"no agent PBIR, ever"** to **"agent PBIR
  only via this bounded, formatting-only, validated adapter."** The core stays
  forbidden; the carve-out is explicit and gated.
- FR-008/FR-009 in `specs/001-retail-bi-agent-kit/spec.md` are now qualified by this
  ADR: they hold everywhere except this named adapter. (A cross-reference note is
  added to spec 106; spec 001's text is not rewritten -- the ADR is the amendment
  record, per the repo's append-only ADR convention.)
- No `retail check` rule is weakened; a NEW authoring-lint is ADDED (spec-106 FR-007)
  to police the written PBIR (allow-list-only) -- the gate gets stronger, not weaker.
- No maturity/confidence score is introduced (hard rule #9). "Great professional
  dashboards" remains a separate design-intelligence concern, explicitly NOT claimed
  by this mechanism.

## Alternatives considered

- **Keep FR-008/FR-009 absolute; leave PBIR a human-only action.** Rejected by the
  owner: it blocks the stated goal and the capability is self-contained and gated.
- **Use pbi-cli / the Power BI MCP to author PBIR.** Rejected: the owner requires the
  tool be complete in itself, with no external dependency (decision 4).
- **Let the core (`retail check`) write PBIR.** Rejected: execution stays in a
  companion adapter, never the DEFINE/CHECK core (decision 1, F024 pattern).
- **Let a successful write advance `dashboard_ready`.** Rejected: evidence is not
  approval (decision 3); a named human still signs off.
- **Author meaning (bindings/measures), not just formatting.** Rejected: the adapter
  is a styler bound to an allow-list (decision 2); meaning stays with its owning
  feature (contracts F009, model F010).

## See also

- The spec / plan / tasks: `specs/106-pbir-authoring-adapter/{spec,plan,tasks}.md`.
- The rule this qualifies: `specs/001-retail-bi-agent-kit/spec.md` FR-008/FR-009.
- The companion-adapter precedents: ADR 0009 (dbt), ADR 0010 (Dagster);
  `docs/architecture/product-modules.md`.
- The styling source this adapter consumes: the `retail theme-gen` verb
  (`src/seshat/theme_gen.py`) + `themes/` (Slice 1, PR #204).
- The parked publish adapter (separate, never overlapping): F016.
- `.specify/memory/constitution.md` (Principles III, IV, V, VIII, IX; hard rule #9).
