# BI Python Knowledge Router

Route the task to the **fewest** files that answer it. Open those files only. End on
the named artifact. Do not pre-load the whole `knowledge/` directory.

> **Initial seed.** Only the routes in **Live routes** resolve to files shipped in
> this PR. Everything under **Planned routes** is **not yet implemented** — do not
> open those files; they do not exist yet. When a planned slice lands, its route
> moves up into the live tables.
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
| Profile a **standalone file source** (CSV / Excel) — grain, encoding, delimiter, header row, multi-sheet, inferred-type traps | `knowledge/file-source-grain.md` (PY-CN-081..085, PY-BP-007, PY-PB-011) | the File-source addendum in `templates/source-profile.md` (marked `[PROPOSED]` / `[PENDING LIVE PROFILE]`) |
| Clean / standardize strings, categories, currency, units, sentinels, or duplicates | `knowledge/cleaning-and-standardization.md` | row-count ledger + cleaning verdict (defined in the file; the cleaning-review checklist is planned — see note) |
| Aggregate / groupby at a correct grain (use the checklist as a standalone review artifact) | *(groupby knowledge file is planned)* | `checklists/aggregation-grain-checklist.md` |
| Review proposed (not-yet-active) static-analysis rules for Python pipelines | `patterns/analyzer-rule-candidates.json` | the candidate list itself (staging artifact) |
| Confirm the business meaning of a retail column | `references/source-map.md` | n/a (reference) |
| Confirm the fictional retail schema used by all examples | `references/retail-dataframe-schema.md` | n/a (reference) |
| Look up an ID family (`PY-CN-*`, `PY-AP-*`, `PY-AR-*`, …) | `references/id-conventions.md` | n/a (reference) |
| Evaluate an agent's Python reasoning against a seed Q&A set | `references/agent-training-set.json`, `references/agent-training-set.md` | n/a (eval seed) |

> **Cleaning route endpoint:** the cleaning knowledge file (PY-CN-036) ends on a
> **cleaning review checklist**, which is **planned / not yet implemented** in this
> seed. Until it lands, produce the row-count ledger and verdict described inside
> `knowledge/cleaning-and-standardization.md` itself, and treat that as the artifact.

### Symptom routes — live

| Symptom the agent observes | Likely cause | Open | End on |
|---|---|---|---|
| A file reads with the whole row in one column, or non-ASCII labels are garbage, or leading-zero codes vanish, or the header looks like a title / `Unnamed: N` | Wrong delimiter / encoding / BOM / type inference / header row on a file source | `knowledge/file-source-grain.md` (PY-PB-011) | the recorded finding + File-source addendum |
| Excel row count includes a phantom blank/summary row, or the wrong sheet was read | Merged/multi-row header, or first-sheet-assumed | `knowledge/file-source-grain.md` (PY-CN-085) | enumerated sheets + flattened header |
| Numbers import as text / `object` dtype | Thousands separators, currency symbols, no coercion | `knowledge/cleaning-and-standardization.md` (PY-CN-033) | row-count ledger + verdict (in file) |
| `channel`/`region` shows more values than its domain | Casing / whitespace drift | `knowledge/cleaning-and-standardization.md` (PY-CN-031/032) | row-count ledger + verdict (in file) |
| Sentinel values (`-1`, `999`) summed as if real | Sentinel not mapped to null | `knowledge/cleaning-and-standardization.md` (PY-CN-034) | row-count ledger + verdict (in file) |
| Duplicate rows suspected | No declared uniqueness key | `knowledge/cleaning-and-standardization.md` (PY-CN-035) | row-count ledger + verdict (in file) |
| Sums look too big after grouping | Double-counting / wrong grain / non-additive measure summed | *(groupby knowledge file is planned)* | `checklists/aggregation-grain-checklist.md` |

---

## Planned routes (not yet implemented)

These routes are part of the intended layer but their knowledge/checklist files are
**not in this seed**. Do not open these files — they do not exist yet.

| Intended route | Planned file | Status |
|---|---|---|
| Understand what a dataframe *is* in BI terms | `knowledge/dataframe-mental-model.md`, `knowledge/python-core-concepts-for-bi.md` | planned / not yet implemented |
| Profile a freshly loaded source (general dataframe profiling) | `knowledge/profiling-and-source-inspection.md` | planned / not yet implemented — for a **file source** (CSV/Excel), the file-specific slice `knowledge/file-source-grain.md` is **live** (see task routes) |
| Judge or fix dtypes / detect schema drift | `knowledge/pandas-dtypes-and-schema.md` | planned / not yet implemented |
| Decide how to handle nulls / blanks / sentinels (full slice) | `knowledge/nulls-missing-values-and-blanks.md` | planned / not yet implemented |
| Merge/join two dataframes safely | `knowledge/joins-merge-and-fanout.md` | planned / not yet implemented |
| Aggregate / groupby at a correct grain (knowledge file) | `knowledge/groupby-aggregation-and-grain.md` | planned / not yet implemented |
| Parse dates / build period columns | `knowledge/dates-times-and-calendars.md` | planned / not yet implemented |
| Validate / reconcile a result before handoff | `knowledge/validation-and-reconciliation.md`, `patterns/validation-patterns.json` | planned / not yet implemented |
| Diagnose slowness or memory blowup | `knowledge/performance-and-memory.md` | planned / not yet implemented |
| Review a Python pipeline against active rules | `knowledge/python-anti-patterns.md`, `patterns/analyzer-rules.json` | planned / not yet implemented |
| Recommended positive patterns | `patterns/python-patterns.json` | planned / not yet implemented |
| Find an original worked retail example | `knowledge/python-retail-examples.md` | planned / not yet implemented |
| Cleaning review checklist (cleaning route endpoint) | `checklists/cleaning-review-checklist.md` | planned / not yet implemented |
| Dataframe review checklist | `checklists/dataframe-review-checklist.md` | planned / not yet implemented |
| Merge / fan-out checklist | `checklists/merge-fanout-checklist.md` | planned / not yet implemented |
| Validation / reconciliation checklist | `checklists/validation-reconciliation-checklist.md` | planned / not yet implemented |
| Python pipeline review checklist | `checklists/python-pipeline-review-checklist.md` | planned / not yet implemented |

---

## File map (this seed)

```
knowledge/   reasoning content, one domain per file
             — shipped: cleaning-and-standardization.md
patterns/    machine-readable rule + pattern sets (JSON)
             — shipped: analyzer-rule-candidates.json (candidates only, not active)
checklists/  the artifacts routes end on
             — shipped: aggregation-grain-checklist.md
references/  shared schema, source map, copyright, ID conventions, training/eval seed
             — shipped: all four references + agent-training-set.{json,md}
```

## Stop rules (router level)

- If a single route answers the need, do not open a second file "for context".
- If you cannot name the artifact you will end on, you are not ready to start.
- If a route you want is under **Planned routes**, the file does not exist — do not
  fabricate its contents; stop and note the slice is not yet built.
- If the task is metric definition, semantic logic, or gating — stop; it belongs to
  DAX / readiness, not here.
