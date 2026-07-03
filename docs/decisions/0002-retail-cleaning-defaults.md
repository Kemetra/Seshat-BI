# 0002 — Retail cleaning & modeling defaults

- **Date:** 2026-06-24
- **Status:** Accepted
- **Context:** Building the C086 pharmacy medallion warehouse forced a series of
  cleaning and dimensional-modeling decisions. Most of them are not C086-specific —
  they are sensible **defaults for any retail sales table** moving bronze → silver →
  gold. This ADR records each as a reusable default with its rationale and the
  conditions under which a future table should override it. C086 is cited as the
  worked example. The *process* that surfaces these decisions lives in
  `docs/medallion-playbook.md`; this ADR records the *rulings*.

## Decision

The following are the **default rulings** for any retail table. Adopt them unless the
table's own profiled data contradicts the "override when" condition.

### Grain & keys

- **RC1 — Model at the lowest grain the source provides.** Default to the line-item /
  atomic grain; roll up in gold or DAX, never down. Decide grain **first**, before any
  column drop, because it fixes the non-droppable structural keys.
  *Override when:* the source is already pre-aggregated and the atomic rows are
  genuinely unavailable. *(C086: invoice line item, PK `invoice_no + line_no`.)*
- **RC2 — Verify the primary key on the data, and re-verify on the transformed output.**
  Raw uniqueness can break after TRIM/cast. *(C086: PK held on all 246,916 transformed rows.)*

### Columns & PII

- **RC3 — Drop columns that carry no signal:** 100%-empty, single-value, verified
  duplicates (≥95% equal to another), and the code half of a 1:1 code↔label pair (keep
  the human-readable label, keep the code only if used as a stable join key).
  *Override when:* a "redundant" column is the only link to an upstream system that
  reconciliation needs.
- **RC4 — Remove personal/sensitive data before the BI layer — decided EARLY, not at
  review.** A published BI dataset is effectively irreversible (cached tiles, exports).
  Default to dropping PII; if a need exists, hash/mask or isolate in a restricted
  dataset — never rely on row-level security to hide a *column*.
  *Override when:* the column is non-identifying or a governance sign-off explicitly
  permits it. *(C086: insurance phone + claim number were patient health data → dropped.)*

### Missing values & types

- **RC5 — Treat the empty string as missing.** Convert `''` → NULL on all columns first;
  measure missingness as `'' OR NULL`, never `IS NULL` alone.
- **RC6 — Fill policy:** NULL for genuinely-unknown facts; a sentinel
  (`'UNKNOWN'`/`'UNCLASSIFIED'`) only for dimension attributes that must group cleanly,
  and only after verifying the sentinel collides with no real value.
- **RC7 — Money/quantities → exact `NUMERIC`, never float. Dates → `DATE` if no real time
  component. IDs/codes → `TEXT` when they have leading zeros** (casting to int corrupts
  them); ordinal line numbers with no leading zeros → small integer (sorts correctly).
  *(C086: customer_id `0451000217` stayed TEXT; line_no → SMALLINT.)*

### Returns & measures

- **RC8 — Keep returns, and derive an `is_return` boolean from the authoritative column
  (billing/transaction type), never from the measure sign.** Returns must be separable
  for net-of-returns analysis; the sign alone misses zero-value and edge-case returns.
  Pair with English/standardized type labels so returns are also human-legible.
  *Override when:* the business explicitly excludes returns from the dataset's scope.
- **RC9 — Keep the independent money measures (gross, net, tax, discount); drop only true
  duplicates.** Do not collapse to a single measure unless the others are derivable on
  the data. Dropping them is irreversible from silver (only bronze retains them).
  *(C086: the gross→net gap was 8.7% / 3.1M — not reconstructable once dropped.)*

### Standardization, rollups, hierarchy

- **RC10 — Unify categorical encodings to one standard** (one language, one case). Keep
  the original code as a separate column when it is a stable join key.
- **RC11 — Add business rollups only from an analyst-supplied mapping; never invent the
  mapping.** Document that a merchandising rollup is not a clinical/structural axis if
  it cross-cuts. *(C086: `business_segment` PHARMA/HVI/NON-PHARMA from divisions.)*
- **RC12 — Model a non-tree hierarchy as flat denormalized levels, not a snowflake.** When
  a child appears under multiple parents, flat levels keep one path per row so totals
  don't double-count; forcing a single parent destroys real overlap.

### Build & star schema

- **RC13 — Materialize silver as a TABLE (not a view) via an idempotent numbered
  migration** (DROP+CREATE+ADD PK+INDEX in one transaction, UTF-8 no BOM). A view can't
  carry the PK that gold's FKs reference. Transform order is load-bearing: TRIM → fix
  encoding → junk filters (before `''`→NULL) → `''`→NULL → casts via `NULLIF` → numeric
  filters on cast values → derived columns.
- **RC14 — Gold is a Kimball star:** one fact at the silver grain + conformed dims;
  surrogate `_sk` keys; an **unknown member at `_sk = -1`** per dim with fact FKs
  `COALESCE`'d to -1; transaction identifiers as **degenerate dimensions** on the fact.
- **RC15 — The date dimension is a CONTIGUOUS generated calendar over the full span,**
  never `SELECT DISTINCT date` (missing days break time-intelligence).
- **RC16 — Reconcile measure totals at every layer** (source → silver → gold → BI) and
  assert **0 orphan FKs** before declaring a build done.

## Alternatives rejected

- **Record decisions only in the playbook (method doc).** Rejected: the method and the
  *rulings* serve different needs — a future analyst wants to inherit the defaults
  without re-reading the whole process. Kept both; the playbook references this ADR.
- **C086-specific decision log.** Rejected per the goal: the value is a *general* retail
  default set. C086 appears only as the example behind each ruling.
- **One ADR per decision (6-8 files).** Rejected as heavier to maintain than one
  cohesive defaults ADR for a set of rulings that are adopted together.

## Consequence

Any new retail table starts from RC1–RC16 as defaults and only documents **deviations**,
with the triggering data fact, in its own ADR. This compresses the per-table decision
work to "confirm defaults + record overrides" instead of re-deriving the policy each
time. The defaults are opinionated, so a table whose data genuinely differs (e.g. no
returns, pre-aggregated grain) must override explicitly rather than silently — the
"override when" clauses make those forks visible. Pairs with `docs/medallion-playbook.md`
(the process) and the `medallion-cleaning` skill (the interactive driver).

See a filled worked example under `docs/worked-examples/` for all 16 defaults applied and validated end-to-end.
