---
name: first-hour-compass
description: Show a NEW-table author the stateful "you are here / next artifact / authoring skill" orientation card for ONE table in the Seshat BI repo. Use when someone asks "where is this table in the readiness journey", "what do I do next for <table>", or "orient me on a new table". READ-ONLY and invoke-and-present only: it parses that table's mappings/<table>/readiness-status.yaml and RENDERS a single-table orientation card (current stage, the next non-pass stage + the artifact it needs + the authoring skill that produces it, plus recorded STOP rows). It RENDERS recorded state (never recomputes a status, advances a stage, writes a pass, infers/back-fills an approval, or fabricates evidence), runs NO validator, opens NO DB connection, and emits NO numeric health/confidence/percent-ready/maturity score (hard rule #9). It is the STATEFUL single-table sibling of the F026 readiness-viewer (multi-table matrix) and the stateful form of the F006 static onboarding checklist.
---

# First-Hour Compass

The stateful single-table orientation card for a new-table author. F024 module class:
**Product Module / `read-only`**. It answers, for ONE table: *where am I, what is the next
artifact, which skill authors it, and what human STOP is recorded?*

## What it does / does NOT do

- **Creates no truth.** It copies recorded fields; it defines no meaning, sets no status.
- **Changes no state.** It edits no file and runs no git mutation (a run leaves `git status`
  clean -- see the read-only proof below).
- **Infers no approval.** It never populates, back-fills, or synthesizes an approval; it only
  reports whether the next stage's `<stage>-ready.md` names a required owner and whether an
  `approvals[]` entry is recorded.
- **Fabricates no evidence.** A missing/absent field is reported as the honest not-started
  state, never invented.
- **Runs no validator, opens no DB.** It reads `readiness-status.yaml` only.
- **Emits no score.** No numeric health / confidence / percent-ready / maturity value. A
  request for one is DECLINED (hard rule #9); orientation is the four explicit statuses +
  evidence + blockers + the next allowed step.

## How it renders (renders, never re-derives)

| Card field | Source (copied verbatim) |
|------------|--------------------------|
| You are here | `readiness-status.yaml` `current_stage` + that stage's `status` |
| Next stage | the FIRST non-`pass` stage in pipeline order (Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish) |
| Next artifact | the required artifact named in that stage's `docs/readiness/<stage>-ready.md` |
| Authoring skill | the cross-walk row in `templates/first-hour-compass.md` for that stage |
| STOP rows | that stage's `blocking_reasons[]` verbatim + an approval-required flag |
| Conflict flags | surfaced (never auto-corrected): a `pass` with empty `evidence[]`; a downstream stage entered while an upstream is not `pass` |

## Honest-state rules

- **No file** for the table -> "Not yet onboarded -- start at Source Ready with
  `retail-onboard-table`." (Absent is not-started, never a fabricated stage.)
- **A stage `pass`** is reported only as recorded; the card never sets or upgrades it.
- **Pipeline ordering** is respected: a downstream stage is never presented as reachable while
  an upstream gate is not `pass`.

## First arrival: offer a worked example as the reference pattern

When there is **no table yet** -- the user has just arrived and named nothing -- do not stop
at "run `retail-onboard-table`". First give them a concrete pattern to steer by. This is the
first-hour "aha": a new author's fastest path is to hold up a filled example and copy its
*shape*, not to start from an empty gate.

Present the committed worked example as the reference pattern to steer by:

| Worked example | What it demonstrates | Pick it when your table is... |
|----------------|----------------------|-------------------------------|
| `docs/worked-examples/retail-store-sales.md` | The **full seven-stage spine** to Dashboard Ready -- metric contracts, governed model, dashboard design, handoff (on the public Kaggle retail-store-sales dataset) | ...any retail-sales table; it carries the build mechanics AND the later stages (semantic model, dashboard, handoff) |

Then hand off to `retail-onboard-table` for the user's own table, **holding the example
up as the reference** for that walk (see `docs/worked-examples/README.md`). Be explicit
about what "use this example" means:

- The example is a **narrative pattern, not a file template** -- `retail-store-sales.md` itself
  says "copy this section structure, swap in the new table, run the playbook's 7 phases". So the
  skill **references** the example while onboarding; it does **not** copy files into the user's
  table dir. (The actual starting artifacts come from `templates/`, seeded by
  `retail-onboard-table`.)
- **Read-only + route only.** This section presents the worked example and routes into the
  existing onboarding walk. It creates no truth, seeds no artifact, and writes nothing itself
  (the run still leaves `git status` clean; `retail-onboard-table` is what later authors files).

Set expectations honestly on the same breath: **the agent handles the sequence and the
plumbing; the user still owns the judgment** -- grain, PII placement, business rollups, and
metric policy are the four human seams `retail-onboard-table` will surface and STOP on, never
auto-resolve (Principle V).

## The two-condition approval flag

The card flags "approval required" for the next stage only when BOTH hold, read from the stage
doc's "Required owner / approval" field: (1) that stage requires a named human sign-off, and
(2) no matching `approvals[]` entry is recorded. It never names, infers, or supplies the owner
(mirrors the readiness-viewer contract) -- a Principle-V human seam.

## The four judgment seams (surfaced, never resolved -- Principle V)

Grain/uniqueness, PII publish-safety, business rollup/segment, and product identity are human
judgment calls. The Compass RE-PRESENTS a recorded STOP touching any of these; it never
asserts a grain, clears a PII gap, embeds a rollup/segment, or fixes a product identity.

## Deltas vs its parents

- **vs F026 readiness-viewer**: F026 is the multi-table stage MATRIX (all items, all stages).
  The Compass is the SINGLE-table, next-artifact, authoring-skill-routed orientation card.
- **vs F006 onboarding-checklist**: F006 is the STATIC definition-of-done. The Compass is the
  STATEFUL "you are at Stage N of it" read of the same journey.

## Read-only proof

Rendering the card writes nothing. After a run, `git status` is clean (the skill mutates no
tracked file); the only output is the rendered card in the response.

## See also

- The card template + stage->skill cross-walk: `../../../templates/first-hour-compass.md`
- First-arrival reference pattern: `../../../docs/worked-examples/retail-store-sales.md`
  (a narrative pattern, not a template)
- The onboarding walk this routes into: `../retail-onboard-table/SKILL.md`
- Usage + boundary doc: `../../../docs/tools/first-hour-compass.md`
- Multi-table parent (F026): `../readiness-viewer/SKILL.md`
- Static parent (F006): `../../../docs/readiness/onboarding-checklist.md`
- Pipeline ordering + gates: `../../../docs/readiness/readiness-pipeline.md`
