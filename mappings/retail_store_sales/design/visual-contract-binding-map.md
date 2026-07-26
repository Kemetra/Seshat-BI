# Visual -> contract binding map -- retail_store_sales

The artifact the DESIGN REVIEW signs off: proves every measure-bearing visual binds
to exactly ONE approved metric contract (no orphan visual) and that no approved
contract is silently dropped. Authored by `dashboard-design`; it NEVER invents a
metric and NEVER self-grants `dashboard_ready: pass`. ASCII, UTF-8 no BOM.

<!--
  MIGRATED to `seshat.binding-map/v1` (issue #514, Phase B) -- DRAFT AWAITING
  OWNER RE-SIGN (D5).

  What changed: a machine-readable `seshat.binding-map/v1` front section was
  ADDED, carrying the THIRD leg the F011 two-way format lacked -- the
  decision-question(s) each visual answers, resolved against the committed
  narrative brief. The signed two-way content below is PRESERVED VERBATIM: the
  same 10 visuals, the same contract per visual, the same coverage table, the same
  v04 caveat, and the original 2026-06-25 sign-off block unaltered.

  The agent did NOT re-sign this artifact. Whether the 2026-06-25 sign-off carries
  forward over the added front section, or a fresh design review is required, is
  decision D5 in `../approval-request-narrative-brief-migration.md` -- an owner
  ruling R5 explicitly reserved (a delegated mandate does not cover re-signing a
  signed artifact).

  v10 IS DELIBERATELY UNBOUND. See the "v10 held" note below the front section.
-->

```yaml
# binding-map front section -- FROZEN schema seshat.binding-map/v1
schema: seshat.binding-map/v1
table: retail_store_sales
brief: mappings/retail_store_sales/narrative-brief.md

pages:
  - id: executive_overview

visuals:
  # --- overview band: every headline answers the overview question -----------
  - visual_id: v01
    page: executive_overview
    contract: TotalSales
    decision_questions:
      - Q1
    headline: true
  - visual_id: v02
    page: executive_overview
    contract: TransactionCount
    decision_questions:
      - Q1
    headline: true
  - visual_id: v03
    page: executive_overview
    contract: AvgTransactionValue
    # serves TWO owner decisions: a headline number AND the basket-value answer
    decision_questions:
      - Q1
      - Q5
    headline: true
  - visual_id: v04
    page: executive_overview
    contract: DiscountedTransactionRate
    decision_questions:
      - Q6
    headline: false                # NOT a headline: Q6 is action-stage, and a
                                   # headline visual MUST answer an overview
                                   # question (FR-006)

  # --- change band ----------------------------------------------------------
  - visual_id: v05
    page: executive_overview
    contract: TotalSales
    decision_questions:
      - Q2
    headline: false

  # --- driver band (why / where) -------------------------------------------
  - visual_id: v06
    page: executive_overview
    contract: TotalSales
    decision_questions:
      - Q3
    headline: false
  - visual_id: v07
    page: executive_overview
    contract: TotalQuantity
    decision_questions:
      - Q3
    headline: false
  - visual_id: v08
    page: executive_overview
    contract: TotalSales
    decision_questions:
      - Q4
    headline: false
  - visual_id: v09
    page: executive_overview
    contract: AvgTransactionValue
    decision_questions:
      - Q5
    headline: false

  # v10 (TransactionCount by dim_customer_rss[customer_id], "top customers") is
  # HELD OUT of this list -- see the note below. Re-adding it needs the
  # source-profile PII write-through first.
```

### v10 held: the customer visual cannot bind yet

The signed map's tenth visual is `TransactionCount` by
`dim_customer_rss[customer_id]` ("Q6 top customers"). It is **not** in the front
section above, and that is deliberate rather than an omission:

- The narrative brief has **no customer-level question**. Customer analysis is
  `gaps[]` entry 3, because `source-profile.md` -- one of the only two permitted
  derivation inputs -- still records the `customer_id` PII question as **open**
  with `Source-ready status: warning`.
- Listing v10 with an empty or invented `decision_questions` would be an
  `orphan_visual` finding; inventing a customer question to bind it would derive
  from an input the route forbids. Both are worse than holding it.

**Unblocking it is an owner action**, prepared in
`../approval-request-source-profile-writethrough.md`: writing the already-recorded
2026-06-25 Q1 keep-ruling through to `source-profile.md` makes customer-level
publishing derivable, the gap becomes a question, and v10 binds to it.

Until then the owner's D4/W3 choice is: **write the ruling through** (v10 returns),
or **drop v10** from the design. The agent makes neither call.

## Subject area

- subject_area: `RetailStoreSales` (`gold.fct_sales_rss`)
- governed_model: `../../../powerbi/RetailStoreSales.SemanticModel`
- semantic_model_ready: `pass`

## Binding map (every visual -> exactly one APPROVED contract)

All 5 approved contracts are bound; 10 measure-bearing visuals, zero orphans.

| visual_id | visual_type | business_question | bound_contract (approved) | semantic_model_field(s) |
|-----------|-------------|-------------------|---------------------------|-------------------------|
| v01 | card | Q1 headline revenue | TotalSales | `[TotalSales]` |
| v02 | card | Q1 transaction volume | TransactionCount | `[TransactionCount]` |
| v03 | card | Q1/Q5 basket value | AvgTransactionValue | `[AvgTransactionValue]` |
| v04 | card | Q1 discount share (caveated) | DiscountedTransactionRate | `[DiscountedTransactionRate]` |
| v05 | line | Q2 trend / seasonality | TotalSales | `[TotalSales]` by `dim_date_rss[full_date]` (month) |
| v06 | bar | Q3 revenue by category | TotalSales | `[TotalSales]` by `dim_product_rss[category]` |
| v07 | bar | Q3 units by category | TotalQuantity | `[TotalQuantity]` by `dim_product_rss[category]` |
| v08 | bar/donut | Q4 channel split | TotalSales | `[TotalSales]` by `dim_location_rss[location]` |
| v09 | column | Q5 basket value by payment method | AvgTransactionValue | `[AvgTransactionValue]` by `dim_payment_method_rss[payment_method]` |
| v10 | table | Q6 top customers by activity | TransactionCount | `[TransactionCount]` by `dim_customer_rss[customer_id]` (Top N) |

> Every row cites one APPROVED contract by name + the mapped model field(s). No visual
> lacks a backing approved contract (no orphan). A measure reused across visuals (e.g.
> TotalSales in v01/v05/v06/v08) is still ONE contract bound multiple ways -- allowed;
> what is forbidden is a visual with NO approved contract behind it.

## Contract coverage (all 5 approved contracts appear)

| approved_contract | on which visuals |
|-------------------|------------------|
| TotalSales | v01, v05, v06, v08 |
| TransactionCount | v02, v10 |
| AvgTransactionValue | v03, v09 |
| DiscountedTransactionRate | v04 |
| TotalQuantity | v07 |

## Dropped contracts (record each -- no silent omission)

None. All 5 approved contracts are bound to at least one visual on the page.

## Caveat carried to the page (not a binding issue, a data-honesty note)

- v04 (DiscountedTransactionRate): the approved contract is the KNOWN-STATUS rate
  (50.37% = discounted / known status); unknown-status transactions are EXCLUDED. The
  card must footnote that 33.39% of transactions have an unknown discount status, and
  that the floor (if unknowns were treated as not-discounted) is 33.55%. Source:
  `../metrics/DiscountedTransactionRate.yaml`.

## Review sign-off (Principle V -- the reviewer's action, NOT the skill's)

- reviewer (BI report owner): `data_owner` (the user, acting as BI report owner)
- decision: `approved`
- at: `2026-06-25`

> Sign-off recorded 2026-06-25: the BI report owner reviewed this binding map (10
> visuals, all bound 1:1 to approved contracts, zero orphans, the v04 discount caveat
> noted) and approved the design. `dashboard_ready` is promoted to `pass` with a
> matching `approvals[]` entry in `readiness-status.yaml`. (Recorded by the reviewer,
> not self-granted by the skill.)
