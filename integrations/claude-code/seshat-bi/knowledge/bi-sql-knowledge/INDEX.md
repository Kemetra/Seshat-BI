# INDEX -- route a SQL task to the right file(s)

> Read this BEFORE opening any knowledge file. Find the row that matches the task or the
> symptom, open **only** the file(s) it names, then end on the output contract / checklist in
> the last column. Do not read the whole base.
>
> **Boundary — KPI meaning lives upstream.** A KPI's *business meaning* (definition,
> additivity, required fields, grain intent, ambiguity, owner rulings) is owned by
> `skills/retail-kpi-knowledge/`. This layer owns SQL correctness and the **physical field
> binding** (logical field → real column), the silver/gold transform, and reconciliation.
> If a request is really "what does this KPI mean / which fields and grain does it need",
> route to `skills/retail-kpi-knowledge/` first, then implement here against a ready
> contract — do not invent the KPI's meaning in SQL.

## Route by task

| I need to... | Open (only these) | End on |
|---|---|---|
| **Profile a source table** | `knowledge/sql-core-concepts.md` (SC-003/004/006/008), `knowledge/sql-cookbook-extension-notes.md` (SC-068..070, metadata-driven) | `patterns/sql-validation-patterns.json` VP-PROFILE; `checklists/sql-validation-checklist.md` |
| **Identify table grain** | `knowledge/sql-core-concepts.md` (SC-003, SC-005) | one-sentence grain statement; `checklists/sql-review-checklist.md` |
| **Verify keys / uniqueness** | `knowledge/sql-core-concepts.md` (SC-004), `knowledge/sql-grain-and-joins.md` (SC-010) | `patterns/sql-validation-patterns.json` VP-UNIQUE |
| **Investigate suspected join fan-out** | `knowledge/sql-grain-and-joins.md` (SC-009..011) | `knowledge/sql-diagnostics-playbook.md` PB-SQL-01/02 |
| **Fix aggregation totals that are wrong** | `knowledge/sql-aggregation-correctness.md` (SC-005..008) | `knowledge/sql-diagnostics-playbook.md` PB-SQL-01/04/08 |
| **Reason about COUNT / COUNT DISTINCT / NULL semantics** | `knowledge/sql-aggregation-correctness.md` (SC-006, SC-008), `knowledge/sql-core-concepts.md` | `knowledge/sql-diagnostics-playbook.md` PB-SQL-03 |
| **Write validation queries** | `patterns/sql-validation-patterns.json` (VP-*), `knowledge/sql-reconciliation-playbook.md` (SC-027..029, SC-031) | `checklists/sql-validation-checklist.md` |
| **Write reconciliation queries** | `knowledge/sql-reconciliation-playbook.md` (SC-030), `knowledge/sql-cookbook-extension-notes.md` (SC-039..043 set ops) | `patterns/sql-validation-patterns.json` VP-CONTROLTOTAL, VP-ROWCOUNT, VP-DIFF; `checklists/sql-reconciliation-checklist.md` |
| **Write deduplication logic** | `knowledge/sql-grain-and-joins.md` (SC-013), `knowledge/sql-window-functions.md` (ROW_NUMBER survivor) | `patterns/sql-validation-patterns.json` VP-DEDUP |
| **Use window functions** | `knowledge/sql-window-functions.md` (SC-015..020) | `patterns/sql-patterns.json` (window patterns) |
| **Do date / time analysis** | `knowledge/sql-date-time-analysis.md` (SC-021..026), `knowledge/sql-cookbook-extension-notes.md` (SC-059..063 recipes) | `patterns/sql-patterns.json` (date patterns) |
| **Write silver / gold SQL transformation logic** | `knowledge/sql-transformation-patterns.md` (SC-044..058), `knowledge/sql-reconciliation-playbook.md` (SC-032 idempotency) | `checklists/sql-review-checklist.md`; VP-DEDUP, VP-CONTROLTOTAL |
| **Review SQL for anti-patterns** | `knowledge/sql-anti-patterns.md` (SQL-AP-001..060) | `patterns/sql-analyzer-rules.json` (SAR-*); `checklists/sql-review-checklist.md` |
| **Reason about performance** | `knowledge/sql-performance-notes.md` (SC-033..038) | `knowledge/sql-diagnostics-playbook.md` PB-SQL-11/12 |
| **Run a diagnostic playbook** | `knowledge/sql-diagnostics-playbook.md` (PB-SQL-01..19) | the matching PB-SQL-* verdict + fix + stop rule |
| **Get training questions** | `references/agent-training-set.json` (84 graded items) | a scored answer against the rubric |
| **Get analyzer-rule candidates** | `patterns/sql-analyzer-rule-candidates.json` (SARC-*, staged), `patterns/sql-analyzer-rules.json` (10 SAR-*, static draft) | -- (review artifact; not runtime) |

## Route by symptom (jump straight to a playbook)

| Symptom | Playbook | Supporting cards |
|---|---|---|
| "My total doubled / inflated" | PB-SQL-01 | SC-007, SC-010, SC-011 |
| "Row count changed after a join" | PB-SQL-02 | SC-009, SC-010, SC-014 |
| "COUNT is higher/lower than expected" | PB-SQL-03 | SC-006, SC-008 |
| "The average looks wrong" | PB-SQL-04 | SC-008 |
| "Can't filter on an aggregate / window" | PB-SQL-05 | SC-002, SC-020 |
| "Running total / ranking is nondeterministic" | PB-SQL-06 | SC-016..018 |
| "Trend missing periods / YoY-MoM wrong" | PB-SQL-07 | SC-021, SC-023..025 |
| "Gold totals don't reconcile to source" | PB-SQL-08 | SC-005, SC-030 |
| "Gates pass but data is stale / a segment is missing" | PB-SQL-09 | SC-031, SC-023 |
| "A reload doubled the data" | PB-SQL-10 / PB-SQL-14 | SC-032, SC-013, SC-047 |
| "Slow but correct" | PB-SQL-11 | SC-033..037 |
| "Deep CTE query -- can't tell if it's right" | PB-SQL-12 | SC-038, SC-005 |
| "Two tables should match but don't" | PB-SQL-13 | SC-039..042 |
| "Subtotals / grand totals look wrong or duplicated" | PB-SQL-15 | SC-051, SC-052 |
| "Groups split by case/whitespace; a join misses obvious matches" | PB-SQL-16 | SC-054, SC-055, SC-058 |
| "Missing dates in a trend / overlaps mis-detected" | PB-SQL-17 | SC-059..062 |
| "Recursive query runs forever / islands wrong / gaps missed" | PB-SQL-18 | SC-064..067 |
| "Validation doesn't scale / the schema drifted" | PB-SQL-19 | SC-068..070 |

All playbooks live in `knowledge/sql-diagnostics-playbook.md`.

## File map (what each file holds -- open via a route above, not all at once)

```
bi-sql-knowledge/
- SKILL.md                                   the interface (start here)
- INDEX.md                                   this router
- README.md                                  overview, scope, boundaries
- knowledge/
  - sql-core-concepts.md                     SC-001..008  mental model, grain, keys, counts, nulls
  - sql-logical-query-processing.md          SC-002       clause evaluation order + consequences
  - sql-grain-and-joins.md                   SC-009..014  joins, cardinality, fan-out, anti-joins, dedup
  - sql-aggregation-correctness.md           SC-005..008  COUNT/SUM/AVG, GROUP BY completeness
  - sql-window-functions.md                  SC-015..020  OVER/partition/order/frames, ranking, LAG/LEAD
  - sql-date-time-analysis.md                SC-021..026  truncation, date spine, ranges, YoY/MoM
  - sql-reconciliation-playbook.md           SC-027..032  validation gates, control totals, freshness, idempotency
  - sql-transformation-patterns.md           SC-044..058  silver/gold: DML/MERGE, reshaping, string cleaning
  - sql-anti-patterns.md                     SQL-AP-001..060
  - sql-performance-notes.md                 SC-033..038  sargability, SELECT *, cross joins, CTE grain
  - sql-diagnostics-playbook.md              PB-SQL-01..19  symptom -> cause -> checks -> fix -> stop rule
  - sql-cookbook-extension-notes.md          SC-039..043, 059..070  set ops, date recipes, gaps/islands, hierarchy, metadata
- patterns/
  - sql-patterns.json                        practical SQL pattern cards (SP-*)
  - sql-validation-patterns.json             VP-* validation/reconciliation gate shapes (11)
  - sql-analyzer-rule-candidates.json        SARC-* staged candidates
  - sql-analyzer-rules.json                  SAR-* 10 promoted draft rules (static, not runtime)
- references/
  - agent-training-set.json                  84 graded Q&A across all topics
  - source-map.md                            attribution + per-slice derivation log
  - copyright-safety.md                      what was distilled vs never reproduced
  - id-conventions.md                        the ID scheme + cross-reference rules
- checklists/
  - sql-review-checklist.md                  pre-merge review of a SELECT/transform
  - sql-validation-checklist.md              build a validation gate set for a table
  - sql-reconciliation-checklist.md          tie source <-> silver <-> gold
```

## Future extension

**PostgreSQL execution-plan reasoning is deferred to a later EP slice.** This layer reasons
about SQL *correctness and trust*; engine-specific plan reading (EXPLAIN/ANALYZE, costs, index
and join strategies) is intentionally out of scope here and will arrive as a separate slice.
Performance content in `knowledge/sql-performance-notes.md` is *reasoning* (sargability, filter
early, grain across CTEs), not plan analysis.

**Deferred seams (explicitly unclaimed here -- routed elsewhere, not silently missing):**

- **Cross-dialect SQL (SQL Server / T-SQL, MySQL, Snowflake, ...).** This layer's cards are
  engine-agnostic in intent but Postgres-flavoured in examples (dollar-quoting, `bronze/silver/
  gold` schema zones, `"`-quoted identifiers). Per-dialect identifier quoting, type/date-timestamp
  semantics, and window/aggregation portability are **not covered yet** and will arrive as a
  separate dialect slice. Reason about SQL *correctness* here; do not assume a card's syntax ports
  verbatim to another engine.
- **Standalone file sources (CSV / Excel).** A source that arrives as a file, not a DB table, is
  **not this layer's job.** Its grain, encoding, header/type-inference, and multi-sheet reasoning
  are owned by `skills/bi-python-knowledge/` (route: *profile a freshly loaded source* /
  *file-source grain*). Route a file source there; the SQL layer picks up only once the file has
  landed as a bronze table.
