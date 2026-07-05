# Customer dimension worksheet -- `<table-id>`

> **Template.** A copy-me, fillable worksheet instantiating the shape
> described in `docs/patterns/customer-dimension-pattern.md`. Copy this file
> into a table's own mapping artifacts (alongside
> `mappings/<table>/unresolved-questions.md`) and replace every
> `<placeholder>`. ASCII only. This worksheet itself never fills the three
> unresolved slots below -- filling them is that table's own owner ruling,
> recorded in that table's `unresolved-questions.md`.
>
> **Read the pattern first:** `docs/patterns/customer-dimension-pattern.md`
> explains WHY each slot exists and what it does and does not decide. This
> worksheet is the fill-in-the-blanks counterpart, not a restatement of that
> reasoning.
>
> **Generic placeholders only.** Do not bake one table's answers (a specific
> column name, a specific PII ruling) into this template. See
> `mappings/retail_store_sales/...` for one filled, source-specific answer
> -- a worked example, never the universal schema.

---

- **Table id:** `<table-id>`
- **Date raised:** `<YYYY-MM-DD>`
- **Raised by:** `<agent | analyst-name>`
- **Pattern this instantiates:** `docs/patterns/customer-dimension-pattern.md`

---

## Dimension shape

| Slot | Filled or unresolved? | This table's value |
|---|---|---|
| Surrogate key | FILLED (structural convention, RC14) | `customer_sk` -- the generated-key mechanics for this table are recorded in this table's own `source-map.yaml`, not here. |
| Natural/identity-key slot | UNRESOLVED until the owner rules it | `[NEEDS CLARIFICATION: identity key not ruled -- owner ruling]` |
| PII-publish-safety slot | UNRESOLVED until the owner rules it | `[NEEDS CLARIFICATION: PII publish-safety not ruled -- owner ruling]` |
| SCD/historization-type slot | UNRESOLVED until the owner rules it | `[NEEDS CLARIFICATION: SCD/historization type not ruled -- owner ruling]` -- Type 1 (overwrite) or Type 2 (track history); this worksheet decides neither. |
| Unknown-member row | FILLED (structural convention, RC14) | A row at `customer_sk = -1` representing an unresolved/unknown member; every fact FK referencing this dimension `COALESCE`s to `-1`. |

> Replace each unresolved-ruling marker cell only when the named owner has
> actually ruled on it. Record that ruling in this table's own
> `mappings/<table>/unresolved-questions.md`, not by editing this worksheet
> in place with an invented answer.

## Identity resolution note (if this source has multiple raw customer ids)

If this source can produce more than one raw identifier for the same
customer (for example, both a loyalty card and a phone number appear across
different transactions for one person), record that fact here and route it
to the table's own `unresolved-questions.md` as a blocking question. This
worksheet proposes no merge rule, matching heuristic, or precedence order
between competing raw identifiers -- see
`docs/patterns/customer-dimension-pattern.md`'s "Identity resolution"
section and `skills/retail-kpi-knowledge/domains/customer.md`'s "Customer
identity / grain" stop.

- **Multiple raw ids present for this source?** `<yes | no | unknown -- profile to confirm>`
- **If yes, routed to blocking question:** `<mappings/<table-id>/unresolved-questions.md Q#>`

## Citing this dimension from `source-map.yaml`

Once the three unresolved slots above are filled by the named owner, cite
this dimension by name from the table's own `templates/source-map.yaml`
`gold_star.dimensions[]` entry -- no new schema key is added; this worksheet
maps onto the fields the schema already defines:

```yaml
gold_star:
  dimensions:
    - name: "dim_customer"                 # this table's chosen dimension name
      surrogate_key: "customer_sk"         # RC14, from this worksheet
      has_unknown_member: true             # RC14, from this worksheet
      attributes:
        - "<identity_key_attribute>"       # filled once the owner rules the identity key
        # - "<other_attribute>"
```

Do not copy this worksheet's prose into `source-map.yaml`; cite this file
by path in an authoring comment instead (FR-014).

## See also

- `docs/patterns/customer-dimension-pattern.md` -- the pattern this
  worksheet instantiates; read it first for the reasoning behind each slot.
- `docs/patterns/customer-grain-pattern.md` -- the companion grain pattern
  for retention/frequency/CLV/new-vs-returning facts, once this dimension
  exists.
- `templates/source-map.yaml` -- the `gold_star.dimensions[]` shape this
  worksheet's filled values feed into.
- `templates/unresolved-questions.md` -- where a real table records the
  owner's ruling on the identity-key, PII-publish, and SCD/historization
  slots.
- `docs/decisions/0002-retail-cleaning-defaults.md` -- RC14, the surrogate
  key + unknown-member + FK `COALESCE` convention this worksheet reuses.
- `mappings/retail_store_sales/unresolved-questions.md` -- one filled,
  source-specific answer, for one source only. Not a default for this
  table.
