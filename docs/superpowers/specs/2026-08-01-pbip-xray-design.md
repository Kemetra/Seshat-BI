# PBIP X-Ray — design

**Date:** 2026-08-01
**Status:** approved by owner (brainstorm session, approach A)
**Capability id:** `pbip-xray`

## Why this exists

An open scan of candidate capabilities (verified against the committed tree,
not the roadmap backlog) found exactly one high-uniqueness gap: nothing in the
kit — and nothing in the surrounding tool landscape — reads a **committed PBIP
model as text** and reviews it the way a senior modeler would in a pull
request. Tabular Editor / BPA need a live model or a `.bim`; this kit already
parses TMDL (`src/seshat/tmdl.py`) but only for narrow per-rule scans
(D1–D8, C1). The missing layer is the **model graph**: who references whom,
what is dead weight, and what a TMDL diff *means* in business terms.

Two verbs share one graph core:

- `seshat xray` — full-model audit of a committed PBIP semantic model.
- `seshat model-diff --base <ref>` — PR-scoped semantic diff, base vs head.

## Fit with the kit's hard principles

- **Read-only observer.** Parses committed text; the diff base side comes from
  `git show <ref>:<path>` — no checkout, no working-tree mutation, no DB, no
  Power BI execution adapter (F016 stays deferred).
- **Advisory authority, no readiness effect.** Ships like
  `cross-table-lineage`: skill + CLI helper + inventory entry,
  `authority: advisory`. It never blocks, never moves a stage, and is **not**
  an 11th compass verb (the ten verbs are spec-138 territory with contract
  tests).
- **No fabricated scores.** Findings and counts only; there is deliberately no
  "model health score".
- **No duplication of enforcement.** D6 (bi-directional relationships) and D7
  (date-table marker) remain the enforcement rules; X-Ray findings *cite* them.

## Architecture

```
src/seshat/xray/
  graph.py      TMDL -> ModelGraph (frozen dataclasses). Reuses parse_tmdl,
                parse_relationships, normalize_measure_body. Nodes: table,
                column, measure, relationship. Edges: measure->measure,
                measure->column (DAX identifier extraction), relationship
                keys, sort-by, hierarchy membership.
  bindings.py   PBIR reader: visual field bindings -> bound-by-visual edges.
  audit.py      X1-X4 finding families over the graph.
  diff.py       Base-vs-head semantic classification.
  render.py     Markdown report + JSON payload (agent-consumable).

src/seshat/cli/commands/xray.py   both verbs; response envelope, categorical
                                  exit codes, and blocker payloads follow
                                  src/seshat/cli/commands/analyze.py.
.claude/skills/pbip-xray/SKILL.md agent front door (consumer capability).
```

Files stay small (200–400 lines typical); functions <50 lines, nesting <4
(CodeScene delta gate is a required PR check).

## Findings catalog

Each finding: `id`, severity `info|warning`, location, evidence, fix hint —
the same shape as `seshat check` findings, but advisory-only and **not** wired
into the check rule registry (no rule-count claims, no 9-surface wiring).

| Family | Findings |
|---|---|
| **X0 parse notice** | A `.tmdl` file `parse_tmdl` could not parse — reported once, audit continues. |
| **X1 unused fields** | Column/measure referenced by nothing scanned: no measure DAX, no relationship key, no sort-by, no hierarchy, no PBIR visual binding. Wording is `unreferenced in scanned surfaces`; RLS expressions and calc groups are scanned when present. |
| **X2 relationship risks** | many-to-many; inactive relationship with no `USERELATIONSHIP` in any measure; relationship keys of `string` dataType (statically provable from the column declaration — cardinality itself is never guessed); snowflake chains >= 3 deep. Bi-di cites D6. |
| **X3 measure graph** | Orphan measures (no visual binding, no inbound measure reference); dependency depth >= 5; duplicate-logic clusters via `normalize_measure_body` resolved through the graph (extends D3). |
| **X4 model hygiene** | Measures placed on dim tables while scanning only fact columns; unmarked date table (cites D7); default-summarized columns feeding no aggregation. |

## Semantic diff buckets

`seshat model-diff --base <ref>` classifies every model change:

- **semantic** — measure expression changed (compared on
  `normalize_measure_body`, so formatting churn never fires); relationship
  added/removed or direction/cardinality changed; column type changed;
  filter/RLS expression changed. Each semantic change renders one
  business-terms sentence (e.g. "`GrossMargin` now excludes returns: filter
  added on `is_return`").
- **cosmetic** — display folder, format string, description, lineage tags.
- **additive** — new measure/column/table, listed with what they reference.

## Error handling — fail-soft observer

The correctness core is an asymmetry: **absence of evidence never becomes a
finding.**

- Unparseable table file -> one X0 notice; the audit continues.
- Report folder absent/unreadable -> graph built without binding edges; every
  binding-dependent finding downgrades its wording ("no report scanned —
  visual usage unknown") instead of firing.
- DAX identifier extraction is heuristic (strings/comments stripped via the
  shared D3 helper); unresolvable references become `unresolved` edges and are
  excluded from unused-detection.
- Bad `--base` ref or file missing at base -> categorical blocker payload
  (code/message/recovery) + non-zero exit, same envelope as `seshat analyze`.
  A file new at head is simply `additive`.

## Testing

1. **Graph unit tests** — synthetic TMDL fixtures (<= ~2 KB): measure chains,
   `'Table'[Col]` vs `[Measure]` refs, comment/string traps.
2. **Audit tests** — one fixture per family, plus degradation tests (no PBIR
   -> X1 downgrades wording; zero false "unused").
3. **Diff tests** — synthetic base/head pairs per bucket; formatting-only
   churn must classify cosmetic.
4. **Integration** — both verbs against the committed `RetailStoreSales`
   model; clean-or-known findings pin the live repo (the `test_doctor`
   pattern).
5. **Contract/wiring** — capabilities.yaml entry validates; agent bundles
   regenerate clean (`test_committed_bundles_match_clean_regeneration`).
6. **CodeScene** — `analyze_change_set` locally before push.

## Wiring obligations

- `docs/capabilities/capabilities.yaml`: new `pbip-xray` entry
  (`state: shipped`, `authority: advisory`, `surface: skill`,
  `readiness_stage: not-stage-scoped`).
- Bundle regeneration: `python scripts/export_agent_bundles.py --repo .`
  (integrations vendor `skills/**`).
- COMPASS fast-routing row + `docs/knowledge-map.md` entry.

## Non-goals

- No 11th compass verb; no kit-router edit (`CLAUDE.md` router block is
  generated from `.seshat/kit-source.yaml` and is not touched).
- No live-model connectivity, no `.bim` support, no Power BI Desktop.
- No numeric health/quality score.
- No auto-fix; findings carry fix hints only.
- No new `seshat check` rules in this round.

## Backlog entries recorded by the same scan (not built now)

- **KPI Derivation-Lineage** (ratified `specs/044`, fail-closed spec-only) —
  044-era spec needs re-validation against the 138-era codebase; overlaps
  shipped `cross-table-lineage`.
- **Evidence replay / Reproducible Proof Card** — eligible only on the strict
  read-only-recompute reading (hard-principle auditor's knife-edge note).
