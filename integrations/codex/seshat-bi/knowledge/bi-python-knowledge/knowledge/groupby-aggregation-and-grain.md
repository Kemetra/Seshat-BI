# Groupby, Aggregation, and Grain (pandas for BI)

> **Knowledge route.** The *review* companion is
> [`checklists/aggregation-grain-checklist.md`](../checklists/aggregation-grain-checklist.md)
> — a standalone checklist you walk to a categorical verdict. This file is the
> conceptual knowledge that checklist draws on; it does **not** duplicate the
> checklist's steps.
>
> **Boundary — KPI meaning lives upstream.** Whether a measure is *supposed* to be
> summed, averaged, or distinct-counted is a KPI *business* decision owned by
> `skills/retail-kpi-knowledge/`. This file covers the mechanical pandas behavior of
> grain and aggregation only. Do not infer a KPI's additivity from column names here.

Core concept: **PY-CN-007 Grain of a dataframe**. Named failure mode:
**PY-AP-011 Groupby without declared grain**.

---

## 1. What "grain" is, before you group

The **grain** of a dataframe is the set of columns whose combination makes each row
unique — the answer to *"one row is one **what**?"*. A sales-line frame is at
*transaction-line* grain (`transaction_id, line_no`); a daily-store rollup is at
*store-day* grain (`store_id, date`).

You cannot aggregate correctly until you can name the current grain. If you can't name
it, stop and profile first — an unknown grain is the root of almost every double-count.

```python
# State the grain as an assertion, not an assumption:
assert not df.duplicated(subset=["transaction_id", "line_no"]).any(), \
    "frame is not at transaction-line grain"
```

## 2. The double-counting trap (fan-out before aggregation) — PY-PB-003

The classic bug: a **merge fans out** rows (a one-to-many join multiplies the left
rows), and a later `sum()` counts the multiplied rows.

```python
# orders: one row per order (grain = order_id), carries order_total
# items:  many rows per order (grain = order_id, sku)
merged = orders.merge(items, on="order_id")   # fans orders out to item grain
merged["order_total"].sum()                    # WRONG: order_total counted once PER ITEM
```

The fix is to know which grain each measure is valid at and aggregate to a single grain
*before* summing a measure that lives at a coarser grain. Use `validate=` on merges to
catch unexpected fan-out early:

```python
orders.merge(items, on="order_id", validate="one_to_many")  # raises if not 1:m
```

## 3. Additive vs non-additive under groupby

A measure's **additivity** governs whether `sum()` across groups is even meaningful:

| Class | Safe to re-sum across groups? | Examples |
|---|---|---|
| Additive | Yes | quantity, gross_sales, cost |
| Semi-additive | Only across some dimensions (not time) | inventory on hand, account balance |
| Non-additive | No — recompute from parts | ratios, rates, %, distinct counts, averages |

Non-additive measures must be **recomputed from their additive parts** at the target
grain, never summed:

```python
# WRONG: averaging an average
daily["margin_pct"].mean()
# RIGHT: recompute from additive parts at the target grain
g = df.groupby("date").agg(margin=("margin", "sum"), sales=("sales", "sum"))
g["margin_pct"] = g["margin"] / g["sales"]     # ratio rebuilt at date grain
```

(The additivity *class* of a KPI is declared upstream and checked by the `AD1`
additivity-consistency rule; this file only shows the pandas mechanics.)

## 4. Choosing groupby keys = declaring the output grain

`df.groupby(keys)` **defines a new grain**: after the aggregation, `keys` are exactly
the columns that make each output row unique. Choosing the keys *is* the grain decision.

```python
out = (
    df.groupby(["store_id", "date"], as_index=False)
      .agg(units=("qty", "sum"), sales=("sales", "sum"))
)
# out is now at store-day grain: one row per (store_id, date)
```

## 5. Verifying grain after aggregation — PY-VP-004

Always confirm the output grain and reconcile totals; do not trust the groupby blindly.

```python
# a) the new grain is truly unique
assert not out.duplicated(subset=["store_id", "date"]).any()

# b) an additive total is conserved (no rows dropped or duplicated)
assert out["sales"].sum() == df["sales"].sum()
```

Attach the before/after row counts and the conservation check to the
`aggregation-grain-checklist.md` verdict.

## Symptoms this file explains

- **"Sums look too big after grouping"** → double-counting / wrong grain / a
  non-additive measure summed (§2, §3).
- **"The rollup has duplicate keys"** → the groupby keys did not match the intended
  output grain (§4, §5).
