# Unresolved questions -- `sales_c086`

> The judgment calls that block the build. All six were ANSWERED by the data-owner
> (Ahmed Shaaban) on 2026-06-29 while walking the hybrid cleaning chain. ASCII only.
> Rule: the agent recommends, the human decides.

---

- **Table id:** `sales_c086` (El Ezaby pharmacy branch C086 sales)
- **Date raised / answered:** `2026-06-29`
- **Raised by:** agent  |  **Answered by:** Ahmed Shaaban (data-owner)
- **Gate status:** `ANSWERS RECORDED -- MAP REVIEW PENDING`. The six judgment calls are
  answered, but the full map has NOT yet been reviewed/approved. **No `silver.*` SQL is
  written until the map is reviewed.** (Answers != map approval.)

---

## Questions (all answered)

| ID | Question | Who | Status | Resolution (2026-06-29, Ahmed Shaaban) |
|----|----------|-----|--------|----------------------------------------|
| Q1 | Authoritative return flag + full code->label map? | data-owner | `answered` | `Is_Return = billing_type_2 IN ('Z4','Z5','Z6','Z8','Z10')` (RC8). `Billing_Type_Label` = English map: FP=Credit Sale, Z1=Cash Sale, Z3=Delivery, Z7=Delivery-Credit, Z9=Pick-Up Order, Z4=Cash Return, Z5=Credit Return, Z6=Delivery Return, Z8=Delivery-Credit Return, Z10=Pick-Up Order Return. Code is the join key; Arabic label replaced by English (RC10). |
| Q2 | PII handling for the flagged name/contact columns? | governance | `answered` | DROP sensitive: `insurance_tel` (patient phone), `cosm_mg`, `area_mg` (manager names). KEEP as NON-PII business attributes: `person_name`/`buyer` (staff KPI names), `customer_name` (B2B company names). |
| Q3 | Single-branch site: drop to constant, or keep dim_branch? | analyst | `answered` | Keep a 1-member `dim_branch` (Branch_ID=C086, Branch_Name) + `-1` member, for multi-store conformance. |
| Q4 | Confirm the bronze->silver row filters? | analyst | `answered` | Apply BOTH: junk-division (513) + zero-value (1,680), overlap 3 -> `513+1,680-3 = 2,190` dropped -> silver 246,916. Blank-division filter must run PRE-sentinel (D12). |
| Q5 | The independent measure set? | data-owner | `answered` | Keep ONLY `Gross_Sales` + `Quantity` as fact measures. Drop net_sales, tax, dis_tax, salse_not_tax, subtotal5_discount, kzwi1, add_dis, paid. (RC9 deviation -- recorded in assumptions.md.) |
| Q6 | Contaminated `customer` field (85,911 = site code)? | analyst | `answered` | VALUE REMAP via derived `Customer_ID_Clean` = `CASE WHEN customer='C086' THEN 'WALK_IN' ELSE customer`. `dim_customer` keyed on the clean value. (Not a missing-value sentinel -- the value is present-but-wrong.) |

---

## Grain / key decision (recorded, not a blocking question)

The grain step produced a non-default key decision (recorded here for the reviewer):
- **Grain:** one invoice line item (249,106 bronze -> 246,916 silver).
- **Fact PK:** a GENERATED surrogate `Sale_SK` (over post-filter rows).
- **Natural key `(billing_document, item_no)`:** retained SILVER-ONLY as the uniqueness
  /dedup proof; NOT exposed to gold. `reference_no` -> degenerate `Invoice`.
- This is an RC2 deviation (see assumptions.md). Caveat: a bare surrogate cannot prove
  row-uniqueness; the silver-only natural key supplies that proof.

---

## Categories considered

- **Grain (RC1/RC2):** resolved -- surrogate `Sale_SK`, natural key silver-only.
- **PII (RC4):** Q2 answered (sensitive dropped; staff/company names kept).
- **Business-rollup (RC11):** none requested; none invented.
- **Sentinel-vs-null (RC5/RC6):** per-column (Phase B): grouping attrs -> `UNKNOWN`
  /`UNCLASSIFIED`; key (`personel_number`) -> NULL -> `-1`. WALK_IN is a value remap, not a sentinel.
- **Returns (RC8):** Q1 answered.
- **Hierarchy multi-parent (RC12):** resolved -- flat.

---

## Kit-level open decisions (inherited)

- **[RESOLVED -- ADR 0003]** artifact location: `mappings/sales_c086/`.
- **[NEEDS CLARIFICATION: deferred `retail validate` live surface]** -- the per-table live
  run is NOT done (no silver/gold built). `reconciliation-report.md` is PENDING.

## See also

- `docs/medallion-playbook.md` Phase 2 (the hybrid chain); `docs/decisions/0002-retail-cleaning-defaults.md`.
- Sibling artifacts: `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `reconciliation-report.md`.
