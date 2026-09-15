# Reconciliation Report -- `finance_gl_actuals`

> LIVE acceptance run (RC2 / RC15 / RC16), recorded after silver + gold were applied
> and `seshat validate --source-map mappings/finance_gl_actuals/source-map.yaml`
> returned exit 0 (0 findings). Figures are as-observed. ASCII only.

---

## Run header

| Field | Value |
|-------|-------|
| Table id | `finance_gl_actuals` |
| Silver object | `silver.finance_gl_actuals` (5,000 rows) |
| Gold objects | `gold.fct_gl_actuals_fgl` + `dim_account_fgl` / `dim_department_fgl` / `dim_cost_center_fgl` / `dim_date_fgl` / `dim_fiscal_period_fgl` |
| Run date | 2026-09-15 |
| DB cluster / database | local Docker Postgres (identity digest only: `mappings/finance_gl_actuals/db-provenance.json`) |
| Run by | agent (`seshat validate`, read-only) |
| Connection | READ-ONLY for validate; credentials from the gitignored `.env`; no writes during validate |

## 1. PK uniqueness (RC2) -- on the TRANSFORMED silver rows

| Check | Expected | Observed |
|-------|----------|----------|
| `COUNT(*) = COUNT(DISTINCT (journal_entry_id, line_id))` | equal | 5,000 = 5,000 -- PASS |
| `0` NULL PK values | 0 | 0 -- PASS |

## 2. Date-dim coverage (RC15)

| Check | Expected | Observed |
|-------|----------|----------|
| `dim_date_fgl` spans every fact `posting_date` (2024-01-01 .. 2025-12-31), contiguous | 731 days, no gaps | 731 rows, min/max match fact, 0 fact dates outside -- PASS |

## 3. Orphan FKs (RC16)

| Fact FK | Dimension | Expected orphans | Observed |
|---------|-----------|------------------|----------|
| `account_sk` | `dim_account_fgl` | 0 | 0 -- PASS (0 rows on `-1`) |
| `department_sk` | `dim_department_fgl` | 0 | 0 -- PASS (0 rows on `-1`) |
| `cost_center_sk` | `dim_cost_center_fgl` | 0 | 0 -- PASS (0 rows on `-1`) |
| `date_sk` | `dim_date_fgl` | 0 | 0 -- PASS (no `-1` date member; S8) |
| `fiscal_period_sk` | `dim_fiscal_period_fgl` | 0 | 0 -- PASS (0 rows on `-1`) |

Clean fixture: B1/C1 did not refuse any rows (every natural key matched).

## 4. Cross-layer measure reconciliation (RC16)

| Measure | Silver | Gold | BI | Match? |
|---------|--------|------|----|--------|
| `debit_amount` (sum) | 31,135,795.20 | 31,135,795.20 | n/a | PASS (penny-exact) |
| `credit_amount` (sum) | 31,135,795.20 | 31,135,795.20 | n/a | PASS (penny-exact) |
| `amount` (sum) | 62,271,590.40 | 62,271,590.40 | n/a | PASS (penny-exact) |
| row count | 5,000 | 5,000 | n/a | PASS |

Debit total equals credit total (double-entry still holds through gold).

## Verdict

**PASS** -- `seshat validate --source-map mappings/finance_gl_actuals/source-map.yaml`
exit 0, 0 findings. PK unique on transformed silver, date coverage complete, 0 orphan
FKs across 5 FKs, penny-exact reconciliation on three measures. Gold Ready satisfied
for this table.

Budget remains separately blocked: `finance_gl_budget` still cannot load
`validate_targets` (no `gold_star.date_dimension`; FR-010).

## See also

- Provenance (no raw host): `db-provenance.json`
- Rulings applied in gold SQL: `approval-decision-model-integrity.md` (A1, B1, C1)
- Readiness: `readiness-status.yaml`
