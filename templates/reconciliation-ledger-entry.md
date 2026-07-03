# Reconciliation Ledger Entry -- `<table-id>`

> **GENERIC template -- append one entry per reconciliation result to a table's ledger**
> (per-table, under `mappings/<table>/` per ADR 0003; concrete store deferred). Copy the
> ENTRY block below, fill every `<placeholder>` with a MEASURED value, and APPEND it --
> never edit a prior entry. See `docs/readiness/gold-ready.md` (the stage this serves)
> and `templates/reconciliation-report.md` (the point-in-time complement).
>
> **A history layer, NOT a validator.** This records the verdict the existing
> `retail validate` reconciliation check (RC16, feature 004) already produced -- it
> RECOMPUTES nothing and adds NO new gate (Principle VIII; hard rule #4 unchanged).
>
> **Append-only.** Recording a new result ADDS an entry; it never mutates or deletes a
> prior one. A wrong past entry is SUPERSEDED by appending a corrective entry that
> references it -- never edited in place.
>
> **Binary verdict, no score.** Penny-exact = `pass`; ANY non-zero delta = `fail`. There
> is NO `warning`/score middle value for the reconciliation number, and NO fabricated
> confidence number anywhere (roadmap rule #9). Every numeric field is a MEASURED value
> or a measured difference; a delta is recorded to the penny, never rounded to a verdict.
>
> **Did-not-run = NO entry.** If `retail validate` could not run (no DSN / no `db`
> extra), do NOT write a fabricated `pass` or `0` delta -- write NO entry at all
> (absence over fabrication; gold-ready.md deferred-mode rule).
>
> **DESIGN-ONLY this slice.** No storage runtime, no auto-append writer, no query CLI is
> built (roadmap F015 "Later" tier; hard rule #8). The two example entries below prove
> the shape by hand.
>
> **Generic, not C086.** Placeholders only; C086 is cited as the eventual filled
> instance, never copied. ASCII only, UTF-8 no BOM; secrets only in the git-ignored `.env`.

---

## ENTRY block (copy-and-append; one per reconciliation run)

### Provenance

| Field | Value |
|-------|-------|
| Table id | `<table-id>` |
| Silver object | `silver.<table_name>` |
| Gold objects | `gold.fct_<...>` + `gold.dim_<...>` |
| Run timestamp | `<YYYY-MM-DDTHH:MM:SSZ>` (precise enough to order same-day re-runs) |
| Run id (optional) | `<run-id>` (disambiguates two runs the same second) |
| Actor | `<agent | analyst>` |
| DB cluster / database | `<cluster_id>` / `<database_name>` |
| Connection | READ-ONLY; credentials from the git-ignored `.env` (never committed) |
| Evidence | the `retail validate` run + the corresponding `mappings/<table>/reconciliation-report.md` |
| Supersedes (if corrective) | `<prior entry timestamp/run-id, or "-">` |

### Per-measure result

Record the measure set AS MEASURED at this run (do not retro-fit older entries). The
delta is silver->gold to the penny; a NULL total on a layer is a reconciliation defect
(a `fail` line), never an omitted or zero line. The BI column is `n/a` until available
(never a guessed number).

| Measure | Source total | Silver total | Gold total | BI total | Delta (silver->gold) | Line verdict |
|---------|--------------|--------------|------------|----------|----------------------|--------------|
| `<measure_a>` | `<N>` | `<N>` | `<N>` | `n/a` | `0.00` | `pass` |
| `<measure_b>` | `<N>` | `<N>` | `<N>` | `n/a` | `0.00` | `pass` |
| row count | `<N>` | `<N>` | `<N>` | `n/a` | `0` | `pass` |

### Overall verdict

- Verdict: `<pass | fail>` (penny-exact across every line = `pass`; any non-zero delta
  or NULL-total line = `fail`).
- Gold Ready effect: a `pass` entry is a valid member of `gold_ready.evidence[]`; a
  `fail` entry is a `gold_ready` blocking reason ("reconciliation not penny-exact"). This
  does NOT change the Gold Ready gate criteria.

---

## EXAMPLE 1 -- a penny-exact `pass` (generic placeholders, NOT C086)

### Provenance
| Field | Value |
|-------|-------|
| Table id | `<example_table>` |
| Silver object | `silver.<example_table>` |
| Gold objects | `gold.fct_<example>` + `gold.dim_<example>` |
| Run timestamp | `2026-01-15T09:00:00Z` |
| Actor | `agent` |
| DB cluster / database | `<cluster_id>` / `<database_name>` |
| Evidence | `retail validate` run + `mappings/<example_table>/reconciliation-report.md` |
| Supersedes | - |

### Per-measure result
| Measure | Source total | Silver total | Gold total | BI total | Delta (silver->gold) | Line verdict |
|---------|--------------|--------------|------------|----------|----------------------|--------------|
| `<measure_a>` | `1,234,567.89` | `1,234,567.89` | `1,234,567.89` | `n/a` | `0.00` | `pass` |
| `<measure_b>` | `42,000.00` | `42,000.00` | `42,000.00` | `n/a` | `0.00` | `pass` |
| row count | `100,000` | `100,000` | `100,000` | `n/a` | `0` | `pass` |

### Overall verdict
- Verdict: `pass` (every line penny-exact). Citable in `gold_ready.evidence[]`.

---

## EXAMPLE 2 -- a `fail` with a measured non-zero delta (the cent is recorded, not rounded)

This entry is APPENDED after EXAMPLE 1; EXAMPLE 1 is unchanged. A later corrective run
would append a THIRD entry referencing this one in `Supersedes`, never edit this one.

### Provenance
| Field | Value |
|-------|-------|
| Table id | `<example_table>` |
| Silver object | `silver.<example_table>` |
| Gold objects | `gold.fct_<example>` + `gold.dim_<example>` |
| Run timestamp | `2026-02-15T09:00:00Z` |
| Actor | `agent` |
| DB cluster / database | `<cluster_id>` / `<database_name>` |
| Evidence | `retail validate` run + `mappings/<example_table>/reconciliation-report.md` |
| Supersedes | - |

### Per-measure result
| Measure | Source total | Silver total | Gold total | BI total | Delta (silver->gold) | Line verdict |
|---------|--------------|--------------|------------|----------|----------------------|--------------|
| `<measure_a>` | `1,250,000.00` | `1,250,000.00` | `1,250,000.03` | `n/a` | `+0.03` | `fail` |
| `<measure_b>` | `43,500.00` | `43,500.00` | `<NULL>` | `n/a` | `NULL total` | `fail` |
| row count | `101,200` | `101,200` | `101,200` | `n/a` | `0` | `pass` |

### Overall verdict
- Verdict: `fail`. Drift: `<measure_a>` gold exceeds silver by `+0.03` (a join fan-out or
  filter is duplicating rows); `<measure_b>` gold total is NULL (a reconciliation defect,
  recorded as a `fail` line, never omitted).
- Gold Ready effect: a `gold_ready` blocking reason -- "reconciliation not penny-exact"
  (`+0.03` on `<measure_a>`; NULL gold total on `<measure_b>`). The stage is `blocked`,
  not silently `pass`.

---

## Gold Ready evidence citation (how an entry wires into the spine)

A `pass` entry is cited in `mappings/<table>/readiness-status.yaml`:

```yaml
stages:
  gold_ready:
    status: "pass"
    evidence:
      - "mappings/<table>/reconciliation-ledger.md entry 2026-01-15T09:00:00Z (pass, penny-exact)"
    blocking_reasons: []
```

A `fail` entry instead populates `gold_ready.blocking_reasons[]` and keeps the stage
`blocked`. The ledger never edits the status; it supplies the evidence/blocker text.

## See also

- The check it records (never recomputes): `../src/retail/validate.py` (RC16,
  feature 004); the point-in-time complement: `reconciliation-report.md`.
- The stage it advances: `../docs/readiness/gold-ready.md`; the spine:
  `../docs/readiness/readiness-model.md`; the status shape:
  `readiness-status.yaml`.
- RC16 (cross-layer reconciliation + 0 orphan FKs):
  `../docs/decisions/0002-retail-cleaning-defaults.md`.
- The roadmap row: `../docs/roadmap/roadmap.md` (F015, Layer 4, "Later"). The
  cited instance is a filled worked example under `../docs/worked-examples/`,
  not the schema.
