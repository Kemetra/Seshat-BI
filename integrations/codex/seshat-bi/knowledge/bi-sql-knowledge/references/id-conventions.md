# ID Conventions

Stable identifiers let the knowledge files, JSON, checklists, and training set cross-reference
each other precisely. Every ID is permanent once assigned; never renumber.

## The ID families

| Prefix | Means | Range / form | Lives in |
|---|---|---|---|
| `SC-NNN` | **Concept card** | `SC-001` .. `SC-070` | `knowledge/*.md` (one `### SC-NNN` header) |
| `SQL-AP-NNN` | **Anti-pattern** | `SQL-AP-001` .. `SQL-AP-060` | `knowledge/sql-anti-patterns.md` |
| `VP-<NAME>` | **Validation / reconciliation gate** | named (e.g. `VP-UNIQUE`, `VP-DIFF`) | `patterns/sql-validation-patterns.json` |
| `PB-SQL-NN` | **Diagnostic playbook** | `PB-SQL-01` .. `PB-SQL-19` | `knowledge/sql-diagnostics-playbook.md` |
| `SP-<NAME>` | **Practical pattern card** | named (e.g. `SP-FANOUT-SAFE-AGG`) | `patterns/sql-patterns.json` |
| `SARC-<TOPIC>-NN` | **Analyzer-rule candidate** (staged) | named+numbered | `patterns/sql-analyzer-rule-candidates.json` |
| `SAR-<TOPIC>-NN` | **Promoted draft analyzer rule** (static) | 10 rules | `patterns/sql-analyzer-rules.json` |
| `SQ-<TOPIC>-NN` | **Training question** | named+numbered | `references/agent-training-set.json` |

## Where each SC range lives (concepts -> file)

| SC range | Topic | File |
|---|---|---|
| SC-001..008 | mental model, logical order, grain, keys, counts, nulls | `sql-core-concepts.md` (+ `sql-logical-query-processing.md` for SC-002) |
| SC-005..008 | aggregation correctness | `sql-aggregation-correctness.md` |
| SC-009..014 | joins, cardinality, fan-out, anti-joins, dedup, nulls | `sql-grain-and-joins.md` |
| SC-015..020 | window functions | `sql-window-functions.md` |
| SC-021..026 | date/time analysis | `sql-date-time-analysis.md` |
| SC-027..032 | validation gates, reconciliation, freshness, idempotency | `sql-reconciliation-playbook.md` |
| SC-033..038 | performance reasoning | `sql-performance-notes.md` |
| SC-039..043 | set operations & table comparison | `sql-cookbook-extension-notes.md` |
| SC-044..058 | DML, reshaping, string cleaning (silver/gold) | `sql-transformation-patterns.md` |
| SC-059..063 | advanced date recipes | `sql-cookbook-extension-notes.md` |
| SC-064..067 | gaps & islands, recursive/hierarchical | `sql-cookbook-extension-notes.md` |
| SC-068..070 | metadata-driven profiling | `sql-cookbook-extension-notes.md` |

(A concept may be referenced from several files; its defining `### SC-NNN` card lives in exactly
one. The diagnostics playbook and transformation file re-state cards by ID, they do not redefine
them.)

## Cross-reference rules

- A concept card's **Feeds** line links the anti-patterns and analyzer candidates it informs.
- An anti-pattern (`SQL-AP-NNN`) maps to an analyzer rule/candidate where one exists.
- A pattern card (`SP-*`) links `related_concepts`, `related_anti_patterns`, `related_validation`.
- A playbook (`PB-SQL-NN`) links the `SC` / `SQL-AP` / `VP` it draws on.
- An analyzer rule (`SAR-*`) carries `promoted_from` pointing at its `SARC-*` candidate.

## Analyzer status (important)

- `SARC-*` are **staged candidates** -- reviewable, not enforced.
- `SAR-*` are **static draft skill rules** -- the 10 candidates marked `analyzer_v1`, promoted for
  review. They are **NOT** runtime enforcement: this skill wires no analyzer, CLI, or runtime. The
  remaining candidates stay staged (`analyzer_v2` / `human_guidance_only`).

## Numbering discipline

- IDs are append-only and permanent. A retired idea keeps its ID (marked deprecated), never reused.
- Book-2 (SQL Cookbook) content continues the same sequences from Book-1's maxes -- it did not
  start new ranges. The "slice" labels (Slices 1-7, C1-C7) in `source-map.md` are the **authoring
  order**, not part of any ID.
