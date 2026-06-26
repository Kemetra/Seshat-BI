# SQL Review Checklist

Run before trusting / merging a `SELECT` or a transformation. Copy it, check each box, and record
the grain statement. A failed box is a finding, not a nit. References point to the cards behind
each check.

## Grain & keys
- [ ] **Grain stated** in one sentence: "one row of this result is one ___." (SC-003, SC-005)
- [ ] Every column assumed unique is **verified**, not believed (SC-004; gate VP-UNIQUE).
- [ ] After every `GROUP BY`, the new grain is named and nothing downstream silently re-inflates it.

## Joins & fan-out
- [ ] Each join's cardinality is known; the "one" side key is verified unique (SC-010; SP-CARDINALITY-CHECK).
- [ ] No additive aggregate (`SUM`/`COUNT(*)`) runs after a 1:many join without fixing grain first
      (SC-007, SC-011; never patched with `DISTINCT`, SQL-AP-014).
- [ ] `LEFT JOIN` right-table conditions are in `ON`, not `WHERE` (else it becomes INNER) (SQL-AP-012).
- [ ] Anti-joins use `NOT EXISTS` / `LEFT JOIN ... IS NULL`, never `NOT IN` over a nullable set (SC-012).

## Aggregation, COUNT & NULL
- [ ] `COUNT(*)` vs `COUNT(col)` vs `COUNT(DISTINCT col)` chosen on purpose (SC-006).
- [ ] `AVG` denominator (all rows vs non-null) is intended; not an unweighted average-of-averages (SC-008).
- [ ] Aggregate conditions are in `HAVING`; window functions are filtered in an outer query, not `WHERE` (SC-002).
- [ ] Division guarded against zero / NULL denominators.

## Text, dates & windows (if used)
- [ ] Text keys canonicalized (trim/case/accent) before group/join (SC-054).
- [ ] Date filters use half-open ranges; trends anchored on a date spine, not the sparse fact (SC-024, SC-060).
- [ ] Window `ORDER BY` is deterministic (has a tiebreak); running totals use an explicit `ROWS` frame (SC-016, SC-018).

## Hygiene
- [ ] No `SELECT *` in a persisted/consumed query; columns listed explicitly (SQL-AP-035, SC-036).
- [ ] No accidental cross join (every join condition present and selective) (SC-043).
- [ ] Deep CTE stacks annotate grain per CTE (SC-038).

## Verdict
- [ ] Open anti-patterns recorded by `SQL-AP-NNN`; applicable `SAR-*` rules checked.
- [ ] If a key's uniqueness or a null's meaning can't be confirmed from data -> **stop and request
      metadata**; do not guess.
- [ ] Result routed to a validation gate (`sql-validation-checklist.md`) where it persists to silver/gold.
