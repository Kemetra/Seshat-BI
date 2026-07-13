# Source Map -- `bi-sql-knowledge`

Attribution and per-slice derivation log for the SQL knowledge layer. The slice numbering
(Slices 1-7 for Book 1, C1-C7 for Book 2) reflects the **authoring order** in which the layer
was built; the shipped skill is organized by topic (see `../INDEX.md`), not by slice. Books were
read locally for grounding only and are **not** in the repository. See `copyright-safety.md` for
the full boundary statement.

## Books

- **Primary source (Book 1):** *SQL for Data Analysis* -- Cathy Tanimura (O'Reilly, 2021).

## Slice 1 -- SQL analytical mental model, logical query processing, grain, aggregation correctness

- **Chapter 2 -- Preparing Data for Analysis.** Grounded: SQL query structure, profiling, detecting
  duplicates, deduplication with GROUP BY/DISTINCT, null handling (`coalesce`/`nullif`/`nvl`),
  missing data. Informs SC-004, SC-006, SC-008.
- **Chapter 8 -- Creating Complex Data Sets.** Grounded: order of SQL clause evaluation (logical
  query processing), CTEs/subqueries, code organization. Informs SC-002.
- **Original Seshat BI reasoning (book implicit):** table grain (SC-003), uniqueness as a
  verification step (SC-004), aggregation correctness & fan-out preview (SC-007), and the
  validation-first framing (declare grain -> verify keys -> aggregate -> sanity-check).
- **Artifacts:** `sql-core-concepts.md` (SC-001...008), `sql-logical-query-processing.md`,
  `sql-aggregation-correctness.md`, `sql-anti-patterns.md` (SQL-AP-001...009),
  `sql-slice1-diagnostic-playbook.md`, plus seed entries in the two JSON files.

## Slice 2 -- joins, relationship/uniqueness assumptions, duplicate amplification, NULL behavior

- **Chapter 2.** Grounded: duplicate detection, dedup with GROUP BY/DISTINCT, null handling.
  Informs SC-013 (dedup) and SC-014 (nulls).
- **Chapter 3 -- "Joining Data from Different Sources."** Light grounding for combining sources.
- **Original Seshat BI reasoning (book implicit):** join cardinality verification (SC-010),
  duplicate/fan-out amplification (SC-011), anti-join null traps as a validation tool (SC-012),
  the LEFT-JOIN-filter trap. The book does not teach joins or fan-out as dedicated topics.
- **Artifacts:** `sql-grain-and-joins.md` (SC-009...014, fan-out diagram), `sql-anti-patterns.md`
  (added SQL-AP-010...015), JSON candidates (added SARC-FANOUT-01, SARC-M2M-01, SARC-NOTIN-01,
  SARC-LEFTFILTER-01, SARC-DEDUP-01), training questions (joins/cardinality/fan-out/anti-joins/dedup).

## Slice 3 -- window functions for BI analytics

- **Chapter 3 -- Time Series Analysis.** Grounded: rolling windows, cumulative values,
  percent-of-total, period-over-period (YoY/MoM) -- all built on window functions. Informs SC-016,
  SC-017, SC-019.
- **Chapter 4 -- Cohort Analysis.** Grounded: cumulative/retention calculations using windows.
- **Original Seshat BI reasoning (book applies, doesn't teach):** window-function mechanics --
  OVER/PARTITION BY/ORDER BY, ROWS-vs-RANGE frames, ranking-function tie behavior, the WHERE-clause
  restriction (SC-015...020).
- **Artifacts:** `sql-window-functions.md` (SC-015...020, partition/frame diagram), `sql-anti-patterns.md`
  (added SQL-AP-016...021), JSON candidates (added SARC-WINDOW-ORDER-01, SARC-WINDOW-FRAME-01,
  SARC-WINDOW-LASTVAL-01, SARC-WINDOW-WHERE-01, SARC-WINDOW-SPARSE-01), 7 window training questions.

## Slice 4 -- date/time & time-series analysis

- **Chapter 3 -- Time Series Analysis.** Grounded: date/datetime/time manipulation, time zones, date
  math, trending, percent-of-total, indexing, rolling/cumulative, seasonality, period-over-period
  (YoY/MoM). Informs SC-021, SC-022, SC-024, SC-025, SC-026.
- **Original Seshat BI framing:** the date spine (SC-023) and half-open ranges (SC-024) as standard
  practice; the partial-vs-full-period guard (SC-026).
- **Artifacts:** `sql-date-time-analysis.md` (SC-021...026, date-spine diagram), `sql-anti-patterns.md`
  (added SQL-AP-022...027), JSON candidates (added SARC-DATE-BETWEEN-01, SARC-DATE-TRUNC-01,
  SARC-DATE-TZ-01, SARC-DATE-SPINE-01, SARC-DATE-SARG-01, SARC-DATE-PARTIAL-01), 7 time training questions.

## Slice 5 -- validation & reconciliation query patterns (Seshat BI signature)

- **Chapter 2 -- Preparing Data for Analysis.** Grounded: duplicate detection, data-quality
  profiling, nulls/missing data. Informs SC-028 (uniqueness/not-null), SC-029 (orphans).
- **Chapter 6 -- Anomaly Detection.** Grounded: outliers and the "absence of data" failure class.
  Informs SC-031 (freshness/completeness) and VP-RANGE.
- **Mostly original Seshat BI reasoning:** the validation-gate concept (SC-027), control-total
  reconciliation across layers (SC-030), idempotency/dedup verification (SC-032), and the gate
  shapes themselves. The book does not teach validation/reconciliation as a topic.
- **Artifacts:** `sql-reconciliation-playbook.md` (SC-027...032, pipeline diagram, 8 gate examples,
  reconciliation method, symptom playbook); NEW `patterns/sql-validation-patterns.json`
  (VP-UNIQUE, VP-NOTNULL, VP-REFINTEGRITY, VP-ROWCOUNT, VP-CONTROLTOTAL, VP-FRESHNESS,
  VP-COMPLETENESS, VP-DEDUP, VP-RANGE); `sql-anti-patterns.md` (added SQL-AP-028...032); JSON
  candidates (added SARC-VAL-GATE-01, SARC-RECON-TOTAL-01, SARC-RECON-GRAIN-01,
  SARC-VAL-COUNTONLY-01, SARC-VAL-FRESH-01); 7 validation/reconciliation training questions.

## Slice 6 -- SQL anti-patterns consolidation & performance basics

- **Chapter 1 -- Analysis with SQL.** Light grounding: row-store vs column-store databases. Informs
  SC-035.
- **Chapter 8 -- Creating Complex Data Sets.** Grounding: code organization, sampling, managing
  data-set size. Informs SC-036, SC-038.
- **Mostly original Seshat BI distillation:** sargability (SC-033), filter-early (SC-034), join-order
  /cardinality intuition (SC-037), and CTE-grain discipline (SC-038). Performance here is *reasoning*,
  not engine-specific tuning.
- **Consolidation:** `sql-analyzer-rule-candidates.json` now carries a `promotion_readiness` summary
  (counts by future_phase/category + the analyzer_v1 promotion shortlist). No enforceable rules file
  is created -- promotion remains a later review decision (mirrors the bi-dax-knowledge approach).
- **Artifacts:** `sql-performance-notes.md` (SC-033...038, reasoning routine, symptom table);
  `sql-anti-patterns.md` (added SQL-AP-033...037); JSON candidates (added SARC-SELECTSTAR-01,
  SARC-CROSSJOIN-01, SARC-SARG-01, SARC-CTE-GRAIN-01, SARC-FILTER-LATE-01); 6 performance training
  questions.

## Slice 7 -- consolidated diagnostics & training (skill assembly)

- **Synthesis slice (no new book chapter):** unifies the per-slice mini-playbooks into one
  symptom-driven reference and rounds out the training set; drafts the skill interface.
- **Artifacts:** `knowledge/sql-diagnostics-playbook.md` (PB-SQL-01...12, symptom->cause->checks->fix->stop
  rule, index); draft `SKILL.md` (interface, file map, ID conventions, routing, boundaries);
  6 integrative/diagnostic training questions.


## SQL Cookbook (Book 2) -- extension slices

- **Source:** *SQL Cookbook, 2nd ed.* -- Molinaro & de Graaf (O'Reilly, 2020). Extends the layer; new IDs continue the existing sequences. No recipes/EMP-DEPT tables reproduced; original retail examples only.

### Slice C1 -- set operations & table comparison (Ch 3)
- Concepts SC-039...043; anti-patterns SQL-AP-038...041; validation VP-DIFF; candidates SARC-UNIONALL-01, SARC-SETOP-COLS-01; playbook PB-SQL-13; 4 training questions. Strengthens reconciliation (row-level diff) over Slice 5's sum tie-out.


### Slice C2 -- DML & transformation logic (Ch 4)
- Concepts SC-044...048; anti-patterns SQL-AP-042...045; candidates SARC-DML-NOFILTER-01, SARC-DML-IDEMPOTENT-01, SARC-DML-MULTIMATCH-01; playbook PB-SQL-14; 4 training questions. Adds the write side (INSERT/UPDATE/DELETE/MERGE) that builds silver/gold; closes idempotency loop (SC-032).


### Slice C3 -- reporting & reshaping (Ch 12)
- Concepts SC-049...053; anti-patterns SQL-AP-046...049; candidates SARC-ROLLUP-01, SARC-GROUPINGFLAG-01; playbook PB-SQL-15; 4 training questions. Adds pivot/unpivot, ROLLUP/CUBE/GROUPING SETS, GROUPING(), bucketing/NTILE for the gold/reporting layer.


### Slice C4 -- string & data cleaning (Ch 6)
- Concepts SC-054...058; anti-patterns SQL-AP-050...052; candidates SARC-STR-NORMALIZE-01, SARC-CAST-UNSAFE-01; playbook PB-SQL-16; 4 training questions. Silver-layer cleaning: canonicalize keys, split/build delimited, pattern validation, safe parsing.


### Slice C5 -- advanced date recipes (Ch 8-9)
- Concepts SC-059...063; anti-patterns SQL-AP-053...055; candidates SARC-CALENDAR-GEN-01, SARC-OVERLAP-01; playbook PB-SQL-17; 4 training questions. Operationalizes the date spine (generate/fill), business-day arithmetic, and the canonical overlap test.


### Slice C6 -- gaps & islands + hierarchical/recursive (Ch 10, 13)
- Concepts SC-064...067; anti-patterns SQL-AP-056...058; candidate SARC-RECURSE-GUARD-01; playbook PB-SQL-18; 4 training questions. Adds consecutive-run grouping, gap detection, and recursive tree traversal with cycle/depth guards.


### Slice C7 -- metadata-driven profiling & SQL-generating-SQL (Ch 5)
- Concepts SC-068...070; anti-patterns SQL-AP-059...060; validation VP-PROFILE; candidates SARC-METADATA-DRIFT-01, SARC-GENSQL-INJECTION-01; playbook PB-SQL-19; 4 training questions. Scales the Slice 5 gates across many tables via the catalog.

### SQL Cookbook (Book 2) tallies -- extension COMPLETE
- New concepts SC-039...070 (32); new anti-patterns SQL-AP-038...060 (23); new validation patterns VP-DIFF, VP-PROFILE; new playbooks PB-SQL-13...19 (7); ~28 new training questions. Copyright-safe: no recipes/EMP-DEPT tables reproduced; original retail examples only.

## Copyright-safety confirmations (all slices)

- No long copied text from the book; explanations are distilled and rewritten in our own words.
- No book examples or datasets reproduced -- the book's retail-sales, legislators, and UFO datasets
  are not used. All examples are original Seshat BI / retail examples on the fictional schema
  (`sales`, `product`, `customer`, `store`, `date`).
- The PDF is not added to the repo; read locally for grounding only.
- Not a replacement for the book.

## Tallies (Slices 1-7) -- bi-sql-knowledge draft COMPLETE

- Concept cards: SC-001...SC-038 (38).
- Anti-patterns: SQL-AP-001...SQL-AP-037 (37).
- Analyzer-rule candidates: 33 total -- 10 promoted to enforceable (sql-analyzer-rules.json, SAR-*), 23 staged (analyzer_v2 / human_guidance_only).
- Validation gate patterns: 9 (VP-*).
- Training questions: 56.

## Analyzer-rule promotion (draft proposal)

- Promoted the 10 `analyzer_v1` candidates into NEW `patterns/sql-analyzer-rules.json` (SAR-*):
  SAR-COUNT-01, SAR-HAVING-01, SAR-NOTIN-01, SAR-LEFTFILTER-01, SAR-WINDOW-LASTVAL-01,
  SAR-WINDOW-WHERE-01, SAR-DATE-SARG-01, SAR-SELECTSTAR-01, SAR-CROSSJOIN-01, SAR-SARG-01.
  Each carries detect/fix/rationale/refs + detectability/required_inputs/related_concepts +
  promoted_from. Candidates marked `promotion_status: promoted`.
- Status: DRAFT proposal for review; the remaining 23 candidates (analyzer_v2 / human_guidance_only)
  stay staged. Installing as a real skill and wiring into a runtime are later repo actions (not done
  here -- Cowork does not edit the repo).

## Status

Slices 1-7 complete (draft). The bi-sql-knowledge draft package is finished. Not implementation, not execution, not dbt/Dagster, not a runtime
validator, not a replacement for the book -- an agent knowledge layer. Remaining (later, your decision): promote analyzer_v1 candidates into an enforceable rule set, and install as an actual skill.
