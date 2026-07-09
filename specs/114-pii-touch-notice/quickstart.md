# Quickstart: Personal-Data-Touch Notice

## What it does

Composes a per-column PII-disclosure notice for one mapped table from its
committed `source-map.yaml`. One sentence per `pii:true` column (kept or dropped),
echoing the recorded governance disposition verbatim; an explicit GAP for any
`pii:true` column with no recorded decision. Read-only, no gate, no score.

## Run it

```
# print the notice for a table (dry read; writes nothing)
retail pii-notice --table retail_store_sales

# write the companion artifact
retail pii-notice --table retail_store_sales --write
# -> mappings/retail_store_sales/pii-touch-notice.md

# machine-readable
retail pii-notice --table retail_store_sales --format json
```

## Expected on the worked example

`retail_store_sales` has exactly one `pii:true` column, `customer_id`
(`decision: keep`), with the RC4 disposition recorded. The notice renders one
decided-kept disclosure line quoting "... Q1 RESOLVED 2026-06-25 (data owner):
keep, no raw PII." verbatim, cites `defaults.deviations[RC4]`, and emits no GAP,
no score.

## What it will NOT do

- Never says "safe to publish" / "cleared" / "no PII risk" in its OWN voice --
  only a verbatim quote of a committed disposition may contain such words.
- Never omits a `pii:true` column; an undecided one is an explicit GAP marked
  "NOT cleared".
- Never writes any file but `mappings/<table>/pii-touch-notice.md`; opens no DB.
- Never emits a score, risk level, or "N of M" count.
- Never adds a `retail check` rule or blocks a stage.

## Verify

```
pytest tests/unit/test_pii_notice.py -q
```

The tests are the FR-011 verifier: they assert every quoted disposition is a
verbatim substring of a committed source-map field, every `pii:true` column is
present and correctly classified (decided->echo, undecided->GAP), no clearance
token is authored, and no score appears -- across a decided-kept, decided-dropped,
undecided, no-pii, missing-source-map, and inconsistent fixture, on two distinct
tables.
