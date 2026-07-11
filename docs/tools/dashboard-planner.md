# Dashboard Planner -- usage and boundary

- **Status:** Runtime slice shipped: `retail dashboard-planner` (spec 116).
- **Authority category:** Product Module / `read-only`.

## What it does

`retail dashboard-planner` answers one recurring owner question: *is this new
dashboard idea genuinely new, or a repeat of a page we already have?* Given a
PROPOSED dashboard idea for a subject area, it returns ONE categorical verdict --
`new` / `extends <page>` / `duplicate of <page>` -- by comparing the proposal
against the target table's committed design corpus.

```bash
# free-text proposal
retail dashboard-planner --table retail_store_sales --proposal "TotalSales by category"

# explicit structured tuples (repeatable): <business_question>::<contract>::<dimension>
retail dashboard-planner --table retail_store_sales \
  --tuple "Q3::TotalSales::category" --tuple "Q5::AvgTransactionValue::payment_method"

# read the proposal from a file, or emit the machine shape
retail dashboard-planner --table retail_store_sales --proposal @proposal.txt
retail dashboard-planner --table retail_store_sales --proposal "OrderCount by channel" --format json
```

## How the verdict is decided

The comparison corpus is the target table's committed design directory
`mappings/<table>/design/` -- `dashboard-layout.md`, `visual-list.md`, and the
authoritative `visual-contract-binding-map.md`. Each committed page is reduced to
the SET of its `(business_question, bound_contract, dimension)` tuples; the match
key is `(bound_contract, dimension)` compared by EXACT committed value (never by
question-text similarity, never fuzzily equating near-match names).

The proposal is reduced to the same tuple shape AS GIVEN and the verdict is a
DETERMINISTIC SET RELATIONSHIP:

- `duplicate of P` -- the proposal has >= 1 readable tuple, shares >= 1 with page
  P, and EVERY proposal tuple is covered by P.
- `extends P` -- the proposal shares >= 1 tuple with P and adds >= 1 tuple absent
  from P (the added tuples are named, with any cross-page coverage recorded).
- `new` -- the proposal shares no `(bound_contract, dimension)` tuple with any
  committed page (an empty / no-readable-tuple proposal is `new`, never a
  vacuously-true duplicate).

When tuples match rows on more than one page, the fixed precedence
`duplicate` > `extends` > `new` names the single strongest-matched page. There is
NO overlap number, NO threshold, and NO ranking -- the decision reduces to set
membership over committed facts.

## New by absence

If the target table has no committed `mappings/<table>/design/` corpus (or it is
empty/unreadable), every proposal is `new` explicitly qualified as *by absence --
no committed dashboard design found at <path>*, naming the path checked. Absence
is never presented as "compared against pages and found distinct", and no
committed page is fabricated.

## What it will NOT do (the scope wall)

- **It computes no score and no overlap number** (hard rule #9). The three verdict
  values are categorical; the decision is set membership, never a similarity
  percentage, confidence value, threshold, or ranking.
- **It WRITES NOTHING and opens no connection.** No file-write path exists
  (grep-verifiable zero write calls), matching the shipped read-only surfaces
  `approval_inbox`, `blocker_explainer`, `run_next`. It prints only; it never
  edits the design artifacts, `readiness-status.yaml`, or any file, and never
  opens a DB / Power BI / network connection.
- **It invents nothing.** It classifies the proposal as given -- no invented page,
  visual, metric, or business question, and no enrichment. A proposal measure with
  no committed contract is treated as adds-new, never matched by inventing a
  contract.
- **A `new` verdict is NOT clearance to build and NOT a gate pass.** The planner is
  gate-agnostic: it neither enforces nor clears `no_dashboard_before_metric_contracts`
  / `semantic_model_ready`, adds no `retail check` rule, and moves no readiness
  stage. The human decides build / extend / drop.
- **It does not rank proposals or recommend which to build**, and it is single-
  table (no cross-table dedup).

## Neighbours (what this is, and is not)

- It **retargets** the shipped `.claude/workflows/idea-engine.js` verdict shape
  (new / extension / duplicate for repo feature ideas) to DASHBOARD ideas; it does
  not import or re-run that JS workflow.
- It **reads** the `dashboard-design` verb's Stage-6 output as its comparison
  corpus, but authors, edits, and gates nothing there.
- It is **not** `dashboard-qa` (the anti-pattern catalog in
  `powerbi-dashboard-design`), which critiques a BUILT page's visuals for design
  defects. This planner triages whether a PROPOSED page duplicates an existing one.
