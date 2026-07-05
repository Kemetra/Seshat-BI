# Promotion/Markdown Fact and Factless-Fact Coverage Pattern

**Feature**: `specs/097-promotion-markdown-factless/` (gap #11)

**What this is**: a documented, reusable PATTERN for two Kimball fact shapes
the kit's vocabulary does not otherwise carry: (1) a measure-bearing
promotion/markdown fact, and (2) a factless coverage fact -- a fact table
that records that a combination of dimension keys held true, with NO
required additive measure. Together they answer a business question that a
measure-bearing fact alone cannot: "what did we discount / put on promotion
that did NOT sell?"

**What this is not**:

- It does NOT redefine or restatus any KPI. `skills/retail-kpi-knowledge/
  domains/discounts-and-promotions.md` already owns Discount Amount and
  Discount Rate % (Seeded) and Promotion Uplift % (Planned, pending "a
  promotion dimension + baseline rule"). This doc supplies the missing
  structural half -- a promotion dimension/fact and the factless-fact concept
  -- and leaves the Promotion Uplift % baseline rule exactly where the domain
  doc left it: open, for a future, separate decision.
- It does NOT edit `templates/source-map.yaml`. The factless-fact template
  this pattern ships (`templates/factless-fact.yaml`) is a separate new file
  that mirrors that template's `gold_star` convention for the no-measure
  case; it changes nothing in `source-map.yaml` itself.
- It does NOT edit `docs/worked-examples/retail-store-sales.md`. That worked
  example is cited once, below, as an existing measure-bearing fact a
  coverage fact could be anti-joined against -- never restated with invented
  promotion data.
- It does NOT add a `retail check` rule, a reserved rule id, or a new
  readiness stage. Cross-star conformance between this pattern's dimensions
  and an existing sales star's dimensions is the concern of spec 087
  (cross-star conformed-dimension readiness, reserved rule id HR1) -- a
  separate, not-yet-ratified spec this doc cites but does not implement,
  wire, or depend on landing first.
- It does NOT pick a grain, primary key, promotion mechanic, or column set
  for any real table. Every such call belongs to an adopting table's own
  analyst and data owner, made through the existing, unchanged
  source-mapping gate (Principle IV/V) -- exactly like any other new table.

## 1. Why a measure-bearing fact alone cannot answer "did not sell"

A promotion or markdown fact that only records line items where discounted
units actually sold can never answer "what was on promotion but did NOT
sell," because a promotion that sold zero units leaves no row to look at. If
the only fact table in the model requires a sale to exist as a row, then "no
sale happened" and "this combination was never on promotion at all" are
indistinguishable -- both produce zero rows.

Answering the question requires a different kind of record: a COVERAGE row
that states a (product, store, day, promotion) combination was true,
independent of whether a sale happened. That coverage record must exist on
its own -- not as a column bolted onto the sales fact, and not only for rows
where a sale occurred -- so that it can be compared against the sales fact
afterward to find the combinations with no matching sale.

This is why the pattern below introduces a FACTLESS fact: a fact table whose
only job is to assert that a combination of dimension keys held true, with
no dollar amount, no quantity, and no required measure at all. It is still a
valid Kimball star (Principle III: fact + conformed dimensions) -- what it
lacks is an additive measure, not a dimension or a conformed key.

## 2. The factless coverage fact shape

The factless coverage fact records one row per (product, store, day,
promotion) COMBINATION that was true, regardless of whether a sale happened
against it. Its grain is a combination, not a transaction.

Illustrative `gold_star` shape (generic placeholders only; mirrors
`templates/source-map.yaml`'s `gold_star` convention):

```yaml
gold_star:
  fact:
    name: "fct_<coverage_grain>"     # placeholder; adopting table names its own
    grain: "<= meta.grain>"          # e.g. "one row per product per store per day
                                      #       that was on promotion" -- adopter decides
    measures: []                     # EMPTY BY DESIGN -- see note below
    # Authoring note: COUNT(*) over this fact's rows is a valid read
    # ("how many combinations were on promotion") without being a stored
    # measure column. Do NOT add a fabricated "coverage_count" column here
    # (see Edge Cases, section 6) -- that would misrepresent the fact's
    # nature by inventing a quantity the source does not provide.
  dimensions:
    - name: "dim_product"            # CONFORMED -- the same instance the sales star uses
    - name: "dim_store"              # CONFORMED
    - name: "dim_date"               # CONFORMED
  degenerate_dimensions:
    - "<promotion_id>"               # if the source has a promotion/markdown identifier
                                      # with no attributes of its own
```

**This is the defining structural difference from every other fact template
in the repo**: `measures: []` is empty, not merely small. Every other
worked or templated fact in this kit (e.g. `templates/source-map.yaml`'s
`gold_star.fact.measures`) carries at least one additive measure. This fact
carries none, on purpose --
its purpose is coverage, not measurement. It is still a Kimball star
(Principle III) because it still has a fact table joined to conformed
dimensions; what changes is that the fact table's only "measure" is its own
row count, read with `COUNT(*)`, never materialized as a stored column.

## 3. The anti-join mechanism

The business question -- "what was on promotion but did not sell?" -- is
answered by a set-difference between the factless coverage fact (section 2)
and an existing sales fact, on their shared conformed dimensions: every
coverage row with NO matching sales row is a row that was on promotion and
did not sell.

The standard technique for this set-difference is a LEFT ANTI JOIN
(expressed below as a LEFT JOIN with a `WHERE ... IS NULL` filter, which is
equivalent). This is an ILLUSTRATION of the technique only -- generic
placeholder names throughout, never a proposed or runnable migration
against any real table:

```sql
-- ILLUSTRATION ONLY -- not a proposed or runnable migration.
-- Generic placeholder names throughout; no real table/column/promotion name.
SELECT
    coverage_fact.product_sk,
    coverage_fact.store_sk,
    coverage_fact.date_sk
FROM coverage_fact
LEFT JOIN sales_fact
    ON  sales_fact.product_sk = coverage_fact.product_sk
    AND sales_fact.store_sk   = coverage_fact.store_sk
    AND sales_fact.date_sk    = coverage_fact.date_sk
WHERE sales_fact.product_sk IS NULL;   -- equivalent to a LEFT ANTI JOIN
```

**Precondition**: the two facts MUST share a conformed, grain-compatible key
on every joined dimension. When they do not, this is a blocking mapping-gate
question for the adopting table to resolve -- see Edge Case (a) in section 6.

**Scope note**: "did not sell" here means "zero recorded sale rows for that
combination" -- a plain anti-join. A "sold below baseline" definition is a
different, unresolved question -- see Edge Case (c) in section 6.

## 4. The promotion/markdown fact shape

Separately from the factless coverage fact, a real promotion or markdown
source (line items or events tagged with a promotion identifier and a
markdown/discount amount) has its own measure-bearing fact shape: a fact
that lets promotion activity be measured on its own terms (markdown amount,
promoted units, promotion-line count), joined to the same conformed
dimensions the sales star already uses.

Illustrative `gold_star` shape (generic placeholders only):

```yaml
gold_star:
  fact:
    name: "fct_<promotion_grain>"    # placeholder; adopting table names its own
    grain: "<= meta.grain>"          # e.g. "one row per promotion line per store
                                      #       per day" -- an adopting-table decision,
                                      #       not a value this pattern supplies
    measures:                        # at least one additive measure REQUIRED
      - "<markdown_amount>"          # e.g. a markdown-amount-shaped measure
      - "<promoted_units>"           # e.g. a promoted-units-shaped measure
      # - "<promotion_line_count>"   # optional; a promotion-count measure
  dimensions:
    - name: "dim_product"            # CONFORMED -- reused, not re-created
    - name: "dim_store"              # CONFORMED
    - name: "dim_date"               # CONFORMED
```

This is a distinct entity from the factless coverage fact in section 2 --
the two are never conflated. The promotion/markdown fact carries at least
one additive measure by design; the factless coverage fact carries none by
design. A table may adopt either shape independently of the other (see
Edge Case (e) in section 6).

The candidate grain above ("one row per promotion line per store per day")
is a placeholder only. The actual grain, primary key, and measure set for
any real table are decided by that table's own source-mapping gate
(Principle IV/V) -- this pattern names the shape, not the specifics.

## 5. Conformed dimensions

Both the promotion/markdown fact (section 4) and the factless coverage fact
(section 2) are expected to reuse the SAME `dim_product` / `dim_store` (or
`dim_location`) / `dim_date` dimensions an existing sales star already
carries -- never mint a new copy of a dimension that already exists for the
sales star. Reusing the same conformed dimensions is what makes the
anti-join in section 3 possible at all: the join only works because the
coverage fact and the sales fact share the same dimension keys at a
compatible grain.

Spec 087 (cross-star conformed-dimension readiness, reserved rule id HR1) is
the pending mechanism that would eventually verify this conformance
automatically, once ratified and implemented. This pattern cites that spec
as the FUTURE check -- it does not implement, wire, or duplicate any part of
it, and it does not depend on spec 087 landing before this pattern can be
adopted. Until HR1 (or an equivalent) exists, conformance is the adopting
table's own mapping-gate responsibility, checked by the analyst and reviewer
the same way any other cross-table naming consistency is checked today.

## 6. Edge cases

**(a) The two facts do not share a conformed dimension.** If the promotion
coverage rows and the sales rows do not share a conformed, grain-compatible
key on a dimension the anti-join in section 3 needs (for example, the
promotion source only carries a category, not a product key), the anti-join
cannot run correctly. This pattern does not resolve that mismatch with an
invented crosswalk. It is a blocking mapping-gate question (a Principle-V
grain/mapping judgment) for the adopting table's analyst and data owner to
resolve.

**(b) Partial-day or overlapping promotions.** A product/store/day
combination may have been on promotion for only part of a day, or under more
than one overlapping promotion. Grain and overlap-handling for a real
promotion source are adopting-table mapping decisions (Principle V). This
pattern flags the question through the template's grain field; it does not
answer it.

**(c) "Did not sell" vs. "sold below baseline."** This pattern's anti-join
(section 3) illustrates "did not sell" as "zero recorded sale rows for that
combination." A stricter "sold below baseline" definition is the same
baseline-rule gap the Promotion Uplift % KPI is already Planned pending (per
`skills/retail-kpi-knowledge/domains/discounts-and-promotions.md`). This
pattern's factless fact enables a zero-units anti-join today; it does not
define or resolve a baseline rule. That stays a future, separate
KPI-contract decision.

**(d) Do not add a fabricated measure to the factless fact.** It can be
tempting to add a `coverage_count` column to the factless fact to make it
"feel" like a normal fact. Do not do this. `COUNT(*)` over the factless
fact's rows already answers "how many combinations were on promotion" as a
valid read -- it needs no stored column to do so. Adding a stored additive
measure that invents a quantity or amount the source does not actually
provide would misrepresent the fact's nature, and is explicitly discouraged.

**(e) Only one of the two shapes may be relevant.** The promotion/markdown
fact (section 4) and the factless coverage fact (section 2) are
independently adoptable. A table with real promotion transaction data but no
need for "did-not-sell" analysis can adopt only the promotion/markdown fact
section. A table that already has a promotion fact modeled elsewhere, and
only needs the coverage answer, can adopt only the factless-coverage
section. Neither requires the other to exist.

## 7. References

- `docs/worked-examples/retail-store-sales.md` -- an existing measure-bearing
  fact (`fct_sales_rss`) to anti-join a factless coverage fact against, cited
  here only as a "see" pointer; this pattern does not restate its columns,
  grain, or data.
- `templates/source-map.yaml` -- the `gold_star` shape and authoring-notes
  convention this pattern's sections 2 and 4 mirror.
- `templates/factless-fact.yaml` -- the copy-me template for the factless
  coverage fact shape described in section 2.
- `skills/retail-kpi-knowledge/domains/discounts-and-promotions.md` -- the
  domain doc that already owns Discount Amount, Discount Rate %, and the
  Promotion Uplift % Planned marker; unchanged by this pattern.
- `docs/decisions/0002-retail-cleaning-defaults.md` -- RC14 (gold is a
  Kimball star: fact + conformed dimensions, surrogate keys, unknown member,
  degenerate dimensions) and RC9 (independent additive measures), the
  defaults both fact shapes in this pattern instantiate.
- `specs/087-conformed-dimension-readiness/spec.md` -- the pending,
  not-yet-ratified cross-star conformance mechanism (reserved rule id HR1)
  cited in section 5; not implemented or depended on by this pattern.
