# Readiness Viewer -- usage and boundary

- **On-disk spec:** `specs/020-readiness-viewer/`  **Roadmap feature:** F026 (the
  roadmap F-number is authoritative when the two disagree).
- **Status:** Authored (docs/templates/skill only; no runtime code this slice).
- **Authority category:** Product Module / `read-only` (F024 Companion Tools
  Architecture -- see `../architecture/product-modules.md`).
- **Skill:** `../../.claude/skills/readiness-viewer/SKILL.md`.
  **Output template:** `../../templates/readiness-view.md`.

## What it is

The Readiness Viewer is the kit's stage-centric reading lens. Every source, table,
and report already carries its truth in one Core Authority artifact: its
`mappings/<item>/readiness-status.yaml` (ADR 0004). That file records
`current_stage`, a per-stage `status`, `evidence[]`, `blocking_reasons[]`,
`approvals[]`, and the single `next_action` across the seven-stage spine (Source
Ready -> Mapping Ready -> Silver Ready -> Gold Ready -> Semantic Model Ready ->
Dashboard Ready -> Publish Ready). The viewer RENDERS that recorded state as a
stage-progression view: a per-stage status matrix, each stage's evidence as
navigable references, and an approvals timeline. It is the agent's read-and-present
procedure; the agent is the runtime. It creates no truth.

## When to use it -- and when to use F012 instead

The viewer reads the SAME inputs as the F012 Data Quality Control Room
(`../../.claude/skills/retail-control-room/SKILL.md`). The two differ only in lens:

| Ask | Use |
|-----|-----|
| "What is broken across all tables, how badly, which do I fix next?" | F012 control room (findings + blockers, worst-first) |
| "Which of the seven stages has each item reached?" | Readiness Viewer (the stage matrix) |
| "What evidence backs Gold Ready -- show me the file?" | Readiness Viewer (evidence as references) |
| "Who approved this gate, and when?" | Readiness Viewer (the approvals timeline) |

The three genuine deltas vs. F012 are exactly: (1) the per-stage status matrix
across all seven stages (F012 shows only `current_stage` + one status), (2)
`evidence[]` rendered as navigable references rather than F012's measured counts,
and (3) the `approvals[]` timeline (F012 does not read `approvals[]`). `next_action`
is SHARED with F012 and is NOT a delta.

**Chosen shape: (a)** -- a separate `readiness-viewer` skill that REUSES F012's
read-fan-out over the per-item files (one aggregation, two lenses). **Merge fallback
(b):** if the three deltas ever reduce so that the only durable difference is sort
order + column labels, the viewer should NOT ship as a separate module -- it should
fold into F012 as an optional stage-view section.

## How it reads readiness-status.yaml

Every rendered element traces to a recorded field; nothing is computed.

| Rendered element | Source field (copied verbatim) |
|------------------|--------------------------------|
| each matrix cell | `stages.<stage>.status` (one of `not_started` / `blocked` / `warning` / `pass`) |
| the marked current stage | `current_stage` |
| the single next action | `next_action` |
| each evidence reference | `stages.<stage>.evidence[]` (as-recorded -- bare path stays bare; an anchor is rendered only if present) |
| each timeline approval | `approvals[]` ({stage, owner, at}) in date order |
| which gates require an approval | the "Required owner / approval" field of `../readiness/<stage>-ready.md` |

Item discovery is exactly F012's fan-out: scan each `mappings/<item>/` directory for
a `readiness-status.yaml`; one matrix row per discovered file. The viewer adds no
second discovery path and invents no row for an item without a file.

## The read-only contract (F024 Product Module / read-only)

Per the F024 module contract (`../../templates/module-contract.md`), this module
reads, summarizes, and visualizes Core Authority -- and does nothing else. It:

- creates NO truth: it never defines business meaning, never approves a metric or
  mapping, never moves a readiness stage to `pass`;
- changes NO state: it never edits a `readiness-status.yaml` or any per-item
  artifact, never advances a stage, never writes a `pass`;
- infers NO approval: it renders recorded `approvals[]` and flags a missing required
  one; it never establishes, infers, or back-fills an approval (no-self-approval;
  Principle V);
- fabricates NO evidence: a stage with empty `evidence[]` shows "evidence missing";
  an absent referenced file shows "referenced file not found"; a missing-evidence
  `pass` is surfaced, never hidden;
- runs NO validator and opens NO DB connection: no `seshat check` / `retail
  validate` as a new check, no SQL;
- emits NO numeric health / confidence / percent-ready score (hard rule #9). A score
  request is DECLINED, citing readiness-model "No fake confidence"; the four explicit
  statuses across the seven stages are returned instead.

After a run, `git status` shows zero modified per-item files -- read-only proven.

### The approval-flag rule (two conditions, read from the stage doc)

A `pass` gate is flagged "approval not recorded" ONLY when BOTH hold: (a) that
stage's `../readiness/<stage>-ready.md` "Required owner / approval" field declares an
approver IS required, AND (b) no matching `approvals[]` entry exists. Where the stage
doc declares no required approver (a mechanical gate whose doc reads "None --
mechanical ... No human approval is added at this stage"), an empty `approvals[]` is
NORMAL and is NOT flagged. The viewer reads the requirement from the stage doc; it
never decides the requirement itself.

## Conflicts are surfaced, never resolved

When `current_stage` disagrees with the per-stage statuses, when a `pass` stage has
empty `evidence[]`, or when an approval references a `not_started` stage, the viewer
surfaces the conflict as a flag and does NOT resolve it by picking one side
(Principle V; surface, never bury). It is a lens, not an arbiter.

## Generic, not C086

The skill and the template are generic -- no worked-example specifics (billing
codes, segments, PII column names, per-table grain keys). C086 / retail_store_sales
are cited filled instances (see the worked examples under `../worked-examples/`),
never inlined (Principle VII).

## Deferred (enumerated, NOT built this slice)

- **`src/seshat/tools/readiness_viewer.py`** -- an OPTIONAL future read-only CLI
  renderer that would parse the per-item files and emit the matrix if item volume
  outgrows hand-rendering. It is still a read-only reporter (NO new validator, NO new
  `seshat check` rule, NO DB read). It is ENUMERATED here only; nothing in this slice
  creates it.
- **A machine-readable view export** (e.g. `readiness-view.json`) for a future UI --
  DEFERRED until a consumer exists.
- **A numeric readiness score / percent-ready** -- DEFERRED until scoring rules are
  defined in the readiness model (hard rule #9); the viewer must not be where one
  first appears.

## See also

- The skill: `../../.claude/skills/readiness-viewer/SKILL.md`; the output template:
  `../../templates/readiness-view.md`.
- The F012 overlap it is the delta of:
  `../../.claude/skills/retail-control-room/SKILL.md`,
  `../../templates/data-quality-control-room.md`.
- The Core Authority input: `../../templates/readiness-status.yaml`; ADR 0004
  (`docs/decisions/0004-readiness-status-location.md`).
- The module category + read-only contract: `../architecture/product-modules.md`,
  `../architecture/core-vs-modules-and-adapters.md`, `../../templates/module-contract.md`.
- The model + no-fake-confidence rule: `../readiness/readiness-model.md`; the stage
  sequence: `../readiness/readiness-pipeline.md`.
- The conductor it plugs into: `../../.claude/skills/retail-orchestrate/SKILL.md`.
- The spec: `../../specs/020-readiness-viewer/spec.md`. C086 / retail_store_sales are
  cited filled instances under `../worked-examples/`.
