# Assumptions -- `sales_c086`

> Which ADR 0002 defaults (RC1-RC16) this table adopted vs deviated from. Decisions made
> by walking the hybrid cleaning chain with the data-owner (Ahmed Shaaban) on 2026-06-29.
> NOT copied from the prior c086 worked example. ASCII only.

| Field | Value |
|-------|-------|
| Table id | `sales_c086` (`bronze.sales_c086_raw` -> `silver.sales_c086`) |
| Date | `2026-06-29` |
| Author | agent + data-owner (Ahmed Shaaban) |
| Source profile | `mappings/sales_c086/source-profile.md` |
| Source map | `mappings/sales_c086/source-map.yaml` |
| Per-table ADR | `<TBD -- docs/decisions/00NN-sales_c086-deviations.md at review>` |

---

## Defaults adopted as-is

| ADR id | Default summary | Adopted? | Note |
|--------|-----------------|----------|------|
| RC1  | Lowest grain; grain first. | `[OK]` | invoice line item; 2.42 lines/invoice |
| RC2  | Verify PK on data + transformed output. | `[x]` | DEVIATION -- PK is a generated surrogate; natural key kept silver-only for the proof (see below) |
| RC3  | Drop no-signal columns. | `[OK]` | knumv/ref_return_date empty; crm_order 99.5%; mat_group_2 dup |
| RC4  | Remove PII early. | `[OK]` | sensitive PII dropped (insurance_tel, cosm_mg, area_mg); staff/company names are NOT personal PII (see Q2) |
| RC5  | `''` -> NULL; missingness `'' OR NULL`. | `[OK]` | applied per-column (no global baseline -- chain change) |
| RC6  | NULL unknown facts; sentinel grouping dims only. | `[x]` | DEVIATION -- 1-member dim_branch + WALK_IN value remap (see below) |
| RC7  | Money/qty NUMERIC; leading-zero ids TEXT. | `[OK]` | Gross_Sales/Quantity numeric; ids TEXT; Line_No smallint |
| RC8  | is_return from authoritative column. | `[OK]` | from billing_type_2 Z-codes (Q1 answered) |
| RC9  | Keep independent money measures. | `[x]` | DEVIATION -- only Gross_Sales + Quantity kept; net/tax/all discount dropped (see below) |
| RC10 | Unify categorical encodings; keep code if a join key. | `[OK]` | billing_type_2 code kept; label standardized to English (Q1) |
| RC11 | Rollups only analyst-supplied; never invent. | `[OK]` | none requested, none invented |
| RC12 | Non-tree hierarchy -> flat. | `[OK]` | product hierarchy flat (36 multi-parent subcats) |
| RC13 | Idempotent numbered migration. | `[OK]` | applies at build; no silver SQL yet (gate shut) |
| RC14 | Gold Kimball star (-1 member, FK COALESCE, degenerate). | `[OK]` | 1 fact + 6 entity dims + date; degenerate Invoice |
| RC15 | Contiguous generated date dim. | `[x]` | partial DEVIATION -- contiguous YES, but date dim carries NO -1 member (see below) |
| RC16 | Reconcile totals; 0 orphans before done. | `[OK]` | deferred to live run (reconciliation-report.md, PENDING) |

> Namespace note: RC1-RC16 = ADR 0002 cleaning defaults; the checker uses D1-D8. No collision.

---

## Deviations (5)

Each cites the triggering fact. The data-owner chose these deliberately while walking the
chain; they are recorded for the reviewer to see, not buried.

| # | ADR | What we did instead | Triggering fact |
|---|-----|---------------------|-----------------|
| 1 | **RC9** | Kept ONLY 2 measures (`Gross_Sales`, `Quantity`); dropped `net_sales`, `tax`, `dis_tax`, `salse_not_tax`, `subtotal5_discount`, `kzwi1`, `add_dis`, `paid`. | No money identity holds universally (net=gross+dis_tax only 77.9%); data-owner defined the reported figures as gross + units only (Q5). |
| 2 | **RC2** | Fact PK is a GENERATED surrogate `Sale_SK` (1..246,916), not the natural key. Natural `(billing_document,item_no)` retained SILVER-ONLY for the uniqueness/dedup proof, hidden from gold. | Data-owner chose a surrogate-key model; natural key kept so RC2 uniqueness is still provable (a bare surrogate is unique by construction and cannot detect a double-load). |
| 3 | **RC6** | (a) single-branch `site` kept as a 1-member `dim_branch` (not dropped to a constant) for multi-store conformance. (b) `customer='C086'` (85,911 rows = the site code) remapped to a `WALK_IN` member via `Customer_ID_Clean` -- a VALUE REMAP, not a missing-value sentinel. | `site`/`site_name` single-valued; `customer` contaminated with the site code on 34.5% of rows (Q3, Q6). |
| 4 | **RC15** | Date dim is contiguous (adopted) BUT carries NO `-1`/unknown member. | Power BI requires a date table to be unique/contiguous with no sentinel/null rows; a `-1` member would block marking it as a date table (D10/S8). An unmatched fact date fails via `Date_SK NOT NULL`. |
| 5 | **(naming)** | Gold/BI column names use PascalCase with `_` by logic (`Product_ID`, `Gross_Sales`, `Sale_SK`), NOT the repo's silver snake_case convention. | Data-owner naming preference for the BI-facing layer. |

---

## PII classification note (Q2)

The generic "a name is probably PII" rule produced false positives here. The data-owner
reclassified on business context:
- **Sensitive -> DROPPED:** `insurance_tel` (patient phone), `cosm_mg` / `area_mg` (manager
  personal names + single-value constants).
- **NOT personal PII -> KEPT:** `person_name` / `buyer` (STAFF names, used for KPIs);
  `customer_name` (B2B insurance-customer COMPANY names, not individuals).

This refined the pipeline's PII step (it must distinguish individual/patient data from
staff and company names) -- recorded in the skill + playbook.

---

## Kit-level assumptions

- **Gold-only for Power BI.** Semantic model reads `gold` only.
- **Postgres-first medallion.** `bronze -> silver -> gold`.
- **Mapping before silver.** No `silver.*` SQL until this set is reviewed (the gate).

## See also

- `docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Sibling artifacts: `source-profile.md`, `source-map.yaml`, `unresolved-questions.md`,
  `reconciliation-report.md`.
