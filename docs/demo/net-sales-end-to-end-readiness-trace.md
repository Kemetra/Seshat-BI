# Net Sales End-to-End Readiness Trace

A single-KPI **paper trace** that walks **Net Sales** through every layer of
Seshat BI: business question → KPI contract → required fields → source/table
coverage → blockers → SQL/gold expectation → DAX/semantic readiness → dashboard
usage → readiness gates. It exists to prove the layers actually hand off to each
other on one real KPI before any broader (scale) work begins.

This is a **trace**, not a live run. It cites committed artifacts; it invents no
source data, writes no new SQL/DAX, grants no readiness, and claims no live
validation. Each step is labeled with one of three evidence tiers:

- **Proven (artifact present)** — a committed file exists and is cited.
- **Documented (not runtime-enforced)** — the gate exists as docs/templates only.
- **Needs real data / live run** — cannot be confirmed without a DB or a real source.

## Step 0 — Why Net Sales

Net Sales is the base realized-revenue KPI most other retail KPIs derive from
(growth, margin, ATV, vs-target), and it already has a **Seeded** metric contract
— the ideal single path to prove end-to-end.

## Step 1 — Business question

> "How much sales revenue did the business actually realize after discounts,
> before returns and tax?"

- **Tier:** Proven (artifact present), with one wording inconsistency to reconcile.
- **Evidence:** `skills/retail-kpi-knowledge/contracts/net-sales.md` ("Business
  question") and the F7 decision-question index in
  `skills/retail-kpi-knowledge/domains/sales-and-revenue.md` ("How much did we sell
  after returns and deductions?" → `contracts/net-sales.md`).
- **Inconsistency to reconcile (human ruling):** the F7 domain question phrases it
  as "after returns and deductions," but the contract's own business question is
  "after discounts, **before returns** and tax" with returns reported separately.
  The two are not identical; a domain owner should reconcile the wording (it does
  not change the measure, but it changes how a reader interprets "Net Sales").

## Step 2 — Net Sales KPI contract

- **Tier:** Proven (artifact present).
- **Evidence:** `skills/retail-kpi-knowledge/contracts/net-sales.md` (KPI-MC-02,
  **Status: Seeded**). Business definition: gross sales less line + header
  discounts, **pre-tax**, returns reported separately unless policy states
  otherwise. Grain: transaction line, additive to branch-day / product-day /
  customer-period. Owner: Finance (primary) + Sales.
- **Boundary:** the contract owns the *meaning*; it explicitly authors no DAX
  ("No DAX authored here"). KPI meaning stays in `retail-kpi-knowledge`.

## Step 3 — Required fields

- **Tier:** Proven (artifact present) for the field *list*; **Needs real data** for
  field *presence in a specific source*.
- **Evidence:** the contract's "Required fields" + the logical field list in
  `skills/retail-kpi-knowledge/references/source-field-requirements.md`.
- **Fields:** net sales amount per line *(assumption — or derive from gross + line
  discount + header discount)*; sale date key, branch key, product key,
  transaction id *(confirmed concept)*; cancellation/test flags, return flag /
  transaction type *(assumption)*.
- **Note:** "confirmed concept" means *expected in any retail sales model*, not
  *confirmed present in a named source* — that confirmation is a real-data step.

## Step 4 — Source / table coverage

- **Tier:** Needs real data.
- **What is needed:** a per-table KPI coverage assessment using the F8 scorecard
  template (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`)
  against a real source table — confirming that net sales amount (or gross + the two
  discount fields) and the exclusion flags are actually present. Coverage is
  expressed as status + named blocker, never a score.
- **Not done here:** this trace does not assert any specific table is "covered";
  doing so requires confirming fields against a real source (F8's own rule: a field
  merely existing is not coverage, and an absent required field is a blocker).

## Step 5 — Blockers

- **Tier:** Proven (artifact present) — the *open rulings* are named in the contract.
- **Open policy rulings (each blocks until the owner decides):**
  - **VAT (A1):** the contract assumes **pre-tax**; confirm with Finance.
  - **Returns (A2):** excluded / netted / separate measure — must be documented.
  - **Sale vs posting date (A3):** name the primary date axis.
  - **Discount fields (A5):** confirm line vs header discount to avoid
    double-subtraction.
- Until these are ruled, a strict contract instance is **Needs business
  definition** for the unresolved policy — a human ruling, not an agent decision.

## Step 6 — SQL / gold expectation

- **Tier:** Mixed — gold **table present**; reconciliation **needs real data**.
- **Evidence (present):** a gold fact table exists in the committed semantic model,
  `powerbi/Retailgold.SemanticModel/definition/tables/gold fct_sales.tmdl`, with a
  `net_amount` column the Net Sales measure sums (see Step 7). The expectation is
  that gold supplies `net_amount` (or `sales_amount` + `discount_amount` to derive
  it) at transaction-line grain.
- **Needs real data:** the SQL-knowledge reconciliation/validation expectations
  (PK uniqueness, no fan-out, gold-to-source reconciliation) are reasoning the
  `bi-sql-knowledge` layer provides; *running* them is a `retail validate` live
  step that needs a DB + the `db` extra + a filled source-map. **Not run here.**
- **No new SQL authored** in this trace.

## Step 7 — DAX / semantic readiness

- **Tier:** Proven (artifact present) for the measure; **Documented** for the
  semantic-model readiness gate.
- **Evidence (present):** a real measure exists —
  `measure NetSales = SUM('gold fct_sales'[net_amount])` in
  `powerbi/Retailgold.SemanticModel/definition/tables/gold fct_sales.tmdl`,
  alongside `TotalSales` (gross), `TotalDiscount`, and `EffectiveTaxRate`
  (`DIVIDE([TotalTax], [NetSales])`). This matches the contract's handoff note
  ("base SUM measure, with separate Gross Sales and Discount measures for
  transparency").
- **Documented (not runtime-enforced):** Semantic Model Ready
  (`docs/readiness/semantic-model-ready.md`) is "Planning (docs/templates; no
  runtime code)". The L1–L2 DAX rules (`retail check` D1–D11) and the L3
  `retail semantic-check` (contract↔DAX denominator drift) and L4
  `retail value-check` (live value proxy) are the relevant gates; L4 needs real
  data.
- **Discount-field gap (needs human ruling):** the gold model exposes a single
  `discount_amount` column (one `TotalDiscount` measure), but the contract requires
  the **line vs header discount** split to audit double-subtraction (A5). Confirm
  whether `discount_amount` already nets line + header, or only one of them, as part
  of the A5 ruling before relying on the derived path.
- **No new DAX authored** in this trace — the `NetSales` measure already exists and
  is cited as-is.

## Step 8 — Dashboard usage

- **Tier:** Documented (not runtime-enforced); gated, not approval.
- **Evidence:** the contract's "Dashboard use" lists Executive summary, Sales
  Performance, Branch/Product performance, Margin pages. The dashboard-design skill
  (`.claude/skills/powerbi-dashboard-design/`) designs **from approved contracts**.
- **Boundary:** dashboard usage here is a *step gated on contracts +
  `semantic_model_ready`*, **not** a publish approval. Using Net Sales on a page
  does not grant Dashboard Ready or Publish Ready.

## Step 9 — Readiness gates

- **Tier:** Documented (not runtime-enforced).
- **Evidence:** the readiness spine
  (`docs/readiness/readiness-model.md` + the per-stage docs) defines the gate order
  Source → Mapping → Silver → Gold → Semantic Model → Dashboard → Publish. The
  Gold/Semantic/Dashboard/Publish stage docs are each "Planning (docs/templates; no
  runtime code)".
- **Boundary:** no stage is advanced by this trace. Readiness is status + evidence +
  blockers, and a `pass` is a named human action — never self-granted.

## What is proven (on paper)

- The Net Sales **business meaning** is contracted and Seeded (Steps 1–2).
- The **required-field list** is specified (Step 3).
- A real **`NetSales` DAX measure** exists in the committed gold semantic model and
  matches the contract's handoff shape (Step 7).
- The **gold fact table** that measure sums exists (Step 6).
- The **open policy rulings** that gate a strict instance are named (Step 5).
- The **layer hand-off is coherent**: meaning (retail-kpi) → fields (sql/source) →
  measure (dax) → dashboard (gated) → readiness (human), with no layer redefining
  another's responsibility.

## What is not proven

- That any specific real source table **covers** Net Sales (Step 4 — needs an F8
  scorecard run against real fields).
- That the `NetSales` measure **reconciles** to source / P&L (Step 6/7 — needs a
  live `retail validate` / `value-check` run).
- That the documented readiness gates **pass** — they are docs/templates, not a
  runtime `pass`, and no human approval has been recorded here.

## What needs human ruling

- VAT treatment (A1), returns treatment (A2), date axis (A3), discount-field
  handling (A5) — and every readiness stage `pass`.
- The **F7 domain vs contract wording** for returns ("after returns" vs "before
  returns, reported separately") — a domain-owner reconciliation (Step 1).
- Whether the gold `discount_amount` already nets **line + header** discount, or
  only one (Step 7, part of the A5 ruling).

## What needs real data

- F8 coverage confirmation of required fields in a named source.
- Live PK/coverage/orphan/reconciliation checks (`retail validate`, needs DB + `db`
  extra + source-map).
- L4 value-proxy reconciliation of the `NetSales` aggregate to an owner-approved
  expected value (`retail value-check`).

## Verdict

This trace **proves on paper** that Net Sales has a coherent end-to-end path —
contract → fields → gold table → a real `NetSales` measure → gated dashboard use →
human-gated readiness — with every layer's responsibility intact and no boundary
crossed. It does **not** claim live validation, does **not** grant readiness, and
honestly separates what is artifact-present from what still needs real data and a
human ruling. The next real-data step (live reconciliation) is out of scope for a
trace and would be a separate, explicitly authorized run.
