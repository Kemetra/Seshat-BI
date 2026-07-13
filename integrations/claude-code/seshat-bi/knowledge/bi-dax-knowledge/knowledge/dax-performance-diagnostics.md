# DAX Performance & Correctness Diagnostics

> The agent's diagnostic method: a repeatable way to turn "this number/measure is wrong or slow"
> into a located cause and a fix. Built on the reasoning layer (`dax-evaluation-context-deep-dive.md`,
> `dax-calculate-deep-dive.md`) and the engine model (`dax-engine-internals.md`). Each playbook is a
> step-by-step checklist that ends in a concrete fix, with links to concepts (CC-xxx), best
> practices (BP-xxx), anti-patterns (AP-xxx), live rules (AR-xxx), and staged candidates (ARC-xxx).
> Examples use the reference retail schema. Original teaching material — no book text or examples
> reproduced.

---

## The triage workflow (run before any playbook)

1. **Reproduce on realistic data.** Toy data hides both bugs and slowness. Use representative
   volume and a real visual layout.
2. **Correctness before performance.** A fast wrong answer is worthless. Confirm the number is
   right first (the "name the context" drill in `dax-evaluation-context-deep-dive.md`).
3. **Locate, don't guess.** For slowness, capture timings (e.g. DAX Studio server timings): is the
   time in the **Storage Engine** or **Formula Engine**, and are there **CallbackDataID**s?
   (CC-013). For wrong numbers, identify the *step* where the context diverges from intent.
4. **Pick the playbook** below by symptom.
5. **Fix the biggest lever, then re-measure.** Stop at "good enough"; don't micro-optimize cold
   paths.

> Symptom → playbook quick index:
> wrong total → PB-WRONG-TOTAL · ignores slicer → PB-IGNORES-SLICER · slow → PB-SLOW-MEASURE ·
> time-intelligence wrong → PB-TI-WRONG · blank/zero → PB-BLANK-ZERO · filter won't propagate →
> PB-PROPAGATION · iterator surprises → PB-CONTEXT-TRANSITION · % of total wrong → PB-PERCENT-OF-TOTAL.

---

## PB-WRONG-TOTAL — the total row ≠ the sum of the visible rows

1. **Is the measure non-additive by nature?** Distinct counts, ranking, segmentation, and
   semi-additive balances *should not* equal the sum of rows. Confirm whether the total is actually
   wrong or just non-additive. (CC-001; AR-ADD-001; AP-005)
2. **Name the context of a detail row vs the total row.** What filter is present on a category row
   that is absent on the total? The total often has *fewer* filters (no row context from the axis).
3. **Is an iterator at the wrong grain?** Many non-additive measures need to be computed per grain
   and summed: `SUMX(VALUES(grain), <measure>)`. Missing that yields a total computed "all at once."
4. **Does an `ALL`/`ALLSELECTED` behave differently at the total?** At the total there's no axis
   filter to clear, so an over-broad clear can change the number. (CC-009, CC-019)
5. **Fix:** compute at the correct grain and aggregate explicitly, or document the non-additive
   total deliberately. (See `dax-patterns.json`: dynamic-segmentation, ranking.)

## PB-IGNORES-SLICER — a measure doesn't react to a slicer

1. **Does a `CALCULATE` filter replace that column's filter?** A predicate does an implicit
   `ALL(column)` and overrides the slicer. (CC-004, CC-005)
2. **Should it intersect instead?** Wrap the computed/explicit filter in `KEEPFILTERS`.
   (CC-006; AR-CALC-001; ARC-CALC-01)
3. **Is an `ALL`/`REMOVEFILTERS` too broad?** `ALL('Date')` clears the slicer's column too; scope
   it with `REMOVEFILTERS('Date'[Date])` or `ALLEXCEPT`. (CC-019; AR-ALL-001; ARC-ALL-01)
4. **Is the slicer column reachable?** Check the relationship path/direction and lineage; a
   disconnected table needs `TREATAS`. (CC-010, CC-015; ARC-LINEAGE-01)
5. **Fix:** narrow the cleared columns; add `KEEPFILTERS`; correct the propagation path.

## PB-SLOW-MEASURE — measure is slow

1. **Reproduce on realistic volume; capture timings.**
2. **SE or FE?** If mostly SE with no callbacks, suspect volume/cardinality, not the formula — go
   to step 6. If high FE / many callbacks, continue. (CC-013)
3. **Measure iterated at fact grain?** `SUMX('Sales', [Measure])` → context transition per row.
   Iterate a dimension or use column arithmetic. (CC-003; AR-PERF-001; ARC-PERF-01)
4. **`FILTER` over a whole table where a predicate suffices?** Switch to a column predicate or
   `FILTER(VALUES(col), …)`. (CC-005; AR-PERF-002; ARC-PERF-03)
5. **Per-row `IF`/`SWITCH` calling measures inside an iterator?** Hoist invariants into `VAR`s
   outside the iterator; simplify to SE-friendly form. (CC-013; ARC-PERF-04)
6. **Model levers (cardinality):** high-cardinality columns (datetime, keys)? Split/reduce/drop.
   Heavy `DISTINCTCOUNT`? Reduce key cardinality; test bridge vs `TREATAS`. (CC-014; AR-PERF-004;
   ARC-MODEL-02)
7. **Repeated expensive subexpression?** Capture once in a `VAR`. (BP-022; AR-PERF-003)
8. **Fix the biggest lever, re-measure, stop at good-enough.**

## PB-TI-WRONG — time intelligence returns wrong values

1. **Date table marked & contiguous?** Must be Marked as Date Table and span full years with no
   gaps. (BP-001; AR-TI-002)
2. **TI table function used outside `CALCULATE` / in an iterator?** Move it to a filter arg or
   `VAR`. (BP-031; AR-TI-001; ARC-FUNC-01)
3. **Standard Gregorian calendar?** Weeks/4-4-5/custom fiscal → built-ins won't work; use the
   custom/week pattern. (BP-030)
4. **Scalar vs table date function confusion?** `EOMONTH` (scalar) vs `ENDOFMONTH` (table), day
   math vs `DATEADD`. (BP-032; AP-002; ARC-FUNC-01)
5. **Future-date guard present?** YTD/running totals flat-line past the last real date — guard with
   `DateWithSales`/last-date-with-data. (AP-006)
6. **Auto Date/Time interfering?** Disable it. (BP-002; AR-TI-003)
7. **Fix** per the first failing step.

## PB-BLANK-ZERO — blanks vs zeros look wrong

1. **Is `BLANK()` intended to hide rows?** Patterns return blank to hide future dates / empty
   combinations; that's deliberate. (core-concepts §9 blank handling)
2. **Did a `+0` / `COALESCE` / `DIVIDE(…,0-alternate)` turn hide-rows into show-everything?**
   Coalescing to 0 makes otherwise-blank rows appear. Choose intentionally.
3. **Are blanks distorting an aggregate?** `AVERAGEX` skips blanks (changes the denominator);
   counts may differ from expectation.
4. **Need "are there any rows?"** Use `ISEMPTY` rather than testing a summed value against 0.
5. **`BLANK() = 0` is TRUE but displays empty** — don't rely on equality to detect "no data."
6. **Fix:** preserve `BLANK()` where row-hiding is wanted; coalesce only at the display layer when
   safe; use `ISEMPTY`/`HASONEVALUE` for existence/selection tests.

## PB-PROPAGATION — a filter won't flow between tables

1. **Does a relationship exist on the needed path, and in which direction?** Default is one→many.
   (CC-015)
2. **Active or inactive?** Role-playing dates need `USERELATIONSHIP`. (CC-016; ARC-REL-01)
3. **Filtering many→one or across a bridge?** Needs explicit help: `CROSSFILTER`, `TREATAS`, or a
   summarize/bridge pattern. (CC-006, CC-010)
4. **Bidirectional causing ambiguity instead?** Ambiguous paths give wrong totals — prefer
   single-direction + per-measure cross-filter. (ARC-MODEL-01)
5. **Disconnected/config table doing nothing?** Apply via `TREATAS` with matching lineage.
   (CC-010; ARC-LINEAGE-01)
6. **Fix:** choose explicit propagation; avoid blanket bidirectional relationships.

## PB-CONTEXT-TRANSITION — iterator gives surprising results

1. **Is a measure (implicit `CALCULATE`) called inside the iterator?** That triggers context
   transition per row. (CC-003)
2. **Is the transition intended?** Per-entity calculations want it; raw arithmetic does not.
3. **Is the iteration grain right?** `SUMX(VALUES(grain), [m])` vs iterating the fact changes both
   result and cost.
4. **Performance:** is the iterated table fact-grain? (CC-013; ARC-PERF-01)
5. **Fix:** iterate the correct grain; use pure column math when no transition is wanted; capture
   outer-row values in a `VAR` (no `EARLIER`).

## PB-PERCENT-OF-TOTAL — the denominator is wrong

1. **Which total is meant?** Grand total → `ALL`; the user's *visible* total → `ALLSELECTED`.
   Picking wrong is the classic bug. (CC-009, CC-019; ARC-CTX-03)
2. **Does the denominator clear only the intended columns?** Over-broad clearing changes the base.
   (AR-ALL-001)
3. **Should some slicers remain in the denominator?** Use `KEEPFILTERS` or `ALLEXCEPT` to keep
   them. (CC-006)
4. **Ratio computed with `DIVIDE`?** Guard divide-by-zero. (BP-021)
5. **Fix:** choose `ALL` vs `ALLSELECTED` deliberately; scope the cleared columns; use `DIVIDE`.

---

## Agent reasoning questions (Slice 3 — diagnostics)

1. *"A matrix's grand total for '# distinct customers' is smaller than the sum of the rows. Bug?"*
   → Distinct count is non-additive; a customer counted in two rows is counted once in the total.
   **Not a bug — expected.** PB-WRONG-TOTAL; CC-001.
2. *"A measure is slow; timings show 95% Formula Engine and many callbacks. Where do I look?"*
   → FE-bound with callbacks = per-row logic. **Find a measure/IF inside an iterator; restructure.**
   PB-SLOW-MEASURE step 3–5; CC-013.
3. *"YTD is flat for all of next year. Why and fix?"*
   → No future-date guard; TI happily extends past real data. **Guard with `DateWithSales`.**
   PB-TI-WRONG step 5; AP-006.
4. *"My '% of total' adds up to far more than 100% across visible categories. Likely cause?"*
   → Denominator uses `ALL` (grand total) while rows are a filtered subset, or vice versa.
   **Check `ALL` vs `ALLSELECTED`.** PB-PERCENT-OF-TOTAL; CC-009.

---

## Links — companion files

- `dax-engine-internals.md` — the SE/FE/cardinality model these playbooks reference.
- `dax-evaluation-context-deep-dive.md` / `dax-calculate-deep-dive.md` — the correctness reasoning.
- `dax-best-practices.md`, `dax-anti-patterns.md`, `patterns/analyzer-rules.json`,
  `patterns/analyzer-rule-candidates.json` — the rules cited by step.
- Planned (later): `references/agent-training-set.md` will turn these playbooks into graded
  exercises.
