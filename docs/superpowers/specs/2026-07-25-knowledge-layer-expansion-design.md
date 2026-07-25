# Knowledge-Layer Expansion Design

**Date:** 2026-07-25
**Status:** Approved direction; written-spec review pending
**Branch:** `codex/knowledge-layers-expansion`

## Objective

Expand Seshat BI's six public knowledge layers into a more complete, consistently
routed reasoning system:

- `retail-kpi-knowledge`
- `bi-sql-knowledge`
- `bi-dax-knowledge`
- `bi-python-knowledge`
- `bi-bigdata-knowledge`
- `bi-analyst-knowledge`

The expansion must preserve Seshat BI's agent-first contract. Knowledge layers
reason, validate, and produce reviewable artifacts; they do not execute workloads,
grant readiness, invent business policy, or bypass named-human approvals.

## Evidence Behind the Design

The repository audit found:

- all six layers have a `SKILL.md` and an `INDEX.md`;
- SQL, DAX, Big Data, KPI, and Analyst already expose substantial live routes;
- Python still advertises eleven explicitly planned or not-yet-implemented routes,
  including profiling, dtypes, null handling, joins, dates, validation, performance,
  anti-patterns, and general review checklists;
- PostgreSQL execution-plan reasoning is an explicit deferred seam in SQL;
- the public distribution includes all six layers, but some summary prose still
  refers to the original five;
- the focused baseline covering knowledge allowlisting, generated bundles, public
  command routing, Compass navigation, and knowledge contracts passes with
  68 tests and 1 platform skip.

This makes a staged expansion safer and more valuable than equal-size additions to
every layer.

## Design Principles

### 1. Route before loading

Every capability follows:

```text
SKILL.md -> INDEX.md -> only the named resources -> checklist / verdict / contract / handoff
```

New content is incomplete until it has a task route, a symptom route where
applicable, a named terminal artifact, and a stop rule.

### 2. One owner for each kind of meaning

| Concern | Owning layer |
|---|---|
| KPI business meaning, additivity intent, policy ambiguity | Retail KPI |
| SQL grain, binding, transformation, reconciliation | SQL |
| DAX filter context, measure implementation, model prerequisites | DAX |
| Single-node dataframe preparation and validation | Python |
| Distributed execution topology and scale-specific validation | Big Data |
| Decision framing and narrative order from approved metrics | Analyst |
| Stage status and approval | Readiness system, never a knowledge layer |

Cross-layer documents reference the owner. They do not copy or redefine the
owner's knowledge.

### 3. Evidence, not confidence

Every review artifact returns categorical findings, evidence, assumptions, named
blockers, and one handoff or next action. No knowledge artifact emits a numeric
confidence/readiness score or claims a live check passed without live evidence.

### 4. Progressive disclosure

`SKILL.md` remains a concise trigger and operating contract. Detailed reasoning
lives in focused knowledge files; repeatable evaluation criteria live in
checklists or machine-readable pattern files. New files stay directly discoverable
from `INDEX.md` and avoid multi-hop reference chains.

### 5. Approval safety

Expansion must not convert owner-dependent KPI policy into settled knowledge.
Same-store policy, VAT treatment, returns policy, cost method, snapshot date,
sentinel-vs-null, PII publish safety, grain approval, and business rollups remain
human decisions. Additions may improve the decision packet and blockers but may
not grant the decision.

## Delivery Architecture

### Phase 1 — Complete the Python reasoning spine

Turn the largest explicit deferred surface into live, routed capabilities:

1. dataframe mental model and core BI concepts;
2. source profiling and inspection;
3. dtype contracts and schema drift;
4. null, blank, and sentinel handling;
5. safe merge/join and fan-out diagnosis;
6. date, time, and calendar preparation;
7. validation and reconciliation;
8. performance and memory diagnosis;
9. Python anti-pattern and positive-pattern catalogs;
10. a domain-neutral worked example;
11. dataframe, merge/fan-out, validation, and pipeline-review checklists.

The Python layer remains reasoning/review only. Examples may show diagnostic
snippets, but the layer does not execute code or claim observed results.

### Phase 2 — Establish a common handoff contract

Add one concise cross-layer handoff contract that every layer can reference. A
handoff records:

- originating layer and terminal artifact;
- declared input and output grain;
- approved business definition reference, when a metric is involved;
- required fields and physical bindings;
- null/sentinel assumptions;
- filters, exclusions, and additivity constraints;
- validation/reconciliation obligations;
- unresolved decisions and named authority;
- destination layer and exact next action.

Each layer's router gains explicit inbound and outbound routes. The common contract
defines the envelope; owner layers continue to define the content.

### Phase 3 — Deepen the five established layers

#### SQL

Implement the deferred PostgreSQL execution-plan reasoning slice as a bounded,
read-only diagnostic capability:

- plan-node literacy;
- estimated-versus-actual row divergence;
- scan and join strategy interpretation;
- sort/hash spill indicators;
- index usefulness boundaries;
- a plan-review checklist and symptom routes.

It reviews supplied plan evidence; it never connects to or tunes a database.

#### DAX

Expand diagnostic coverage around:

- virtual relationships and relationship ambiguity;
- calculation groups and precedence;
- semi-additive time behavior;
- blank/zero display semantics;
- measure dependency and performance triage;
- semantic-model prerequisite handoffs.

Every route starts from an approved metric contract and known model metadata.

#### Retail KPI

Expand policy-safe coverage and improve decision support:

- add generic contracts only where meaning is stable without owner policy;
- add sufficiency and ambiguity decision packets for policy-dependent KPIs;
- strengthen derivation lineage and implementation handoffs;
- reconcile registry, router, README, and pack counts.

Owner-dependent planned contracts remain planned until a named authority settles
their policy.

#### Big Data

Add operational reasoning that is specific to distributed execution:

- observability and evidence collection;
- retry/failure and partial-output diagnosis;
- late-data/backfill strategy review;
- partition-evolution and compaction decisions;
- cost/performance evidence packets.

Engine-independent concepts continue to reference Python or SQL rather than being
duplicated.

#### Analyst

Expand decision framing without crossing into layout or metric definition:

- diagnostic question trees;
- driver and exception prioritization;
- confidence/uncertainty wording without scores;
- action-owner and review-cadence framing;
- narrative-change review when contracts or source profiles drift;
- additional domain-neutral examples and review checks.

### Phase 4 — Distribution and integration closure

For every canonical knowledge change:

- update `COMPASS.md` and `docs/knowledge-map.md`;
- update `distribution/public-knowledge-allowlist.yaml`;
- reconcile public command-surface metadata;
- update navigation fixtures and contract tests;
- regenerate both Claude and Codex bundles from canonical sources;
- review both provenance manifests;
- run `scripts/export_agent_bundles.py --check`;
- run focused knowledge/navigation tests and the broad unit suite.

Generated integration copies are never hand-edited.

## Content Contract for Every New Capability

Each capability must answer:

1. What user task or symptom triggers it?
2. Which authoritative inputs are required?
3. What reasoning steps are non-obvious?
4. What common failure modes must be checked?
5. What evidence distinguishes a clean verdict from a blocker?
6. What is the exact terminal artifact?
7. Which boundary or stop rule applies?
8. Which layer receives the handoff?

Knowledge files should use stable identifiers when the layer already has an ID
family. Checklists should be usable independently and should not require loading the
whole knowledge file.

## Commit Strategy

Work remains isolated in the linked worktree. Commits are unsigned and focused:

1. design specification;
2. implementation plan;
3. Python concepts and routing;
4. Python validation, diagnostics, patterns, and checklists;
5. shared handoff contract and cross-layer router adoption;
6. SQL execution-plan slice;
7. DAX diagnostic expansion;
8. Retail KPI policy-safe expansion;
9. Big Data operational expansion;
10. Analyst framing expansion;
11. Compass, knowledge map, distribution allowlist, and fixtures;
12. generated Claude/Codex bundles and verification closure.

If a step proves too large for a coherent review, split it into smaller commits. Never
combine unrelated layer changes merely to match this numbering.

## Verification Strategy

### Structural checks

- every skill has valid frontmatter;
- every new resource is reachable from its `INDEX.md`;
- no index routes to a missing file;
- no new deep reference chain is required;
- no generated bundle is edited directly.

### Behavioral routing checks

Add fixtures that prove representative prompts select:

- Python profiling, merge/fan-out, validation, and performance routes;
- SQL execution-plan review;
- DAX semi-additive or relationship diagnostics;
- KPI ambiguity decision packets;
- Big Data retry/backfill or observability review;
- Analyst diagnostic-question and narrative-drift routes.

Each scenario must name the expected files and terminal artifact.

### Governance checks

- no self-granted approval;
- no numeric readiness/confidence score;
- no database, Python, Spark, DAX, or Power BI execution;
- no KPI meaning invented outside Retail KPI;
- no owner-dependent policy promoted to seeded;
- no C086-specific schema generalized.

### Repository checks

Run, at minimum:

```powershell
python scripts/export_agent_bundles.py
python scripts/export_agent_bundles.py --check
pytest tests/contract/test_public_knowledge_allowlist.py
pytest tests/contract/test_public_command_surface.py
pytest tests/contract/test_generated_agent_bundles.py
pytest tests/unit/test_navigation_regression.py
pytest tests/unit/test_knowledge_contracts.py
pytest -m unit
```

Use a repository-local ignored pytest base directory when sandbox permissions prevent
the default Windows temporary directory.

## Success Criteria

The expansion is complete only when:

- Python's listed core deferred routes are live or explicitly removed with a documented
  boundary reason;
- all six layers expose consistent inbound/outbound handoffs;
- each of the other five layers gains at least one substantial, routed capability rather
  than wording-only changes;
- all new routes end on concrete artifacts and enforce their stop rules;
- canonical and generated public knowledge are byte-consistent through the exporter;
- focused routing/distribution tests and the broad unit suite pass;
- the commit history shows one unsigned, reviewable commit per completed step.

## Non-Goals

- executing SQL, Python, Spark, DAX, or Power BI;
- changing the seven-stage readiness model;
- granting human approvals;
- adding a vector database or runtime retrieval service;
- replacing domain-owner decisions with generic defaults;
- rewriting established knowledge merely for style;
- treating generated bundles as canonical sources.
