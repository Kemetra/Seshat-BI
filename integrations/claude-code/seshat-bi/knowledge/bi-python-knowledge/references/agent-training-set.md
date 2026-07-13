# Agent Training / Eval Set

Original Q&A pairs to train and evaluate a BI agent's Python reasoning. Each item states
the question, the correct reasoning, the artifact it should end on, and the IDs it
exercises. All scenarios use the fictional retail schema. Machine-readable form:
`references/agent-training-set.json`.

> Use for evaluation: present the question, score the agent's reasoning against the
> expected answer and whether it ended on the right artifact.

> **Seed note:** this is an initial seed. Several `Ends on` targets name artifacts that
> are **planned / not yet implemented** in this seed — `dataframe review checklist`,
> `merge fan-out checklist`, `cleaning checklist`, `date readiness verdict`,
> `validation/reconciliation verdict`, and `performance diagnostic verdict`. The only
> shipped checklist is `checklists/aggregation-grain-checklist.md`. Until the others
> ship, score on reasoning quality and accept the verdict produced inside the live
> knowledge file (e.g. the cleaning row-count ledger) as the artifact.

---

**PY-QA-001** — *`store_id` loaded as integers and a join to `stores` dropped rows. Why?*
Expected: numeric keys lose leading zeros (`"00042"`→`42`) and/or mismatch string keys,
so matches silently fail. Keys must be string-typed. Ends on: dataframe review checklist
(dtype verdict). Exercises: PY-CN-023, PY-AP-011.

**PY-QA-002** — *Revenue is 8% high after joining orders to returns. What happened?*
Expected: one-to-many fan-out duplicated order lines; summing revenue double-counts.
Aggregate returns to order-line grain first, then merge many-to-one. Ends on: merge
fan-out verdict. Exercises: PY-CN-046, PY-CN-051, PY-AR-002.

**PY-QA-003** — *Should I `fillna(0)` on `discount_amt` before averaging?*
Expected: no, not by default — null ≠ zero; it changes the mean. Decide skip-vs-treat-as-
zero explicitly and record it; imputation is deferred to the metric owner. Ends on:
cleaning checklist (null policy). Exercises: PY-CN-039, PY-CN-043, PY-AP-013.

**PY-QA-004** — *"Number of orders per store" — which operation?*
Expected: `nunique(order_id)`, because the frame is at order-line grain; `size` counts
lines, overcounting. Ends on: aggregation-grain verdict. Exercises: PY-CN-055, PY-AP-017.

**PY-QA-005** — *Can I sum each region's average basket value to get the company average?*
Expected: no — averages are non-additive. Recompute from base totals (weighted average).
Ends on: aggregation-grain verdict. Exercises: PY-CN-054, PY-AP-016.

**PY-QA-006** — *`channel` shows 6 values but the domain has 3. Fix?*
Expected: trim + lowercase, confirm collapse to exactly `{store, web, app}`; flag any
survivor rather than auto-mapping. Ends on: cleaning checklist. Exercises: PY-CN-031,
PY-CN-032, PY-AP-014.

**PY-QA-007** — *Dates parse differently across files, smearing monthly revenue. Fix?*
Expected: pin the format per source, coerce failures to NaT, record parse rate; treat
format change as schema drift. Ends on: date readiness verdict. Exercises: PY-CN-060,
PY-AP-019.

**PY-QA-008** — *A join to customers linked many unrelated guest orders. Why?*
Expected: empty-string `customer_id` keys matched each other; convert `""` to null before
joining. Ends on: cleaning + merge checklists. Exercises: PY-CN-040, PY-AP-004-adjacent.

**PY-QA-009** — *Can I mark the frame "reconciled" because the numbers look right?*
Expected: no — reconciliation requires control-total evidence (expected/actual/delta) with
a declared tolerance. Ends on: validation/reconciliation verdict. Exercises: PY-CN-068,
PY-AP-024, PY-AR-015.

**PY-QA-010** — *The notebook is slow with a row loop computing net line value. Fix?*
Expected: vectorize the column expression; diagnose the real constraint first; stop at
fast-enough. Ends on: performance diagnostic verdict. Exercises: PY-CN-075, PY-AP-022.

**PY-QA-011** — *Should I compute YTD revenue in pandas for the dashboard?*
Expected: no — period metrics are DAX measures; the Python layer prepares a clean
datetime and period keys only. Ends on: date readiness verdict + handoff. Exercises:
PY-CN-064, PY-AP-021, PY-AR-012.

**PY-QA-012** — *Several columns are `object` dtype in the "ready" frame. Acceptable?*
Expected: no — resolve each to a real dtype (string/numeric/datetime/category) or justify
it; `object` means uninferred and costs memory. Ends on: dataframe review checklist.
Exercises: PY-CN-017, PY-AP-010, PY-AR-006.

**PY-QA-013** — *Can I `drop_duplicates()` to clean up the frame?*
Expected: only after declaring the uniqueness key and measuring duplicates; distinguish
exact dupes from key collisions with differing attributes. Ends on: cleaning checklist.
Exercises: PY-CN-035, PY-AP-001.

**PY-QA-014** — *Grouped revenue total is lower than ungrouped. Why?*
Expected: rows with a null group key were dropped from groups; make null an explicit
group or include null keys; reconcile before/after totals. Ends on: aggregation-grain
verdict. Exercises: PY-CN-057, PY-CN-058.

**PY-QA-015** — *Python validated everything; can I skip the readiness gate?*
Expected: no — Python validates and produces a reconciliation record; readiness owns
gating. Hand off the record. Exercises: PY-CN-070, PY-AP-025, PY-AR-016.
