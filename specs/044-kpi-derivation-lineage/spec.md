# Feature Specification: KPI Derivation-Lineage Contract (base-vs-derived dependency graph)

**Feature**: none (no roadmap F-number -- this idea is an ADOPT item from the exploratory
idea-bank `docs/roadmap/idea-backlog.md`, which is "not a roadmap and not a commitment";
promotion + F-numbering is a human decision. Content-family lineage is the F009 Metric Contract
Store / Retail KPI Knowledge pack, but F009 is SHIPPED and shipped WITHOUT any `derives_from`
field or lineage doc, so this work is NOT tagged F009 -- doing so would falsely assert it
re-opens/advances F009. The grounder confirmed no shipped feature encodes a derives_from
dependency graph: F8 scores per-table presence, F7 routes per-domain questions.) | **Spec
directory**: `044-kpi-derivation-lineage` (next free on-disk slot; the create-new-feature script
numbered from current max `043`)

**Feature Branch**: `044-kpi-derivation-lineage` (located via `.specify/feature.json`)

**Created**: 2026-06-29

**Status**: Ratified (Ahmed Shaaban, 2026-06-29)

**Input**: User description: "KPI Derivation-Lineage Contract (base-vs-derived dependency graph)"

**Readiness stage advanced**: none. This is DEFINE-layer / reasoning-layer KPI knowledge content
(layer-5). Authoring a `Derives from` body section and a lineage reference doc grants NO readiness
stage in the 7-stage spine -- it has no per-table F-row, it reads only committed contract text, and
it computes/executes nothing. It MUST NOT self-grant any readiness or dashboard-readiness
(Principle I). It advances no stage; it adds a navigation/reasoning seam over existing contracts.

## Clarifications

This block records the load-bearing ambiguities. The grounding seed listed four `open_for_human`
questions. THREE of them are answerable design/convention calls (reversible) -- the readiness
stage, the representation of the field, and hand-authored-vs-generated. They are NOT Principle-V
carve-outs (grain / PII / rollup / identity), so the advisor resolved them in clarification and
they are integrated below under the dated session. The FOURTH grounding question -- whether edges
may be transcribed from existing contract prose or must be human-ratified per edge -- is the one
Principle-V-adjacent line; it is resolved CONSERVATIVELY (transcribe-with-citation only; invent
nothing) and the genuine reserved part (declaring a NEW derivation relationship not already stated
in committed prose) is carried as a stop-and-ask marker the agent must not cross.

### Owner judgment calls (Principle V -- carried as stop-and-ask markers, NOT answered here)

- **[Principle V -- declaring a NEW derivation relationship]** An edge that is NOT already stated
  in committed contract prose (a derivation a human believes true but no contract yet records) is a
  human-declared fact reserved for the metric owner. The authoring agent MUST NOT invent such an
  edge into the template, a contract, or the lineage doc. The agent transcribes only edges already
  present in committed prose, each citing its source line; anything beyond that is a stop-and-ask.
  This is the Principle-V boundary the duplication/eligibility lenses verified ("edges are
  human-declared facts ... not fabricated").

### Owner ruling (Ahmed Shaaban, 2026-06-29)

- **RESOLVED -- Principle-V boundary affirmed.** The metric owner rules that the authoring agent
  transcribes ONLY edges already stated in committed contract prose, each citing its source line,
  and invents NO new derivation edge into the template, a contract, or the lineage doc. Declaring a
  derivation relationship not already recorded in committed prose remains reserved for the metric
  owner and is out of scope for implementation.
- **ACCEPTED -- Net Sales (KPI-MC-02) concept-match edges.** The owner accepts the flagged nuance:
  the Net Sales -> KPI-MC-01 (Gross Sales) and -> KPI-MC-06 (Discount Amount) edges rest on a
  concept/name match inside Net Sales's verbatim formula "Gross Sales - total discount", rather
  than an explicit cross-reference like ATV's "from Net Sales contract". Both are sound
  transcriptions from committed prose; the concept-match is approved as a real edge.
- **RESOLVED -- Net Sales (KPI-MC-02) is DERIVED, not base (supersedes T006).** The spec carried an
  internal contradiction: US2/T006 instructed the net-sales contract section to read "none -- base
  KPI", while US1/T010 (and the accepted edges above) list Net Sales as deriving from KPI-MC-01 +
  KPI-MC-06. The metric owner rules Net Sales is DERIVED: its own committed formula "Net Sales =
  Gross Sales - total discount (line + header), pre-tax" is a derivation. The "primary
  realized-revenue base" language in its Interpretation refers to reuse (base FOR downstream KPIs),
  not graph topology -- a node can be both an intermediate (derived from 01, 06) and a parent (base
  for 05, 08, 09, 10). T006 is therefore authored as `**Derives from**: KPI-MC-01, KPI-MC-06`. The
  lineage doc is unchanged (4 base: 01, 03, 04, 06; 6 derived: 02, 05, 07, 08, 09, 10). ATV remains
  the derived exemplar; the base-exemplar role for the section seam is not required by any FR.

### Session 2026-06-29

These are the answerable ambiguities (NOT Principle-V carve-outs). Each was resolved by the advisor
against the constitution, the readiness spine, the F009 store boundary, and the id-conventions
precedent, and integrated into the spec below.

- Q: Which readiness stage does authoring a `Derives from` section + lineage doc advance?
  -> A: None. DEFINE/reasoning-layer content; grants no readiness (Principle I). It mirrors the
  F009 store's "DEFINES, does not CHECK" boundary -- it never reads `powerbi/`, never asserts a
  measure, never adds a `retail check` rule. [reversible: easy -- a future human ruling could
  re-scope it; the conservative default commits nothing.]
- Q: What is the canonical representation for the dependency edges -- introduce YAML front-matter to
  the contract template, add a new prose body section, or a separate edges manifest?
  -> A: A new prose body section titled `**Derives from**`, listing edges by stable KPI-MC ID,
  mirroring the existing body sections (e.g. "Required fields"). Contracts today are flat markdown
  with an `ID:` line and NO front-matter; `id-conventions.md` mandates ID cross-references ("never
  the filename"). A body section is the minimal seam that carries the relationship with zero
  restructuring. REJECTED: YAML front-matter (the grounder's "sharpest blocking assumption" --
  restructures all 10+ contracts, over-scope for a first step); a separate edges manifest
  (duplicates the prose -> drift, and only pays off with a generator, which hard-rule #8 / docs-first
  defers). [reversible: easy -- a later spec could promote the section to front-matter or a manifest
  if a generator is ever built.]
- Q: Should the lineage doc be hand-authored or generated from the edges?
  -> A: Hand-authored. Hard-rule #8 (docs/templates first, automate later) and YAGNI: no generator
  exists; building one before the artifact has proven useful is premature and would add an executor
  this DEFINE-layer idea must not have. [reversible: easy -- a generator can replace hand-authoring
  later without changing the doc's shape.]
- Q: Does the spec scope all 10 contracts or only the 2 named exemplars (net-sales, ATV)?
  -> A: The `Derives from` SECTION SEAM is added to the template + the two exemplar contracts
  (KPI-MC-02 Net Sales, KPI-MC-05 ATV) only -- so the seam is demonstrated, not bulk-applied. The
  rendered lineage DOC expresses the full graph across all 10 existing contracts (every edge
  transcribed from committed prose). This matches the grounder's realist first-step scope: add the
  seam on two contracts, render the whole readable graph once. [reversible: easy -- adding the
  section to the other 8 contracts is a later mechanical follow-up.]
- Q: Which edges are real, given net-sales prose names targets like "growth, sales per sqm,
  vs-target" that are NOT existing contracts?
  -> A: Edges connect ONLY the 10 existing KPI-MC nodes. "Base for growth, ... sales per sqm, and
  vs-target" names downstream USES that have no contract; the lineage doc MUST NOT draw an edge to a
  non-existent node. Likewise COGS and Return Value are FIELDS, not contracts -- they are not nodes.
  [reversible: easy -- if a future contract is added for one of these, an edge can be added then.]

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader can see the base-vs-derived dependency graph in one place (Priority: P1)

A KPI analyst or semantic-model author wants to know which KPIs are BASE (computed directly from
fact fields) and which are DERIVED (computed from other KPIs), and exactly which base each derived
KPI depends on. Today this is implicit in scattered prose ("Base for growth, margin, ATV ..." in
Net Sales; "Net Sales / Transactions Count" in ATV). After this work, a single hand-authored
`references/kpi-derivation-lineage.md` expresses the whole graph across the 10 existing contracts,
with every edge transcribed from committed contract prose and citing its source, so a reader sees
that one Net Sales ruling (e.g. the pre-tax VAT decision) propagates to ATV, Gross Margin, Gross
Margin %, and Returns Rate %.

**Why this priority**: This is the core deliverable -- the readable lineage graph. Without it the
dependency structure stays implicit and a change to a base KPI's definition has no visible blast
radius.

**Independent Test**: Open `references/kpi-derivation-lineage.md`; confirm every node is one of the
10 existing KPI-MC contracts; confirm every derived->base edge cites the committed contract prose it
was transcribed from; confirm no edge points to a non-contract (growth, sales per sqm, vs-target,
COGS, Return Value); confirm base KPIs are listed as base with no outgoing derives-from edge.

**Acceptance Scenarios**:

1. **Given** the retail-kpi-knowledge skill, **When** a reader opens
   `references/kpi-derivation-lineage.md`, **Then** they see the 10 contracts partitioned into base
   and derived, with each derived KPI's `derives_from` edges listed by KPI-MC ID.
2. **Given** the lineage doc, **When** a reader inspects any edge, **Then** the edge cites the
   source contract prose it was transcribed from (e.g. ATV KPI-MC-05 derives_from KPI-MC-02,
   KPI-MC-04, citing "ATV = Net Sales / Transactions Count").
3. **Given** the lineage doc, **When** a reader looks for an edge to "growth", "sales per sqm",
   "vs-target", "COGS", or "Return Value", **Then** there is none -- these are uses or fields, not
   contract nodes.

### User Story 2 - The `Derives from` section seam exists on the template and two exemplar contracts (Priority: P2)

A contract author starting a new derived KPI needs a place in the contract shape to declare what it
derives from. After this work the metric-contract template carries a `**Derives from**` body section
(with placeholder guidance), and two exemplar contracts -- Net Sales (derived from KPI-MC-01 +
KPI-MC-06) and Average Transaction Value (derived from KPI-MC-02 + KPI-MC-04) -- carry a filled
`**Derives from**` section, so the seam is demonstrated on two derived cases (the template's
placeholder still shows the base "none -- base KPI" form, so both forms are documented). [The
Net Sales classification follows the metric-owner ruling in ## Clarifications: Net Sales is
DERIVED per its formula "Gross Sales - total discount", superseding the original T006 "base"
framing.]

**Why this priority**: The template change is the reusable seam; the two exemplars prove it reads
correctly for the derived case (Net Sales: "KPI-MC-01, KPI-MC-06"; ATV: "KPI-MC-02, KPI-MC-04"),
while the template placeholder documents the base "none -- base KPI" form. The other 8 contracts
are a later mechanical follow-up (out of this first-step scope).

**Independent Test**: Diff `references/metric-contract-template.md`; confirm a `**Derives from**`
section was added with generic placeholder text (including the "none -- base KPI" form) and no C086
specifics. Diff `contracts/net-sales.md` and `contracts/average-transaction-value.md`; confirm each
gained a `**Derives from**` section whose content is transcribed from that contract's own committed
prose (Net Sales: KPI-MC-01 + KPI-MC-06; ATV: KPI-MC-02 + KPI-MC-04).

**Acceptance Scenarios**:

1. **Given** the metric-contract template, **When** an author reads it, **Then** it has a
   `**Derives from**` section instructing them to list base-KPI dependencies by KPI-MC ID (or state
   "none -- base KPI"), referencing IDs never filenames.
2. **Given** `contracts/net-sales.md`, **When** a reader reaches the `**Derives from**` section,
   **Then** it lists KPI-MC-01 (Gross Sales) + KPI-MC-06 (Discount Amount) -- transcribed from its
   formula "Net Sales = Gross Sales - total discount" -- and notes Net Sales is in turn the base for
   its downstream KPIs (per the ## Clarifications ruling).
3. **Given** `contracts/average-transaction-value.md`, **When** a reader reaches the `**Derives
   from**` section, **Then** it lists KPI-MC-02 (Net Sales) and KPI-MC-04 (Transactions Count),
   transcribed from "ATV = Net Sales / Transactions Count".

### User Story 3 - The references router/index stays accurate (Priority: P3)

A maintainer reading the skill's router/index sees the new `references/kpi-derivation-lineage.md`
listed, so navigation does not misrepresent what exists.

**Why this priority**: If the skill has a router/index/file-map that enumerates `references/`, a new
file that is not listed is a stale-pointer self-inconsistency (the lesson the 042 plan-review
flagged: `/speckit-analyze` cross-checks the three spec artifacts, NOT the live repo, so a stale
index is invisible to it).

**Independent Test**: Search the skill for any index/router/SKILL.md/INDEX.md that enumerates files
under `references/`. If one exists, confirm a task adds the new doc to it (and bumps any count). If
none enumerates `references/`, record that explicitly and add no router edit.

**Acceptance Scenarios**:

1. **Given** a skill index that enumerates `references/`, **When** the new lineage doc lands,
   **Then** the index lists it (and any file count is updated).
2. **Given** no index enumerates `references/`, **When** the doc lands, **Then** no router edit is
   made and the spec records that the references dir is not enumerated.

### Edge Cases

- A reader expects the lineage doc to compute or rank KPIs by some score. It does not -- it is a
  static relationship map, never a number a tool guessed (Principle VIII; the hard-principle and
  realist lenses both flagged that this idea must stay categorical/observed-only, never acquire a
  numeric score).
- A contract's prose names a base KPI relationship that is genuinely ambiguous or only partially
  stated. The agent MUST NOT resolve the ambiguity by inventing an edge; it transcribes only what is
  stated and leaves anything unstated as a stop-and-ask (Principle V).
- The existing contracts use Unicode math glyphs (minus, division, multiplication, arrow). The
  authored artifacts MUST be ASCII (`-`, `/`, `*`, `->`); when a formula is quoted, glyphs are
  converted. The agent MUST NOT "fix" the glyphs in the existing contract bodies -- that is out of
  scope (Principle IX applies to the NEW authored text).
- The C086 pharmacy worked example sits beside this content. The lineage doc and the template change
  MUST use only generic retail KPIs (the 10 KPI-MC contracts); no pharmacy-specific KPI, billing
  code, payer segment, or filled C086 edge may leak into the generic kit (Principle VII). C086 may be
  cited as a filled instance, never inlined.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deliverable MUST add a new body section titled `**Derives from**` to
  `skills/retail-kpi-knowledge/references/metric-contract-template.md`, inside the template's
  markdown body (NOT as YAML front-matter), with generic placeholder guidance: list base-KPI
  dependencies by stable KPI-MC ID, or state "none -- base KPI"; reference IDs, never filenames
  (per `id-conventions.md`). Placement SHOULD be adjacent to "Formula in business terms" (the
  section that already references base KPIs).
- **FR-002**: The deliverable MUST add a filled `**Derives from**` section to
  `contracts/net-sales.md` (KPI-MC-02) stating it is a base KPI with no derives-from edge,
  consistent with its committed "Base for growth, margin, ATV ..." prose.
- **FR-003**: The deliverable MUST add a filled `**Derives from**` section to
  `contracts/average-transaction-value.md` (KPI-MC-05) listing KPI-MC-02 (Net Sales) and KPI-MC-04
  (Transactions Count), transcribed from its committed "ATV = Net Sales / Transactions Count" and
  "net sales amount (from Net Sales contract)" prose.
- **FR-004**: The deliverable MUST author one new committed-text file
  `skills/retail-kpi-knowledge/references/kpi-derivation-lineage.md` expressing the base-vs-derived
  dependency graph across all 10 existing KPI-MC contracts. It MUST partition the 10 into BASE
  (KPI-MC-01 Gross Sales, KPI-MC-03 Quantity Sold, KPI-MC-04 Transactions Count, KPI-MC-06 Discount
  Amount) and DERIVED (KPI-MC-02 Net Sales, KPI-MC-05 ATV, KPI-MC-07 Discount Rate %, KPI-MC-08
  Returns Rate %, KPI-MC-09 Gross Margin, KPI-MC-10 Gross Margin %), and list each derived KPI's
  edges by KPI-MC ID.
- **FR-005**: EVERY edge in the lineage doc MUST be transcribed from committed contract prose and
  MUST cite the source it was transcribed from. The transcribed edge set is:
  KPI-MC-02 derives_from KPI-MC-01, KPI-MC-06 ("Net Sales = Gross Sales - total discount");
  KPI-MC-05 derives_from KPI-MC-02, KPI-MC-04 ("ATV = Net Sales / Transactions Count");
  KPI-MC-07 derives_from KPI-MC-06, KPI-MC-01 ("Discount Rate % = Discount Amount / Gross Sales");
  KPI-MC-08 derives_from KPI-MC-02 ("Returns Rate % = Return Value / Net Sales"; Return Value is a
  field, not a contract node);
  KPI-MC-09 derives_from KPI-MC-02 ("Gross Margin = Net Sales - COGS"; COGS is a field, not a
  contract node);
  KPI-MC-10 derives_from KPI-MC-09, KPI-MC-02 ("Gross Margin % = Gross Margin / Net Sales").
- **FR-006**: The lineage doc MUST NOT draw an edge to any node that is not one of the 10 existing
  KPI-MC contracts. Named downstream USES (growth, sales per sqm, vs-target) and FIELDS (COGS,
  Return Value) are NOT nodes and MUST NOT receive edges. The agent MUST NOT INVENT any edge absent
  from committed prose (Principle V).
- **FR-007**: The work MUST stay generic retail. No C086 / pharmacy-specific KPI, billing code,
  payer segment, or filled C086 edge may appear in the template, the two exemplar contracts, or the
  lineage doc (Principle VII). C086 may be cited as a filled instance only, never inlined.
- **FR-008**: The work MUST NOT advance or self-grant any readiness or dashboard-readiness stage,
  MUST NOT include any executor / query / DAX / live-data step, MUST NOT compute or rank a KPI, and
  MUST NOT emit any fabricated confidence or readiness score (Principles I and VIII; repo hard
  rule #9). It DEFINES relationships; it does not CHECK a model (the F009 store boundary).
- **FR-009**: All NEW authored text MUST be ASCII, UTF-8 without BOM (use `-`, `/`, `*`, and `->`;
  no Unicode glyphs; constitution Principle IX / repo encoding rule). The existing Unicode glyphs in
  the contract bodies MUST NOT be altered (out of scope).
- **FR-010**: If a skill index/router/file-map enumerates files under `references/`, it MUST be
  edited to list the new `kpi-derivation-lineage.md` (and any count updated). If no index enumerates
  `references/`, the spec/plan MUST record that explicitly and make no router edit (the
  stale-pointer guard the 042 review surfaced).

### Key Entities *(include if feature involves data)*

- **Derivation edge**: a directed relationship `derived KPI derives_from base KPI`, identified by
  stable KPI-MC IDs, each transcribed from committed contract prose and citing its source. Not a
  data record -- a stated relationship in committed text.
- **`Derives from` section**: the new body section added to the metric-contract template and to the
  two exemplar contracts; carries the edges (or "none -- base KPI") for one contract.
- **Lineage doc**: the new `references/kpi-derivation-lineage.md` -- a navigation/reasoning artifact
  expressing the whole 10-node graph; partitions base vs derived and lists every edge with its
  citation. Not a data artifact, not a generator output.
- **KPI-MC node (referenced, not created)**: each of the 10 existing contracts in `contracts/`;
  the lineage graph spans these real files and invents no node.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `references/kpi-derivation-lineage.md` exists and partitions exactly the 10 existing
  KPI-MC contracts into 4 base and 6 derived; zero non-contract nodes appear.
- **SC-002**: 100% of edges in the lineage doc are transcribed from committed contract prose and
  carry a citation; zero invented edges; zero edges to a non-contract (growth, sales per sqm,
  vs-target, COGS, Return Value).
- **SC-003**: The metric-contract template and both exemplar contracts (`net-sales.md`,
  `average-transaction-value.md`) each carry a `**Derives from**` body section; zero YAML
  front-matter is introduced; the other 8 contracts are unchanged (out of first-step scope).
- **SC-004**: Zero C086 / pharmacy-specific tokens appear in any authored artifact (generic-retail
  scan passes).
- **SC-005**: The `retail check` static gate exits 0 over the changed text (no new rule violation,
  no fabricated readiness/score), and the Principle-V stop (no invented edge) holds -- every edge
  traces to prose.
- **SC-006**: Zero new executor / query / DAX / generator code is added; the deliverable is
  docs/template text only.
- **SC-007**: If a references index exists, it lists the new doc; if none exists, the spec records
  that explicitly. No stale router pointer remains.

## Assumptions

- The 10 existing KPI-MC contracts and their committed prose are the authoritative source of every
  edge; the edge set in FR-005 was read verbatim from those files (net-sales.md, ATV, discount-rate,
  returns-rate-value, gross-margin, gross-margin-percent).
- "Derivation-Lineage Contract" in the idea title is the body-section seam + the rendered doc, NOT a
  new front-matter schema or a generator (the grounder's realist scope; the advisor-confirmed
  representation ruling).
- This work advances no readiness stage (advisor-recommended ruling; carried in the front-matter
  "Readiness stage advanced: none"); it is DEFINE/reasoning-layer content under Principle I, mirroring
  the F009 store's "DEFINES, does not CHECK" boundary.
- The cited downstream "T6.3" and upstream "T1.1 derives_from" in the idea text are idea-backlog task
  IDs, NOT roadmap features; no downstream runtime consumer is assumed to exist.
- No live database, no F016 Power BI Execution Adapter, and no F031-F033 spec-only runtimes are
  assumed to exist or are touched (YAGNI / static-first).
- BASE KPIs (Gross Sales KPI-MC-01, Quantity Sold KPI-MC-03, Transactions Count KPI-MC-04, Discount
  Amount KPI-MC-06) are those whose contracts state a direct SUM/COUNT over fact fields with no
  derives-from-another-KPI prose; this base/derived partition is itself read from the contracts, not
  invented.
