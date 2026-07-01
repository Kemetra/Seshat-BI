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
- **Use the readiness-viewer (F026)** instead when you want the multi-table stage MATRIX across
  every source/table/report.
- **Use the control room (F012)** instead when you want the worst-first, cross-table
  data-quality findings + blockers roll-up.

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

The template + cross-walk are generic (`<schema>.<table>`, `<stage_key>`). C086 /
`retail_store_sales` appears only as a cited filled instance in `../worked-examples/c086-pharmacy.md`.

## Deferred (not built this slice)

- `src/retail/tools/next_step.py` -- a read-only resolver/scaffolder that would compute the
  next-artifact hint in code (still stdlib, read-only). DEFERRED: the MVP is the docs-card slice
  (template + skill + this doc); the code resolver is a later, optional add once the card proves
  useful (hard rule #8, YAGNI). It is intentionally NOT part of this feature.

## See also

- The card template + stage->skill cross-walk: `../../templates/first-hour-compass.md`
- The skill: `../../.claude/skills/first-hour-compass/SKILL.md`
- Multi-table parent (F026): `readiness-viewer.md`
- Static parent (F006): `../readiness/onboarding-checklist.md`
- Pipeline ordering + gates: `../readiness/readiness-pipeline.md`
