---
name: approval-evidence-pack
description: >-
  Compose one PRE-approval evidence pack for ONE stage gate of ONE table in the
  Seshat BI repo, so a named human can decide a stage approval from a single
  legible, fully-traceable document instead of hunting across scattered artifacts.
  Use when someone asks to "assemble the approval evidence pack", "gather what I
  need to sign the <stage> gate for <table>", or "show the pre-approval evidence
  for this stage". This is a Product Module, artifact-writing: it READS committed
  artifacts only (the per-stage readiness doc, the table's readiness-status.yaml,
  the AL1 assumption signal from the metric contracts, the parked-on map, and the
  pending-contract set), renders the ordered pack for the selected + prior stages,
  surfaces the recorded four-status state / blockers / unresolved assumptions /
  blocking parked-on edges, ends with an EMPTY approval slot the named human fills
  -- then STOPS. A missing or unreadable source is a BLOCKER, never fabricated. It
  writes NO approval, moves NO stage to `pass`, defines NO business meaning, edits
  NO source artifact, runs NO live DB/PBIP read, and emits NO numeric score and NO
  count. Generic across all seven stages via a stage parameter (no C086 specifics).
---

# approval-evidence-pack

- **Roadmap feature:** F035  **On-disk spec:** `specs/063-approval-evidence-pack/`
  (dir 063 == F035; when the dir number and the F-number disagree, the roadmap
  F-number wins).
- **Authority category:** Product Module / `artifact-writing`
  (the F024 enumerated declaration -- see `docs/architecture/product-modules.md`).

Four of the seven readiness stages -- Mapping Ready, Semantic Model Ready,
Dashboard Ready, Publish Ready -- require a NAMED-HUMAN approval the agent is
constitutionally forbidden to grant for itself (Principle V; recorded in each
table's `mappings/<table>/readiness-status.yaml` `approvals[]`). When such a human
is asked to sign a stage gate, the evidence they need is real but SCATTERED: the
per-stage readiness doc says what the gate requires; readiness-status.yaml carries
the four-status state and the open blockers; the AL1 assumption ledger (surfaced
from the metric contracts) may flag an unresolved judgment call; the parked-on map
may show the work is blocked on a shared bottleneck. This skill is the COMPOSER
that assembles those scattered, already-committed artifacts into ONE ordered
PRE-approval pack for one (table, stage). It FILLS the pack; it originates no
evidence and owns no truth. Every line points back at the artifact it came from;
any source that is missing or unfilled is a BLOCKER, never papered over with
invented content. The pack surfaces the gate's readiness picture; it never signs it.

## Boundary against neighbouring shipped work (read first)

- **F028 evidence-pack-generator** (`.claude/skills/evidence-pack-generator/`,
  spec 022) composes a LATE-STAGE, per-table 10-section pack for the Semantic Model
  -> Dashboard -> Publish window only, written to
  `mappings/<table>/evidence-pack-index.md` / `evidence-pack-summary.md`. This
  module is a PRE-approval packet GENERIC across ALL seven stage gates (stage
  parameter), scoped to what ONE gate needs, written to
  `mappings/<table>/approval-evidence-pack-<stage>.md`. It REUSES F028's
  surface-never-assert discipline and empty-approvals rule verbatim in spirit; it
  does NOT edit F028 and does NOT re-render F028's 10 sections.
- **F027 Approval Console** (`.claude/skills/approval-console/`,
  `templates/approval-request.md` / `approval-decision.md`, spec 021) packages ONE
  raised judgment call into a decidable request and TRANSCRIBES a human's answer
  back into the committed artifacts. This module packages a WHOLE-GATE readiness
  picture (many pieces of evidence, not one question) and WRITES NOTHING BACK -- it
  never transcribes an answer, never appends to `approvals[]`. The two compose:
  this pack is the evidence a human reads BEFORE the Approval Console records their
  signature.

This module adds NO new readiness stage and NO new `seshat check` rule -- it
composes results other tools recorded (the F024 Product Module boundary).

## Authority declaration (F024) -- the filled module contract

This module declares EXACTLY ONE of the five F024 authority categories. Quoted
verbatim from `docs/architecture/product-modules.md`: a **Product Module** is "a
focused tool that consumes Core Authority and presents, summarizes, or derives from
it. A module MUST declare exactly one capability level: `read-only` |
`artifact-writing` | `execution-capable`. It never creates truth." This module's
capability level is **`artifact-writing`**: it derives one committed artifact (the
pack) from committed evidence, and -- per the matrix -- MAY write derived evidence
but MUST NOT execute.

The filled `templates/module-contract.md` declaration follows.

---

### Module Contract -- Approval Evidence Pack

- **Authority category:** Product Module
- **Capability level:** `artifact-writing`  *(exactly one)*
- **Product layer:** `6`  *(the functional axis -- see docs/roadmap/roadmap.md; orthogonal to category; sibling of the F028 evidence pack)*
- **Roadmap feature:** `F035`  **On-disk spec:** `specs/063-approval-evidence-pack/`
- **Owner:** the named human who signs the selected stage gate (analyst / metric owner / report owner / data-owner / governance, per the stage)
- **Status:** Authored (docs/templates; no runtime code -- the agent is the runtime)

#### What it does (one line)

> Composes the committed pre-approval evidence for ONE (table, stage) -- gate
> requirements, four-status state for the selected + prior stages, open blockers,
> per-contract unresolved assumptions, blocking parked-on edges, pending contracts
> -- into one ordered pack ending with an EMPTY approval slot, inventing nothing.

#### Core Authority it READS

It reads; it never writes these.

- `docs/readiness/<stage>-ready.md` -- what the selected gate requires and which
  named human (if any) must sign.
- `mappings/<table>/readiness-status.yaml` -- per-stage `status`, `evidence[]`,
  `blocking_reasons[]`, top-level `blocking_reasons[]`, and `approvals[]` (the
  recorded state, blockers, and any already-recorded approval the pack surfaces).
- `mappings/<table>/metrics/*.yaml` -- the metric contracts: the AL1 assumption
  signal surfaced per offending contract (FR-021), and the pending-contract set
  (those whose `readiness.status` is not `pass`, FR-008).
- `docs/quality/parked-on.yaml` -- the parked-on dependency edges; surface any that
  block this table's stage.

#### Derived evidence it WRITES

Composed FROM committed evidence; never a new approval, metric definition, or stage
change.

- `mappings/<table>/approval-evidence-pack-<stage>.md` -- one filled copy of
  `templates/approval-evidence-pack.md` for the selected (table, stage). This is
  the ONLY file the module writes.

#### Approved step it EXECUTES

- none (capability is `artifact-writing`, not `execution-capable`; it composes and
  STOPS, touching no DB and publishing nothing).

#### Forbidden operations (the matrix says NO)

These hold for EVERY Product Module regardless of capability level:

- MUST NOT create truth: no defining/approving business meaning (metric, mapping,
  rollup, segment), no PII publish-safety ruling.
- MUST NOT grant approval, populate the `approvals[]` slot, or move a readiness
  stage to `pass` (named-human / Core Authority only).
- MUST NOT connect to a DB or external service, read a live Power BI/PBIP surface,
  or invoke a deferred execution adapter (F016) or spec-only runtime (F031-F033).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9), and MUST
  NOT emit a completeness / "N of M" count (Clarifications 2026-06-25).

#### How it handles a missing input

When a required Core Authority input is absent, unfilled, a blank template, or
unreadable, the module SURFACES it as a BLOCKER naming the missing/unreadable path
and stops treating that source as content -- it never fabricates the input,
self-approves, or proceeds past the missing gate (Principle V; stop-and-ask).

---

## The input contract (committed-only)

The pack composes EXACTLY these committed sources -- no live DB, no PBIP model, no
Power BI execution adapter (F016), no spec-only runtime (F031-F033), no network.
Any live signal must already be recorded as committed evidence before the pack can
cite it.

1. `docs/readiness/<stage>-ready.md` -- gate requirements (section 1).
2. `mappings/<table>/readiness-status.yaml` -- readiness state + blockers +
   approvals (sections 2, 3, 7).
3. `mappings/<table>/metrics/*.yaml` -- AL1 assumption signal per contract
   (section 4) and the pending-contract set (section 6).
4. `docs/quality/parked-on.yaml` -- blocking parked-on edges (section 5).

## Stage-key -> readiness-doc map (1:1)

| Stage key | Approval gate? | Readiness doc |
|-----------|----------------|---------------|
| `source_ready` | data-owner confirm (proposed semantics/PII) | `docs/readiness/source-ready.md` |
| `mapping_ready` | YES (analyst / governance) | `docs/readiness/mapping-ready.md` |
| `silver_ready` | mechanical (no stage approval) | `docs/readiness/silver-ready.md` |
| `gold_ready` | mechanical (no stage approval) | `docs/readiness/gold-ready.md` |
| `semantic_model_ready` | YES (metric owner) | `docs/readiness/semantic-model-ready.md` |
| `dashboard_ready` | YES (report owner) | `docs/readiness/dashboard-ready.md` |
| `publish_ready` | YES (data-owner / governance) | `docs/readiness/publish-ready.md` |

The four highlighted `approvals[]` gates are `mapping_ready`,
`semantic_model_ready`, `dashboard_ready`, `publish_ready` (readiness-model.md).
`silver_ready` and `gold_ready` are MECHANICAL gates with no stage approval ->
Form C. `source_ready` needs a data-owner confirm of proposed semantics/PII but is
not one of the four highlighted `approvals[]` stages -- surface its recorded state
and any confirm the source records; do not manufacture a fresh `approvals[]` slot
the spine does not define for it.

## Compose steps (numbered; do not reorder)

### 1. Resolve the (table, stage) and read the state
Read `mappings/<table>/readiness-status.yaml`. This is read-only; it fixes the
recorded status of the selected stage and every prior stage, the blockers, and any
recorded `approvals[]`. If the file is MISSING or unreadable, do not fabricate any
status: record a top-level BLOCKER naming the missing path (FR-011) and still
render the pack shell with the approval slot empty.

### 2. Section 1 -- what this gate requires
Open `docs/readiness/<stage>-ready.md` via the map above. Summarise/link its gate
requirements and the required owner/approval. Do NOT re-author the readiness doc;
link and point to it. If it is missing/unreadable -> a BLOCKER naming the path.

### 3. Section 2 -- readiness state (selected + prior only)
List the selected stage and every stage BEFORE it in the seven-stage order, with
each `status` VERBATIM (`not_started | blocked | warning | pass`) and its
`evidence[]` paths. NEVER surface a stage AFTER the selected one (FR-020). Never
assert a status the source does not record (FR-004).

### 4. Section 3 -- open blockers
List every `blocking_reasons[]` entry for the selected stage plus the cross-cutting
top-level `blocking_reasons[]`, each traceable to its source (FR-005). If none are
recorded, say so -- do not read absence-of-a-block as readiness.

### 5. Section 4 -- unresolved assumptions (per contract)
Surface the AL1 assumption-ledger signal from `mappings/<table>/metrics/*.yaml`,
PER offending contract (FR-021): each item names the specific
`mappings/<table>/metrics/<Metric>.yaml` file and the recorded contradiction. Do
NOT re-run or re-implement the AL1 rule (`src/seshat/rules/assumptions.py`); surface
its recorded result only. Do NOT resolve the assumption (Principle V). An
unreadable contract -> a BLOCKER naming the path (FR-011).

### 6. Section 5 -- blocking parked-on edges
Read `docs/quality/parked-on.yaml`; surface any edge that blocks this table's stage,
citing its recorded `blocked`, `parked_on`, `doc`, and `evidence` (FR-007). If none
apply, say so.

### 7. Section 6 -- pending contracts (FR-008, RESOLVED)
List `mappings/<table>/metrics/*.yaml` contracts whose `readiness.status` is not
`pass` (the existing on-disk set, read-only). Do NOT introduce a new per-stage
pending list and do NOT reinterpret the KPI-layer Seeded/Planned markers. For any
business-rule content, LINK-AND-CITE ONLY (see the FR-013 boundary below): cite the
contract path, never paraphrase its grain/rollup/segment/PII ruling. A
missing/unreadable contract -> a BLOCKER (FR-011).

### 8. Section 7 -- the terminal approval slot (exactly one form)
Pick the ONE form that matches the source and delete the other two:
- **Form A (EMPTY slot)** -- the selected stage is an approval gate and
  `approvals[]` has no entry for it: render an empty slot (`owner: ""`, `at: ""`)
  for the named human. The module CANNOT fill it.
- **Form B (RECORDED, read-only)** -- `approvals[]` already records an entry for
  this stage: surface `{ stage, owner, at }` from source; offer NO fresh slot and
  overwrite nothing (FR-016).
- **Form C (NOT APPLICABLE)** -- the stage is a mechanical gate
  (`silver_ready` / `gold_ready`): state "no stage-approval slot applies" and
  surface the mechanical gate result (FR-015) -- do NOT manufacture a human-approval
  seam the spine does not define.

### 9. STOP
Write only `mappings/<table>/approval-evidence-pack-<stage>.md`. Edit no source
artifact. Write no approval, move no stage to `pass`. Any judgment call surfaced in
the pack -- a grain/rollup/segment/PII ambiguity, a source disagreement, the stage
approval itself -- is a stop-and-ask for the named human (Principle V).

## Surface, never assert -- the empty-approvals discipline (reused from F028)

The module is structurally INCAPABLE of writing `approvals[]`, moving a stage to
`pass`, granting an approval, or defining business meaning (FR-009, FR-010). It
DISPLAYS values it read from Core Authority and records nothing back. The terminal
section is one of: an EMPTY slot only the named human fills; a read-only surfacing
of an already-recorded approval; or, for a mechanical gate, a "no stage-approval
applies" statement with the mechanical result. The decision belongs to the named
human via Core Authority; the pack reads-and-displays it.

## No score, no count (hard rule #9)

The pack emits NO numeric confidence / health / maturity value and NO completeness
or "N of M" count. Readiness is expressed ONLY as the four explicit statuses
(`not_started | blocked | warning | pass`) + `evidence[]` + `blocking_reasons[]`
(FR-012). If a score or count is requested, refuse and return the four-status
picture with evidence and blockers.

## Honest-state rules (never invent, never silently reconcile)

| Situation | What the composer does |
|-----------|------------------------|
| `readiness-status.yaml` is missing / unreadable | top-level BLOCKER naming the path; assert no stage status as fact; slot stays empty (FR-011, US2.1) |
| The selected stage status is `not_started` | surface `not_started` as recorded; do NOT treat absence of a block as readiness; slot stays empty (US2.2) |
| A metric contract the ledger references is unreadable | record that unreadable path as a BLOCKER rather than silently dropping it (FR-011, US2.3) |
| The prior stage is not yet `pass` | surface "gate not yet reachable -- prior stage not `pass`" as a blocker; never imply the current gate is signable while an earlier stage is open (edge case) |
| `approvals[]` for the selected stage is ALREADY filled | Form B: surface the recorded approval read-only (owner + date from source); offer NO fresh slot; overwrite nothing (FR-016) |
| The stage is a mechanical gate (`silver_ready` / `gold_ready`) | Form C: "no stage-approval slot applies"; surface the mechanical result (FR-015) |
| A source records a grain / rollup / segment / PII ruling | LINK-AND-CITE ONLY (FR-013): cite the ruling's own recorded text + source path; NEVER paraphrase it into fresh wording; when in doubt, link rather than summarise |
| A numeric confidence/health score or an "N of M" count is requested | refuse; return the four statuses + evidence + blockers (hard rule #9; FR-012) |
| Live data or a PBIP model is requested as a source | out of scope; the composer reads only committed artifacts (FR-002) |

## The FR-013 business-rule / PII boundary -- LINK-AND-CITE ONLY

For any evidence whose underlying artifact records a business-rule ruling (a metric
contract's grain / rollup / segment) or a PII publish-safety ruling, the pack MUST
only LINK and CITE the committed ruling -- it quotes/points at the committed
ruling's own recorded text and its source path and NEVER paraphrases the decision
into new wording that could read as a fresh judgment. The pack emits the citation +
a neutral pointer ("see <path>"), not a restatement; when in doubt it links rather
than summarises. This keeps the named human's business-rule/PII judgment the single
source of truth (Principle V/VII). These rulings do NOT widen the module's write
surface -- it remains structurally incapable of writing `approvals[]` or moving any
stage (FR-009/FR-010).

## Generic only (Principle VII)

The template (`templates/approval-evidence-pack.md`) and any fixed section label
carry NO worked-example (C086 / retail_store_sales) label, grain key, or column
name. C086 appears only as a cited filled instance (see docs/worked-examples/).
The module resolves a generic `mappings/<table>/` path from the table parameter
(FR-014, SC-006). ASCII only, UTF-8 no BOM (use `--` and `->`, no glyphs); short
repo-relative paths (Windows 260-char budget).

## Composes-only proof

After a run, `git status` shows the only new/modified file is the one derived pack
at `mappings/<table>/approval-evidence-pack-<stage>.md`. No source artifact is
modified, `readiness-status.yaml` / `approvals[]` is unchanged, and no stage moved
to `pass`. The skill triggered no `seshat check` / `retail validate` run of its own
and opened no DB connection.

## What the agent must NOT do

- Do NOT invent or fabricate any section's content when its source is missing --
  record a blocker naming the path.
- Do NOT write, grant, or imply an approval; do NOT populate the `approvals[]`
  slot; do NOT move any readiness stage to `pass`.
- Do NOT edit, re-author, or redefine any source artifact (readiness-status.yaml,
  the readiness docs, the metric contracts, the parked-on map).
- Do NOT paraphrase a committed grain / rollup / segment / PII ruling into fresh
  wording (FR-013 -- link and cite only).
- Do NOT emit a numeric confidence / health / maturity score or a completeness
  count.
- Do NOT read a live database or PBIP model; do NOT call the Power BI execution
  adapter (F016) or any spec-only runtime (F031-F033); do NOT publish / deploy.
- Do NOT add a `seshat check` rule, define a new readiness stage, or alter a gate.
- Do NOT surface a stage AFTER the selected one (FR-020).
- Do NOT inline C086 / retail_store_sales specifics into the pack, the template, or
  this doc.

## See also

- The output shape: `../../../templates/approval-evidence-pack.md` (the generic
  copy-me pack).
- The neighbour it composes AFTER, never edits: F028
  `../../../.claude/skills/evidence-pack-generator/SKILL.md` (late-stage 10-section
  pack); the neighbour that records the signature it precedes: F027
  `../../../.claude/skills/approval-console/SKILL.md`.
- The four-status / no-fake-confidence model:
  `../../../docs/readiness/readiness-model.md`; the per-stage gate docs under
  `../../../docs/readiness/`.
- The state artifact it reads: `../../../templates/readiness-status.yaml` (schema);
  the filled copy lives at `mappings/<table>/readiness-status.yaml` (ADR 0004).
- The AL1 assumption signal source: `../../../src/seshat/rules/assumptions.py`
  (surfaced, never re-run). The parked-on map:
  `../../../docs/quality/parked-on.yaml` (DF1).
- The authority contract: `../../../docs/architecture/product-modules.md` (the five
  categories + the matrix), `../../../templates/module-contract.md` (the copy-me
  declaration filled above).
- The spec: `../../../specs/063-approval-evidence-pack/spec.md`. A filled worked
  example lives under `../../../docs/worked-examples/`.

## Orchestration

When a table is driven end-to-end, the conductor may invoke this skill BEFORE a
named-human stage approval (Mapping / Semantic Model / Dashboard / Publish Ready)
to compose the pre-approval pack the human reads. This skill stays single-purpose:
it composes the pack for one (table, stage), surfaces (never asserts) the state,
ends with an empty approval slot, and STOPS at the human approval boundary.
Recording the approval is the Approval Console (F027) / Core Authority, never here.
