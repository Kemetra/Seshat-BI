# Feature Specification: business meaning registry + Arabic<->English retail term dictionary (generic schema, not a filled instance)

**Feature Branch**: `008-business-meaning-registry` (roadmap F007; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Implemented (commit `7dfbcf5`, 2026-06-25) -- shipped to `main`

**Input**: "Roadmap F007 (Layer 2 Source Intelligence). Advances readiness stage: Source Ready. A GENERIC registry of business terms plus an Arabic<->English retail term DICTIONARY (term, canonical meaning, synonyms, the readiness evidence it contributes) -- the schema/template for the registry, NOT a filled pharmacy dictionary. Strictly generic: carry NO C086/ezaby/pharmacy values (hard rule #7); those would be a filled instance later. Docs/templates first (hard rule #8). Feeds Source Ready evidence per docs/readiness/source-ready.md. No fake confidence (hard rule #9)."

## Why this feature exists

Stage 1 of the readiness spine (Source Ready) requires the analyst to PROPOSE the
semantic meaning of a raw source -- what a column means, what a coded value rolls up
to, what an Arabic billing/segment term means in English -- and to mark each proposal
as a proposal awaiting sign-off, never as invented fact (`docs/readiness/source-ready.md`).
Today there is no shared SHAPE for recording those proposals. `source-profile.md`
records the mechanical numbers and a free-text "Semantics" pass; `assumptions.md`
records the bilingual CASE/rollup decisions as prose; the only worked instance of the
bilingual mappings lives baked inside `docs/data-dictionary.md` (the filled C086
billing_type Arabic->English table and the business_segment rollup). There is no
generic, reusable place to register "here is a business term, here is its canonical
meaning, here are its synonyms, here is the Source-Ready evidence it contributes" --
so every new source re-derives that shape ad hoc.

This feature adds that shape, and only the shape. It is a Layer 2 (Source Intelligence)
docs/templates slice that gives Source Ready two generic artifacts:

1. a **Business Meaning Registry** -- a generic schema/template for registering a
   business term, its canonical meaning, its source-observed surface forms, the
   PROPOSED status, and the evidence it contributes to Source Ready; and
2. an **Arabic<->English retail term Dictionary** -- a generic bilingual schema/template
   for the retail terms a bilingual Arabic/English source carries (e.g. the *kind* of
   billing-type, returns, and segment terms a retail POS export uses), with the term,
   its canonical English meaning, its synonyms/surface variants, and the evidence it
   contributes.

It is strictly generic. It carries NO C086/El Ezaby/pharmacy values -- no Arabic
returns term, no `Z5`-style code, no `PHARMA` rollup, no real drug or store name.
Those are a FILLED INSTANCE
that a later table-onboarding pass would author under `mappings/<table>/`, exactly as
C086 is the first filled instance of the other templates (Principle VII; hard rule #7).

## Roadmap and stage alignment

- **Roadmap entry:** F007 "Business Meaning Registry + Arabic Retail Dictionary",
  Layer 2 (Source Intelligence), advances **Source Ready** (`docs/roadmap/roadmap.md`,
  the "Now" table). (Numbering note: the roadmap lists this as F007; this spec is
  filed in `specs/008-business-meaning-registry/` because this batch was drafted from
  the next free on-disk slot (`specs/` already held 001-006), giving a consistent
  **spec-dir = roadmap-F + 1** offset across the whole batch (007=F006 ... 016=F015).
  There is no `specs/007-*` on `main` -- the offset is the cause, not a "taken slot".
  The roadmap F-number and the spec directory number intentionally differ here; the
  roadmap row, not the directory number, is authoritative for sequence. See the
  numbering-offset note in `docs/roadmap/roadmap.md`.)
- **Readiness stage advanced:** Source Ready (stage 1 of 7). This feature does NOT
  add a new stage, a new gate, or a new principle. It gives the EXISTING Source Ready
  stage a reusable artifact shape for the semantic-proposal half of its work
  (`docs/readiness/source-ready.md`: "the semantic profile rows are PROPOSED for human
  confirmation, never invented").
- **Layer:** Layer 2, Source Intelligence (`docs/roadmap/roadmap.md`, six product layers).

## The generic/instance boundary (the load this feature respects)

This is the hard line this feature is built around (Principle VII; hard rule #7).

- **The SCHEMA/TEMPLATE is in-scope.** Authoring generic template text -- field
  definitions, placeholder rows, the PROPOSED-not-invented discipline, the evidence
  linkage to Source Ready -- is the same category as the five existing
  `templates/*.md`/`.yaml` mapping artifacts: reviewable text, no source values, no DB.
- **The FILLED INSTANCE is out of scope.** A registry/dictionary populated with real
  terms for a real table (the C086 billing_type Arabic->English rows, the
  business_segment rollup, any real product/segment value) is a later table-onboarding
  output that lives under `mappings/<table>/`, cited as a worked example -- never baked
  into the generic template. This feature MUST NOT copy the `docs/data-dictionary.md`
  C086 mappings into the template; it may cite them as the filled instance.

## Architecture (pure docs/templates; no code, no CLI, no new validator)

The deliverables are template/doc text only -- the same posture as features 001-005's
docs/templates slices and consistent with hard rule #8 ("Docs/templates/checklists
first; automate only after artifacts prove useful").

- **Decision: docs/templates only.** Add two generic templates under `templates/` and a
  short Layer-2 reference doc under `docs/` (placement to be fixed in plan). No new
  Python, no `retail check` rule, no CLI subcommand, no automated extraction. The
  registry is a file an analyst fills during the Source Ready semantic pass and commits
  as evidence; it is read by humans and by the agent that proposes meanings.
- **Why no checker rule (YAGNI):** the registry's correctness is a SEMANTIC review (is
  the meaning right? is it PROPOSED not invented? does the analyst confirm?) -- exactly
  the Source Ready "Profile review" gate, which the readiness model defines as a review,
  not a `retail check`/`retail validate` exit code (`docs/readiness/source-ready.md`:
  "This stage has no retail check / retail validate gate. The gate is a review"). A
  static rule cannot judge whether a proposed Arabic->English meaning is correct, so
  adding one would assert false rigor. A future ASCII/no-BOM/frontmatter lint is
  recorded as a deferred decision, not built here.
- **No fake confidence (hard rule #9):** the registry records each entry's status as
  the readiness vocabulary -- a term's meaning is `proposed` (awaiting analyst
  confirmation) or `confirmed` (analyst signed off) -- plus the evidence it cites. It
  MUST NOT carry a numeric confidence/score field (`docs/readiness/readiness-model.md`:
  numeric scores are optional and deferred; prefer explicit status + evidence).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a business term with a PROPOSED meaning (Priority: P1)

During the Source Ready semantic pass on a new source, an analyst (or the agent, on the
analyst's behalf) opens the **Business Meaning Registry** template, copies it for the
table, and registers each business term the profile surfaced: the term as it appears in
the source, its canonical meaning, its observed surface forms, and a `proposed` status
that flags it as awaiting confirmation. The filled registry becomes Source Ready evidence.

**Why this priority**: this is the core gap -- the reusable shape for the
"PROPOSED for human confirmation, never invented" half of Source Ready. Without it,
semantic proposals stay ad hoc prose and the no-invention discipline is unenforced by
shape.

**Independent Test**: a reviewer can take the empty template, fill it with placeholder
(non-C086) terms, and confirm that (a) every entry has a meaning and a `proposed`/
`confirmed` status, (b) there is no numeric confidence field to abuse, and (c) the
filled file is citable as `evidence[]` under the table's Source Ready status -- without
any code being written.

**Acceptance Scenarios**:

1. **Given** a Source Ready semantic pass with a column carrying coded business values,
   **When** the analyst registers them, **Then** each entry records term + canonical
   meaning + surface forms + `proposed` status, and the template instructs that meaning
   be PROPOSED, not asserted (Principle V; source-ready "What the agent must NOT do").
2. **Given** an analyst confirms a proposed meaning, **When** they update the entry,
   **Then** the status reads `confirmed` with the confirming owner recorded (a named
   human action; the agent cannot self-grant it -- Principle V).
3. **Given** an entry whose meaning is a business rollup or PII ruling, **When** it is
   registered, **Then** the template forces it to `proposed` and points the open
   decision to `unresolved-questions.md` (the agent never decides a rollup/PII alone --
   Principle V; source-ready blocking reasons).

### User Story 2 - Look up / record an Arabic<->English retail term (Priority: P1)

A bilingual retail source (Arabic billing/returns/segment terms, English product
names) needs each Arabic term's canonical English meaning recorded so silver mapping
can reference a single shared vocabulary rather than re-deriving it. The analyst uses
the **Arabic<->English retail term Dictionary** template to record term (Arabic),
canonical English meaning, synonyms/surface variants, and the evidence it contributes.

**Why this priority**: the bilingual mapping is the single most error-prone semantic
step in this repo's worked source (the 10-arm billing CASE, the returns Z-code set);
giving it a generic, reviewable shape -- separate from any one table's values -- is
high-value and directly serves Source Ready.

**Independent Test**: fill the dictionary with PLACEHOLDER bilingual rows (generic
"`<arabic-term>` -> `<english-meaning>`", NOT a real source term such as the C086
Arabic returns label mapping to `Credit Return`), confirm the
schema captures term + meaning + synonyms + evidence + status, and confirm an entry
explicitly notes that the source-of-truth for returns is the authoritative billing
column, not a measure sign (RC8) -- demonstrating the generic discipline travels with
the template, with no real values present.

**Acceptance Scenarios**:

1. **Given** the dictionary template, **When** a reviewer scans it, **Then** it carries
   NO C086/ezaby/pharmacy values -- only `<placeholder>` terms and a citation to
   `docs/data-dictionary.md` / `docs/worked-examples/c086-pharmacy.md` as the filled
   instance (Principle VII; hard rule #7).
2. **Given** an Arabic term with multiple surface spellings/encodings in a source,
   **When** it is recorded, **Then** the schema captures them as synonyms/surface
   variants under one canonical meaning (so encoding corruption, RC-encoding, does not
   fork the term).
3. **Given** a returns-related term, **When** it is recorded, **Then** the template
   states returns identity comes from the authoritative billing column (RC8), not the
   sign of a measure -- the discipline is in the schema, not just the instance.

### User Story 3 - The registry feeds Source Ready evidence without inventing readiness (Priority: P2)

A filled registry/dictionary is cited in the table's readiness status as Source Ready
`evidence[]`, and its presence or absence maps onto the Source Ready statuses
(`pass` requires PROPOSED-and-flagged semantics; `blocked` when meaning was INVENTED).
The artifacts add evidence; they never themselves grant a `pass`.

**Why this priority**: closes the loop to the spine, but the registry is usable
(US1/US2) before this linkage is documented; it is a P2 refinement, not the MVP.

**Independent Test**: trace a generic example end-to-end -- an empty registry maps to
Source Ready `blocked`/`warning`, a filled+PROPOSED registry contributes to `pass`
evidence, an INVENTED-meaning registry is a `blocked` blocking-reason -- using only the
status vocabulary already defined in `docs/readiness/source-ready.md`, with no new
status invented.

**Acceptance Scenarios**:

1. **Given** a filled registry with PROPOSED semantics flagged for confirmation,
   **When** the Source Ready status is recorded, **Then** the registry path appears in
   `evidence[]` and the stage may read `pass` only after the analyst confirms
   (source-ready owner/approval).
2. **Given** a registry that asserts an invented business rollup as fact, **When**
   reviewed, **Then** Source Ready is `blocked` with the existing blocking reason
   "Semantic meaning INVENTED ... rather than PROPOSED" -- no new blocking reason added.
3. **Given** the registry, **When** anyone tries to express its readiness as a number,
   **Then** the template forbids it (status + evidence only; hard rule #9).

### Edge Cases

- **A term whose meaning is genuinely a judgment call (business rollup / PII / grain).**
  The template MUST route it to `proposed` + an `unresolved-questions.md` pointer; it
  MUST NOT offer a field that lets the agent self-confirm a rollup or a PII ruling
  (Principle V; these stay in `open_for_human`).
- **The same Arabic term with two encodings (mojibake vs clean).** Recorded as synonyms
  under one canonical meaning; the template notes encoding-corruption is a surface-form
  variant, not a new term.
- **A term with no confirmable meaning yet.** Stays `proposed`; never silently promoted;
  never assigned a fabricated score to look "mostly done."
- **Someone tries to fill the template with the C086 billing_type table.** Disallowed by
  template instruction -- that is the filled instance for `mappings/<table>/`, cited, not
  inlined.
- **An entry that contradicts the source profile** (e.g. claims a returns term but the
  authoritative column shows none). The agent MUST surface the conflict, not bury it
  (Principle V, Socratic cross-check) -- recorded as a template reminder.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add a **Business Meaning Registry** generic template under `templates/`
  (exact filename in plan; e.g. `business-meaning-registry.md`). ASCII only, UTF-8 no
  BOM, with the same `>`-blockquote header convention the existing templates use ("copy
  this file to ...", "ASCII only", "cite numbers not adjectives").
- **FR-002**: The registry schema MUST define, per entry: the business term / coded
  value as it appears in the source; its canonical meaning; observed surface forms;
  the column(s) it was seen in; a status of `proposed` | `confirmed`; the confirming
  owner (when `confirmed`); and the evidence it cites. It MUST NOT define a numeric
  confidence/score field (hard rule #9).
- **FR-003**: Add an **Arabic<->English retail term Dictionary** generic template under
  `templates/` (e.g. `retail-term-dictionary.md`). Same encoding/header conventions.
- **FR-004**: The dictionary schema MUST define, per entry: the term (source language,
  e.g. Arabic); the canonical English meaning; synonyms / surface variants (including
  encoding-corruption variants under one canonical term); the column it was seen in; a
  `proposed` | `confirmed` status; and the evidence it contributes. It MUST state that
  returns identity comes from the authoritative billing column (RC8), not a measure sign.
- **FR-005**: Both templates MUST carry STRICTLY generic content -- `<placeholder>`
  values only, ZERO C086/El Ezaby/pharmacy specifics (no real Arabic source terms, no
  `Z`-codes, no `PHARMA`/segment values, no real product/store/staff names). They MUST cite the filled
  instance (`docs/data-dictionary.md` reference mappings; `docs/worked-examples/c086-pharmacy.md`)
  rather than inline it (Principle VII; hard rule #7).
- **FR-006**: Both templates MUST encode the PROPOSED-not-invented discipline: every
  semantic claim defaults to `proposed`; promotion to `confirmed` is a named human
  action; business-rollup / PII / grain meanings are routed to `unresolved-questions.md`
  and never self-confirmed by the agent (Principle V; source-ready "must NOT do").
- **FR-007**: Add a short Layer-2 reference doc (placement in plan; e.g.
  `docs/source-intelligence.md` or a section under `docs/readiness/`) that explains how
  the two artifacts contribute Source Ready `evidence[]`, maps them onto the existing
  Source Ready statuses (no new status, no new blocking reason), and links the spine.
- **FR-008**: Update `docs/readiness/source-ready.md` "Required artifacts" / "See also"
  (additively) to reference the registry + dictionary as the OPTIONAL semantic-proposal
  artifacts that strengthen the stage's evidence -- WITHOUT making them a new REQUIRED
  gate (the profile remains the one required artifact; Source Ready's gate stays a review).
- **FR-009**: The deliverables MUST keep `retail check` exit 0 and add no Python and no
  dependency: `dependencies = []` unchanged, the full unit suite stays green (the change
  is template/doc text only).
- **FR-010**: Cross-link both templates to the constitution principles they express
  (V Agent-Stops-at-Judgment-Calls, VII C086-is-an-example), the cleaning defaults they
  rely on (RC8 returns-from-authoritative-column, RC-encoding), and the Source Ready doc
  -- the same "See also" convention the existing templates follow.

### Key Entities

- **Business Meaning Registry** (generic template): the reusable shape for registering
  a business term -> canonical meaning -> surface forms -> proposed/confirmed status ->
  evidence. A filled copy lives at `mappings/<table>/` and is Source Ready evidence.
- **Arabic<->English retail term Dictionary** (generic template): the reusable bilingual
  shape -- term (Arabic) -> canonical English meaning -> synonyms/variants -> status ->
  evidence -- with RC8 returns discipline baked in. A filled copy is a per-table instance.
- **Registry entry**: term/value, canonical meaning, surface forms, source column(s),
  status (`proposed` | `confirmed`), owner-when-confirmed, evidence -- NO score field.
- **Filled instance** (out of scope here, cited): the C086 billing_type Arabic->English
  table + business_segment rollup in `docs/data-dictionary.md` -- the worked example the
  generic templates point to, never copy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two generic templates (`business-meaning-registry`, `retail-term-dictionary`)
  exist under `templates/`, ASCII + UTF-8 no BOM, following the existing template header
  convention; both define the per-entry fields in FR-002/FR-004 with NO numeric score field.
- **SC-002**: A leakage scan over both templates and the new doc finds ZERO C086/ezaby/
  pharmacy specifics (no real Arabic source terms, no `Z`-codes, no `PHARMA`, no real
  product/store/staff names); every reference to those is a citation to the worked example, not an inlined value
  (Principle VII; hard rule #7).
- **SC-003**: `retail check` stays exit 0 (current rule count) and the full unit suite stays green
  with the new templates + doc + the additive `source-ready.md` edit; no new Python; no new
  dependency; no new `retail check` rule.
- **SC-004**: A reviewer can trace a generic example mapping the registry/dictionary onto
  Source Ready evidence and statuses using ONLY the vocabulary in
  `docs/readiness/source-ready.md` / `readiness-model.md` -- no new stage, status, blocking
  reason, or confidence number is introduced (hard rule #9).
- **SC-005**: Both templates encode the PROPOSED-not-invented discipline and route
  business-rollup / PII / grain meanings to `unresolved-questions.md` -- verified by the
  presence of the proposed-default + the human-confirmation + the open-decision pointer
  in each template (Principle V).

## Assumptions

- Docs/templates only -- no code, no CLI, no new checker rule, no automated extraction
  (hard rule #8; YAGNI: the Source Ready gate is a semantic review, not a static exit code).
- The registry/dictionary are OPTIONAL semantic-proposal artifacts that STRENGTHEN Source
  Ready evidence; the required Source Ready artifact remains `source-profile.md`
  (`docs/readiness/source-ready.md` left structurally intact, edited additively).
- Filled bilingual values are a per-table instance under `mappings/<table>/`, authored by a
  later table-onboarding pass (roadmap F006 wizard), cited here as the worked example.
- The C086 reference mappings in `docs/data-dictionary.md` are the filled instance the
  generic templates point to; they are NOT migrated, moved, or copied by this feature.
- Status vocabulary reuses the readiness model (`proposed`/`confirmed` for entry meaning;
  the table's Source Ready stage status stays the four-value spine vocabulary). No numeric
  confidence is introduced (hard rule #9).

## Deferred decisions (future specs / issues -- recorded, not built)

- **A filled per-table registry/dictionary instance** under `mappings/<table>/` for a real
  source -- the bilingual values, the rollup table. Authored when a real table is onboarded
  (roadmap F006), not here.
- **An ASCII / no-BOM / frontmatter lint** for the new templates (a mechanical, not
  semantic, check) -- could be a future `retail check` C-family or doc-lint rule; the
  registry's MEANING correctness stays a human review regardless. Recorded, not built.
- **A machine-readable registry format** (YAML alongside the `.md`) for a future agent to
  read programmatically when proposing meanings -- deferred until the markdown shape proves
  useful (hard rule #8: automate only after artifacts prove useful).
- **Source Drift Detector linkage** (roadmap F014): when a source's terms drift from the
  registered meanings, flag it. The registry is the baseline that detector would compare
  against; the detector itself is a later feature.
- **Promoting the registry to a REQUIRED Source Ready artifact** -- only after the optional
  artifact proves useful on a real onboarding; this feature keeps the profile the sole
  required artifact to avoid widening the gate prematurely.

## See also

- The stage this advances: `docs/readiness/source-ready.md` (Source Ready, stage 1; the
  PROPOSED-not-invented semantic discipline and its review gate).
- The spine + status vocabulary + no-fake-confidence rule: `docs/readiness/readiness-model.md`,
  `docs/readiness/readiness-pipeline.md`.
- The roadmap entry + hard rules: `docs/roadmap/roadmap.md` (F007, Layer 2; hard rules
  #7 generic-not-C086, #8 docs-first, #9 no-fake-confidence).
- The constitution principles expressed: `.specify/memory/constitution.md` Principle V
  (Agent Stops at Judgment Calls), Principle VII (C086 Is An Example, Not The Schema),
  Principle VI / RC8 (returns from the authoritative column).
- The existing template conventions to mirror: `templates/source-profile.md`,
  `templates/assumptions.md`, `templates/unresolved-questions.md`.
- The filled instance the templates CITE (never inline): `docs/data-dictionary.md`
  (the C086 billing_type Arabic->English table + business_segment rollup),
  `docs/worked-examples/c086-pharmacy.md`.
