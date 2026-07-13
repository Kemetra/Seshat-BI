# Copyright Safety

This knowledge layer was distilled from SQL books read locally for grounding. It reproduces
**none** of their text, code listings, recipes, figures, or datasets. This note records the
boundary so a reviewer can confirm it at a glance.

## What was distilled (allowed)

- **Ideas, rules, structure, and terminology** -- paraphrased and reorganized in original wording,
  synthesized with widely-established SQL knowledge.
- **The concept -> anti-pattern -> validation -> playbook -> training-question chain** -- an
  original Seshat BI structure (the same pipeline used by `bi-dax-knowledge`).
- **Topic selection** -- a curated, high-value subset for BI pipelines, not an exhaustive
  reproduction of any book's chapters.

## What was deliberately NOT done (the boundary)

- **No long passages of book text** copied or lightly reworded.
- **No book code listings, recipes, figures, or extended prose** reproduced.
- **No book datasets** used: in particular **no `EMP`/`DEPT`** (the SQL Cookbook sample tables),
  and none of *SQL for Data Analysis*'s retail-sales, legislators, or UFO datasets.
- **No PDFs or book files added to the repository.** The books were read locally for grounding
  only and are not tracked in git (no `_local_sources/`).
- **No substitution for the books.** Anyone wanting full coverage, every variation, and the
  authors' complete explanations should read the original works.

## Original examples only

Every example in this skill is an original Seshat BI / retail example on a **fictional schema**:

```text
sales        one order line   (order_line_id PK, order_id, order_date, product_key,
                               customer_key, store_key, quantity, net_price, unit_cost)
product      one product      (product_key PK, category, brand)
customer     one customer     (customer_key PK, region)
store        one store        (store_key PK, store_name, region, channel)
date         one calendar day (date PK, year, month)
```

Star-schema variants used in transformation/gold examples: `fact_sales`, `dim_product`,
`dim_branch`, `dim_date`, `branch`. Layer prefixes `bronze.` / `silver.` / `gold.` denote the
medallion stage. No other schema or any book sample model appears.

## Attribution

Source attribution and the per-slice derivation log live in `source-map.md`. Treat that file as
the authoritative record of which book chapters informed which distilled concepts, and treat all
code and examples here as original derivative teaching material.

## Reviewer quick-check

- `grep -ri "EMP\|DEPT\|UFO\|legislator"` over this skill should return only this file and
  `source-map.md` (the disclaimer mentions), never an actual example.
- Every SQL block should reference only the fictional schema tables listed above.
- No `.pdf` / `.epub` / book file should exist anywhere under `skills/bi-sql-knowledge/`.
