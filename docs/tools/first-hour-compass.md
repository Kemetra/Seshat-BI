# First-Hour Compass -- usage & boundary

The `first-hour-compass` skill renders a **single-table** "you are here" orientation card for a
new-table author: current stage, the next non-`pass` stage, the artifact that stage needs, the
authoring skill that produces it, and any recorded human STOP.

## What it is

A read-only presenter over one table's `mappings/<table>/readiness-status.yaml` (ADR 0004). It
is the STATEFUL single-table sibling of the F026 readiness-viewer and the stateful form of the
F006 static onboarding checklist.

## When to use it (and when not)

- **Use it** when you are working ONE table and ask "where am I / what do I do next?"
- **Use it on first arrival** -- before any table exists -- to get a starting pattern (see
  the next section).
- **Use the readiness-viewer (F026)** instead when you want the multi-table stage MATRIX across
  every source/table/report.
- **Use the control room (F012)** instead when you want the worst-first, cross-table
  data-quality findings + blockers roll-up.

## First arrival: offering a worked example (no table yet)

When there is no `mappings/<table>/` at all -- a new author has just installed the kit and
named nothing -- the Compass does more than point at `retail-onboard-table`: it first offers a
**worked example to steer by**. This is the first-hour "aha" -- the fastest start is to hold a
filled example up and copy its *shape*, not to begin at an empty gate.

The card presents the committed worked example as the reference pattern:
`docs/worked-examples/retail-store-sales.md` (the full seven-stage spine to Dashboard Ready --
build mechanics through semantic model, dashboard, and handoff, on the public Kaggle
retail-store-sales dataset). It then
routes into `retail-onboard-table` for the author's own table, holding the example up as
the reference: retail-store-sales carries the whole spine end to end, from Source through
Mapping and Silver/Gold build mechanics to the semantic-model, dashboard, and handoff stages
(see `docs/worked-examples/README.md`).

Two honesty rules the card states in the same breath:

- The examples are **narrative patterns, not file templates** -- the Compass references one
  while onboarding; it copies no files. The starting artifacts are seeded by
  `retail-onboard-table` from `templates/` (read-only contract preserved: a Compass run leaves
  `git status` clean).
- **The agent handles sequence and plumbing; the author still owns the judgment** -- grain, PII
  placement, business rollups, and metric policy are the four Principle-V seams
  `retail-onboard-table` surfaces and STOPs on, never auto-resolves.

## How it reads `readiness-status.yaml` (renders, never re-derives)

| Card field | Source field (copied verbatim) |
|------------|--------------------------------|
| You are here | `current_stage` + that stage's `status` |
| Next stage | first non-`pass` stage in pipeline order (Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish) |
| Next artifact | required artifact named in that stage's `docs/readiness/<stage>-ready.md` |
| Authoring skill | the cross-walk row in `templates/first-hour-compass.md` |
| STOP rows | that stage's `blocking_reasons[]` + the approval-required flag |

Every value is a verbatim copy. The card never recomputes a status or synthesizes a line.

## The read-only contract

- Creates no truth, changes no state, infers no approval, fabricates no evidence.
- Runs no validator, opens no DB connection.
- Emits NO numeric health / confidence / percent-ready / maturity score (hard rule #9); a score
  request is DECLINED.
- After a run, `git status` is clean.
- The four judgment seams (grain / PII publish-safety / business rollup-segment / product
  identity) are SURFACED as recorded STOPs, never resolved (Principle V).

## Generic, not C086

The template + cross-walk are generic (`<schema>.<table>`, `<stage_key>`).
`retail_store_sales` appears only as a cited filled instance in `../worked-examples/retail-store-sales.md`.

## Deferred (not built this slice)

- `src/seshat/tools/next_step.py` -- a read-only resolver/scaffolder that would compute the
  next-artifact hint in code (still stdlib, read-only). DEFERRED: the MVP is the docs-card slice
  (template + skill + this doc); the code resolver is a later, optional add once the card proves
  useful (hard rule #8, YAGNI). It is intentionally NOT part of this feature.

## See also

- The card template + stage->skill cross-walk: `../../templates/first-hour-compass.md`
- The skill: `../../.claude/skills/first-hour-compass/SKILL.md`
- First-arrival reference pattern: `../worked-examples/retail-store-sales.md`,
  `../worked-examples/retail-store-sales.md`
- The onboarding walk the arrival flow routes into: `../../.claude/skills/retail-onboard-table/SKILL.md`
- Multi-table parent (F026): `readiness-viewer.md`
- Static parent (F006): `../readiness/onboarding-checklist.md`
- Pipeline ordering + gates: `../readiness/readiness-pipeline.md`
