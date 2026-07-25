# BI Python Knowledge Router

Route the task to the **fewest** files that answer it. Open those files only. End on
the named artifact. Do not pre-load the whole `knowledge/` directory.

> **Core routes live.** Every route below resolves to a shipped resource and a named
> terminal artifact. Future additions must enter through the same route-and-artifact
> contract; do not invent an unlisted capability.
>
> **Boundary — KPI meaning lives upstream.** A KPI's *business meaning* (definition,
> additivity, required fields, grain intent, ambiguity, owner rulings) is owned by
> `skills/retail-kpi-knowledge/`. This layer owns dataframe source-prep: reading a
> standalone **file source** (CSV / Excel) into a trustworthy frame, cleaning,
> dtype/quality reasoning, and aggregation grain. A KPI contract hands its required
> fields + dtype/quality assumptions here for source-prep. If a request is really "what
> does this KPI mean", route to `skills/retail-kpi-knowledge/` first — do not infer the
> KPI's meaning from column names in Python.
>
> **Scale boundary — distributed work lives in the sibling layer.** This layer is
> **single-node** pandas. If the data is too large for one machine (it spills, OOMs, or the
> job is about partitioning/shuffle/skew/distributed joins/Spark/Dask), route to
> `skills/bi-bigdata-knowledge/` — the scale-out sibling that borrows this layer's
> grain/additivity spine and owns the distributed twist. Single-node first; scale out only
> when genuinely needed.

---

## Live routes (files shipped in this seed)

### Task routes — live

| If the agent needs to… | Open | End on |
|---|---|---|
| Understand dataframe semantics for BI | `knowledge/dataframe-mental-model.md`, `knowledge/python-core-concepts-for-bi.md` | `checklists/dataframe-review-checklist.md` |
| Profile a freshly loaded dataframe | `knowledge/profiling-and-source-inspection.md` | `checklists/dataframe-review-checklist.md` |
| Profile a **standalone file source** (CSV / Excel) — grain, encoding, delimiter, header row, multi-sheet, inferred-type traps | `knowledge/file-source-grain.md` (PY-CN-081..085, PY-BP-007, PY-PB-011) | the File-source addendum in `templates/source-profile.md` (marked `[PROPOSED]` / `[PENDING LIVE PROFILE]`) |
| Judge dtypes or schema drift | `knowledge/pandas-dtypes-and-schema.md` | `checklists/dataframe-review-checklist.md` |
| Classify nulls blanks and sentinels | `knowledge/nulls-missing-values-and-blanks.md` | `checklists/dataframe-review-checklist.md` |
| Clean / standardize strings, categories, currency, units, sentinels, or duplicates | `knowledge/cleaning-and-standardization.md` | `checklists/cleaning-review-checklist.md` (cleaning verdict + row-count ledger) |
| Merge two dataframes safely | `knowledge/joins-merge-and-fanout.md` | `checklists/merge-fanout-checklist.md` |
| Aggregate / groupby at a correct grain (use the checklist as a standalone review artifact) | `knowledge/groupby-aggregation-and-grain.md` | `checklists/aggregation-grain-checklist.md` |
| Parse dates and periods | `knowledge/dates-times-and-calendars.md` | `checklists/dataframe-review-checklist.md` |
| Validate and reconcile a dataframe result | `knowledge/validation-and-reconciliation.md`, `patterns/validation-patterns.json` | `checklists/validation-reconciliation-checklist.md` |
| Diagnose dataframe performance or memory | `knowledge/performance-and-memory.md` | performance and memory verdict |
| Review a Python pipeline against active rules | `knowledge/python-anti-patterns.md`, `patterns/analyzer-rules.json` | `checklists/python-pipeline-review-checklist.md` |
| Apply recommended Python BI patterns | `patterns/python-patterns.json` | `checklists/python-pipeline-review-checklist.md` |
| Study the worked dataframe example | `knowledge/python-retail-examples.md` | worked example evidence ledger |
| Review proposed (not-yet-active) static-analysis rules for Python pipelines | `patterns/analyzer-rule-candidates.json` | the candidate list itself (staging artifact) |
| Confirm the business meaning of a retail column | `references/source-map.md` | n/a (reference) |
| Confirm the fictional retail schema used by all examples | `references/retail-dataframe-schema.md` | n/a (reference) |
| Look up an ID family (`PY-CN-*`, `PY-AP-*`, `PY-AR-*`, …) | `references/id-conventions.md` | n/a (reference) |
| Evaluate an agent's Python reasoning against a seed Q&A set | `references/agent-training-set.json`, `references/agent-training-set.md` | n/a (eval seed) |

> **Cleaning route endpoint:** the cleaning knowledge file (PY-CN-036) ends on the
> **cleaning review checklist** (`checklists/cleaning-review-checklist.md`) -- walk it to
> a categorical cleaning verdict (CLEANING SOUND / OPEN FINDINGS / GRAIN VIOLATED /
> BLOCKED) and attach the row-count ledger.

### Symptom routes — live

| Symptom the agent observes | Likely cause | Open | End on |
|---|---|---|---|
| A file reads with the whole row in one column, or non-ASCII labels are garbage, or leading-zero codes vanish, or the header looks like a title / `Unnamed: N` | Wrong delimiter / encoding / BOM / type inference / header row on a file source | `knowledge/file-source-grain.md` (PY-PB-011) | the recorded finding + File-source addendum |
| Excel row count includes a phantom blank/summary row, or the wrong sheet was read | Merged/multi-row header, or first-sheet-assumed | `knowledge/file-source-grain.md` (PY-CN-085) | enumerated sheets + flattened header |
| Row count looks right but business observations duplicate | Shape confused with grain / candidate key not tested | `knowledge/dataframe-mental-model.md`, `knowledge/profiling-and-source-inspection.md` | `checklists/dataframe-review-checklist.md` |
| Numbers import as text / `object` dtype | Thousands separators, currency symbols, no coercion | `knowledge/cleaning-and-standardization.md` (PY-CN-033) | row-count ledger + verdict (in file) |
| Leading-zero IDs vanished or currency precision changed | Logical type does not match storage dtype | `knowledge/pandas-dtypes-and-schema.md` | `checklists/dataframe-review-checklist.md` |
| `channel`/`region` shows more values than its domain | Casing / whitespace drift | `knowledge/cleaning-and-standardization.md` (PY-CN-031/032) | row-count ledger + verdict (in file) |
| Sentinel values (`-1`, `999`) summed as if real | Sentinel not mapped to null | `knowledge/cleaning-and-standardization.md` (PY-CN-034) | row-count ledger + verdict (in file) |
| Zero-fill changed totals or blank keys joined | Missing-value classes collapsed without policy | `knowledge/nulls-missing-values-and-blanks.md` | `checklists/dataframe-review-checklist.md` |
| Duplicate rows suspected | No declared uniqueness key | `knowledge/cleaning-and-standardization.md` (PY-CN-035) | row-count ledger + verdict (in file) |
| Rows multiplied or disappeared after merge | Wrong cardinality / unmatched keys / null keys | `knowledge/joins-merge-and-fanout.md` | `checklists/merge-fanout-checklist.md` |
| Sums look too big after grouping | Double-counting / wrong grain / non-additive measure summed | `knowledge/groupby-aggregation-and-grain.md` | `checklists/aggregation-grain-checklist.md` |
| Dates swap day/month, shift a day, or sort periods incorrectly | Locale/timezone/calendar contract missing | `knowledge/dates-times-and-calendars.md` | `checklists/dataframe-review-checklist.md` |
| Totals match globally but segments differ | Cancelling errors / scope mismatch | `knowledge/validation-and-reconciliation.md`, `patterns/validation-patterns.json` | `checklists/validation-reconciliation-checklist.md` |
| A sample looks fine but controls are absent | Sample substituted for reconciliation | `knowledge/validation-and-reconciliation.md` | `checklists/validation-reconciliation-checklist.md` |
| Pipeline is slow or memory grows by stage | Row-wise work / copies / object dtype / fan-out | `knowledge/performance-and-memory.md` | performance and memory verdict |
| A clean notebook is claimed as readiness | Governance boundary bypass | `knowledge/python-anti-patterns.md`, `patterns/analyzer-rules.json` | `checklists/python-pipeline-review-checklist.md` |

---

## File map

```
knowledge/   reasoning content, one domain per file
             — live foundation: dataframe semantics, profiling, dtypes, missingness,
               cleaning, joins, groupby grain, and dates/calendars
patterns/    machine-readable rule + pattern sets (JSON)
             — active analyzer, validation, positive-pattern, and candidate catalogs
checklists/  the artifacts routes end on
             — dataframe, cleaning, merge/fan-out, aggregation/grain, validation,
               and pipeline review
references/  shared schema, source map, copyright, ID conventions, training/eval seed
             — shipped: all four references + agent-training-set.{json,md}
```

## Stop rules (router level)

- If a single route answers the need, do not open a second file "for context".
- If you cannot name the artifact you will end on, you are not ready to start.
- If no route matches, stop and name the missing capability; do not free-scan the
  directory or fabricate an artifact.
- If the task is metric definition, semantic logic, or gating — stop; it belongs to
  DAX / readiness, not here.
