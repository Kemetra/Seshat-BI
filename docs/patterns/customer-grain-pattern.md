# Customer-grain pattern

> **Pattern doc, doc-only -- no copy-me template.** This document names
> CANDIDATE grains for the four `Planned` customer KPIs in
> `skills/retail-kpi-knowledge/domains/customer.md` (Customer Retention
> Rate, Purchase Frequency, Customer Lifetime Value, New-vs-Returning
> split). Each candidate grain is an OPTION to be ruled on, not a shipped
> default. No copy-me grain template ships alongside this doc: a template
> would instantiate a CHOSEN grain (a period length, a horizon, an anchor
> rule), and which grain a table adopts is itself part of the reserved
> rulings this pattern must not make.
>
> **Depends on:** `docs/patterns/customer-dimension-pattern.md`. A grain
> pattern is meaningless without a conformed customer dimension to key
> against -- read the dimension pattern first.

---

## Why this pattern exists

A customer dimension (`docs/patterns/customer-dimension-pattern.md`) alone
does not make retention, frequency, or CLV computable. Those KPIs are
grain-dependent facts: retention and frequency need a snapshot period,
CLV needs a horizon, and a new-vs-returning split needs a first-purchase
anchor. `skills/retail-kpi-knowledge/domains/customer.md` already names
these ambiguities and decides none of them; this document adds the missing
half -- a candidate grain SHAPE for each KPI family -- without deciding the
open ambiguity either.

## Structural join, fixed for every candidate grain

Every candidate grain below keys to the customer dimension's surrogate key,
`customer_sk`, as a foreign key, `COALESCE`'d to `-1` for an unresolved or
unknown member -- the same convention (RC14,
`docs/decisions/0002-retail-cleaning-defaults.md`) the customer dimension
pattern and the rest of the star already use. This fixes only the
STRUCTURAL join surface (a conformed dimension needs a documented join,
Principle III); it decides no grain, period, horizon, or anchor value.

## Candidate grains by KPI

Cited from `skills/retail-kpi-knowledge/domains/customer.md`'s KPI table.

### Customer Retention Rate

- **Candidate grain (OPTION):** a periodic-snapshot grain -- one row per
  customer per calendar period.
- **Structural FK join (FILLED, RC14):** keys to the customer dimension via
  `customer_sk`, `COALESCE`'d to `-1` for an unresolved/unknown member.
- **Unresolved value:**
  `[NEEDS CLARIFICATION: retention window not ruled -- owner ruling]` --
  the period length itself (rolling twelve months, calendar year, since
  first purchase, or another window) is not decided here. See
  `domains/customer.md`'s "Retention window definition" ambiguity.

### Purchase Frequency

- **Candidate grain (OPTION):** the same periodic-snapshot grain family as
  Customer Retention Rate -- one row per customer per calendar period.
- **Structural FK join (FILLED, RC14):** keys to the customer dimension via
  `customer_sk`, `COALESCE`'d to `-1`.
- **Unresolved value:**
  `[NEEDS CLARIFICATION: retention window not ruled -- owner ruling]` --
  Purchase Frequency shares the same period-length ambiguity that Customer
  Retention Rate carries. This document states that sharing explicitly
  rather than inventing a second, independent period for frequency.

### Customer Lifetime Value (CLV)

- **Candidate grain (OPTION):** a customer-to-date grain -- one row per
  customer, lifetime-to-date (not periodic).
- **Structural FK join (FILLED, RC14):** keys to the customer dimension via
  `customer_sk`, `COALESCE`'d to `-1`.
- **Unresolved value:**
  `[NEEDS CLARIFICATION: CLV horizon not ruled -- owner ruling]` -- the
  horizon length and whether future value is discounted are both left open.
  See `domains/customer.md`'s "CLV horizon and discounting" ambiguity.

### New-vs-Returning Customer split

- **Candidate grain (OPTION):** a periodic-snapshot grain classifying each
  period's customers against a first-purchase anchor date (the same
  snapshot family as Customer Retention Rate, applied to a different
  classification question).
- **Structural FK join (FILLED, RC14):** keys to the customer dimension via
  `customer_sk`, `COALESCE`'d to `-1`.
- **Unresolved value:**
  `[NEEDS CLARIFICATION: anchor not ruled -- owner ruling]` -- the
  first-purchase anchor rule itself (what counts as a customer's first
  purchase, and over what lookback) is not decided here; this document does
  not silently pick a first-transaction-date default. See
  `domains/customer.md`'s "One-time vs repeat customer" ambiguity.

## What this document does not do

- It does not ship a copy-me grain template (Clarify Q3 in `spec.md`): a
  template would instantiate a chosen grain, and the choice itself is a
  reserved owner ruling.
- It does not pick a retention window, a CLV horizon or discount rate, or a
  new-vs-returning anchor rule for any table.
- It does not seed a metric contract. A future customer metric contract
  still needs F009's contract-template + review process, in addition to a
  confirmed identity/PII ruling from the dimension pattern.
- It does not restate `domains/customer.md`'s ambiguities in different
  words that could read as a fresh ruling -- each unresolved value above
  cross-references that file rather than re-deriving it.

## See also

- `docs/patterns/customer-dimension-pattern.md` -- the customer dimension
  shape this grain pattern keys against (`customer_sk`).
- `skills/retail-kpi-knowledge/domains/customer.md` -- the knowledge-layer
  KPI table and the retention-window / CLV-horizon / anchor ambiguities
  cited above.
- `docs/decisions/0002-retail-cleaning-defaults.md` -- RC14, the FK
  `COALESCE`-to-`-1` join convention every candidate grain above reuses.
