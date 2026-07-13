# Cleaning Review Checklist

Terminal artifact for the cleaning/standardization route. Ends on a categorical
cleaning verdict plus a row-count ledger. Clean only what profiling flagged
(PY-BP-005); every value-altering step is recorded so validation can reconcile.
Schema: `references/retail-dataframe-schema.md`.

## A. Evidence-driven scope (PY-BP-005)

- [ ] Every cleaning step traces to a profiling finding (no "just in case" cleaning).
- [ ] Columns not flagged by profiling are left unchanged.
- [ ] Plan is profile -> flag -> clean the flagged -> re-profile.

## B. String + category standardization (PY-CN-031, PY-CN-032)

- [ ] Text columns cleaned by a consistent rule: trim, canonical case, collapse
      internal whitespace.
- [ ] Canonical target form is a recorded domain decision, not a default.
- [ ] After cleaning, the distinct set collapses to the documented domain; any value
      outside the domain is flagged (never auto-mapped to the nearest known value).

## C. Numeric-as-text coercion (PY-CN-033)

- [ ] Currency symbols and thousands separators stripped before conversion.
- [ ] Conversion uses coercion (unparseable -> null), never raise-or-drop.
- [ ] Coerced-null count measured; a nonzero count is recorded as a finding.

## D. Invalid / out-of-range / sentinels (PY-CN-034) -- human-recorded rulings

- [ ] Sentinel meaning (`-1`, `999` -> null vs a real value) recorded by a human.
- [ ] Out-of-range values FLAGGED, not silently deleted; keep-vs-flag recorded by a
      human.
- [ ] Every value-altering rule documented so validation can reconcile counts.

## E. Deduplication (PY-CN-035, guarding PY-AP-001) -- human-recorded keep-policy

- [ ] Uniqueness key declared FIRST (e.g. `order_line_id`, `return_id`).
- [ ] Duplicates measured (rows minus distinct keys).
- [ ] Keep-policy when keys collide recorded by a human (latest? first-seen?).
- [ ] Exact duplicates distinguished from key-collisions-with-differing-attributes
      (the latter is investigated, never blindly de-duped -- PY-AP-001).

## F. Grain + row accountability (PY-CN-036, PY-CN-037)

- [ ] Grain unchanged unless deduplication was an explicit goal.
- [ ] Row-count ledger kept: rows in -> altered -> coerced-null -> dropped -> out.
- [ ] Every delta in the ledger is explainable.
- [ ] Lossy transforms (sentinel -> null, currency strip) stay traceable: a raw column
      retained during the pipeline OR the exact rule recorded (PY-CN-037).

## Fork boundaries (reference, do not re-own)

- [ ] Any groupby / grain / additivity concern -> `checklists/aggregation-grain-checklist.md` (owner).
- [ ] Any large-data / distributed-cleaning concern -> `skills/bi-bigdata-knowledge/` (this layer is single-node pandas).

## Verdict

- **CLEANING SOUND** -- every section passed; ledger balances and each delta is explained.
- **OPEN FINDINGS** -- one or more sections flag an item a human must record a ruling on
  (sentinel meaning, out-of-range keep-vs-flag, dedupe keep-policy, an unknown domain value).
- **GRAIN VIOLATED** -- row-count accountability broke: rows changed with no recorded reason.
- **BLOCKED** -- a required input is missing or unreadable (e.g. no profiling evidence, no schema).

No numeric cleanliness score, percentage, or "N of M" tally -- the verdict is observed
from the section checkboxes, never computed.

Attach: the row-count ledger (rows in -> altered -> coerced-null -> dropped -> out) + the
cleaning verdict.
