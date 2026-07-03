# Demo: retail_store_sales

A guided reading path through the worked example, `retail_store_sales`. Follow
it to see the readiness spine applied end to end on a real domain.

## Why this demo exists

`retail_store_sales` is a generic store-sales source (no returns, PII kept,
English-only) carried through every readiness gate with no special-casing, so
the kit's generality doesn't depend on any one client's schema.

## How it proves the kit is not hardcoded to a client schema

`retail_store_sales` uses the same artifacts, the same gates, and the same
`retail` surfaces as any onboarded table, but with its own grain, its own keys,
and its own metric contracts. Nothing in the spine is named after this example
-- the same spine reaches Dashboard Ready here precisely because it never
special-cased this example's schema.

## Read in this order

1. [`docs/worked-examples/retail-store-sales.md`](../worked-examples/retail-store-sales.md)
   -- the narrative walkthrough of the whole run.
2. [`mappings/retail_store_sales/source-profile.md`](../../mappings/retail_store_sales/source-profile.md)
   -- what the source looked like before any mapping (Source Ready).
3. [`mappings/retail_store_sales/source-map.yaml`](../../mappings/retail_store_sales/source-map.yaml)
   -- the reviewed map: grain, keys, PII, placement (the Mapping Ready gate).
4. [`mappings/retail_store_sales/assumptions.md`](../../mappings/retail_store_sales/assumptions.md)
   and
   [`mappings/retail_store_sales/unresolved-questions.md`](../../mappings/retail_store_sales/unresolved-questions.md)
   -- the recorded reasoning behind the map.
5. [`mappings/retail_store_sales/metrics/`](../../mappings/retail_store_sales/metrics/)
   -- the five approved metric contracts (`TotalSales`, `TotalQuantity`,
   `TransactionCount`, `AvgTransactionValue`, `DiscountedTransactionRate`).
6. [`mappings/retail_store_sales/reconciliation-report.md`](../../mappings/retail_store_sales/reconciliation-report.md)
   and
   [`mappings/retail_store_sales/reconciliation-bronze-to-gold.md`](../../mappings/retail_store_sales/reconciliation-bronze-to-gold.md)
   -- the validation/reconciliation evidence.
7. [`mappings/retail_store_sales/design/`](../../mappings/retail_store_sales/design/)
   -- the dashboard layout, visual list, and visual-to-contract binding map
   (Dashboard Ready, designed from the approved contracts).
8. [`mappings/retail_store_sales/handoff/`](../../mappings/retail_store_sales/handoff/)
   -- the BI handoff pack and its review checklist.
9. [`mappings/retail_store_sales/readiness-status.yaml`](../../mappings/retail_store_sales/readiness-status.yaml)
   -- the per-stage readiness state that ties it all together.

## What this demo proves

- **Source mapping before silver.** The reviewed `source-map.yaml` exists and the
  Mapping Ready gate is cleared before any silver build -- mapping is not skipped.
- **Metric contracts before dashboard.** The five contracts under `metrics/` are
  defined and approved before the dashboard design under `design/` -- every visual
  binds to a contract, none invents a KPI.
- **Validation before Power BI.** Reconciliation/validation evidence is recorded
  before any handoff toward Power BI -- gold is not handed off unvalidated.
- **Publish Ready can honestly remain `warning`.** In
  `readiness-status.yaml`, stages 1-6 are `pass` while `publish_ready` is
  `warning` (a prior publish approval was retracted as stale after a metric
  correction, and live publish is the deferred F016 adapter). The kit records the
  honest state rather than forcing a green Publish Ready.
