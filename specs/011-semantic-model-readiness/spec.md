# Feature Specification: Semantic Model Readiness -- the model-checking layer

**Feature Branch**: `011-semantic-model-readiness` (work on the feature branch per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Implemented (commit `8fa6bbf`, 2026-06-25) -- shipped to `main`

**Input**: "Roadmap F010 (Layer 5 Metrics & Semantic Model). Advances readiness stage: Semantic Model Ready. Readiness CHECKS for the governed PBIP semantic model: relationships valid, a marked date table exists, and every measure BINDS to an approved metric contract from the metric-contract store (F009 / on-disk 010). This is the model-CHECKING layer; it CONSUMES the contracts that F009 DEFINES -- do not redefine contracts here. Gold must be live-validated before Power BI (hard rule #4) -- this stage sits AFTER Gold Ready. No pbi-cli/PBIP AUTHORING automation (hard rule #6 -- F016 is last and gated); this only READS/checks an existing PBIP model. Maps to docs/readiness/semantic-model-ready.md. No fake confidence (#9)."

## Why this feature exists

Stage 5 of the readiness spine -- **Semantic Model Ready** -- is the gate between a
live-validated gold star and any dashboard design. The stage DOC
(`docs/readiness/semantic-model-ready.md`) already states what "ready" means, but
there is no defined **procedure** that computes the stage status from the committed
PBIP model. Today an agent looking at the model would have to invent how to decide
`not_started` / `blocked` / `warning` / `pass`. This feature fills that hole with a
**pure checking procedure**: a `retail-semantic-check` agent skill that READS the
committed PBIP semantic model plus the metric-contract store, runs the existing
`retail check` gate, evaluates the contract-binding criterion, and emits one
readiness verdict with `evidence[]` and `blocking_reasons[]` -- then STOPS.

It closes the gap between the model-authoring artifacts (the committed PBIP model,
already on disk) and the dashboard stage (F011, gated on this stage being `pass`):
this skill is the verb the `retail-orchestrate` conductor parks at for the Phase-7
model half. It is the live sibling of `retail-govern` and `retail-validate`, one
layer up -- it governs the SEMANTIC MODEL, not the SQL.

## The check/define boundary (the load this feature respects)

- **CHECKING the model is in-scope.** Reading the committed PBIP TMDL, reading the
  metric-contract store, running `retail check`, evaluating "every measure binds to
  an approved contract", and emitting a readiness verdict are all side-effect-free
  reads over committed text -- the same category as `retail-govern` reading TMDL.
- **DEFINING contracts is OUT of scope (F009).** The metric-contract STORE (name,
  grain, formula intent, owner) is defined and owned by feature 009 (Metric Contract
  Store + Retail KPI Packs). This feature is the CONSUMER: it reads contracts to test
  the binding, it never creates, edits, or approves one. This is the F009/F010
  scope boundary -- F009 DEFINES, F010 CHECKS. (Per the roadmap "Next" tier, this
  slice carries the F010 line; the description's "F010 / on-disk 010" naming refers
  to the same checking layer this spec defines.)
- **AUTHORING the model is OUT of scope FOR THIS SKILL.** This read-only checker never
  writes TMDL, never adds or edits a measure, relationship, or date marker. (Clarified
  2026-06-25: authoring the governed model as committed TMDL is a SEPARATE Stage-7
  activity -- `pbip-workflow` + `powerbi-analyst`, model-as-code -- NOT F016. F016 is the
  execution-only adapter: live connection / refresh / publish, which CANNOT define
  semantic logic; it is last and gated on this stage being `pass`, constitution
  Principle II / roadmap hard rule #6.) The checker reads an EXISTING model and reports;
  a human (or the Stage-7 authoring step) edits the TMDL to remediate, never this skill.

## Architecture (a pure skill; no codegen, no new checker rules, no CLI)

The checker is `.claude/skills/retail-semantic-check/SKILL.md` -- agent-procedure
text; the agent is the runtime (same posture as the other readiness verbs).
**Decision: pure skill, no new Python, no new `retail check` rule, no `retail`
CLI subcommand.**

Deciding reason: the MECHANICAL half of this stage already ships as enforced rules
in the static checker -- D1 (PascalCase measures), D2 (displayFolder), D4 (DIVIDE
not `/`), D6 (no bidirectional relationships), D7 (time-intelligence needs a marked
date table), D8 (gold-only partitions), C1 (parameterized connection), R1 (relative
reference), G6 (no real host in PBIP parameters). The skill CALLS `retail check`
for all of that; it adds no rule. The remaining half -- "every measure binds to an
approved metric contract" -- is a CROSS-ARTIFACT JUDGMENT (match each TMDL measure
to a contract in the F009 store, confirm owner approval). That binding is naturally
an agent reading two committed artifacts and a human approval record; encoding it as
a static rule would require the F009 store schema to be frozen first (it is not) and
would duplicate F009's ownership of contract identity. So the skill orchestrates the
existing gate + performs the binding read; it introduces no maintained code surface
for ~zero gain at this stage (YAGNI), and keeps the all-skills verb architecture.

## The current model (why this stage is `blocked` today, by design)

The committed `powerbi/Retailgold.SemanticModel` model already has six star
relationships (`fct_sales` -> six dims on `_sk`), a `gold dim_date` table, and ~12
PascalCase measures in display folders -- and `retail check` passes on it. BUT the
metric-contract store (F009) is NOT built yet, so there is NOTHING for those measures
to bind to. By the stage doc, that means Semantic Model Ready is `blocked` (measures
with no contract) -- NOT `pass`, even though the mechanical gate is green. This
feature must make that exact outcome legible: a clean `retail check` is
NECESSARY-not-sufficient; the binding criterion is what gates `pass`. The skill must
report `blocked` with the reason "metric-contract store (F009) not built" rather than
read a green checker as a pass. This is the central correctness property.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute the Semantic Model Ready verdict (Priority: P1)

Given a committed PBIP semantic model whose prior stage (Gold Ready) is `pass`, the
skill runs `retail check`, evaluates the contract-binding criterion against the F009
store, and emits ONE readiness verdict (`not_started` | `blocked` | `warning` |
`pass`) with `evidence[]` and `blocking_reasons[]`, then STOPS.

**Why this priority**: the verdict IS the feature -- it is the single legible answer
the readiness spine and the `retail-orchestrate` conductor read to decide the next
allowed action at the Phase-7 model seam.

**Independent Test**: against the committed RetailGold model with NO F009 store
present, the skill emits `blocked` with `blocking_reasons` including "metric-contract
store not built; measures have no contract to bind to", cites the green `retail
check` run as evidence-of-mechanical-pass-only, and does NOT emit `pass`.

**Acceptance Scenarios**:

1. **Given** Gold Ready is not `pass`, **When** the skill runs, **Then** it emits
   `not_started` and STOPS -- it never checks a model whose source gold is unproven
   (hard gate: Gold live-validated before Power BI, constitution Principle VIII).
2. **Given** `retail check` reports a D1-D8 / C1 / R1 / G6 finding, **When** the
   skill runs, **Then** it emits `blocked` with the finding id(s) as
   `blocking_reasons` and STOPS.
3. **Given** `retail check` is exit 0 BUT the F009 metric-contract store does not
   exist, **When** the skill runs, **Then** it emits `blocked` ("no contracts to
   bind to"), NOT `pass` -- a green checker is necessary-not-sufficient.
4. **Given** `retail check` is exit 0, every measure binds to an approved contract,
   and the metric owner's approval is recorded, **When** the skill runs, **Then** it
   emits `pass` with the contract names + owner + date as `evidence[]`.

### User Story 2 - The contract-binding criterion (Priority: P1)

For each PascalCase measure in the model, the skill confirms there is a matching
APPROVED metric contract in the F009 store (by measure name / contract key) and that
an owner approval is recorded. Any unmatched measure, or any matched-but-unapproved
contract, is a `blocking_reason`. The skill never invents, edits, or self-approves a
contract.

**Why this priority**: contract-binding is the one criterion this stage adds beyond
the mechanical gate; it is what makes the model GOVERNED rather than merely clean.

**Independent Test**: with a fixture F009 store covering only SOME of the model's
measures, the skill lists each unmatched measure as a distinct `blocking_reason` and
emits `blocked`; with a store covering ALL measures but missing the owner approval
record, it emits `blocked` ("owner approval not recorded"), never `pass`.

**Acceptance Scenarios**:

1. **Given** a measure with no matching contract, **Then** that measure is a named
   `blocking_reason`; the skill never auto-creates the contract.
2. **Given** a contract exists but is not marked approved by the named owner,
   **Then** `blocked` ("owner approval missing") -- approval is a human action the
   skill cannot self-grant (constitution Principle V).
3. **Given** a model measure name that does not map cleanly to a contract key,
   **Then** the skill STOPS and raises the ambiguous mapping for a human rather than
   guessing a match.

### User Story 3 - Read-only, author-nothing honesty (Priority: P1)

The skill READS committed artifacts only. It never writes TMDL, never edits a measure
or relationship, never marks a date table, never calls pbi-cli / PBIP automation, and
never writes a readiness `pass` it cannot back with evidence.

**Why this priority**: this is the hard rule #6 / Principle II boundary -- the whole
stage is a gate that PRECEDES any authoring automation; a checker that authored would
collapse the gate.

**Acceptance Scenarios**:

1. **Given** a fixable finding (e.g. a measure missing a displayFolder), **Then** the
   skill REPORTS it as a `blocking_reason` and prints the human remediation step (edit
   in Power BI Desktop, re-save PBIP) -- it never edits the TMDL itself.
2. **Given** any model state, **Then** the skill opens no DB connection, invokes no
   pbi-cli command, and modifies no file under `powerbi/`.
3. **Given** insufficient evidence for a `pass`, **Then** the skill emits `blocked` or
   `warning` and STOPS -- never a `pass` without recorded `evidence[]` (no fake
   confidence, hard rule #9).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `.claude/skills/retail-semantic-check/SKILL.md` (ASCII, UTF-8 no
  BOM, valid frontmatter). No new Python, no new `retail check` rule, no CLI
  subcommand.
- **FR-002**: The skill MUST refuse to evaluate unless the prior stage (Gold Ready)
  is `pass` -- it reads the readiness status at the canonical
  `mappings/<table>/readiness-status.yaml` (ADR 0004; shaped to
  `templates/readiness-status.yaml`) and emits `not_started` + STOPS otherwise
  (hard gate; Principle VIII).
- **FR-003**: The skill MUST run `retail check` over the committed PBIP model and
  treat any D1-D8 (TMDL/DAX), C1 (connection params), R1 (relative reference), or G6
  (no real host) finding as a `blocking_reason`. It cites the `retail check` exit
  code as evidence; exit 0 is recorded as MECHANICAL-pass-only.
- **FR-004**: The skill MUST evaluate the structural readiness facts the stage doc
  requires: relationships present and single-direction (D6), a marked date table
  present (D7's marker: the `DATE_TABLE_MARKER` annotation OR table-level
  `dataCategory: Time` + a key column), measures PascalCase (D1) in display folders
  (D2). These are surfaced via `retail check`; the skill interprets, it does not
  re-implement the rules.
- **FR-005**: The skill MUST evaluate the CONTRACT-BINDING criterion: for every model
  measure, a matching APPROVED metric contract exists in the F009 store, with a
  recorded owner approval. Any unmatched measure or unapproved/missing contract is a
  distinct `blocking_reason`. The skill READS the F009 store; it never creates, edits,
  or approves a contract (F009/F010 boundary; Principle V).
- **FR-006**: The skill MUST treat a clean `retail check` as NECESSARY-not-sufficient:
  it MUST NOT emit `pass` on a green checker alone; `pass` additionally requires the
  contract-binding criterion satisfied AND owner approval recorded.
- **FR-007**: The skill MUST emit exactly one stage verdict
  (`not_started` | `blocked` | `warning` | `pass`) shaped to the readiness-status
  schema, with `evidence[]` (committed files + check runs) and `blocking_reasons[]`.
  A `pass` MUST carry evidence; the skill MUST NOT fabricate a confidence number
  (hard rule #9; readiness-model "No fake confidence").
- **FR-008**: The skill MUST be read-only: it writes no TMDL, edits no measure /
  relationship / date marker, opens no DB connection, invokes no pbi-cli / PBIP
  automation, and modifies no file under `powerbi/` (Principle II; hard rule #6).
- **FR-009**: The skill MUST carry a fail-loud judgment-stop table: F009 store absent;
  measure name not cleanly mappable to a contract key; a `warning`-vs-`blocked`
  ambiguity; owner identity unclear. Each is a HARD-STOP raised for a human, never a
  silent default. Grain semantics, PII publish-safety, business-rollup mappings, and
  product-identity are NOT decided by this skill (Principle V).
- **FR-010**: Append a `## Orchestration` pointer to the skill; `retail-orchestrate`
  references it at the Phase-7 model `[SEAM]` (the conductor's semantic-model seam is
  filled by a checking verb that still stops before any authoring).
- **FR-011**: The skill MUST cross-link the stage doc
  (`docs/readiness/semantic-model-ready.md`) as the authority on the stage's required
  artifacts, checks, statuses, blocking reasons, and approver -- it implements that
  doc's procedure, it does not redefine the stage.

### Key Entities

- **Semantic-check skill** (`retail-semantic-check`): the read-only checking verb;
  the agent is the runtime. Computes the Stage-5 verdict.
- **PBIP semantic model** (`powerbi/<Model>.SemanticModel/definition/`): the
  committed TMDL read (relationships, date table, measures, connection params).
  Read-only input.
- **Metric-contract store** (F009 artifact): the on-disk store of contracts (name,
  grain, formula intent, owner, approval). READ here; OWNED by F009. Absent today.
- **Readiness verdict**: one Stage-5 record (`status` + `evidence[]` +
  `blocking_reasons[]` + `approvals[]`) shaped to `templates/readiness-status.yaml`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/retail-semantic-check/SKILL.md` exists, ASCII + UTF-8
  no BOM, registered by the harness, with valid frontmatter and an `## Orchestration`
  pointer that `retail-orchestrate` references at the Phase-7 model seam.
- **SC-002**: `retail check` stays exit 0 (no new rule added) and the full unit suite
  stays green with the new skill present; no new Python; `dependencies = []`
  unchanged.
- **SC-003**: Against the committed RetailGold model with NO F009 store, the skill
  emits `blocked` with a `blocking_reason` naming the missing metric-contract store,
  cites the green `retail check` as mechanical-pass-only, and does NOT emit `pass`
  (the central correctness property).
- **SC-004**: The skill documents, in its own text, that a clean `retail check` is
  NECESSARY-not-sufficient for Stage-5 `pass` -- `pass` requires contract-binding +
  owner approval as `evidence[]` -- and that it authors nothing (read-only;
  pbi-cli / PBIP automation stays deferred to F016).

## Assumptions

- Pure skill (no new Python / rule / CLI) -- the mechanical half ships as existing
  D1-D8/C1/R1/G6 rules; the binding half is a cross-artifact read best done by the
  agent (YAGNI; the F009 store schema is not frozen, so a static rule is premature).
- This stage is the CONSUMER of metric contracts; F009 is the producer. Until F009
  ships, the stage is `blocked` for any model with measures (nothing to bind to) --
  that is the correct, designed outcome, not a defect.
- Gold Ready must be `pass` first (this stage sits after the live-validation hard
  gate) -- the skill reads the readiness status to enforce ordering.
- The committed RetailGold model is the available fixture for the read-only check;
  the F009-store-absent case is the primary acceptance scenario.
- Numbering: THIS checker is **on-disk 011** (roadmap F010). The metric-contract STORE
  it consumes is **on-disk 010** (roadmap F009). The input's "F009 / on-disk 010"
  refers to that store; this spec's own checking layer is on-disk 011 -- the two are
  the producer (010) and consumer (011), not the same number.

## Deferred decisions (future specs / issues -- recorded, not built)

- **The F009 metric-contract store itself** (name, grain, formula intent, owner,
  approval record + KPI packs) -- DEFINED by feature 009, consumed here. The exact
  store schema and the measure-name <-> contract-key matching convention are F009's
  to settle; this spec assumes a readable store and a recordable owner approval.
- **A static `retail check` rule for contract-binding** -- once the F009 store schema
  is frozen, a rule that fails closed when a model measure has no approved contract
  could move this criterion onto the gate (stronger than an agent read). Premature
  until F009 lands; recorded for a later checker slice.
- **pbi-cli / PBIP authoring automation** (F016, LAST + gated) -- editing TMDL,
  marking a date table, adding a measure programmatically all belong to the deferred
  authoring adapter, gated on this stage being `pass` (Principle II; hard rule #6).
- **Dashboard design against the approved contracts** (F011, Stage 6) -- begins only
  after this stage is `pass`; explicitly not started here.
- **A numeric readiness score** -- optional and deferred until scoring rules are
  defined (readiness-model "No fake confidence"); the four explicit statuses are the
  contract for now.

## See also

- The stage this advances: `docs/readiness/semantic-model-ready.md` (the authority).
- The spine: `docs/readiness/readiness-model.md`, `docs/readiness/readiness-pipeline.md`.
- The conductor that parks at this seam: `.claude/skills/retail-orchestrate/SKILL.md`;
  `specs/005-layer-d-orchestration/spec.md`.
- The mechanical gate it calls: `retail check` (D1-D8 `src/retail/rules/dax.py`,
  C1/R1 `src/retail/rules/pbir.py`, G6 `src/retail/rules/g6.py`); the
  `retail-govern` skill.
- The model under check: `powerbi/Retailgold.SemanticModel/definition/`.
- The producer of contracts (out of scope here): roadmap feature 009.
- The roadmap + hard rules: `docs/roadmap/roadmap.md` (rules #4, #5, #6, #9).
- The constitution principles reinforced: II, V, VIII, and the Readiness System spine.
