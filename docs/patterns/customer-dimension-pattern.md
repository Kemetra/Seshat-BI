# Customer dimension pattern

> **Pattern doc, not a filled table.** This is a GENERIC conformed Kimball
> dimension SHAPE (Principle III) for any source that carries some notion of
> "customer" (a loyalty id, an account, a member number, a phone number). It
> names a surrogate key, an unresolved identity-key slot, an unresolved
> PII-publish-safety slot, an unresolved SCD/historization-type slot, and the
> `-1` unknown-member convention (RC14). It decides none of the three
> unresolved slots -- each is a reserved owner ruling (Principle V) that a
> future table's own mapping-gate review fills in, not this document.
>
> **What this is not.** It is not a database object, not SQL DDL, and not
> itself consumed by `seshat check`. It seeds no metric contract (F009's
> contract-template + review process still applies separately) and advances
> no readiness stage. See `templates/customer-dimension.md` for the copy-me
> worksheet that instantiates this shape for a real table.

---

## Why this pattern exists

`skills/retail-kpi-knowledge/domains/customer.md` is the heaviest KPI
knowledge domain in the repo, but every KPI it lists stays `Planned` because
no customer identity key and no customer grain has ever been ruled on
generically. One filled, table-scoped instance exists (see
`mappings/retail_store_sales/...` for one filled, source-specific answer),
but it answers one source's PII question for that source only -- it is not a
reusable shape. This document is the reusable shape a future table's analyst
and owner can read before their own source is mapped, so they are not left
reverse-engineering someone else's already-answered ruling.

## The dimension shape

| Slot | Filled or unresolved? | Content |
|---|---|---|
| Surrogate key | FILLED (structural convention) | `customer_sk` -- an integer identity/generated surrogate key, RC14 convention (`docs/decisions/0002-retail-cleaning-defaults.md`). |
| Natural/identity-key slot | UNRESOLVED | `[NEEDS CLARIFICATION: identity key not ruled -- owner ruling]`. This slot names no candidate field. It is never filled in this document with a specific column (not a loyalty id, not a phone number, not an account number, not any other named field) -- the owner ruling names the field for their own table. |
| PII-publish-safety slot | UNRESOLVED | `[NEEDS CLARIFICATION: PII publish-safety not ruled -- owner ruling]`. No default is implied by this pattern -- neither "keep" nor "drop" is the shipped answer. Each table's owner rules its own case; a different source's answer may come out differently even if the columns look similar. |
| SCD/historization-type slot | UNRESOLVED | `[NEEDS CLARIFICATION: SCD/historization type not ruled -- owner ruling]`. Names Type 1 ("overwrite" -- the dimension row is updated in place, no history kept) and Type 2 ("track history" -- a new row is inserted and prior rows are preserved/dated) as the two options. Decides neither; the choice is a per-table governance/business ruling. |
| Unknown-member row | FILLED (structural convention, RC14) | A row at `customer_sk = -1` representing an unresolved/unknown member. Every fact that references the dimension joins via a foreign key `COALESCE`'d to `-1` when no match is found -- the same convention already used elsewhere in the star. |

**Non-goal.** This is a document, not a database object. It produces no DDL
and is not itself consumed by `seshat check`.

## What is fixed vs. what stays open

Only the STRUCTURAL mechanics are fixed here: the surrogate-key convention
and the unknown-member row (both RC14, reused verbatim -- no new key
convention is invented). Every SEMANTIC or GOVERNANCE decision -- which
field is the identity key, whether that field is publish-safe, and whether
the dimension is Type 1 or Type 2 -- is an explicit, reserved owner ruling.
None of the three is decided, recommended, or implied by this document.

## Identity resolution (a reserved stop, not a mechanism)

A source may carry more than one raw identifier for what is really the same
customer -- for example, a loyalty card AND a phone number recorded on
different transactions for the same person. Resolving those multiple raw
ids down to one `customer_sk` is a reserved owner ruling
(`[NEEDS CLARIFICATION: identity key not ruled -- owner ruling]` extends to
this question as well): this pattern does not decide it and proposes no
merge rule, matching heuristic, or precedence order between competing raw
identifiers (it does not say, for instance, that a loyalty id should be
preferred over a phone number, or vice versa).

See `skills/retail-kpi-knowledge/domains/customer.md`'s "Customer identity /
grain" stop (under "Owner ruling triggers") for the authoritative statement
of this ambiguity. This section cross-references that stop; it does not
restate it in different words, and it does not resolve it.

## Cross-references to the four Principle-V stops

`skills/retail-kpi-knowledge/domains/customer.md` (Owner ruling triggers)
already states four reserved rulings for the customer domain. This pattern
decides none of them; it only cites them so a reader can find the
authoritative statement in one place:

- Customer identity / grain -- see the "Identity resolution" section above
  and `domains/customer.md`'s "Customer identity / grain" stop.
- PII publish-safety -- see the PII-publish-safety slot above and
  `domains/customer.md`'s "PII publish-safety" stop.
- Business-segment rollups -- out of scope for this dimension shape; see
  `domains/customer.md`'s "Business-segment rollups" stop. Any loyalty tier
  or cohort is itself a business-segment rollup and is not authored here.
- Product identity (where a customer KPI leans on it) -- out of scope for
  this dimension shape; see `domains/customer.md`'s "Product identity" stop.

## How a future table adopts this pattern

1. Copy `templates/customer-dimension.md` into the table's own mapping
   artifacts.
2. Fill the identity-key, PII-publish, and SCD/historization slots with that
   table's own owner ruling, recorded in that table's
   `mappings/<table>/unresolved-questions.md` -- not in this pattern
   document or the template.
3. Reference the filled dimension by name from the table's own
   `source-map.yaml` `gold_star.dimensions[]` entry (see
   `templates/source-map.yaml`'s existing `.name` / `.surrogate_key` /
   `.has_unknown_member` / `.attributes[]` fields -- no new schema key is
   needed).
4. Once a customer dimension exists for that table, see
   `docs/patterns/customer-grain-pattern.md` for the candidate grains a
   retention, frequency, or CLV fact would need on top of it.

## See also

- `templates/customer-dimension.md` -- the copy-me worksheet instantiating
  this shape.
- `docs/patterns/customer-grain-pattern.md` -- the companion grain pattern
  for retention/frequency/CLV/new-vs-returning facts built on this
  dimension.
- `skills/retail-kpi-knowledge/domains/customer.md` -- the knowledge-layer
  statement of the four Principle-V customer stops (cited, not restated).
- `docs/decisions/0002-retail-cleaning-defaults.md` -- RC14 (surrogate keys,
  `-1` unknown member, FK `COALESCE`), the structural convention this
  pattern reuses.
- `mappings/retail_store_sales/unresolved-questions.md` -- one filled,
  source-specific answer to the PII-publish question, for one source only.
  Not a repo-wide default.
