# Source Map

Maps each retail frame to its origin, owner, refresh, grain, and known risks. The source
map is the authority for **business meaning** — agents confirm meaning here rather than
inferring from column names (PY-AP-008). Schema: `references/retail-dataframe-schema.md`.

> Fictional. For grounding examples only.

| frame | origin (fictional) | owner | refresh | grain | known risks |
|---|---|---|---|---|---|
| `orders` | POS + web/app order service export | Commerce Ops | daily | one row per order line | currency-as-text, string dates, guest null vs `""`, channel casing |
| `products` | Merchandising catalogue export | Merchandising | weekly | one row per SKU | mixed-case names, list_price gaps |
| `stores` | Store master | Retail Estate | on change | one row per store | small frame; region domain fixed |
| `returns` | Returns service export | Customer Care | daily | one row per return | one-to-many to order lines (fan-out), reason_code drift |
| `suppliers` | Procurement master | Procurement | monthly | one row per supplier | country domain drift |

## Meaning confirmations (examples)

- `unit_price` is **gross** price per unit before line discount; net = `unit_price *
  quantity - discount_amt`. Do not assume from the name.
- `order_ts` is **store-local** time (timezone policy in
  `knowledge/dates-times-and-calendars.md` — **planned / not yet implemented in this seed**).
- `customer_id` null = guest checkout (legitimate); `""` = extract defect.
- `quantity` of 0 occurs on adjustment lines, not sales.

## How to use

When a task needs the meaning of a column, cite this map. If the meaning is not recorded
here, that is a finding — confirm with the listed owner before proceeding. This map, not
the dataframe, is the source of business truth in the prep layer.
