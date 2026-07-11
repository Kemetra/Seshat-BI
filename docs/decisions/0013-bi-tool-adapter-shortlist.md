# 0013 — BI/DAX tool-integration shortlist; pilot Tabular Editor BPA + pbi-tools, build the DAX deferrals in stdlib

- **Date:** 2026-06-26
- **Status:** Accepted (research/decision; pilots are spikes, not yet built)
- **Method:** 7 candidate tools assessed in parallel (Sonnet/high) against a rubric distilled
  from the actual adapter pattern (ADR-0008/0009/0010 + the dbt/dagster adapter skills),
  then an Opus synthesis. Companion research brief:
  `docs/superpowers/specs/2026-06-26-tool-integration-research.md`.

## Context

The kit has two shipped-docs-first adapter precedents — **dbt-transformation-adapter**
(ADR-0009) and **dagster-orchestration-adapter** (ADR-0010), both *Execution Adapter /
DB-connected* skills that read committed gate state, re-run the same commands CI runs, and
write only derived `evidence[]` — never a stage `pass`. The governance hinge:
**tool success = evidence; Core Authority + a named human = approval.** "Fortifying DAX/BI"
next means closing the coverage holes around **Semantic Model Ready** (L2 breadth; the
L1/L4 deferrals) and the **Silver/Gold SQL substrate** — but only with tools that keep
`retail check` stdlib-only (`dependencies = []`), add zero new gate rules / readiness
stages, and honor the entry gate, the two human seams, and the publish wall.

## The rubric (every MUST-NOT is a scoring disqualifier)

An adapter MAY: read approved artifacts, execute approved steps after the gate clears,
write derived `evidence[]` (four-status vocabulary: materialized/failed/skipped/blocked —
never `pass`). An adapter MUST NOT: define meaning, move a stage to `pass`, self-approve,
add a core dependency, emit a numeric/confidence score (hard rule #9), commit real
secrets, or run around an uncleared gate. Integration shape = a `.claude/skills/<name>/`
skill (not a new `retail check` verb, not a new readiness stage); evidence flows into the
existing `readiness-status.yaml`.

## Decision — ranked fit

| tool | gap closed | layer | optional/headless | new dep | verdict |
|------|-----------|-------|-------------------|---------|---------|
| **Tabular Editor 2 BPA** | L2 DAX best-practice breadth (~80 generic rules vs D1–D11) | Semantic Model Ready | yes (skip-safe on missing path) | .NET binary under `tools/`, none to core | **PILOT** |
| **pbi-tools (extract+diff)** | headless PBIX→PBIP extract + model diff (the opaque-`.pbix` hole) | Semantic Model Ready | yes (skip-safe) | .NET binary under `tools/`, none to core | **PILOT** |
| sqlglot + DuckDB | $$-tokenizer / L4 value proxy | L1/L2 + L4 | yes (lazy) | sqlglot=tools, DuckDB=db | **PILOT (scoped to `tools/`)** — the actual fixes need neither |
| Great Expectations | column-level DQ at silver/gold | medallion DQ | yes (lazy) | ~40 transitive pkgs | **DEFER** (needs a new evidence-category ADR; duplicates `retail validate`) |
| sqlfluff | SQL style/format | pre-L1 SQL | yes | dev extra | **DEFER** (no open S-rule gap; best for future dbt-Jinja lint) |
| OpenLineage | column-level lineage | transform provenance | borderline | client + external backend | **DEFER** (emitter, not a gated reader; external-service boundary; duplicates F014) |
| DAX Formatter API | L1 syntax/format | L1 | **no** | external network service | **NO** (network service breaks headless; pretty-printer ≠ parser) |

## The two pilots

**1. Tabular Editor 2 BPA** — strongest fit. Ships as `tabular-editor-bpa-adapter` skill
(Execution Adapter / local-only; runner in `tools/bpa-runner/`). Runs only after
`retail check` passes + Gold Ready = `pass`; findings → `evidence[]` labeled
generic/advisory; never flips Semantic Model Ready (the F038 spec's FR-010 human seam).
Skip-safe on missing `TABULAR_EDITOR_PATH`. **First step:** run the F038 spike against the
committed TMDL and prove the six gates — the make-or-break is whether TE2 parses TMDL
without a `.bim` conversion or live Desktop. Curate the ruleset to drop rules that
duplicate D1/D2/D4/D5/D6 (one source of truth per issue).

**2. pbi-tools (extract + diff only)** — closes the one path `retail check` can't handle:
an opaque binary `.pbix` instead of a committed PBIP `definition/` folder. Headless
extract produces the TMDL that D1–D11 then read (a pre-processor, not a DAX engine).
**Highest-severity MUST-NOT:** pbi-tools' `compile` command (PBIP→.pbix→Service) is
F016's publish territory — the skill carries an explicit MUST-NOT-invoke-`compile` clause.
**First step:** spike `pbi-tools extract` headless and confirm the extracted `model.tmdl`
is parseable by `tmdl.py` (format-drift smoke test). Shares the .NET runtime with F038.

## Build-vs-buy for the deferred DAX work (the decisive finding)

None of the pilot tools change the build-vs-buy call on Mission-2's deferrals:

- **`$$` tokenizer hole → BUILD (stdlib), don't buy sqlglot.** The fix is a single
  dollar-tag regex branch in `tokenize_sql`/`strip_sql_comments` (`src/seshat/sql.py`).
  An sqlglot-AST rewrite would re-test all S-rules for a one-branch problem and contradict
  ADR-0001 (hand-rolled tokenizer, no PyPI parsers). sqlglot's only home is `tools/` for a
  future transpile/migration-safety lint.
- **L4 value proxy → BUILD with psycopg2, don't buy DuckDB.** M2's own design says
  `value_proxy.py + retail value-check mirroring retail validate (lazy psycopg2)` —
  psycopg2 is already the `[db]` extra. DuckDB adds a C++ binary without escaping the
  DB-connected class, and Constitution Principle III bars a DuckDB/Parquet gold substrate.
- **L3 ops** — already shipped stdlib-only via `metric_drift.py`; no tool needed.

**Net:** the two real PILOTs are `.NET binaries under `tools/`` that strengthen Stage 5
without touching the stdlib core or the gate — the F038-precedent adapter shape. The DAX
deferrals stay build-in-stdlib; buy-tools (sqlglot/DuckDB) live in the optional `tools/`
periphery only. **Sequence:** (1) the `$$` tokenizer branch (smallest, most urgent
correctness fix — already DESIGN-ONLY from M2), (2) the F038 BPA spike, (3) the pbi-tools
extract spike — all independent, none expands the core dependency set.

## Consequences

- A clear, rubric-anchored shortlist: 2 pilots, 1 scoped-to-tools, 3 defer, 1 no.
- The stdlib-only core and the engine-vs-brain authority model are preserved by every GO/
  PILOT recommendation; the one NO (DAX Formatter API) is rejected precisely because it
  breaks the headless invariant.
- The deferred DAX work (M2) is reaffirmed as build-in-stdlib, not buy — no tool
  adoption is a prerequisite for it.
