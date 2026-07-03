---
name: evidence-pack-generator
description: >-
  Compose a single readable 10-section evidence pack for a table/report at the
  late readiness stages (Semantic Model Ready -> Dashboard Ready -> Publish Ready)
  in the Seshat BI repo. Use when someone asks to "assemble the evidence pack",
  "gather everything for the data-owner sign-off", or "show the full late-stage
  evidence for this table". This is a Product Module, artifact-writing: it READS the
  already-committed upstream artifacts, renders the ordered 10-section pack index +
  one-page summary, records each section's status (one of four) with evidence and
  blockers, and SURFACES the recorded publish_ready state read from
  readiness-status.yaml -- then STOPS. It invents NO section content (a missing or
  unfilled source is a blocker, never fabricated), embeds the shipped F013 handoff
  pack as section 08 without re-authoring it, writes NO approval, moves NO stage to
  pass, edits NO source artifact, runs NO live DB/PBIP read, and emits NO numeric
  confidence/health score.
---

# evidence-pack-generator

- **Roadmap feature:** F028  **On-disk spec:** `specs/022-evidence-pack-generator/`
  (dir 022 == F028; when the dir number and the F-number disagree, the roadmap
  F-number wins).
- **Authority category:** Product Module / `artifact-writing`
  (the F024 enumerated declaration -- see `docs/architecture/product-modules.md`).

By the time a table reaches the late readiness stages its evidence is real but
SCATTERED across a dozen artifacts. A reviewer about to authorize publish has no
single legible place to SEE it all at once, with each claim traceable to its source.
This skill is the COMPOSER that assembles those scattered, already-committed
artifacts into one ordered pack of 10 fixed sections. It FILLS the bundle; it does
not originate the evidence and it owns no truth. Every section points back at the
artifact it summarizes; any section whose source is missing or unfilled is recorded
as a BLOCKER, never papered over with invented content. The pack surfaces the
publish-ready decision; it never makes it.

## Authority declaration (F024) -- the filled module contract

This module declares EXACTLY ONE of the five F024 authority categories. Quoted
verbatim from `docs/architecture/product-modules.md`: a **Product Module** is "a
focused tool that consumes Core Authority and presents, summarizes, or derives from
it. A module MUST declare exactly one capability level: `read-only` |
`artifact-writing` | `execution-capable`. It never creates truth." This module's
capability level is **`artifact-writing`**: it "derives a committed artifact from
committed evidence" (the pack), and -- per the matrix -- MAY write derived evidence
but MUST NOT execute.

The filled `templates/module-contract.md` declaration follows.

---

### Module Contract -- Evidence Pack Generator

- **Authority category:** Product Module
- **Capability level:** `artifact-writing`  *(exactly one)*
- **Product layer:** `6`  *(the functional axis -- see docs/roadmap/roadmap.md; orthogonal to category; sibling of the F013 BI handoff pack)*
- **Roadmap feature:** `F028`  **On-disk spec:** `specs/022-evidence-pack-generator/`
- **Owner:** data-owner / governance reviewer
- **Status:** Authored (docs/templates; no runtime code -- the agent is the runtime)

#### What it does (one line)

> Composes the already-committed late-stage evidence (10 sections across source ->
> publish) into one ordered, readable pack, links every section to its source, and
> surfaces the recorded publish_ready state -- inventing nothing.

#### Core Authority it READS

It reads; it never writes these.

- `mappings/<table>/readiness-status.yaml` -- `current_stage`, per-stage status,
  `approvals[]`, `blocking_reasons[]` (the publish_ready state + recorded approval
  the summary surfaces).
- The 10 committed section sources (see the section contract below): source-profile,
  source-map.yaml, assumptions.md / unresolved-questions.md / ADRs, the
  `mappings/<table>/metrics/` contracts, the recorded `retail check` / `retail
  validate` results + F012 roll-up, the F010 semantic-model summary, the F011/F011A
  dashboard design, the FILLED F013 handoff pack, `data-issues.md`, and the F015
  reconciliation ledger (+ F014 drift).

#### Derived evidence it WRITES

Composed FROM committed evidence; never a new approval, metric definition, or stage
change.

- `mappings/<table>/evidence-pack-index.md` -- the ordered 10-section index (a filled
  copy of `templates/evidence-pack-index.md`).
- `mappings/<table>/evidence-pack-summary.md` -- the one-page readiness summary (a
  filled copy of `templates/evidence-pack-summary.md`).

#### Approved step it EXECUTES

- none (capability is `artifact-writing`, not `execution-capable`; it composes and
  STOPS, touching no DB and publishing nothing).

#### Forbidden operations (the matrix says NO)

These hold for EVERY Product Module regardless of capability level:

- MUST NOT create truth: no defining business meaning, no approving a metric/mapping.
- MUST NOT grant approval or move a readiness stage to `pass` (named-human / Core
  Authority only).
- MUST NOT connect to a DB or external service, and MUST NOT publish a Power BI
  artifact (those are Execution Adapter capabilities -- F016 owns publish).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9), and MUST NOT
  emit a completeness count (Clarifications 2026-06-25).

#### How it handles a missing input

When a required Core Authority input is absent or a stage is not yet `pass`, the
module SURFACES it as a blocker and stops -- it never fabricates the input,
self-approves, or proceeds past the missing gate (Principle V; stop-and-ask). A
missing/unfilled/blank-template section source -> that section is `blocked` with a
`blocking_reasons[]` entry naming the missing source.

---

## Scope boundary (read first)

- **Composes, never invents.** Every section is a SUMMARY or REFERENCE of an existing
  committed artifact. It adds no data, metric, decision, or number the source does not
  contain. A section whose source is missing/unfilled/blank-template is recorded as a
  `blocked` status with a blocker naming the missing source -- never fabricated.
- **Surfaces, never asserts (publish).** The summary SURFACES the `publish_ready`
  status and the recorded approval (owner + date) READ from `readiness-status.yaml`.
  It DISPLAYS a value it read from Core Authority and records nothing back: it never
  writes an approval, never edits `approvals[]`, never moves a stage to `pass`. It
  prints a publish-ready CLAIM only when `publish_ready: pass` with a named approval
  is recorded. (This is the F028 boundary: it reads-and-displays the decision -- it
  does NOT transcribe a fresh decision and it does NOT make one.)
- **Consumes F013, never redefines it.** Section 08 references/embeds the table's
  FILLED `templates/handoff/bi-handoff-pack.md` instance and links to it. F028 never
  edits that instance, never re-authors the F013 template, and never records the
  publish approval (F013 / Core Authority owns that). If the handoff is missing or
  incomplete, section 08 is a BLOCKER -- no substitute handoff is synthesized.
- **Reads only committed artifacts.** No live database, no PBIP model, no Power BI
  execution adapter (F016), no publish/deploy. Any live signal must already be
  recorded as committed evidence (e.g. by `retail validate`) before the pack can cite
  it.
- **Adds no gate.** It runs no new validator, adds no `retail check` rule, defines no
  new readiness stage. It composes results other tools already recorded.
- **No fake confidence, no count.** Readiness is the four explicit statuses
  (`not_started` / `blocked` / `warning` / `pass`) + `evidence[]` +
  `blocking_reasons[]`. No numeric confidence/health score anywhere (hard rule #9);
  no "N of 10 sections present" tally (the four-status per-section record plus the
  rolled-up blockers convey completeness -- Clarifications 2026-06-25).
- **Generic.** No worked-example specifics (billing codes, segments, PII column names,
  per-table grain keys). C086 is a cited filled instance, never baked in (Principle
  VII). ASCII only, UTF-8 no BOM; short repo-relative paths (Windows MAX_PATH).

## The 10-section contract (fixed, ordered) and its committed source map

The section list and order are a stable contract so packs are comparable across
tables. Each section is COMPOSED from the committed source on its right and links
back to that source's repo-relative path.

| # | Section | Composed from (committed source) |
|---|---------|----------------------------------|
| 01 | source-profile | the table's `source-profile.md` (Source Ready) |
| 02 | source-map-summary | `source-map.yaml` (the Principle-IV mapping-gate artifact; F008 consumes it, does not produce it) |
| 03 | assumptions-and-decisions | `assumptions.md` + `unresolved-questions.md` + relevant ADRs |
| 04 | metric-contracts | `mappings/<table>/metrics/` filled contracts (F009/F010) |
| 05 | validation-summary | recorded `retail check` + `retail validate` results + the F012 data-quality roll-up |
| 06 | semantic-model-summary | F010 / `retail semantic check` recorded output |
| 07 | dashboard-summary | F011 dashboard design + F011A visual foundation |
| 08 | handoff-pack | the table's FILLED F013 `templates/handoff/bi-handoff-pack.md` instance (EMBED / reference; never re-authored) |
| 09 | known-limitations | `data-issues.md` + recorded caveats |
| 10 | release-notes | F015 reconciliation ledger (+ F014 drift signals + `readiness-status.yaml` `approvals[]`) |

Even release notes (10) COMPOSE existing evidence -- they never invent.

## Per-section record shape

Each section row carries: section id + title; `status` (one of `not_started` /
`blocked` / `warning` / `pass`); source artifact path(s); `evidence[]`;
`blocking_reasons[]`; and a one-line summary. Rules:

- A missing / unfilled / blank-template source -> `status: blocked` + a
  `blocking_reasons[]` entry naming the missing source. NO fabricated content.
- A source that exists but is `warning` upstream -> the section carries that
  `warning` verbatim; it does NOT auto-promote to `pass`.
- No numeric confidence/health score and no completeness count anywhere.

## Procedure (numbered; do not reorder)

### 1. Resolve the table and read the state
Read `mappings/<table>/readiness-status.yaml` -- `current_stage`, per-stage status,
`approvals[]`, `blocking_reasons[]`. This is read-only; it fixes the current stage the
summary states and the publish_ready state the summary surfaces.

### 2. Compose the 10 sections in fixed order
For each section 01..10, locate its committed source (the map above). If the source
exists and is FILLED, compose a one-line summary and record the section path + status
+ evidence. If the source is missing / unfilled / a blank template, record the section
`blocked` with a blocker naming the missing source -- do NOT synthesize content. Carry
any upstream `warning` verbatim; never auto-promote it.

### 3. Embed F013 as section 08 (consume, never redefine)
Reference / embed the table's FILLED `mappings/<table>/handoff/bi-handoff-pack.md`
instance and link to it. Never edit it, never re-author the F013 template, never
record the publish approval. If it is missing or incomplete, section 08 is a blocker.

### 4. Render the index
Render `templates/evidence-pack-index.md` filled: one row per section with id+title,
status, source path(s), evidence, blockers, one-line summary. Every present section
resolves to a real committed artifact path; every absent one resolves to a recorded
blocker. No section originates from nothing.

### 5. Render the summary (surface, never assert)
Render `templates/evidence-pack-summary.md` filled: the current readiness stage; the
`publish_ready` status SURFACED from `readiness-status.yaml`; the recorded approval
(owner + date) when `publish_ready: pass`; the rolled-up open blockers across sections;
and an explicit "in-progress" marker when composed before Publish Ready. Print a
publish-ready CLAIM ONLY when `publish_ready: pass` + a named recorded approval exist.

### 6. STOP
Stop at the composition boundary. The skill wrote only the derived index + summary
under `mappings/<table>/`. It wrote no approval, moved no stage to `pass`, and edited
no source artifact (including the F013 handoff). Any judgment call -- publish
authorization, a source disagreement, a grain/PII/sentinel ambiguity surfaced in the
pack -- is a stop-and-ask for the named human (Principle V).

## In-progress posture (US4)

The pack is composable from Semantic Model Ready (stage 5) onward, not only at the
final gate. When composed early: present sections render and link; absent downstream
sections (e.g. 07 dashboard, 08 handoff) are recorded as blockers; the summary states
the table's CURRENT stage honestly and claims no stage the table has not reached. An
in-progress pack NEVER prints a publish-ready claim (the US3 guardrail is not weakened
by the US4 posture).

## Surface, never assert -- the publish-ready guardrail (US3)

| Read state in readiness-status.yaml | What the summary does |
|-------------------------------------|------------------------|
| `publish_ready: pass` + a named approval in `approvals[]` | surfaces the recorded approval (owner + date), cites `readiness-status.yaml` as the source, MAY state publish-ready |
| `publish_ready` is anything else (`not_started` / `blocked` / `warning`) | shows publish-ready as that status with the upstream blocking reasons -- MUST NOT print a publish-ready claim |

In every case the generator has written NO approval, moved NO stage to `pass`, and
edited NO source artifact -- it only wrote the derived pack. The decision belongs to
the named human via Core Authority; the pack reads-and-displays it.

## Honest-state rules (never invent, never silently reconcile)

| Situation | What the generator does |
|-----------|--------------------------|
| A section source is missing / unfilled | record that section `blocked` with a blocker naming the source; the summary cannot read "complete"; no substitute content |
| A source exists but is the blank template, not a filled instance | treat as missing -> `blocked`; do not summarize placeholder text as real evidence |
| F013 handoff (section 08) is incomplete | record section 08 a blocker; do not synthesize a substitute handoff or re-author F013's template |
| Two upstream sources disagree (e.g. a contract count differs between the metric store and the semantic-model summary) | surface BOTH with their source links and record the discrepancy as a `warning` for human resolution (Principle V); do NOT pick a winner or reconcile silently |
| A numeric confidence/health score (or an "N of 10" count) is requested | refuse; return the four explicit statuses + evidence + blockers (hard rule #9; Clarifications 2026-06-25) |
| Live data or a PBIP model is requested as a section source | out of scope; the generator reads only committed artifacts |

## Composes-only proof

After a run, `git status` shows the only new/modified files are the two derived pack
files under `mappings/<table>/` (`evidence-pack-index.md`, `evidence-pack-summary.md`).
No source artifact is modified, `readiness-status.yaml` / `approvals[]` is unchanged,
and no stage moved to `pass`. The skill triggered no `retail check` / `retail validate`
run of its own and opened no DB connection.

## What the agent must NOT do

- Do NOT invent or fabricate any section's content when its source is missing.
- Do NOT write, grant, or imply a publish approval; do NOT move any readiness stage to
  `pass`; do NOT edit `approvals[]`.
- Do NOT edit, re-author, or redefine any source artifact (including the F013 handoff).
- Do NOT emit a numeric confidence / health score or a completeness count.
- Do NOT read a live database or PBIP model; do NOT call the Power BI execution adapter
  (F016); do NOT publish / deploy.
- Do NOT add a `retail check` rule, define a new readiness stage, or alter a gate.
- Do NOT silently reconcile disagreeing sources or choose a winner (Principle V).
- Do NOT inline C086 / retail_store_sales specifics into the pack, the templates, or
  the doc.

## See also

- The tool doc (10-section contract + source map + ops + F013 delta):
  `../../../docs/tools/evidence-pack-generator.md`.
- The output shapes: `../../../templates/evidence-pack-index.md`,
  `../../../templates/evidence-pack-summary.md`.
- The F013 handoff it consumes as section 08: `../../../templates/handoff/bi-handoff-pack.md`
  (scope delta: F028 consumes F013, never redefines it).
- The four-status / no-fake-confidence model: `../../../docs/readiness/readiness-model.md`;
  the publish stage authority: `../../../docs/readiness/publish-ready.md`.
- The authority contract: `../../../docs/architecture/product-modules.md` (the five
  categories + the matrix + the two sub-vocabularies),
  `../../../docs/architecture/core-vs-modules-and-adapters.md` (the prose + the seam),
  `../../../templates/module-contract.md` (the copy-me declaration filled above).
- The spec: `../../../specs/022-evidence-pack-generator/spec.md`. It cites a filled
  worked example under `../../../docs/worked-examples/`.

## Orchestration

When a table is driven end-to-end, the `retail-orchestrate` conductor may invoke this
generator at the late stages (Semantic Model Ready onward) to compose the evidence
pack for the data-owner review. This skill stays single-purpose: it composes the pack,
records per-section status + blockers, surfaces (never asserts) the publish state, and
STOPS at the human approval boundary. Advancing a stage, clearing a blocker, and
recording the publish approval live in the per-table owner / Core Authority, never
here.
