# SQL Reconciliation Checklist

Tie a measure across layers: source <-> silver <-> gold. Reconciliation proves a transformation
preserved the data, not just that each layer looks plausible. Two levels: a cheap **control-total**
tie-out, and a precise **row-level diff**.

## Set up
- [ ] Name the **control total** that should be invariant across layers (e.g. total revenue, count
      of distinct orders) and the shared grain it is measured at (SC-030).
- [ ] Confirm each layer's grain is declared (SC-003); reconciliation breaks where grain drifts.

## Level 1 -- control-total tie-out (cheap, always do this)
- [ ] Compute the control total at **source**, **silver**, and **gold** at the shared grain
      (VP-CONTROLTOTAL).
- [ ] Compare row counts at each layer (VP-ROWCOUNT).
- [ ] Pass: totals and counts match within tolerance. If not, find the **first** layer where it
      diverges -- that is where the transformation broke (PB-SQL-08).

## Level 2 -- row-level diff (precise, when totals match but you need certainty)
- [ ] Run `EXCEPT` **both** directions on the row-identity columns (VP-DIFF, SC-041, SC-042):
      `(A EXCEPT B)` = 0 rows **and** `(B EXCEPT A)` = 0 rows.
- [ ] Confirm `COUNT(*)` is equal too (set-distinct can hide duplicate-count differences, SC-040).
- [ ] Pass: both diffs empty and counts equal -> the layers hold identical rows.

## Idempotency (re-runnable loads)
- [ ] A reload keeps row count and the control total identical (VP-DEDUP, SC-032); the load is
      `MERGE`/replace, not append (SC-047, PB-SQL-14).

## Record the result
- [ ] First divergent layer named (or "none"); the diff rows (if any) captured as evidence.
- [ ] Status with `evidence[]` + `blocking_reasons[]`; never a numeric score; never `pass` without
      the tie-out evidence.
- [ ] If the authoritative source figure is disputed or the row-identity key isn't agreed -> **stop
      and request it**, do not assert (in)equality.
