# Worked Examples — index

The kit's **worked examples**: complete, filled runs of the medallion playbook on real
tables. Each is both an **evidence record** (proof the table is built and governed
correctly) and a **reusable pattern** a new table copies. They are not the universal
schema — the *questions and checks* generalize; the *answers* are per-table (hard rule
#7).

> **New here?** Read `retail-store-sales.md` first for the full spine
> (build mechanics through contracts → governed model → dashboard design → handoff +
> the governance lessons).

## The examples

| Example | Domain | Spine depth | Best read for |
|---------|--------|-------------|---------------|
| [`retail-store-sales.md`](retail-store-sales.md) | Kaggle retail store sales (English-only) | **full spine** (to **Dashboard Ready**; Publish Ready `warning`) | metric contracts, the governed PBIP/TMDL model, dashboard design bound to contracts, the handoff pack, and the approval-retraction governance lesson |

## How to reuse it

1. Copy `retail-store-sales.md`'s **section structure** for your own table.
2. Walk the seven readiness stages (`docs/readiness/readiness-model.md`) via the playbook
   (`docs/medallion-playbook.md`): profile → map → gate → build → validate → contracts →
   model → design → handoff.
3. Fill each section's **Evidence** from your own table's committed artifacts under
   `mappings/<table>/` — never fabricate a figure to reach a verdict.
4. Record **deviations** from the RC defaults with their triggering data fact — the way
   retail_store_sales' RC4 (kept customer PII, pseudonymous surrogate) and RC8 (no returns
   in source) deviations are recorded.

## See also

- The spine: `../readiness/readiness-model.md` and the seven `../readiness/<stage>-ready.md`
  stage docs.
- The method: `../medallion-playbook.md` (the 7 phases).
- The cleaning defaults: `../decisions/0002-retail-cleaning-defaults.md` (RC1–RC16).
- The blanks each example fills: `../../templates/` and `../../mappings/README.md`.
