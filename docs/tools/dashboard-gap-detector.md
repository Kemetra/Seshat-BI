# Dashboard Gap Detector -- usage and boundary

- **Status:** Runtime slice shipped: `retail dashboard-gaps` (spec 117).
- **Authority category:** Product Module / `read-only`.

## What it does

`retail dashboard-gaps` is the PRE-DESIGN inventory. Before a dashboard page is
designed for a subject area, it answers the honest first question: *what is
missing that must be resolved before we can draw this page at all?*

Given a HUMAN-SUPPLIED page-intent for one table (the business questions the page
must answer, each naming its required metric(s) and slicing dimension(s) -- the
same Principle-V input `dashboard-design` requires), it classifies each required
item against the table's committed evidence and emits, per item, one categorical
status plus a named blocker where the item blocks design.

```bash
retail dashboard-gaps --table retail_store_sales --page-intent ./page-intent.yaml
retail dashboard-gaps --table retail_store_sales --page-intent ./page-intent.yaml --format json
```

### Page-intent shape

The page-intent is a caller-supplied YAML file (a Principle-V human input; the
detector reads it, never authors it):

```yaml
questions:
  - question: "Q1 headline revenue"
    metrics: ["TotalSales", "TransactionCount"]
    dimensions: []
  - question: "Q3 revenue by category"
    metrics:
      - name: "TotalSales"
        depends_on: ["Q2"]        # optional: unresolved-questions.md row id(s)
    dimensions: ["category"]
  - question: "Inventory on hand"
    out_of_scope: true            # the human notes the table can't serve this
    metrics: ["InventoryOnHand"]
```

## The five statuses (SL1's vocabulary, reused)

Every required item gets exactly one status from SL1's closed enum -- the detector
mints none:

- `Covered` -- a required metric whose contract is `readiness.status: pass` (and
  whose `binds_to` columns are present in the gold star), or a required dimension
  present in the committed `gold_star`.
- `Blocked -- needs business definition` -- a metric contract present but not
  `pass`, or a required item blocked by an OPEN owner decision in
  `unresolved-questions.md` (the blocker names the row's `Who must answer` owner
  and quotes the question verbatim).
- `Planned` -- a required metric with no contract file drafted at all.
- `Blocked -- missing field` -- a required slicing dimension absent from the
  committed `gold_star` (or a `pass` contract whose `binds_to` gold column is
  absent from the star -- an intra-artifact disagreement, never a silent
  `Covered`).
- `Out of scope` -- a required subject the human marked as outside the table's
  domain; not a clearable blocker.

Committed evidence read: `mappings/<table>/metrics/*.yaml` (contract +
`readiness.status`), `mappings/<table>/source-map.yaml` (`gold_star`), and
`mappings/<table>/unresolved-questions.md` (structured open-decision rows).

## Missing inputs

A missing page-intent, or a missing `metrics/` / `source-map.yaml` /
`unresolved-questions.md`, yields a document-level GAP naming the path checked --
never an empty inventory that reads as "nothing blocks design", and never a
fabricated required list. An item that could not be checked is reported as a gap,
never a silent `Covered`.

## What it will NOT do (the scope wall)

- **Invents nothing.** The required set is the human page-intent; a required item
  with no committed backing is a GAP to report, never a thing to synthesize.
- **Writes nothing** and opens no connection (grep-verifiable zero write calls,
  matching `approval_inbox` / `blocker_explainer` / `run_next`). It records no
  `pass`, writes no `approvals[]` or `blocking_reasons[]` entry, and moves no
  readiness stage.
- **Emits no numeric score**, coverage percentage, confidence value, priority
  number, or "N of M" count (hard rule #9). The per-item categorical status plus
  its named blocker is the only answer.
- **Adds no `seshat check` rule and is not SL1's runtime.** SL1
  (`src/seshat/rules/scorecard.py`) is the static rule that gates a committed
  scorecard's STRUCTURE; this surface reuses SL1's status VOCABULARY only (via the
  shared `coverage_status` constant) and adds no gate.
- **Designs nothing and executes nothing.** It authors no layout plan, visual
  list, or binding map (that is the gated `dashboard-design` verb, which runs
  AFTER the gaps are cleared), and writes no DAX/PBIR.
- **Generic (Principle VII):** table-parameterized; no hardcoded table/metric/
  dimension/column names.

## Neighbours (what this is, and is not)

- It reuses **SL1**'s status vocabulary, not its rule runtime.
- It is the pre-design INVENTORY; **`dashboard-design`** is the gated design verb
  that blocks per-visual DURING authoring -- this surface sees the whole page's
  walls up front.
- Its "gap" is a design-COVERAGE gap for a page's required items -- distinct from
  **spec 115's approver view** (the signer's refutation-first reading of the whole
  readiness case at an approval moment) and the **consumer-data-dictionary** (which
  GAP-marks missing column/metric MEANING citations).
