# driver-decomposition.md — how one metric decomposes into its drivers

> **GENERIC, copy-me template** (spec 087, decision-aid layer / F011A). It records,
> as plain business INTENT, how a headline metric breaks into the factors that
> move it — so "why did the number change?" is expressible as design intent, and a
> driver visual (`key_influencers` / `decomposition_tree` / `smart_narrative`) has
> a factor relation to reference.

## The DEFINE / CHECK boundary (verbatim across F009/F011A — do not drift)

This artifact **DEFINES** an attribution relation as plain intent. It is **NOT** an
implementation and **NOT** a check:

- **NO DAX, NO SQL, NO gold column** — a factor is named by its **approved metric
  contract** (F009), never by a formula or a `gold.*` column. (`SUM(...)`,
  `DIVIDE(...)`, a `gold.` reference in any field below is a defect — reject it.)
- **NO computed number, NO score** (roadmap rule #9): this records the RELATION
  (`headline = factor × factor`), never a materialized value or a 0-100 score.
- **Reference-by-name** (Principle VII): every factor is a contract NAME; a factor
  with no approved contract is an ORPHAN reference — record the blocking reason,
  do not author it.
- **Rendering is F016's** — this is intent; the live driver visual is deferred.

## Principle V — the attribution is a human judgment

*How* a metric decomposes (which factors, additive vs multiplicative) is a business
decision. The agent RECOMMENDS a decomposition; the named owner CONFIRMS it. Leave
placeholders until confirmed; never auto-invent the relation.

---

## The decomposition

```yaml
# The headline metric this artifact decomposes (an approved contract NAME).
headline_metric: "<HeadlineMetricContractName>"     # e.g. NetSales

# relation — how the headline is built from its factors. Plain intent only.
#   additive        headline = f1 + f2 + f3 ...     (e.g. Net Sales = Σ segment sales)
#   multiplicative  headline = f1 × f2 × ...         (e.g. Net Sales = Transactions × ATV)
relation: "<additive|multiplicative>"

# factors — each names an APPROVED metric contract (never a formula/column).
factors:
  - contract: "<FactorContractName>"   # e.g. Transactions
    note: "<plain-language role of this factor in the headline>"
  - contract: "<FactorContractName>"   # e.g. AverageTransactionValue
    note: "<...>"

# recommended_breakdown_dimensions — the dimensions to slice the headline by when
# explaining a move (names only; the dimension must exist in the governed model).
recommended_breakdown_dimensions:
  - "<dim_name>"                       # e.g. product_category
  - "<dim_name>"                       # e.g. branch

# owner — who confirmed this decomposition (Principle V). Blank until confirmed.
owner: "<named owner who confirmed the attribution>"
```

## Worked shape (illustrative placeholder — NOT a filled tenant instance)

> `Net Sales = Transactions × Average Transaction Value`, both factors being their
> own approved contracts; explain a Net Sales move by first checking which factor
> moved (volume vs basket), then breaking the moved factor down by
> `product_category` and `branch`. (Values here would be filled per subject area,
> never inlined into this template — Principle VII.)

## Where the filled copy lives

Co-located with the subject area's other design intent (e.g. alongside the page
blueprints under a per-subject-area working set), never in this template.
