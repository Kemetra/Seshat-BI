---
name: release-notes-generator
description: >-
  Draft an evidence-backed per-release note and assess the kit's honest maturity
  ladder for a shipped roadmap slice in the Seshat BI repo. Use when someone asks
  to "generate the release notes", "what maturity level is the kit at", "assess the
  kit's maturity", or "record what became possible in this release". This is
  Maintenance Automation (F024): it runs as the conductor's post-milestone read, not
  per a per-run human trigger. It READS the F028 evidence pack + the F032
  compatibility matrix + the roadmap ledger, DRAFTS the seven release-note blocks
  with every capability claim cited, ASSESSES the seven evidence-gated maturity rungs
  (L0..L6) by a BINARY evidence test each, reports the level as the highest
  all-evidence-present rung, and then STOPS for the named release owner. It emits NO
  numeric / maturity / confidence score (the ladder is milestones, not a score),
  re-measures NOTHING (no seshat check/validate, no DB, no powerbi/ read),
  self-approves NO release, self-confirms NO level, and publishes nothing.
---

# release-notes-generator

- **Roadmap feature:** F033  **On-disk spec:** `specs/027-release-maturity-management/`
  (dir 027 == F033; when the dir number and the F-number disagree, the roadmap
  F-number wins).
- **Authority category:** Maintenance Automation (the F024 enumerated declaration --
  see `docs/architecture/product-modules.md`). NO connectivity level and NO
  capability level: those sub-axes belong to Execution Adapters and Product Modules;
  Maintenance Automation carries neither (its boundary is prose).

The kit ships in slices. Each slice changes WHAT THE KIT CAN DO, but the kit has no
durable, reviewable record of "what became possible in this release, and how mature is
the capability". Today that answer lives only in commit messages and the roadmap's
delivered ledger. This skill is the record: it DRAFTS a per-release note (seven
required blocks) and ASSESSES an evidence-gated maturity ladder. It composes evidence
others already recorded; it originates none of it and owns no truth. A maturity claim
is exactly where a tool is tempted to round "two worked examples" up to "production
ready"; the kit's no-fake-confidence rule (hard rule #9) forbids that, so the ladder is
an evidence-gated MILESTONE ladder -- not a score -- and the skill drafts-and-stops for
a named release owner to approve.

## Authority declaration (F024) -- Maintenance Automation (no sub-axis)

This skill declares EXACTLY ONE of the five F024 authority categories. Quoted verbatim
from `docs/architecture/product-modules.md`, **Maintenance Automation** is:

> a tool that runs WITHOUT a per-invocation human trigger (scheduled / CI), emits ONLY
> derived evidence (a report, a drift signal, a recomputed index), never creates truth,
> and never self-approves. This is the novel category: it is distinguished from a
> human-invoked Module by the absence of a per-run human trigger. The schedule itself --
> and the evidence it runs on -- is a prior named-human action, so this does NOT relax
> Principle V.

Maintenance Automation is the ONLY non-Core category with **no parallel sub-axis** (a
Module pins a capability level, an Adapter pins a connectivity level; "the other three
categories carry no parallel sub-axis -- their boundary is prose"). So there is no
module-contract / adapter-contract to fill for F033; the declaration is this prose
section plus the matrix column below.

This skill's authority row, quoted verbatim from the F024 authority matrix (the
Maintenance Automation column):

| Capability | Maintenance Automation |
|------------|:--:|
| Reads committed evidence | yes |
| Summarizes / visualizes evidence | yes |
| Writes DERIVED evidence (report, signal) | yes |
| Executes an APPROVED step | yes (scheduled) |
| Connects to a DB / external service | no (if it must connect out, the seam makes it an Adapter) |
| Publishes a Power BI artifact | no |
| **CREATES truth** (business meaning, metric, mapping) | **no** |
| **GRANTS approval** / moves a stage to `pass` | **no** |

In short: this skill reads committed evidence, summarizes it, and writes DERIVED
evidence (the release note + the maturity report). It declares NO connectivity level
(it never connects to a DB or external service -- if it ever had to, the seam would make
it an Adapter, not this category) and NO capability level (that axis is a Module's). It
CREATES no truth and GRANTS no approval; both belong to a named human via Core Authority
(Principle V). It is the conductor's product-level read AFTER a milestone, not a per-run
human-triggered Module -- the prior named-human actions are the schedule and the
already-committed evidence it runs on, so the category fits and Principle V is intact.

## The two load-bearing boundaries (carried verbatim; do not drift)

### Boundary 1 -- No fake confidence: the ladder is MILESTONES, not a score

The maturity ladder is an EVIDENCE-GATED MILESTONE ladder -- a binary "this evidence
exists or it does not" test per rung, level = the HIGHEST rung whose required evidence
ALL exists -- structurally the same kind of artifact as the seven numbered readiness
stages (`docs/readiness/readiness-model.md`), which are legitimate milestones, NOT
scores. The numbered rungs L0..L6 are milestone names, exactly like the numbered
readiness stages; the number is an ordinal milestone, never a quantity.

This skill MUST NOT emit a percentage, a 0-100 health number, an average, or ANY number
that reads as confidence (hard rule #9). A rung is reported as `achieved (evidence: ...)`
or `not achieved (missing: ...)` -- never "73% mature". If asked for a numeric maturity
score, the skill DECLINES, cites hard rule #9, and returns the rung verdicts + cited
evidence instead.

A rung is BINARY -- achieved or not achieved. Partial evidence (one worked example
complete, the second mid-build) is "not achieved" with the missing piece named; it is
never rounded up. The ladder does NOT use the four readiness statuses
(`not_started`/`blocked`/`warning`/`pass`) -- those are the per-table readiness spine's
vocabulary; a rung is a two-valued milestone verdict.

### Boundary 2 -- Consume, never re-measure; never self-approve

This skill READS the F028 evidence pack, the F032 compatibility matrix, the committed
roadmap ledger + commit refs, the worked-example docs, and the on-disk presence of
adapters/projects. It DRAFTS the note and ASSESSES the rung from that committed
evidence. It NEVER:

- runs `seshat check` / `retail validate`, profiles a source, opens a DB connection, or
  reads `powerbi/` (it consumes recorded results; it re-measures nothing). A missing
  input is recorded as "evidence not available", never fabricated.
- self-approves a release (`draft -> approved` is a named release owner recorded in
  `approvals[]`), self-confirms a level, or publishes (tags / GitHub releases / registry
  pushes are out of scope -- release execution stays a human action).
- moves any readiness stage to `pass` or adds any gate / `seshat check` rule / CLI verb /
  validator. Release & maturity is a product-level process orthogonal to the per-table
  readiness spine; it advances no stage.

## Inputs it CONSUMES (referenced by role; never re-measured)

| Input | Role here | Status |
|-------|-----------|--------|
| F028 evidence pack (`docs/tools/evidence-pack-generator.md`; `.claude/skills/evidence-pack-generator/SKILL.md`; the table's filled `mappings/<table>/evidence-pack-*.md`) | the committed evidence behind each "what became possible" claim and each rung verdict | built; consume freely |
| F032 compatibility matrix (planned `docs/operations/adapter-compatibility-matrix.md`; `templates/adapter-version-record.md`) | cited for "what changed" + "migration notes"; never recomputed | referenced by id + role -- if not yet on disk, record "consumed input not yet available", do not fabricate its rows |
| the delivered roadmap ledger (`docs/roadmap/roadmap.md`) + commit refs | the release history of record (one note maps 1:1 to the delivered-ledger row it summarizes) | committed |
| worked-example docs + on-disk presence (`docs/worked-examples/retail-store-sales.md`; `mappings/retail_store_sales/`) | the evidence the L1/L2/L3 binary tests check, and the absence the L4/L5/L6 tests check | committed |

It IMPORTS none of these; it READS them. If an input is missing, the rule is "evidence
not available -- cannot assert capability", never a fabricated claim or row.

## The two output artifacts (two files, two purposes -- never merged)

| Artifact | From template | Purpose | Lifecycle |
|----------|---------------|---------|-----------|
| Release note | `templates/release-notes.md` | per-RELEASE record: what became possible in release N (seven blocks) | `draft` until a named release owner approves |
| Maturity report | `templates/maturity-report.md` | point-in-time ladder SNAPSHOT: how mature is the kit, by evidence (seven rungs) | a snapshot; the reported level is the named release owner's to confirm |

A "release" is one shipped roadmap F-slice keyed by its roadmap F-number. Filled,
approved sets live under `docs/releases/<F-number>/` (e.g. `docs/releases/F033/`), one
set per release -- the per-release record (parallel to `docs/roadmap/` the delivered
ledger). A batch (e.g. F024-F033) is recorded as a GROUP of per-slice notes, never one
merged note. `docs/releases/` is the DESCRIBED output home; this skill drafts into it
and a human approves -- the skill does not create the dir or any approved instance.

## The seven release-note blocks (the per-release record)

The note MUST contain all seven blocks, in order. Every "what became possible" claim
MUST cite the committed evidence behind it (a file/commit, or the cited F028 pack entry);
a claim with no traceable source is a defect.

| # | Block | Sourced from | Citation rule |
|---|-------|--------------|---------------|
| 1 | what became possible | the F028 evidence pack for the slice + the delivered-ledger row | each line cites the committed evidence that makes it true; an UNSUPPORTED capability is omitted here (and, if relevant, listed under "known limitations -- not yet evidenced"), never asserted |
| 2 | what changed | the F032 compatibility matrix rows + commit refs | cite the matrix row / commit; never recompute the matrix |
| 3 | readiness stages affected | the per-table `readiness-status.yaml` deltas this slice produced (or "none" -- release/maturity advances no stage) | name the stage + the evidence; this skill records the delta, it does not move a stage |
| 4 | new modules / adapters | the F024 declarations of the slices in this release | name each + its authority category + sub-axis (if any) |
| 5 | known limitations | the not-achieved maturity rungs + recorded caveats | MUST list at least the unbuilt rungs (L4 dbt, L5 Dagster, L6 Power BI execution today) |
| 6 | migration notes | the F032 compatibility matrix (version ranges / required smoke tests) | cite the matrix; "evidence not available" if the matrix is not yet on disk |
| 7 | next best slice | the roadmap's next undelivered row | name it; recommend, do not commit -- sequencing is the owner's call |

Plus the note's `status` (`draft` / `approved`) and `approvals[]` (named release owner +
date). The skill produces it as `status: draft -- awaiting release-owner approval`; it
has approved nothing.

## The seven-rung evidence-gated maturity ladder (the honesty core)

Exactly seven rungs, each with a BINARY evidence test. The reported level is the HIGHEST
rung whose required evidence ALL exists; rungs above that are reported NOT achieved with
the exact missing artifact named. Rung order is a capability-evidence milestone
narrative, independent of the roadmap's F-sequence: it does NOT imply F016 is the
sequencing apex -- F016 remains the deliberately-last, bottom-of-stack execution-only
adapter that no readiness stage depends on.

| Rung | Capability | Binary evidence test (achieved iff this exists) |
|------|------------|-------------------------------------------------|
| L0 | docs only | the kit's docs/templates/spec-kit artifacts exist (the medallion playbook, the readiness model, the F024 taxonomy) |
| L1 | one worked example | >= 1 worked-example table with mapping artifacts on disk under `mappings/` |
| L2 | two worked examples | >= 2 worked-example tables with mapping artifacts on disk under `mappings/` |
| L3 | repeatable silver / gold | silver + gold proven repeatable for the >= 2 worked tables (each has its silver + gold) |
| L4 | dbt transformation adapter | a dbt transformation adapter (F029) exists in-repo |
| L5 | Dagster orchestration | a Dagster orchestration project (F030) exists in-repo |
| L6 | official Power BI execution adapter | an official Power BI execution adapter (F016) exists in-repo |

L3's caveat -- "generic repeatability BEYOND the worked tables is the NEXT evidence" --
is a FORWARD scope-note reserved for once L3's binary test is satisfied, NOT license to
round an unmet L2/L3 up early. Until >= 2 worked tables exist on disk, L3's binary test
(silver + gold proven repeatable across the >= 2 worked tables L2 requires) is NOT
satisfied, and L3 is reported NOT ACHIEVED with the missing second worked table named --
never rounded up on the strength of the first table alone.

## Worked assessment against today's repo (the honest current state)

Run against the repo as of this authoring, the assessment yields (verify against the
repo, never assert from memory):

| Rung | Verdict TODAY | Evidence (cited) or missing artifact (named) |
|------|---------------|----------------------------------------------|
| L0 | achieved | docs/templates/spec-kit artifacts exist (e.g. `docs/medallion-playbook.md`, `docs/readiness/readiness-model.md`, `docs/architecture/product-modules.md`) |
| L1 | achieved | one worked example: `mappings/retail_store_sales/` |
| L2 | not achieved | missing: a second worked-example table with mapping artifacts on disk under `mappings/` (today there is exactly one: `mappings/retail_store_sales/`) |
| L3 | not achieved | missing: L3 requires the >= 2 worked tables L2 requires; with only one worked table on disk, repeatability across multiple tables is not yet evidenced |
| L4 | not achieved | missing: a dbt transformation adapter (F029) in-repo |
| L5 | not achieved | missing: a Dagster orchestration project (F030) in-repo |
| L6 | not achieved | missing: an official Power BI execution adapter (F016) in-repo |

**Reported level today: L1** (the highest rung whose required evidence ALL exists). The
kit makes NO production / GA / enterprise-grade claim: no rung backs one. No rung is
reported as a number.

## Procedure (numbered; do not reorder)

### 1. Identify the release and read the inputs
Resolve the release (one shipped roadmap F-slice, keyed by its F-number). READ the F028
evidence pack for the slice, the F032 compatibility matrix (by role; "consumed input not
yet available" if absent), the delivered roadmap ledger row + commit refs, and the
on-disk presence of adapters/projects. This is read-only; it re-measures nothing.

### 2. Draft the seven release-note blocks with citations
Fill `templates/release-notes.md`: each of the seven blocks, every "what became possible"
line citing its committed evidence. A capability with no supporting evidence is NOT
listed under "what became possible" -- it is omitted, or listed under "known limitations
-- not yet evidenced", never asserted. Set `status: draft -- awaiting release-owner
approval`.

### 3. Assess each rung by its binary test
Fill `templates/maturity-report.md`: for each rung L0..L6, run its binary evidence test
against the committed evidence / on-disk presence, record `achieved (evidence: ...)` or
`not achieved (missing: ...)`. Record L3's repeatability caveat as a forward scope-note
on its achieved verdict.

### 4. Report the level (no number)
The reported level = the highest rung whose required evidence ALL exists. Name the rungs
above it as not achieved with the missing artifact. Emit NO percentage / score / average.

### 5. Surface conflicts; never resolve them
When inputs disagree (e.g. the matrix asserts an adapter version interoperates but no
adapter exists in-repo), record the conflict as a FINDING and do NOT pick a side
(Principle V). The skill recommends; the human decides.

### 6. STOP for the named release owner
Leave the note `status: draft`. Approval (`draft -> approved`) and level confirmation are
a named release owner's act recorded in `approvals[]` -- Core-Authority, truth-creating,
which this skill cannot perform. After a run, `git status` shows only the drafted derived
artifacts; no release self-approved, no level self-confirmed, no stage moved to `pass`,
no validator run, no DB opened.

## Refusal behaviors (the honesty guard -- testable)

| Request | What the skill does |
|---------|---------------------|
| "give the kit a maturity score out of 100" | DECLINES; cites hard rule #9; returns the rung verdicts + cited evidence instead |
| "report Level 4" with no dbt adapter present | REFUSES; names the missing evidence (a dbt adapter F029 in-repo); reports the true level (L3 today) |
| "call the kit production ready / GA / enterprise grade" | REFUSES; states no evidence rung backs the claim; offers only evidence-backed capability lines |
| "mark this release approved" with no named release owner | leaves `status: draft`; states approval is a human action (Core Authority / Principle V) |
| "the matrix says adapter X works but no adapter X exists" | surfaces the conflict as a finding; does NOT resolve it (Principle V) |

## What the agent must NOT do

- Do NOT emit a numeric maturity score / percentage / averaged confidence (hard rule #9).
- Do NOT claim a capability, "production ready", "GA", or "enterprise grade" with no
  backing evidence rung.
- Do NOT report a level above the highest all-evidence-present rung; do NOT round a
  partial rung up.
- Do NOT self-approve a release, self-confirm a level, or publish (Core Authority).
- Do NOT re-measure: no `seshat check` / `retail validate`, no source profiling, no DB
  connection, no `powerbi/` read.
- Do NOT add a `seshat check` rule, a CLI verb, a validator, or any new gate; do NOT move
  any readiness stage to `pass`.
- Do NOT bake C086 / retail_store_sales specifics into the two generic templates (they are
  cited as track record in a FILLED instance, never inlined into the blank templates).
- Do NOT create `docs/releases/` content or any approved instance -- the skill drafts; a
  human approves.

## See also

- The two output templates: `../../../templates/release-notes.md`,
  `../../../templates/maturity-report.md`.
- The authority contract: `../../../docs/architecture/product-modules.md` (the five
  categories + the matrix + the absence of a Maintenance Automation sub-axis),
  `../../../docs/architecture/core-vs-modules-and-adapters.md` (the prose + the seam).
- The consumed inputs (by id + role): `../../../docs/tools/evidence-pack-generator.md`
  (F028, built), `../../../specs/026-adapter-compatibility-matrix/spec.md` (F032, the
  compatibility matrix -- referenced by role).
- The release history of record: `../../../docs/roadmap/roadmap.md` (delivered ledger).
- The four-status / no-fake-confidence model the ladder mirrors structurally:
  `../../../docs/readiness/readiness-model.md`; hard rule #9.
- The read-and-present sibling it mirrors: `../retail-control-room/SKILL.md`. The
  conductor it plugs into: `../retail-orchestrate/SKILL.md`.
- The worked example that grounds the ladder:
  `../../../docs/worked-examples/retail-store-sales.md`; `mappings/retail_store_sales/`.
- The spec: `../../../specs/027-release-maturity-management/spec.md`.

## Orchestration

When a milestone ships, the `retail-orchestrate` conductor may invoke this generator as
the product-level read AFTER the milestone: it reads the committed evidence (F028 pack +
F032 matrix + roadmap ledger), DRAFTS the seven release-note blocks, ASSESSES the maturity
rung, reports the level, and STOPS for the named release owner. It advances no readiness
stage -- the per-table spine and the product-level release record are orthogonal. Release
approval, level confirmation, and any publish are the named release owner's acts via Core
Authority, never this skill's.
