# Reconciliation Report -- `<table_id>`

> **GENERIC TEMPLATE.** This is the blank that a table's live acceptance run fills.
> Copy it per table, replace every `<placeholder>`, and record real numbers. It is one of
> the five **source-mapping gate** artifacts (architecture doc Sec 5) and the *last* one in
> the workflow -- the others are authored before silver SQL; this one is filled only after
> silver and gold are built and a live DB is reachable.
>
> For a **filled instance**, see a filled worked example under `docs/worked-examples/`
> (section 5), which records real silver row counts, penny-exact measure totals, and any
> rows landing on the `-1` unknown member. A worked example is a *filled instance*, not the
> universal schema -- keep its domain specifics out of this template.

---

## What this report is (and is not)

This report documents the **LIVE acceptance gates** for a medallion table: the checks that
can only be proven against a *running* database, not from committed text. They correspond
to the playbook's **Phase 5/6 validation gates** and to ADR 0002 defaults **RC2, RC15, RC16**
(`docs/decisions/0002-retail-cleaning-defaults.md`).

> **These four categories are the LIVE surface, now implemented as `retail validate`**
> (feature 004; `src/retail/validate.py`): PK uniqueness (RC2), date coverage (RC15),
> 0 orphan FKs (RC16), penny-exact reconciliation (RC16). The checks are built + fixture-
> tested; the **live run** against a real DB (needs the optional `db` extra + read-only
> credentials) is the remaining deferred step. Until that run is wired per table, results
> may be filled by a read-only analyst/agent session and pasted in below. The static,
> CI-able governance gate is the separate, already-shipped `seshat check`
> (23 rules, `src/retail/`); it does **not** cover these -- these need the data.

> **Namespace note (disambiguated -- feature 002):** the ADR ids cited here (`RC2`, `RC15`,
> `RC16`) are **ADR 0002 cleaning/modeling defaults** ("retail cleaning"), distinct from the
> governance checker's `D1-D8` TMDL/DAX rules. Distinct prefixes, no collision: a cleaning
> default reads `RC<n>`, a checker rule reads `D<n>`.

---

## Run header

| Field | Value |
|-------|-------|
| Table id | `<table_id>` (e.g. the silver/gold object family for this table) |
| Silver object | `silver.<table_name>` |
| Gold objects | `gold.fct_<...>` + `gold.dim_<...>` (one fact at silver grain + conformed dims) |
| Run date | `<YYYY-MM-DD>` |
| DB cluster | `<cluster_id>` (e.g. region/host identifier) |
| Database | `<database_name>` (the DB that actually holds the data -- confirm it is not an empty default) |
| Run by | `<analyst_or_agent>` |
| Connection | **READ-ONLY.** Credentials from the git-ignored `.env` (never committed; Power BI uses parameters, not baked-in strings). No writes are performed by this run. |

> **Read-only is a hard requirement.** This is an acceptance/validation run, not a build run.
> Connect with a read-only role and credentials sourced only from `.env`.

---

## 1. PK uniqueness (ADR RC2)

**Gate:** the silver table's row count equals the count of distinct primary-key tuples, and
there are **zero NULL PK** values. Verify on the *transformed* (silver) rows, not the raw
source -- TRIM/cast can collapse or null keys (ADR RC2; playbook Phase 5).

| Check | Expected | Observed |
|-------|----------|----------|
| Silver row count | `<N>` | `<N>` |
| Distinct PK tuples `(<pk_cols>)` | `<N>` (= row count) | `<N>` |
| NULL PK values | `0` | `<n>` |

**Result:** `<N>` rows = `<N>` distinct `(<pk_cols>)`, `0` NULL PK -> **`<PASS|FAIL>`**.

> Filled instance: see worked example section 5 (C086 silver = distinct PK = 246,916, 0 NULL).

---

## 2. Date-dim coverage (ADR RC15)

**Gate:** the gold date dimension is a **contiguous generated calendar** (built from a
`generate_series` over the full span, never `SELECT DISTINCT date`) that spans **every** real
date present in the fact, with **zero** real dates missing from the calendar (ADR RC15;
playbook Phase 6).

| Check | Expected | Observed |
|-------|----------|----------|
| Calendar span | `<min_date>` .. `<max_date>` | `<min_date>` .. `<max_date>` |
| Calendar row count | `<N_days>` (= exact contiguous span, no gaps) | `<N_days>` |
| Contiguous (no missing interior days) | yes | `<yes|no>` |
| Real fact dates outside the calendar | `0` | `<n>` |

**Result:** calendar spans every `<date_column>`, contiguous, `0` missing -> **`<PASS|FAIL>`**.

> Note: the *pattern* half of RC15 (generate_series vs distinct) is statically checkable from
> the migration SQL and is a future `seshat check` candidate; the *coverage* half here is the
> live half and cannot be proven from text (worked example sections 7-8).

---

## 3. Orphan FKs (ADR RC16)

**Gate:** **zero hard orphan FKs** across all dimensions -- every fact FK resolves to a real
dimension surrogate key. The gold star's `-1` unknown-member pattern (ADR RC14) absorbs
unresolved keys *without* creating an orphan, so a clean migration with FK constraints added
after load implies 0 hard orphans. Separately, count the rows landing on each `-1` unknown
member: those are **not** orphans, but they are a **data-quality signal** worth surfacing to
the analyst (ADR RC16; playbook Phase 6).

| Dimension | Hard orphan FKs (expected `0`) | Rows on `-1` unknown member (DQ signal) |
|-----------|--------------------------------|-----------------------------------------|
| `dim_<...>` | `<n>` | `<n>` |
| `dim_<...>` | `<n>` | `<n>` |
| `dim_<...>` | `<n>` | `<n>` |
| ... | ... | ... |

**Result:** `0` hard orphan FKs across all dims -> **`<PASS|FAIL>`**.
**DQ signals:** `<dim>` has `<n>` rows on `-1` (`<short description of the known gap>`).

> Filled instance: worked example section 5 records 0 hard orphans across 6 dims, with 71
> fact rows on the salesperson `-1` member flagged as a known attribution gap (not a defect).

---

## 4. Cross-layer measure reconciliation (ADR RC16)

**Gate:** every measure total matches **to the penny** across layers -- source -> silver ->
gold (-> BI). Reconcile **every** measure, not a sample; a single-cent drift is a FAIL to be
explained, not rounded away (ADR RC16; playbook Phase 5/6). Include the BI column once an
Import-mode model exists; until then it may be left `<n/a>`.

| Measure | Source | Silver | Gold | BI | Match? |
|---------|--------|--------|------|----|--------|
| `<measure_1>` | `<total>` | `<total>` | `<total>` | `<total|n/a>` | `<yes|no>` |
| `<measure_2>` | `<total>` | `<total>` | `<total>` | `<total|n/a>` | `<yes|no>` |
| `<measure_3>` | `<total>` | `<total>` | `<total>` | `<total|n/a>` | `<yes|no>` |
| `<measure_n>` | `<total>` | `<total>` | `<total>` | `<total|n/a>` | `<yes|no>` |
| Row count | `<N>` | `<N>` | `<N>` | `<N|n/a>` | `<yes|no>` |

**Result:** all `<k>` measures reconcile to the penny across layers -> **`<PASS|FAIL>`**.

> Filled instance: worked example section 5 reconciles 5 C086 measures silver<->gold penny-exact
> (with the fact row count equal across silver and gold).

---

## Verdict

| Category | ADR | Playbook | Result |
|----------|-----|----------|--------|
| 1. PK uniqueness | RC2 | Phase 5 | `<PASS|FAIL>` |
| 2. Date-dim coverage | RC15 | Phase 6 | `<PASS|FAIL>` |
| 3. Orphan FKs | RC16 | Phase 6 | `<PASS|FAIL>` |
| 4. Cross-layer reconciliation | RC16 | Phase 5/6 | `<PASS|FAIL>` |

**Overall:** **`<PASS|FAIL>`** -- `<one-line summary; e.g. "all four live gates pass; N DQ
signals noted for analyst follow-up" or "FAIL on category X, see notes">`.

> A FAIL here blocks "build done." Per ADR RC16 the build is not declared complete until
> 0 orphan FKs and penny-exact cross-layer totals are proven on the live data.

---

## See also

- **Method:** `docs/medallion-playbook.md` -- Phase 5 (build silver) and Phase 6 (build gold);
  the validation gates these four categories enforce.
- **Defaults:** `docs/decisions/0002-retail-cleaning-defaults.md` -- RC2 (PK on transformed
  data), RC15 (contiguous generated date dim), RC16 (cross-layer reconciliation + 0 orphan FKs).
- **Architecture:** `docs/architecture/tower-bi-agent-kit.md` -- Sec 5 (this template is the
  Phase 5/6 artifact of the source-mapping gate), Sec 7 (LIVE validator categories / the deferred
  `retail validate` surface).
- **Static gate:** `seshat check` (`src/retail/`, 23 rules) -- the already-shipped CI-able
  surface; complementary to these live gates, not a substitute.
- **Sibling gate artifacts:** `templates/source-profile.md`, `templates/source-map.yaml`,
  `templates/assumptions.md`, `templates/unresolved-questions.md`.
- **Filled instance:** a filled worked example under `docs/worked-examples/` (section 5) --
  records real silver row counts, penny-exact measure totals, and any rows landing on the
  `-1` unknown member. A worked example is a filled instance, never the universal schema.
