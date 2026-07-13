# Cleaning and Standardization

Turning a profiled raw frame into a consistent, BI-ready frame — without inventing
meaning. Cleaning starts only after profiling and grain are understood (stop rule).
Schema: `references/retail-dataframe-schema.md`.

---

## PY-BP-005 — Clean only what profiling flagged

Cleaning is evidence-driven. Each cleaning step should trace to a profiling finding
(`knowledge/profiling-and-source-inspection.md` — **planned / not yet implemented in
this seed**). Cleaning columns "just in case" risks altering correct data and hiding
real issues. Profile → flag → clean the flagged → re-profile.

## PY-CN-031 — String standardization is a domain decision

Text drift (`Web`, `WEB`, `web `) is fixed by a consistent rule: trim whitespace, set a
canonical case, collapse internal whitespace. But the *target* form is a decision, not
a default — `channel` canonical values are `store`/`web`/`app` per the schema. Apply
the rule, then verify the distinct set collapsed to the known domain.

**Retail illustration:** `channel` distinct count drops from (say) 6 messy variants to
exactly 3 after trim+lowercase. If it does not reach exactly the known domain, an
unknown value remains — a finding, not a silent pass.

## PY-CN-032 — Category standardization should converge to a known domain

After cleaning a category-like column, compare the result to the documented domain
(`channel`, `region`, `reason_code`, `category`). Values outside the domain are either
new legitimate values (update the schema, with the owner) or errors (map or flag).
Never auto-map an unknown value to the nearest known one without confirmation — that
fabricates data.

## PY-CN-033 — Currency and numeric-as-text cleaning

To convert `"£1,299.00"` to a number: strip the currency symbol and thousands
separators, then convert with **coercion** so unparseable values become null rather
than raising or being dropped. Then **count the coerced nulls** — a nonzero count is a
finding (what were those rows?). Order matters: clean the text, then convert, then
audit. See dtype reasoning in `knowledge/pandas-dtypes-and-schema.md` (PY-CN-019) —
**planned / not yet implemented in this seed**; until it ships, see
`references/id-conventions.md` for the ID family.

## PY-CN-034 — Invalid and out-of-range values

Profiling surfaces negatives, zeros, and sentinels (`-1`, `999`). Cleaning decides,
per column and with domain knowledge:

- **Sentinel → null:** if `-1`/`999` means "unknown", convert to a real null so it is
  not summed or counted as a value.
- **Out-of-range → flag, not delete:** a negative `quantity` on a sales line is a
  finding to investigate, not a row to silently drop.
- **Document the rule:** every value-altering decision is recorded so validation can
  reconcile counts.

## PY-CN-035 — Deduplication needs a declared key first

You cannot dedupe without first declaring what makes a row a duplicate — i.e. the grain
key (PY-CN-007). Steps:

1. State the uniqueness key (`order_line_id` for `orders`, `return_id` for `returns`).
2. Measure duplicates: rows minus distinct keys.
3. Decide which row to keep when keys collide (latest timestamp? first seen?) — a
   policy choice, recorded.
4. Distinguish **exact duplicates** (whole-row repeats, usually safe to drop) from
   **key collisions with differing attributes** (a data problem; do not blindly keep
   one — investigate).

**Anti-pattern (PY-AP-001):** dropping duplicates with no declared key, which can
silently delete legitimate rows that happen to share some columns.

## PY-CN-036 — Cleaning must preserve grain and row accountability

After cleaning, the grain must be unchanged unless deduplication was an explicit goal.
Keep a row-count ledger: rows in → rows altered → rows coerced-to-null → rows dropped →
rows out. Every delta must be explainable. This ledger is the input to reconciliation
(`knowledge/validation-and-reconciliation.md` — **planned / not yet implemented in this
seed**; the row-count ledger is the artifact for this seed).

## PY-CN-037 — Standardize without destroying source values

When a transformation is lossy (sentinel → null, currency strip), keep the ability to
trace back: either retain a raw column alongside the cleaned one during the pipeline,
or record the exact rule applied. "I changed this and cannot say what it was" is never
acceptable in BI.

---

## Cleaning order of operations (retail)

```
1. trim + canonicalize text columns (channel, region, product_name)
2. converge category columns to known domain; flag unknowns
3. strip currency/separators -> numeric (coerce), count coerced nulls
4. map sentinels (-1, 999) -> null
5. flag (do not delete) out-of-range values
6. declare key -> measure + resolve duplicates
7. record row-count ledger
8. re-profile to confirm
```

---

### Ends on

The cleaning review checklist (`checklists/cleaning-review-checklist.md`) -- walk it to a
categorical cleaning verdict (CLEANING SOUND / OPEN FINDINGS / GRAIN VIOLATED / BLOCKED)
and attach the row-count ledger (PY-CN-036). That checklist is the endpoint of this route.
