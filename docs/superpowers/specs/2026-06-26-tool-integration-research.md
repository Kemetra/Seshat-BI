# Tool-integration research — fortifying DAX/BI via the adapter pattern

- **Date:** 2026-06-26
- **Status:** Research brief (companion to ADR-0013)
- **Method:** 7 tools assessed in parallel (Sonnet/high) against a rubric distilled from the
  real adapter pattern (ADR-0008/0009/0010 + the dbt/dagster adapter skills) → Opus synthesis.
- **Question:** which tools earn an adapter slot (advisory engine behind a gate, Tower BI
  keeping authority, no core dependency), and which force a core dep or conflate
  evidence-with-approval?

## The rubric (the actual Seshat BI pattern)

An adapter MAY: read approved artifacts (by path + git ref), execute approved steps **after**
the gate clears, write derived `evidence[]` using the four-status vocabulary
(materialized / failed / skipped / blocked — never the readiness token `pass`). An adapter
MUST NOT: define meaning (grain/PK/PII/metric logic); move a stage to `pass` or write
`CLEARED`/`approvals[]`; self-approve or invent a parallel marker; **add a dependency to the
stdlib-only `retail check` core**; emit a numeric/confidence score (hard rule #9); commit
real secrets; or run around an uncleared gate. Shape = a `.claude/skills/<name>/` skill
(declares one of five authority categories + one connectivity level), **not** a new
`retail check` verb and **not** a new readiness stage. The hinge: *tool success = evidence;
Core Authority + a named human = approval.*

## Ranked fit table

| tool | gap closed | layer / stage | engine-vs-brain | optional/headless | new dep | effort | leverage | verdict |
|------|-----------|---------------|-----------------|-------------------|---------|--------|----------|---------|
| **Tabular Editor 2 BPA** | L2 best-practice breadth (~80 generic rules vs D1–D11) | L2 / Semantic Model Ready | clean advisory engine | yes (skip-safe) | .NET binary in `tools/`; none to core | medium | medium | **PILOT** |
| **pbi-tools (extract+diff)** | headless PBIX→PBIP extract + model diff (opaque-`.pbix` hole) | Semantic Model Ready | clean (extract/diff only; `compile` walled off) | yes (skip-safe) | .NET binary in `tools/`; none to core | medium | medium | **PILOT** |
| **sqlglot + DuckDB** | $$-tokenizer hole / L4 value proxy | L1/L2 + L4 | fits if lazy — but the real fixes need neither | yes (lazy) | sqlglot=tools, DuckDB=db | high | medium | **PILOT (scoped to `tools/`)** |
| **Great Expectations** | column-level DQ (null/enum/range) at silver/gold | medallion DQ / Stage 3–4 | clean if evidence-only; vocab-collision risk | yes (lazy) | ~40 transitive pkgs (`[dq]`) | high | low | **DEFER** |
| **sqlfluff** | SQL style/format on migrations | pre-L1 SQL substrate | clean read-only linter | yes | PyPI dev extra | medium | low | **DEFER** |
| **OpenLineage** | column-level transform provenance for source-drift | L2 provenance | poor — emitter inside jobs, not a gated reader | borderline | client + external backend | high | low | **DEFER** |
| **DAX Formatter API** | deferred L1 syntax/format | L1 | network service crosses trust boundary | **no** | external network service | medium | low | **NO** |

## Per-tool reasoning

### Tabular Editor 2 BPA — PILOT
Adds the long tail of generic L2 checks (fully-qualified column refs, ISINSCOPE
anti-patterns, redundant args, display-folder edge cases) the home-grown D1–D11 don't cover.
Cannot reach L3 contract-drift (the 50.37-vs-33.55 denominator class is structurally out of
BPA's scope) or L4 value. Ships as `tabular-editor-bpa-adapter` (Execution Adapter /
local-only), runner in `tools/bpa-runner/`, resolved via `TABULAR_EDITOR_PATH`; skip-safe.
The F038 spec already exists and names the FR-010 human seam (no promotion-to-mandatory
without owner approval). **Make-or-break:** does TE2 parse committed TMDL without a `.bim`
conversion or live Desktop? Curate the ruleset to drop rules duplicating D1/D2/D4/D5/D6.

### pbi-tools (extract + diff) — PILOT
Closes the one path `retail check` can't handle: a binary `.pbix` delivered instead of a
committed PBIP `definition/` folder leaves the model opaque to `tmdl.py`. pbi-tools does a
headless PBIX→PBIP extract (no Desktop) — a pre-processor that *produces* the TMDL D1–D11
read, not a DAX engine. **Highest-severity MUST-NOT:** its `compile` command (PBIP→.pbix→
Service) is F016's publish territory; the skill carries an explicit MUST-NOT-invoke-`compile`
clause. Shares the .NET runtime with F038. **First step:** spike `pbi-tools extract` headless
and confirm the output `model.tmdl` parses under `tmdl.py` (format-drift smoke test).

### sqlglot + DuckDB — PILOT, scoped to `tools/` (the real fixes need neither)
sqlglot targets the $$-tokenizer hole; DuckDB targets the L4 value proxy. **But:** the
$$ fix is a single dollar-tag regex branch in `tokenize_sql`/`strip_sql_comments`
(stdlib-only, per the M2 design) — an sqlglot-AST rewrite would re-test all S-rules for a
one-branch problem and contradict ADR-0001 (hand-rolled tokenizer, no PyPI parsers). And the
L4 proxy is already designed for lazy psycopg2 (already the `[db]` extra); DuckDB adds a C++
binary without escaping the DB-connected class, and Principle III bars a DuckDB/Parquet gold
substrate. Both tools belong in the optional `tools/` periphery for *future, separate* use
cases (transpile/migration-safety lint), never as core replacements.

### Great Expectations — DEFER
Clean engine in principle, but `[dq]` pulls ~40 transitive packages (pandas/numpy/pydantic/
marshmallow) — heavier than any precedent — and a column-DQ evidence category does not exist
in the readiness spine, so adoption needs a new ADR (sixth evidence category). It duplicates
`retail validate`'s four load-bearing gates (two-sources-of-truth risk) and its pass/fail
vocabulary collides with the four-status execution vocabulary. Defer until a real column-DQ
gap is felt at a gold table.

### sqlfluff — DEFER
No open S-rule gap: S1–S8 already cover all structural/semantic SQL governance; sqlfluff adds
only *style* findings that gate nothing, and its grammar risks false positives on the repo's
tuned Postgres constructs (dollar-quoting, `::` casts, Arabic literals). Strongest future use
is dbt-Jinja linting once F029 ships runtime files; wiring it before then violates docs-first.
Keep as a possible future `stages: [manual]` pre-commit entry, never in the `retail check` hook.

### OpenLineage — DEFER
Worst engine-vs-brain fit: an event *emitter inside running jobs*, not a gated reader of
committed approval — it needs a separately-built brain-shaped consumer plus an external
metadata backend (Marquez/OpenMetadata), a new external-service boundary beyond the
single-Postgres scope. Duplicates F014 source-drift's column-change classification, and
lineage-impact scores would violate the no-score rule. Premature: F029/F030 have no runtime
code to instrument yet.

### DAX Formatter API — NO
Hard disqualifier: a **network service** (external trust boundary) that makes CI fail closed
when unavailable, breaking the headless/stdlib-only invariant. Compounding: it's a
pretty-printer, not a parser — format-success is not a reliable L1 verdict. The L1 gap is
already low-leverage (PBI Desktop refuses to serialize unparseable DAX). Do not build.

## How this composes with the deferred DAX work (Mission 2)

**None of the surveyed tools change the build-vs-buy call** on M2's deferrals — the decisive
finding:

- **$$ tokenizer → BUILD in stdlib**, don't buy sqlglot (one regex branch vs a full lexer
  rewrite + ADR-0001 conflict).
- **L4 value proxy → BUILD with lazy psycopg2**, don't buy DuckDB (psycopg2 already `[db]`;
  DuckDB adds a binary and brushes Principle III).
- **L3 ops** — already shipped stdlib-only via `metric_drift.py`; no tool needed.

**Net + sequence:** the two real PILOTs (BPA, pbi-tools) are `.NET binaries under `tools/``
that strengthen Stage 5 without touching the stdlib core or the gate — the F038-precedent
adapter shape. Ship (1) the `$$` tokenizer branch first (smallest, most urgent correctness
fix), (2) the F038 BPA spike, (3) the pbi-tools extract spike — all independent, none expands
the core dependency set.
