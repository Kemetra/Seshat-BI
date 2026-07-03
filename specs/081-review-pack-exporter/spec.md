# Feature Specification: Review Pack Exporter (stable serialization formats)

**Feature Branch**: `081-review-pack-exporter`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "Review Pack Exporter -- define EXPORT FORMATS for review/evidence
packs (Markdown for humans, JSON for machines, a compact CI/PR summary). An exporter, not a
review engine: it formats/serializes an already-produced pack. Must define STABLE schemas and
backwards-compatible output expectations. Must preserve the pending / blocked / pass / warning
/ not_applicable distinctions faithfully."

## Boundary against neighbouring shipped/idea work (read first)

This feature is a **formatter**, not a producer. It sits entirely downstream of tools that
already decide status and already assemble content; it never re-decides or re-composes.
Three neighbours must stay distinct:

- **B2 (`retail check --format json`, shipped PR #63)** -- `src/retail/runner.py:run_json`
  already emits one structured JSON document (`{"findings": [...], "exit_code": ...}`) built
  from `core.Finding.to_dict()`. This feature does NOT re-implement or compete with B2's JSON
  shape; the exporter's JSON envelope EMBEDS a `Finding`-shaped record set (RFC: same field
  names) so a caller who already parses B2's JSON recognizes the finding shape inside an
  exported pack.
- **J1 (`approval-evidence-pack`, spec `specs/063-approval-evidence-pack/`, shipped)** -- J1 is
  the COMPOSER: it reads scattered committed sources (readiness docs, `readiness-status.yaml`,
  metric-contract assumption signals, the parked-on map) and renders ONE Markdown document per
  (table, stage), ending in an empty approval slot. This feature is the OPPOSITE half of that
  pipeline: it never reads those scattered sources itself. It accepts an **already-produced,
  in-memory pack** (the kind of content J1, LVR, or a future review engine already assembled)
  and renders that SAME content into multiple output shapes (Markdown / JSON / compact
  CI-summary). J1 (or any other producer) may choose to call this exporter's Markdown
  serializer to render its pack -- but this feature owns no business logic, no artifact
  discovery, and no read-source contract of its own.
- **LVR (`readiness_evidence.py`, spec `057-live-validation-evidence-recorder`, shipped)** --
  LVR maps live-check `Finding`s into a proposed `gold_ready` readiness BLOCK (a plain dict);
  it is itself a small, pure, stdlib producer of pack-shaped content. This feature can accept
  an LVR-shaped block as one instance of the generic pack shape it serializes, but it does not
  alter, re-run, or wrap LVR's derivation logic.

This feature adds **no new readiness stage**, **no new `retail check` rule**, and **no new
review/evidence-gathering logic**. It is a pure OUTPUT-FORMAT layer: given a pack (however
produced), render it faithfully in the requested shape, and guarantee that shape stays
backwards-compatible as the schema evolves.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A human reads an exported pack as Markdown (Priority: P1)

An analyst or table owner has a review/evidence pack (produced by J1, LVR, or a future review
engine) and wants to read it as a legible Markdown document -- the same kind of artifact J1
already writes today, but now produced by a single shared, schema-driven serializer instead of
each producer hand-formatting its own Markdown.

**Why this priority**: Markdown-for-humans is the existing, proven consumption path (J1 already
ships one); making it a reusable serializer over a stable pack shape is the foundation the other
two formats sit on.

**Independent Test**: Given a minimal in-memory pack object (header, one or more sections, each
with a status token, evidence lines, and blocking reasons), rendering it to Markdown produces an
ordered document with a heading per section, the status token shown verbatim, evidence and
blocking-reason lines each traceable to the pack's own data (no invented text).

**Acceptance Scenarios**:

1. **Given** a pack with two sections, one `status: pass` with `evidence: [...]` and one
   `status: blocked` with `blocking_reasons: [...]`, **When** the Markdown exporter renders it,
   **Then** the output shows both statuses verbatim, lists every evidence and blocking-reason
   line exactly once, and introduces no numeric score.
2. **Given** a pack section whose status is `not_applicable`, **When** rendered, **Then** the
   Markdown output states "not applicable" (or the pack's own not-applicable wording) rather
   than omitting the section or rendering it as `blocked`/`pass`.
3. **Given** the same pack rendered twice with no data change, **When** the two outputs are
   compared, **Then** they are byte-identical (deterministic rendering; no timestamp unless the
   pack itself supplies one).

---

### User Story 2 - A tool consumes an exported pack as JSON (Priority: P1)

A downstream script, CI job, or another agent needs the same pack's content in a
machine-parseable shape to feed further tooling (e.g. a future K1-style rollup, once that idea
clears its own HORIZON gate) without scraping Markdown.

**Why this priority**: Machine consumption is the second pillar named in the feature's purpose;
without a stable JSON shape, every consumer re-invents its own scraping logic against Markdown,
which is exactly the fragility this feature exists to remove.

**Independent Test**: Given the same in-memory pack object as User Story 1, serializing it to
JSON and re-parsing it recovers every status token, evidence line, and blocking-reason line
with no loss, and the document validates against the documented JSON schema.

**Acceptance Scenarios**:

1. **Given** a pack with a `schema_version` field, **When** exported to JSON, **Then** the
   top-level document carries that `schema_version` verbatim and every section's status is one
   of the documented tokens (never re-mapped to a different token).
2. **Given** a pack section carrying a `Finding`-shaped list (rule_id/severity/message/locator,
   the same fields `core.Finding.to_dict()` emits), **When** exported to JSON, **Then** each
   finding's fields round-trip unchanged (field names and value shapes match B2's finding
   shape).
3. **Given** the exported JSON, **When** inspected for numeric fields, **Then** no field reads
   as a confidence/health/maturity score and no field is a bare completeness count presented as
   a verdict (hard rule #9).

---

### User Story 3 - CI/PR gets a compact, non-scoring summary (Priority: P2)

A CI job or PR-comment bot wants a short, skimmable summary of a pack's overall result --
enough to decide "does this need human attention" -- without emitting a fabricated health
percentage or a bare "N of M passed" tally that would read as a confidence claim.

**Why this priority**: This is the third named output shape and the one with the highest
fake-confidence risk if built carelessly; it is P2 because it depends on the same pack shape
User Stories 1-2 already stabilize, but it is where the spec must be most explicit about what
is forbidden.

**Independent Test**: Given a pack whose worst section status is `blocked`, the compact
summary states the worst status and lists every `blocking_reasons` line for the section(s) at
that worst status, with no numeric count anywhere; given a pack with no `blocked` or `warning`
sections, the compact summary states the best-available faithful status and cites the evidence
it is based on.

**Acceptance Scenarios**:

1. **Given** a pack with sections `pass`, `warning`, `blocked`, **When** the compact summary is
   generated, **Then** it reports the single worst status across sections (`blocked` in this
   example) plus every blocking reason for that status, and contains no numeric score.
2. **Given** a pack with only `pass` and `not_applicable` sections, **When** the compact summary
   is generated, **Then** it reports `pass` as the overall result and cites at least one
   evidence line, still with no numeric score.
3. **Given** a pack section count that a naive implementation might render as "N of M sections
   passed", **When** the compact summary is generated, **Then** no such completeness tally
   appears anywhere in the output (hard rule #9; this is the primary scenario the analyze step
   must re-verify).

---

### User Story 4 - A schema change stays backwards-compatible (Priority: P2)

A future spec adds a new optional field to the pack shape (e.g. a new section kind). An older
consumer that only understands the previous `schema_version` must not break when it receives a
newer document, and a newer exporter must not silently drop information an older consumer
relied on.

**Why this priority**: "Must define STABLE schemas and backwards-compatible output
expectations" is named explicitly in the feature's purpose; without this story the other three
are one refactor away from breaking every existing consumer.

**Independent Test**: Given two pack documents produced by exporters at `schema_version: "1.0"`
and a hypothetical `schema_version: "1.1"` that only adds one new optional field, a consumer
written against `"1.0"`'s documented fields can still read every field it expects from the
`"1.1"` document unchanged.

**Acceptance Scenarios**:

1. **Given** the documented compatibility rule (additive-only; no field renamed or removed
   within a MAJOR version), **When** a new optional field is proposed, **Then** the rule
   permits it without a `schema_version` MAJOR bump.
2. **Given** a consumer that only reads a subset of documented fields, **When** it receives a
   document carrying additional unknown fields, **Then** the documented contract states the
   consumer MUST tolerate (ignore) unknown fields rather than fail closed.
3. **Given** a change that would remove or repurpose an existing field, **When** evaluated
   against the compatibility rule, **Then** the rule classifies it as MAJOR (breaking) and
   requires a new `schema_version` value the exporter serializes to only on request.

---

### Edge Cases

- What happens when the input pack's status token is one this exporter has never seen (not one
  of the documented tokens)? The exporter MUST NOT silently drop or coerce it to a known token;
  it surfaces the unrecognized token verbatim and flags it (in Markdown, a visible marker; in
  JSON, the raw string plus a `"recognized": false` companion field) rather than guessing.
- What happens when a section has an empty `evidence[]` and an empty `blocking_reasons[]` but a
  non-`not_started`/`not_applicable` status? The exporter renders the status as given and
  states "no evidence recorded" rather than inventing a plausible-sounding justification.
- What happens when the compact CI summary is asked for a pack with zero sections? It reports
  "no sections in pack" as the result, never a fabricated pass.
- What happens when the same pack is exported to more than one format in the same run? Every
  format is derived from the identical in-memory pack object; the exporter never re-reads or
  re-derives content per format (single source of truth per invocation).
- What happens when a producer's status vocabulary (e.g. LVR's `"deferred"` run_mode, or the
  four-status readiness model's `not_started`) does not exactly match this feature's documented
  token set? See Assumptions -- the exporter passes tokens through verbatim; it does not
  normalize or remap between vocabularies (that is a judgment call, Principle V, out of scope).
- What happens when Markdown output is requested but the pack contains a business-rule ruling
  (grain/rollup/segment/PII) inherited from an upstream producer? The exporter renders whatever
  text the pack supplies for that field verbatim; it does not paraphrase, summarize, or
  originate business-rule wording (that discipline belongs to the producer, e.g. J1's FR-013
  link-and-cite rule; this feature has no opinion on business rules, only on formatting).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The exporter MUST accept a pack as an already-constructed, in-memory data
  structure (the "pack shape" defined in `data-model.md`) and MUST NOT itself read
  `readiness-status.yaml`, metric contracts, the parked-on map, or any other committed source
  artifact to assemble pack content. Composing a pack from scattered sources is a producer's
  job (e.g. J1), never this feature's.
- **FR-002**: The exporter MUST support at minimum three output formats from the same pack
  object: (a) Markdown for humans, (b) JSON for machines, (c) a compact CI/PR summary. Each
  format MUST be derivable independently from the same in-memory pack without re-deriving or
  mutating it.
- **FR-003**: Every section's status token in the input pack MUST be preserved verbatim in every
  output format. The exporter MUST NOT remap, normalize, or collapse one status vocabulary into
  another (e.g. it MUST NOT turn `not_started` into `pending`, or `deferred` into `blocked`).
- **FR-004**: The exporter MUST recognize at least the five status tokens named in the feature
  request -- `pending`, `blocked`, `pass`, `warning`, `not_applicable` -- as well as the four
  readiness-model tokens (`not_started`, `blocked`, `warning`, `pass`) it may also receive from
  a readiness-spine-shaped producer, and MUST document the full recognized set plus the
  pass-through behavior for any token outside it (Edge Cases).
- **FR-005**: No output format MAY emit a numeric confidence, health, or maturity score, and no
  output format MAY emit a completeness tally (an "N of M" count) presented as a verdict (hard
  rule #9; constitution Readiness System section; J1 FR-012 precedent). This applies most
  acutely to the compact CI/PR summary (User Story 3).
- **FR-006**: The compact CI/PR summary MUST report the single worst status across the pack's
  sections (using a documented, fixed severity ordering of the recognized tokens) plus the
  blocking reasons associated with that worst status. It MUST NOT contain a numeric section
  count in ANY form -- no percentage, no fraction, no `N of M` tally, anywhere in the output,
  whether as the primary verdict or as an aside. If the summary needs to indicate WHICH
  sections triggered the reported status, it does so by NAMING the section(s), never by a
  count (hard rule #9).
- **FR-007**: The JSON format MUST carry a `schema_version` field at the document's top level.
  The exporter MUST document a compatibility rule: within the same MAJOR `schema_version`,
  fields are additive-only (new fields MUST be optional; no existing field is renamed or
  removed); a breaking change MUST bump the MAJOR version.
- **FR-008**: Every output format MUST document that a consumer MUST tolerate (ignore) unknown
  fields it does not recognize, so a newer document does not break an older consumer built
  against a prior MINOR/PATCH `schema_version`.
- **FR-009**: When the input pack contains a `Finding`-shaped record (fields matching
  `core.Finding.to_dict()`: `rule_id`, `severity`, `message`, `locator`), the JSON exporter
  MUST preserve those field names and value shapes unchanged, so a consumer already parsing
  B2's `retail check --format json` output recognizes the embedded shape.
- **FR-010**: The exporter MUST NOT define, approve, or alter any business-rule ruling (grain,
  rollup, segment, PII publish-safety) carried in pack content; it renders whatever text the
  pack supplies for such a field verbatim, in the same shape the pack received it.
- **FR-011**: The exporter MUST NOT connect to a database, read a live Power BI/PBIP surface, or
  invoke any deferred execution adapter (F016) or spec-only runtime. It operates purely on the
  in-memory pack object passed to it.
- **FR-012**: The exporter MUST NOT write, grant, or imply any approval, and MUST NOT move any
  readiness stage to `pass`. It has no write access to `approvals[]` or any readiness artifact;
  it only renders the pack content it was given into an output string/document. If an output
  format is asked to render a status token whose value in the source pack is not `pass`, no
  output format may present it as `pass`.
- **FR-013**: Markdown rendering MUST be deterministic: given the same pack object and no
  pack-supplied timestamp, two renderings MUST be byte-identical (no wall-clock timestamp, no
  nondeterministic ordering).
- **FR-014**: The exporter and its documented schemas MUST stay generic (Principle VII): no
  worked-example (C086) label, business-segment name, or column name appears in the schema,
  the contracts, or a fixed section label. A worked example may be cited, never inlined.
- **FR-015**: All authored artifacts MUST be ASCII, UTF-8 without BOM (`--` and `->`, no
  glyphs), and MUST use short repo-relative paths (Windows 260-char budget) (Constitution
  Principle IX).
- **FR-016**: YAML output is explicitly OUT OF SCOPE for the initial schema (see Assumptions):
  the machine format is JSON (stdlib-only, no new dependency). A future YAML serializer, if
  ever added, MUST be documented as consuming the same pack shape and the same
  `schema_version`, added as a MINOR (additive) change, never a replacement for JSON.
- **FR-017**: The exporter MUST leave the unrecognized-status-token case visibly distinguishable
  from every recognized token in all three formats (Edge Cases) -- it must never render an
  unrecognized token silently as if it were a known, understood status.

### Key Entities

- **Pack**: the already-produced, in-memory input this feature serializes. Has a
  `schema_version`, a header (identifying what the pack is about, opaque to this feature), and
  an ordered list of Sections. Owns no truth; this feature never constructs one from source
  artifacts.
- **Section**: one named unit within a pack. Carries a `status` token (verbatim, one of the
  recognized set or an unrecognized pass-through), an `evidence[]` list of strings, a
  `blocking_reasons[]` list of strings, and MAY carry a `findings[]` list of `Finding`-shaped
  records (FR-009).
- **Finding** (embedded, not owned): the `rule_id` / `severity` / `message` / `locator` shape
  already defined by `core.Finding.to_dict()` (B2). This feature re-uses, never redefines, that
  shape.
- **Status token**: one of the recognized vocabulary values (FR-004) or an unrecognized
  pass-through value (FR-017). Never a numeric score.
- **Output format**: one of Markdown / JSON / compact-CI-summary. Each is a pure function of a
  Pack; none holds state between invocations.
- **schema_version**: a version string carried in the JSON format (FR-007) governing the
  additive-only compatibility rule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given the same in-memory pack object, all three output formats (Markdown, JSON,
  compact CI summary) can be produced without re-reading any committed source artifact and
  without any network or database call.
- **SC-002**: 100% of status tokens present in an input pack appear verbatim (unmodified) in
  every output format that surfaces status; 0 tokens are silently remapped or dropped.
- **SC-003**: 0 output documents, across all three formats, contain a numeric confidence/health/
  maturity score or an "N of M" completeness tally presented as a verdict.
- **SC-004**: A JSON document produced at a given `schema_version` remains readable, field-for-
  field, by a consumer written against any prior MINOR/PATCH version of the same MAJOR
  `schema_version` (additive-only backwards compatibility, demonstrated by the documented
  compatibility rule plus a worked example in `contracts/`).
- **SC-005**: Two Markdown renderings of the same unchanged pack, run at different times, are
  byte-identical.
- **SC-006**: 0 generic schema/contract artifacts contain a worked-example (C086) domain
  specific.
- **SC-007**: A `Finding`-shaped record embedded in a pack round-trips through the JSON exporter
  with its four fields (`rule_id`, `severity`, `message`, `locator`) unchanged in name and
  value shape.

## Assumptions

- **Producer-agnostic input (tripwire guarded)**: this feature accepts a pack that some other,
  already-shipped or future producer (J1, LVR, a future review engine, K1 if it ever ships)
  constructs. It does not itself discover, read, or validate source artifacts. If a later
  design finds the exporter reading `readiness-status.yaml` or `metrics/*.yaml` directly, that
  is scope creep into the composer role (J1's job) and must be rejected.
- **Status-vocabulary pass-through, not unification**: the feature request names five tokens
  (`pending`, `blocked`, `pass`, `warning`, `not_applicable`); the shipped readiness model
  (`docs/readiness/readiness-model.md`) names four (`not_started`, `blocked`, `warning`,
  `pass`); LVR emits a `run_mode` of `"live"`/`"deferred"`; F028's Form C uses "not applicable"
  prose. Rather than invent one canonical status enum and silently translate between them (a
  judgment call reserved for a human per Principle V), this feature documents the union of
  known tokens and passes every token through verbatim, flagging anything outside that union
  (FR-004, FR-017). Reconciling the vocabularies into a single canonical model, if ever wanted,
  is a separate, future, human-decided feature.
- **JSON, not YAML, is the machine format**: JSON is stdlib (`json` module); YAML would add a
  new third-party dependency, forbidden by this task's boundaries and by the kit's
  stdlib-only static-governance posture (Constitution Principle VIII). YAML support is
  explicitly deferred (FR-016), not silently dropped.
- **This feature ships as code, not a skill-only Product Module, unlike J1**: J1
  (`specs/063-approval-evidence-pack/`) is docs/skill/template-only because its job is judgment
  -- reading and selecting which committed facts belong in a pack is naturally agent-driven
  prose work. This feature's job is the opposite: a byte-stable, backwards-compatible
  serialization contract is exactly the kind of small, pure, deterministic transform that
  belongs in a stdlib module with golden-file tests (the `readiness_evidence.py` / LVR
  precedent), not in agent prose that could render the "same" pack two different ways on two
  different runs. `plan.md` identifies the likely module location without creating it (spec
  work only).
- **No committed spec dir names this feature by its exact title**: a check of the roadmap idea
  backlog and the 2026-07-03 build-plan design doc found no idea entry literally titled "review
  pack exporter"; the closest kin are B2 (JSON findings), J1 (approval-evidence-pack composer),
  LVR (readiness evidence recorder), and the HORIZON-parked K1 (gate-observability-rollup,
  explicitly gated on a third emission format stabilizing -- see the analyze step for why this
  feature is not that third format and does not unblock K1). This feature is assigned
  independently (081) rather than derived from a specific backlog letter; it generalizes the
  export-format concern those three neighbours each partially imply.
- **No live-DB, no PBIP, no execution-adapter dependency**: entirely repo-local, deterministic,
  pure-function work; no `db` extra, no DSN, no network needed for any acceptance scenario.
- **Compact-summary "worst status" ordering is a defensible default, not a judgment call**: a
  fixed severity ordering (`blocked` worse than `warning` worse than `pass`/`not_applicable`/
  `not_started`, with an unrecognized token always surfaced rather than silently ranked) is a
  mechanical, reversible convention for this feature to document -- not a business-rule
  decision reserved for a human. `data-model.md` states the ordering explicitly so it is
  reviewable and changeable by ordinary spec amendment, not buried in code.

## Human-Approval Boundaries and Safety Constraints

- This feature does not touch any of the four named-human approval gates (Mapping / Semantic
  Model / Dashboard / Publish Ready). It has no write access to `approvals[]` and cannot move
  any readiness stage.
- It never originates, resolves, or paraphrases a business-rule ruling (grain, rollup, segment)
  or a PII publish-safety ruling; it renders whatever the pack already contains for such a
  field, verbatim (FR-010).
- It never fabricates evidence, a status, or a blocking reason not present in the input pack
  (Edge Cases; SC-002).
- It never emits a numeric confidence/health/maturity score or a completeness tally presented
  as a verdict, in any format (FR-005, FR-006, SC-003) -- this is the feature's single highest
  safety-relevant constraint and the one the analyze step must re-verify hardest.
- STOP conditions: if a required pack field is missing or malformed such that a format cannot
  be rendered faithfully, the exporter surfaces that as an explicit rendering error/blocker in
  its own output (naming the missing/malformed field) rather than guessing a plausible value or
  silently omitting the affected section.

## Evidence Requirements

- Every claim a rendered output makes (a status, an evidence line, a blocking reason, a finding)
  MUST trace to a field already present in the input pack object -- the exporter originates no
  content of its own beyond formatting/labeling (headings, fixed section order, the documented
  schema wrapper fields such as `schema_version`).
- The backwards-compatibility claim (SC-004) MUST be demonstrable from the documented
  compatibility rule plus a concrete worked example in `contracts/`, not asserted without a
  worked case.
