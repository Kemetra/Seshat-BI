# Feature Specification: Tower BI Agent Kit -- Foundation (Phase 0/1)

**Feature Branch**: `001-retail-bi-agent-kit`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Ratify the already-shipped retail medallion + governance work as a named, agent-first product (the Tower BI Agent Kit) by writing its Phase 0/1 foundation -- an architecture doc, a constitution, and five generic mapping-gate templates -- and introduce one new load-bearing rule: a source must be profiled and mapped into committed, reviewed artifacts before any silver SQL is written."

## User Scenarios & Testing *(mandatory)*

<!--
  Stories are scoped to the DOCS/TEMPLATES-ONLY foundation slice. Each story is
  independently testable by REVIEWING the committed foundation files -- not by running
  an agent, a validator, or a database. Agent orchestration and validator runtimes are
  explicitly out of scope for this slice (see Requirements / Out of Scope).
-->

### User Story 1 - Source mapped and reviewed before any silver SQL exists (Priority: P1)

An analyst (or an agent acting on their behalf) is handed a raw retail source table and
asked to bring it into Power BI. Before writing any `silver.*` transformation SQL, they
must first profile the source and record its mapping -- grain, primary key, column
keep/drop/rename/type, PII handling, and gold star placement -- into committed,
reviewable artifacts, and that mapping must clear a review gate. The foundation defines
this gate as a hard rule and supplies the generic templates that hold the mapping.

**Why this priority**: This is the one new load-bearing idea the kit adds on top of
already-shipped work. Writing silver SQL first bakes ungoverned grain, type, and PII
decisions into a table whose gold FKs and published BI model then depend on it --
effectively irreversible once cached. The gate makes the load-bearing decisions
committed-and-reviewed *as data* before any schema is cut. Without it, the rest of the
kit has nothing to enforce against.

**Independent Test**: A reviewer can confirm, by reading only the committed foundation
files, that: (a) the architecture doc defines the source-mapping gate and reconciles it
with the medallion playbook's Phase 1 + Phase 2.0-2.5 + Phase 4 review gate; (b) the
constitution ratifies mapping-before-silver as a non-negotiable principle; (c) the five
generic templates that hold the mapping exist and contain no domain-specific schema; and
(d) this spec mandates the gate as a functional requirement. No code, agent, or DB run is
required.

**Acceptance Scenarios**:

1. **Given** the foundation file set, **When** a reviewer reads the architecture doc,
   **Then** the source-mapping gate is stated as "before any `silver.*` SQL is written,
   the source must be profiled and mapped into committed artifacts, and that mapping must
   be reviewed," and is explicitly framed as formalizing existing playbook phases, not a
   second method.
2. **Given** a filled `source-map.yaml` for a new table, **When** that map has not yet
   cleared the review gate, **Then** writing `silver.*` SQL for that table is, by the
   ratified rule, out of order -- the rule exists and is documented in this slice; the
   automated enforcement wiring (pre-commit hook / CI) is a later slice.
3. **Given** the templates directory, **When** a reviewer opens any of the five
   templates, **Then** each maps 1:1 to the mapping-gate artifacts named in the
   architecture doc and contains placeholders only -- no pharmacy or other domain
   specifics.

---

### User Story 2 - Decisions traceable: defaults adopted vs deviations recorded (Priority: P2)

When a table is mapped, most cleaning and modeling decisions should follow the
already-ratified retail cleaning defaults. The analyst/agent needs a place to record,
per table, which defaults were adopted as-is and which were deviated from -- with the
triggering data fact for each deviation -- plus the open questions that block the build
and that the agent cannot decide alone. A reviewer should be able to see only what
changed and what is still open, without re-reading every default.

**Why this priority**: Traceability of decisions makes the review gate (P1) cheap to
operate and makes a deviation auditable later. It depends on the gate existing but
delivers standalone value: even before any build runs, the assumptions and
unresolved-questions templates let a table's decisions be reviewed as a diff against the
ratified defaults rather than from scratch.

**Independent Test**: A reviewer can confirm, by reading only the committed files, that
the `assumptions.md` template captures "default adopted as-is" vs "deviation + triggering
data fact" referencing the existing cleaning-defaults ADR by path (not restating its
content), and that the `unresolved-questions.md` template captures blocking decision
points and feeds the review gate. No build is run.

**Acceptance Scenarios**:

1. **Given** the `assumptions.md` template, **When** a reviewer reads it, **Then** it
   distinguishes adopted defaults from deviations and requires a triggering data fact for
   each deviation, and references the cleaning-defaults ADR by file path rather than
   copying its rulings.
2. **Given** the `unresolved-questions.md` template, **When** a reviewer reads it,
   **Then** it provides a structure for open, build-blocking questions that the review
   gate must resolve, including the foundation-level open decisions carried from the
   architecture doc.
3. **Given** the `unresolved-questions.md` template, **When** a reviewer reads it,
   **Then** it enumerates the agent's stop-and-ask decision classes (business-rollup
   mappings, PII publish-safety, grain ambiguity, sentinel-vs-null, and any
   build-blocking question), each with a "who must answer" authority column
   (analyst / governance / data-owner), and marks the build blocked until each is
   answered -- so the agent cannot decide these alone.

---

### User Story 3 - Build is acceptance-checked against a reconciliation report (Priority: P3)

When silver and gold are eventually built for a table, the build must be acceptance-checked
against a reconciliation report: PK uniqueness on materialized rows, date-dimension
coverage, zero orphan foreign keys, and penny-exact measure reconciliation across layers.
The foundation supplies a generic reconciliation-report template (the blank a live run
fills) and documents the LIVE-validator *categories* that will eventually check it --
without implementing any validator.

**Why this priority**: This is the acceptance contract for a finished table, but it is
the last gate chronologically and depends on the prior stories. In this docs-only slice it
delivers value as a ratified template plus a documented category list, giving every future
table a known acceptance shape. The validator runtime itself is deferred.

**Independent Test**: A reviewer can confirm, by reading only the committed files, that
the `reconciliation-report.md` template exists with blanks for PK uniqueness, date-dim
coverage, orphan-FK count, and cross-layer measure reconciliation; that the LIVE-validator
categories are documented (not coded); and that the worked example is cited as the filled
instance. No validator and no DB are run.

**Acceptance Scenarios**:

1. **Given** the `reconciliation-report.md` template, **When** a reviewer reads it,
   **Then** it contains blanks for PK uniqueness, date-dim coverage, orphan-FK count, and
   penny-exact cross-layer measure reconciliation, with no domain-specific measures
   pre-filled.
2. **Given** the architecture doc and this spec, **When** a reviewer looks for validator
   behavior, **Then** only validator *categories* (static vs live) are documented and no
   validator logic exists in this slice -- the `retail validate` live surface is marked as
   a later spec.
3. **Given** the worked example for C086 (El Ezaby pharmacy), **When** a reviewer wants a
   filled reconciliation instance, **Then** it is cited as the first end-to-end pass
   (16/16 ADR-default PASS across 246,916 silver rows) and is referenced as an example,
   never copied into the generic template.

---

### Edge Cases

- What happens when a new table's mapping is partially filled (profile done, map missing)?
  The gate is not satisfied; the rule treats an incomplete or unreviewed map as blocking
  for silver. This slice documents the rule; it does not enforce it programmatically.
- How does the foundation handle a table whose decisions all match the defaults? The
  `assumptions.md` template still records "defaults adopted as-is" so the review gate has
  an explicit, auditable record rather than silence.
- What happens when a default must be deviated from? The deviation is recorded with its
  triggering data fact in `assumptions.md`; an unanswerable trade-off becomes an entry in
  `unresolved-questions.md` for the review gate.
- How does a reviewer tell a generic template from a filled instance? Templates carry
  placeholders only and live in `templates/`; filled instances (e.g. C086) live in
  `docs/worked-examples/` and are cited, never merged back into the templates.
- What happens to the two conflicting `D` numbering schemes? The cleaning-defaults ADR
  numbers defaults `D1-D16`; the governance checker numbers TMDL/DAX rules `D1-D8`. The
  collision is flagged wherever it is relevant and is left unresolved by design in this
  slice (see clarifications below).

## Requirements *(mandatory)*

<!--
  Requirements RATIFY and REFERENCE already-shipped, authoritative work; they do not
  re-decide it. Settled North-Star constraints are stated as MUSTs, not open questions.
  Genuinely-open items carry [NEEDS CLARIFICATION].
-->

### Functional Requirements

- **FR-001**: The foundation MUST define a mandatory **source-mapping gate**: before any
  `silver.*` SQL is written for a table, that table's source MUST be profiled and mapped
  into committed artifacts, and that mapping MUST clear a review gate. This gate MUST be
  presented as formalizing the medallion playbook's existing Phase 1 (connect & profile) +
  Phase 2.0-2.5 (grain-first cleaning decisions) + Phase 4 (review gate) into committed
  reviewable artifacts -- not as a new or competing method.
- **FR-002**: The foundation MUST supply five **generic** mapping-gate templates --
  `templates/source-profile.md`, `templates/source-map.yaml`, `templates/assumptions.md`,
  `templates/unresolved-questions.md`, `templates/reconciliation-report.md` -- each
  containing placeholders only. Templates MUST NOT bake in any domain-specific schema,
  codes, segments, or PII (e.g. no pharmacy billing codes, segment rollups, or insurance
  fields).
- **FR-003**: The foundation MUST cite C086 (El Ezaby pharmacy sales) as the **first
  worked example** -- a filled instance of the templates and the medallion method -- and
  MUST treat it as an example only, never as the universal schema. Domain specifics MUST
  remain in C086's own artifacts under `docs/worked-examples/`.
- **FR-004**: The foundation MUST treat the existing governance core (`retail check`,
  the 23 static rules in `src/retail/`) as the authoritative enforced gate and MUST
  **reference it, not reimplement or re-decide it**. No governance rule may be restated,
  renamed, or forked into a second source of truth by this slice.
- **FR-005**: The foundation MUST document validator **categories only** (static vs live)
  and MUST NOT implement any validator logic in this slice. The static surface MUST be
  identified with the already-shipped `retail check`; the live surface MUST be named as the
  deferred `retail validate` with its categories (PK uniqueness on materialized rows,
  date-dim coverage, zero orphan FKs, penny-exact cross-layer measure reconciliation).
- **FR-006**: The foundation MUST place `pbi-cli` as a **later, pluggable Power BI
  semantic-model engine adapter at the bottom of the stack** -- not the core -- consistent
  with the governance design's settled decision to depend on `pbi-cli` (via `pipx`) and not
  fork it. This slice MUST NOT wire any `pbi-cli` integration.
- **FR-007**: The foundation MUST honor **gold-only** as a settled constraint: Power BI
  reads the `gold` schema only, consistent with the governance design's settled decision.
  The medallion substrate MUST be presented as Postgres-first (`bronze` -> `silver` ->
  `gold`); this slice MUST NOT introduce a DuckDB/Parquet-first storage ADR.
- **FR-008**: The foundation MUST require that secrets live only in `.env` (git-ignored)
  and that Power BI connects via parameters, not baked-in connection strings -- ratifying
  the existing repo rule, not inventing a new one.
- **FR-009**: The foundation MUST be **agent-first**: the agent experience is the primary
  surface that drives the playbook and authors against the gate, with `retail check` as the
  gate the agent calls (not a product the user operates by terminal). The runtime shape of
  that agent is not specified in this slice.
- **FR-010**: The foundation MUST present itself as a **ratification layer** over
  already-shipped work: the architecture doc, constitution, this spec, and the five
  templates MUST cross-link to each other and to the existing authoritative docs (medallion
  playbook, cleaning-defaults ADR, governance design spec, worked example) so a reviewer can
  read all eight foundation files as one coherent set.
- **FR-011**: The five templates MUST map 1:1 to the playbook phases they formalize:
  `source-profile.md` = Phase 1; `source-map.yaml` = Phase 2.0-2.5 / 2.7-2.8;
  `assumptions.md` = Phase 2 + Phase 3; `unresolved-questions.md` = Phase 2 decision points +
  Phase 4 review gate; `reconciliation-report.md` = Phase 5/6 validation gates.
- **FR-012**: The foundation MUST flag, and MUST NOT resolve or rename, the `D`-namespace
  collision: the cleaning-defaults ADR numbers cleaning/modeling defaults `D1-D16`, while
  the governance checker numbers TMDL/DAX rules `D1-D8`. [NEEDS CLARIFICATION: the two
  `D` namespaces must be disambiguated before any ADR default is wired into `retail check`;
  disambiguation is a named later slice, intentionally unresolved here.]
- **FR-013**: The foundation MUST keep the **per-table location of mapping artifacts** open.
  [NEEDS CLARIFICATION: where committed mapping artifacts live per table -- a
  `mappings/<table>/` directory vs alongside the silver migration vs under `docs/` -- is not
  decided in this slice.]
- **FR-014**: The foundation MUST keep the **agent orchestration shape** open.
  [NEEDS CLARIFICATION: which agent/skill drives the playbook (Layer D) and how it
  self-heals against the gate is designed as a seam only; the runtime is a later slice.]
- **FR-015**: The foundation MUST keep the **`retail validate` live-surface specification**
  open. [NEEDS CLARIFICATION: the deferred live-validator categories need their own spec
  before any implementation; not specified in this slice.]
- **FR-016**: The foundation MUST encode an agent **stop-and-ask duty**: the agent MUST NOT
  decide alone -- and MUST record an open question in `unresolved-questions.md` -- for
  business-rollup / segment mappings (analyst-supplied, never invented), PII publish-safety
  (governance sign-off), grain ambiguity, sentinel-vs-null choices, and any build-blocking
  unresolved question. No `silver.*` SQL is written while a build-blocking question is open.
  The `unresolved-questions.md` template MUST enumerate these decision classes and mark the
  build blocked until each is answered by its named owner (analyst / governance / data-owner).
  This is a settled rule (constitution Principle V), not an open item.

### Key Entities *(include if feature involves data)*

These are the five committed mapping-gate artifacts the templates define. Each is a
document/record shape, described without implementation. They map 1:1 to the five
templates (FR-002) and to the playbook phases (FR-011).

- **Source Profile** (`templates/source-profile.md`): A record of a raw source's shape,
  quality, and semantics -- with numbers (row/column counts, missingness measured as
  empty-string-or-null, candidate-key uniqueness, returns population). Formalizes the
  playbook's profiling phase. The blank a profiling run fills.
- **Source Map** (`templates/source-map.yaml`): The machine-readable spine of a table's
  mapping. Captures the grain and primary key decided first, then per-column
  keep/drop/rename/type, the target silver column, and the gold star placement (fact
  measure / dimension attribute / degenerate dimension). The artifact the review gate
  approves before silver is written.
- **Assumptions record** (`templates/assumptions.md`): A per-table ledger of which ratified
  cleaning/modeling defaults were adopted as-is versus deviated from, each deviation paired
  with the triggering data fact -- so review sees only what changed. References the
  cleaning-defaults ADR by path; does not restate it.
- **Unresolved Question** (`templates/unresolved-questions.md`): An open, build-blocking
  decision point that the agent cannot settle alone and that the review gate must resolve.
  Includes the foundation-level open decisions carried from the architecture doc.
- **Reconciliation Report** (`templates/reconciliation-report.md`): The acceptance contract
  for a built table -- blanks for PK uniqueness, date-dimension coverage, orphan-FK count,
  and penny-exact cross-layer measure reconciliation, filled by a live run. C086's report is
  the first filled instance, cited not copied.

## Success Criteria *(mandatory)*

<!--
  Measurable, technology-agnostic outcomes verifiable by reviewing the committed
  foundation files. None require running an agent, validator, or database.
-->

### Measurable Outcomes

- **SC-001**: Every new table brought into the warehouse has a committed source map that is
  reviewed and approved before its first `silver.*` migration is written (the mapping-gate
  rule is stated and ratified in the foundation; measured per-table once the kit is in use).
- **SC-002**: Zero domain-specific tokens appear in `templates/` -- a text scan of the five
  templates finds no pharmacy (or other domain) codes, segment names, or PII field names;
  all such specifics appear only in cited worked examples.
- **SC-003**: The eight foundation files (architecture doc, constitution, this spec, and the
  five templates) cross-link as a set: each links to the others and to the existing
  authoritative docs by file path, and a reviewer can traverse the set without a missing
  reference.
- **SC-004**: The foundation re-decides nothing: a reviewer finds no governance rule,
  cleaning default, or settled design decision restated, renamed, or forked -- every such
  item is referenced by path to its authoritative source.
- **SC-005**: The five templates map 1:1 onto the five mapping-gate artifacts and onto the
  playbook phases they formalize (Phase 1; Phase 2.0-2.5/2.7-2.8; Phase 2+3; Phase 2 decision
  points + Phase 4; Phase 5/6), with no orphan template and no unmapped artifact.
- **SC-006**: Exactly the four named open items carry `[NEEDS CLARIFICATION]` -- the
  `D`-namespace collision, the per-table mapping-artifact location, the agent orchestration
  shape, and the `retail validate` live-surface spec -- and no settled North-Star constraint
  is marked open.

## Assumptions

- This is a **docs-and-templates-only** slice (Phase 0/1 foundation). It produces an
  architecture doc, a constitution, this spec, and five generic templates -- no validator
  scripts, no `pbi-cli` integration, no CLI installer, no warehouse tables, no DB writes,
  and no implementation beyond these artifacts.
- **Spec-Kit is initialized** (constitution v1.1.0 amendment, 2026-06-24): this file lives at
  `specs/001-retail-bi-agent-kit/spec.md` and matches the Spec-Kit spec template shape; the
  constitution lives at `.specify/memory/constitution.md` (hand-authored, preserved unchanged by
  the init). `specify init --here --integration claude --script ps` added `.specify/templates/`,
  `.specify/scripts/powershell/`, and the `speckit-*` agent skills that back the
  spec -> plan -> tasks chain. Presets and custom bundles remain out of scope.
- The **existing governance core is the gate**: `retail check` (23 static rules in
  `src/retail/`) is authoritative and is referenced, not reimplemented. The medallion
  playbook is authoritative on *how to decide*; the templates are authoritative on *what to
  record and in what shape*.
- **C086 is the reference instance**: it is the first table validated end to end (16/16
  ADR-default PASS across 246,916 silver rows) and is cited as a filled example, never as the
  universal schema.
- The **North-Star constraints are settled inputs**, not open questions: agent-first;
  source mapping before silver/gold; `pbi-cli` as a later adapter; Postgres-first medallion
  with no DuckDB/Parquet-first ADR; gold-only for Power BI. Only the four enumerated items
  remain open (SC-006).
- **Constitution-Check tables are intentionally deferred**, not omitted: Spec-Kit normally
  hooks each spec/plan to a per-principle Constitution Check, but that table belongs with a
  `plan.md`, which this Phase 0/1 slice does not produce. It will be added when the first
  implementation plan for a table is written; its absence here is by design.

## See also

- **Architecture:** `docs/architecture/tower-bi-agent-kit.md` -- the map this spec slices.
- **Constitution:** `.specify/memory/constitution.md` -- the non-negotiable principles.
- **Method:** `docs/medallion-playbook.md` -- the 7-phase interactive method this gate
  formalizes.
- **Defaults:** `docs/decisions/0002-retail-cleaning-defaults.md` -- the cleaning/modeling
  defaults (`D1-D16`) the assumptions record diffs against.
- **Governance design:** `docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`
  -- the A->C->D design (depend-not-fork; gold-only).
- **Worked example:** `docs/worked-examples/c086-pharmacy.md` and
  `docs/c086-adr0002-compliance.md` -- the first filled instance.
- **Templates:** `templates/source-profile.md`, `templates/source-map.yaml`,
  `templates/assumptions.md`, `templates/unresolved-questions.md`,
  `templates/reconciliation-report.md`.
