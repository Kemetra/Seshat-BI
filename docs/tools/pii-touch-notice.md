# retail pii-notice -- Personal-Data-Touch Notice

A read-only Product Module (spec 114) that composes a per-column PII-disclosure
notice for ONE table from its committed `mappings/<table>/source-map.yaml`.

## What it does

For each column flagged `pii: true`, it emits ONE disclosure sentence echoing the
committed `pii` flag + keep/drop `decision` and the recorded governance
disposition VERBATIM; any `pii: true` column with no recorded decision is an
explicit GAP. It fills the gap F040 consumer-data-dictionary leaves by design
(F040 omits PII as a disclosure fact): no other shipped surface renders a KEPT
`pii: true` column's governance disposition or GAP-marks an undecided one.

## Run

```
retail pii-notice --table <table>            # print the notice (writes nothing)
retail pii-notice --table <table> --write    # -> mappings/<table>/pii-touch-notice.md
retail pii-notice --table <table> --format json
```

## The disposition join (ratify OPEN-2)

A KEPT `pii: true` column names its governing deviation via a `deviation_ref`
field that EXACTLY matches a `defaults.deviations[].id`; the matched deviation's
`reason` is the authoritative disposition, echoed verbatim. The notice NEVER
scans deviation prose to guess a link. A kept `pii: true` column with no (or an
unmatched) `deviation_ref` is UNDECIDED -> GAP, never a false clearance.

## The scope wall (what it will NOT do)

- Renders NO publish-safety verdict of its own ("safe", "cleared", "no PII risk"
  are never authored by the composer -- they may appear ONLY inside a
  verbatim-quoted disposition).
- Never OMITS a `pii: true` column; an undecided one is a GAP marked "NOT cleared".
- Emits NO score, count, or percentage (hard rule #9).
- Adds NO `retail check` rule and blocks NO stage (FR-007). Its presence/absence
  is never a gate requirement (answerability-summary optional-companion precedent).
- Reads ONLY `source-map.yaml`; writes ONLY `mappings/<table>/pii-touch-notice.md`
  (with `--write`); opens no DB/Power BI/network connection.
- Generic across tables (Principle VII): no hardcoded column names or PII
  categories.

## Boundary against neighbours

- **F013 bi-handoff-pack** PII item -- lists only DROPPED pii:true columns; this
  notice covers kept, dropped, AND undecided.
- **F040 consumer-data-dictionary** -- composes column MEANING, omits PII as a
  disclosure fact by design (its FR-010); this notice is the disclosure sibling.
- **dq-signal-interpretation** PII gate -- scoped to the -1 unknown-member DQ
  signal, not a per-column PII inventory.
