# Worked Dataframe Example: Fictional Retail Lines

This is an illustrative reasoning trace using
`references/retail-dataframe-schema.md`. It is not observed evidence and not a
universal retail schema.

## Decision this route supports

Show how the live Python routes compose without reading the entire knowledge base.

## Required evidence

For a real use, replace every illustrative statement below with the user's committed
source/profile and approved metric contracts.

## Reasoning sequence

**PY-EX-007 — line sales preparation**

1. **Role and grain.** `sales_lines_raw` is proposed as one row per
   `(transaction_id, line_no)`. The proposal remains unproven until uniqueness is
   observed.
2. **Profile.** Record source revision, shape, field inventory, nulls, key
   multiplicity, domain/range findings, and invalid counts.
3. **Dtypes.** Preserve `store_id`, `product_id`, and `transaction_id` as identifiers;
   parse quantity and monetary components under declared precision.
4. **Missingness.** Keep null discount distinct from zero discount until the source/KPI
   contract decides the meaning.
5. **Dates.** Parse `event_timestamp` with its source timezone; derive business date
   only from an approved cutoff/calendar.
6. **Merge.** Join product attributes only after the product key is proven unique;
   record unmatched products and row-count conservation.
7. **Aggregate.** Group to store-day only for additive components approved upstream;
   recompute ratios from components.
8. **Reconcile.** Compare independent source controls for the same period, filters,
   exclusions, and precision.

## Worked example evidence ledger

| Boundary | Evidence required in a real run | Illustrative status |
|---|---|---|
| Raw profile | revision, rows, columns, candidate-key duplicates | not observed |
| Type conversion | invalid literals and nulls created | not observed |
| Product merge | cardinality, unmatched keys, before/after rows | not observed |
| Store-day output | target-grain uniqueness | not observed |
| Reconciliation | expected, actual, delta, tolerance, source | not observed |

## Failure modes

- copying the fictional columns into an unrelated source map;
- treating illustrative status as a pass;
- defining net sales or discount policy inside Python;
- skipping an earlier checklist because the example looks similar.

## Evidence-based verdict

The example demonstrates route order only. A real verdict comes from the route
checklists populated with committed evidence.

## Stop and handoff

Route metric meaning to Retail KPI, SQL controls to SQL, distributed work to Big Data,
and the completed reconciliation record to readiness.
