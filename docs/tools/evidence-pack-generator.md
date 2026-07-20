# Tool -- Evidence Pack Generator

- **Status:** Runtime preview slice shipped: `retail evidence-pack` emits a
  read-only JSON/text 10-section evidence-pack preview. Markdown artifact-writing
  remains the agent-led workflow described below.
- **Roadmap feature:** F028  **On-disk spec:** `specs/022-evidence-pack-generator/`
  (dir 022 == F028; when the dir number and the F-number disagree, the roadmap
  F-number wins).
- **Authority category:** Product Module / `artifact-writing` (the F024 enumerated
  declaration -- see `../architecture/product-modules.md`).
- **Read with:** the skill `../../.claude/skills/evidence-pack-generator/SKILL.md`
  (the invoke-and-compose verb), the two output templates
  `../../templates/evidence-pack-index.md` and `../../templates/evidence-pack-summary.md`,
  the filled module declaration `../../templates/module-contract.md`.

## What it does (one line)

> Composes the already-committed late-stage evidence (10 fixed sections across source
> -> publish) into one ordered, readable pack for a `<schema>.<table>`, links every
> section to its committed source, and surfaces the recorded `publish_ready` state --
> inventing nothing, asserting nothing, owning no truth.

## Why it exists

By the time a table or report reaches the late readiness stages (Semantic Model Ready
-> Dashboard Ready -> Publish Ready), its evidence is real but SCATTERED across a dozen
artifacts: the source profile, the map summary, the decisions, the metric contracts,
the validation results, the semantic-model summary, the dashboard plan, the F013
handoff bundle, the known caveats, and the cross-time reconciliation ledger. A reviewer
or data-owner about to authorize publish has no single legible place to SEE all of it
at once, with each claim traceable to its source.

The generator is the COMPOSER that assembles those scattered, already-committed
artifacts into one ordered pack of 10 fixed sections. It FILLS the bundle; it does not
originate the evidence and it owns no truth. Every section points back at the artifact
it summarizes; any section whose source is missing or unfilled is recorded as a
BLOCKER, never papered over. The pack surfaces the publish-ready decision; it never
makes it.

## CLI preview

```bash
retail evidence-pack --table retail_store_sales
retail evidence-pack --table bronze.retail_store_sales --format json
```

The CLI preview reads committed artifacts and returns the 10-section shape as
data. It writes no `evidence-pack-index.md`, writes no
`evidence-pack-summary.md`, edits no source artifact, runs no validator, and
records no approval. Use it as the agent-facing audit surface before deciding
whether to produce the derived markdown pack.

## Authority posture (F024) -- the filled module contract

This module declares EXACTLY ONE of the five F024 authority categories. A **Product
Module** (verbatim, `../architecture/product-modules.md`) is "a focused tool that
consumes Core Authority and presents, summarizes, or derives from it... It never
creates truth." Its capability level here is **`artifact-writing`** -- it "derives a
committed artifact from committed evidence" (the pack) and per the matrix MAY write
derived evidence but MUST NOT execute.

| F024 capability | Core Authority | ... | Product Module | ... |
|-----------------|:--:|:--:|:--:|:--:|
| Reads committed evidence | yes | -- | yes | -- |
| Summarizes / visualizes evidence | yes | -- | yes | -- |
| Writes DERIVED evidence (report, signal) | n/a | -- | only if `artifact-writing` | -- |
| Executes an APPROVED step | n/a | -- | only if `execution-capable` (this module is NOT) | -- |
| **CREATES truth** (business meaning, metric, mapping) | **yes** | -- | no | -- |
| **GRANTS approval** / moves a stage to `pass` | **yes (named human)** | -- | no | -- |

The full copy-me declaration lives, filled, inside the skill
(`../../.claude/skills/evidence-pack-generator/SKILL.md`) under "Authority declaration
(F024) -- the filled module contract"; the blank template is
`../../templates/module-contract.md`. In short: capability `artifact-writing`; product
layer 6 (sibling of the F013 handoff pack); reads `readiness-status.yaml` + the 10
section sources; writes the derived index + summary under `mappings/<table>/`; executes
no step; creates no truth; grants no approval.

## The 10-section contract (fixed, ordered) and its committed source map

The section list and order are a STABLE contract so packs are comparable across tables.
Each section is COMPOSED from the committed source on its right and links back to that
source's repo-relative path. The pack composes; it invents no section content.

| # | Section | Composed from (committed source) |
|---|---------|----------------------------------|
| 01 | source-profile | the table's `source-profile.md` (Source Ready) |
| 02 | source-map-summary | `source-map.yaml` (the Principle-IV mapping-gate artifact; F008 consumes it, does not produce it) |
| 03 | assumptions-and-decisions | `assumptions.md` + `unresolved-questions.md` + relevant ADRs |
| 04 | metric-contracts | `mappings/<table>/metrics/` filled contracts (F009/F010) |
| 05 | validation-summary | recorded `seshat check` + `retail validate` results + the F012 data-quality roll-up |
| 06 | semantic-model-summary | F010 / `retail semantic check` recorded output |
| 07 | dashboard-summary | F011 dashboard design + F011A visual foundation |
| 08 | handoff-pack | the table's FILLED F013 `templates/handoff/bi-handoff-pack.md` instance (EMBED / reference; never re-authored) |
| 09 | known-limitations | `data-issues.md` + recorded caveats |
| 10 | release-notes | F015 reconciliation ledger (+ F014 drift signals + `readiness-status.yaml` `approvals[]`) |

Even release notes (10) COMPOSE existing evidence -- they never invent. The index
renders one row per section; the summary rolls up the open blockers and surfaces the
publish state. See `../../templates/evidence-pack-index.md` and
`../../templates/evidence-pack-summary.md`.

## The missing-source-is-a-blocker rule (the integrity guarantee)

A composer that fills gaps with invented content is worse than no composer -- it ships
unstated fiction to a decision-maker. So:

- Any section whose source artifact is missing, unfilled, or still a blank template is
  recorded as `blocked` with a `blocking_reasons[]` entry NAMING the missing source.
  The generator MUST NOT fabricate substitute content (no invented profile rows,
  contracts, totals, or summaries).
- A blank template counts as a missing source -- placeholder text is never summarized
  as if it were real evidence.
- A source that exists but is `warning` upstream is carried verbatim as `warning`; it
  does NOT auto-promote to `pass`.
- Where two upstream sources disagree, BOTH are surfaced with their source links and
  the discrepancy is recorded as a `warning` for human resolution (Principle V) -- the
  generator never picks a winner or reconciles silently.

Each section carries one of the four explicit statuses (`not_started` / `blocked` /
`warning` / `pass`) + `evidence[]` + `blocking_reasons[]`. No numeric confidence/health
score, and no "N of 10 sections present" completeness tally, is emitted anywhere (hard
rule #9; Clarifications 2026-06-25 -- the four-status per-section record plus the
rolled-up blockers convey completeness).

## Surface, never assert -- the publish-ready guardrail

The late-stage pack exists to support a publish decision. If it could assert "ready to
publish" without the recorded `pass` + approval, it would manufacture authority the
module does not have (Core Authority / Principle V). So the summary:

- SURFACES the `publish_ready` status and the recorded approval (owner + date) READ
  from `readiness-status.yaml`, citing it as the source.
- DISPLAYS a value it read from Core Authority and records NOTHING back: it never writes
  an approval, never edits `approvals[]`, never moves a stage to `pass`, never edits any
  source artifact.
- Prints a publish-ready CLAIM ONLY when `publish_ready: pass` with a named human
  approval is recorded. In every other case it shows the upstream blocking reasons --
  never a claim.

This is sharper than transcription: F028 reads-and-displays the decision the named
human already recorded; it does not transcribe a fresh decision (that is F027's
posture) and it never makes the decision itself.

## Relationship to shipped F013 (scope delta -- one-directional)

F013 (BI Handoff Pack, shipped) and F028 both "compose existing evidence," so the
boundary is stated sharply:

- **F013 = the handoff TEMPLATE.** It defines the shape and content of the one bundle a
  BI consumer receives at Publish Ready, and it OWNS the recorded publish approval (the
  named-human sign-off in `readiness-status.yaml` `approvals[]`). It lives at
  `../../templates/handoff/bi-handoff-pack.md` + `handoff-review-checklist.md`.
- **F028 = the GENERATOR / COMPOSER.** It assembles the FULL 10-section evidence pack
  across all upstream stages and EMBEDS F013's filled handoff bundle as section 08.
- **The relationship is one-directional: F028 consumes F013, never redefines it.**
  Section 08 references/includes the table's filled `bi-handoff-pack.md` instance and
  links to it. F028 never edits that instance, never re-authors the handoff template,
  and never records the publish approval (F013 / Core Authority does that). If the F013
  handoff is missing or incomplete, F028 records section 08 as a BLOCKER -- it does not
  synthesize a substitute handoff.

In one line: F013 is what a complete handoff looks like; F028 is the tool that gathers
everything (including that handoff) into one traceable pack and tells you, section by
section, what is present and what is still blocking.

## In-progress posture

The pack is composable from Semantic Model Ready (stage 5) onward, not only at the final
gate. When composed early: present sections render and link; absent downstream sections
(e.g. 07 dashboard, 08 handoff) are blockers; the summary states the table's CURRENT
stage honestly and claims no stage the table has not reached. An in-progress pack NEVER
prints a publish-ready claim -- the in-progress posture does not weaken the guardrail.

## Allowed operations

- READ committed upstream artifacts (the 10 section sources) and `readiness-status.yaml`.
- SUMMARIZE and LINK each section to its committed source.
- WRITE the DERIVED evidence pack (index + summary) as a composed artifact under
  `mappings/<table>/`.
- RECORD per-section status (`pass` / `warning` / `blocked` / `not_started`) with
  `evidence[]` + `blocking_reasons[]`.
- EMBED / reference the F013 filled handoff pack as section 08.
- SURFACE the recorded `publish_ready` status and approval (read-only).

## Forbidden operations

- Inventing or fabricating any section's content when its source is missing.
- Writing, granting, or implying a publish approval; moving any readiness stage to
  `pass`; editing `approvals[]`.
- Editing, re-authoring, or redefining any source artifact (including the F013 handoff).
- Emitting a numeric confidence / health score, or a completeness count (hard rule #9;
  Clarifications 2026-06-25).
- Reading a live database or PBIP model; calling the Power BI execution adapter (F016).
- Publishing / deploying to any workspace or Fabric.
- Adding a `seshat check` rule, defining a new readiness stage, or altering a gate.
- Silently reconciling disagreeing sources or choosing a winner (Principle V).
- Inlining C086 / retail_store_sales specifics into the generic skill, doc, or templates.

## Where the filled outputs live

Per-table FILLED packs live under `mappings/<table>/` -- the established per-table
working-set home (ADR 0003 / constitution v1.5.0), NOT a new top-level `packs/` dir
(Clarifications 2026-06-25; cheaply reversible -- a path move):

- `mappings/<table>/evidence-pack-index.md` (a filled copy of
  `../../templates/evidence-pack-index.md`).
- `mappings/<table>/evidence-pack-summary.md` (a filled copy of
  `../../templates/evidence-pack-summary.md`).

The pack export format is markdown only (the index + summary); any additional rendered
form is a later additive slice (hard rule #8; Clarifications 2026-06-25).

## Composes-only proof

After a run, `git status` shows the only new/modified files are the two derived pack
files under `mappings/<table>/`. No source artifact is modified, `readiness-status.yaml`
/ `approvals[]` is unchanged, and no stage moved to `pass`. The module ran no validator
of its own and opened no DB connection.

## See also

- The skill (the invoke-and-compose verb):
  `../../.claude/skills/evidence-pack-generator/SKILL.md`.
- The output templates: `../../templates/evidence-pack-index.md`,
  `../../templates/evidence-pack-summary.md`.
- The F013 handoff embedded as section 08: `../../templates/handoff/bi-handoff-pack.md`
  (scope delta above; F028 consumes F013, never redefines it).
- The authority contract: `../architecture/product-modules.md` (the five categories +
  the matrix + the two sub-vocabularies), `../architecture/core-vs-modules-and-adapters.md`
  (the prose + the seam), `../../templates/module-contract.md` (the copy-me declaration).
- The four-status / no-fake-confidence model: `../readiness/readiness-model.md`; the
  publish stage authority: `../readiness/publish-ready.md`.
- The spec: `../../specs/022-evidence-pack-generator/spec.md`. For a cited filled
  instance, see a filled worked example under `../worked-examples/`.
