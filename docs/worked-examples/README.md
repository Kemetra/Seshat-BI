# Worked Examples — index

The kit's **worked examples**: complete, filled runs of the medallion playbook on real
tables. Each is both an **evidence record** (proof the table is built and governed
correctly) and a **reusable pattern** a new table copies. They are not the universal
schema — the *questions and checks* generalize; the *answers* are per-table (hard rule
#7).

> **New here?** Read `c086-pharmacy.md` first for the build mechanics (bronze → silver →
> gold + live validation), then `retail-store-sales.md` for the rest of the spine
> (contracts → governed model → dashboard design → handoff + the governance lessons).

## The examples

| Example | Domain | Spine depth | Best read for |
|---------|--------|-------------|---------------|
| [`c086-pharmacy.md`](c086-pharmacy.md) | El Ezaby pharmacy sales (Arabic↔English) | build + live validation (to **Gold Ready**) | the medallion build mechanics, the ADR-0002 cleaning defaults applied, the static-vs-live compliance split |
| [`retail-store-sales.md`](retail-store-sales.md) | Kaggle retail store sales (English-only) | **full spine** (to **Dashboard Ready**; Publish Ready `warning`) | metric contracts, the governed PBIP/TMDL model, dashboard design bound to contracts, the handoff pack, and the approval-retraction governance lesson |

## How they differ (and why two examples exist)

One example can't prove a kit is generic. The second was chosen to differ from the first
on exactly the axes that would expose a leaked assumption — and the kit absorbed all of
them without a domain-specific rule firing:

| Axis | C086 (pharmacy) | retail_store_sales |
|------|-----------------|--------------------|
| Spine depth | build + live validation (to Gold) | full spine to Dashboard Ready (+ Publish `warning`) |
| Returns (RC8) | derived from an authoritative billing code | **N/A** — no returns (recorded deviation) |
| Customer PII (RC4) | dropped early (patient data) | **kept** — pseudonymous surrogate, per owner ruling |
| Language | Arabic↔English mapping | English-only source |
| A ratio metric | n/a | `DiscountedTransactionRate` denominator ruling + an honest approval-retraction |

## How to reuse them

1. Pick the closest example to your table and copy its **section structure**.
2. Walk the seven readiness stages (`docs/readiness/readiness-model.md`) via the playbook
   (`docs/medallion-playbook.md`): profile → map → gate → build → validate → contracts →
   model → design → handoff.
3. Fill each section's **Evidence** from your own table's committed artifacts under
   `mappings/<table>/` — never fabricate a figure to reach a verdict.
4. Record **deviations** from the RC defaults with their triggering data fact (the way
   C086's RC8 and retail_store_sales' RC4/RC8 deviations are recorded).

## See also

- The spine: `../readiness/readiness-model.md` and the seven `../readiness/<stage>-ready.md`
  stage docs.
- The method: `../medallion-playbook.md` (the 7 phases).
- The cleaning defaults: `../decisions/0002-retail-cleaning-defaults.md` (RC1–RC16).
- The blanks each example fills: `../../templates/` and `../../mappings/README.md`.
