# Retail Dataframe Schema (fictional)

Every example in this skill uses this fictional retail dataset. It is original and
exists only to ground explanations. Use it consistently so examples compose.

Company: **Meridian Outfitters**, a fictional multi-store apparel retailer.

## Tables / frames

### `orders` — one row per order line
| column | meaning | typical dtype | notes |
|---|---|---|---|
| `order_id` | order identifier | string | repeats across lines |
| `order_line_id` | line within order | string | **grain key** with nothing else needed |
| `order_ts` | order timestamp | datetime64[ns] | store-local, see dates file |
| `store_id` | selling store | string | FK → `stores.store_id` |
| `customer_id` | customer | string (nullable) | null for guest checkout |
| `sku` | product sold | string | FK → `products.sku` |
| `quantity` | units sold | int | can be 0 on adjustments |
| `unit_price` | price per unit | float | currency = GBP |
| `discount_amt` | line discount | float | ≥ 0 |
| `channel` | sales channel | category | {`store`, `web`, `app`} |

Grain: **one row per `order_line_id`**. `order_id` alone is *not* unique.

### `products` — one row per SKU
| column | meaning | dtype | notes |
|---|---|---|---|
| `sku` | product key | string | **unique** |
| `product_name` | display name | string | messy casing in raw extract |
| `category` | merchandise category | category | {`tops`,`bottoms`,`outerwear`,`footwear`,`accessories`} |
| `supplier_id` | supplier | string | FK → `suppliers.supplier_id` |
| `list_price` | catalogue price | float | GBP |

Grain: **one row per `sku`**.

### `stores` — one row per store
| column | meaning | dtype | notes |
|---|---|---|---|
| `store_id` | store key | string | **unique** |
| `store_name` | display name | string | |
| `region` | region | category | {`north`,`south`,`midlands`,`online`} |
| `open_date` | store opening | date | |

Grain: **one row per `store_id`**.

### `returns` — one row per returned line
| column | meaning | dtype | notes |
|---|---|---|---|
| `return_id` | return key | string | **unique** |
| `order_line_id` | line returned | string | FK → `orders.order_line_id` |
| `return_ts` | return timestamp | datetime64[ns] | |
| `return_qty` | units returned | int | ≤ original quantity |
| `reason_code` | reason | category | {`size`,`defect`,`changed_mind`,`other`} |

Grain: **one row per `return_id`**. A single order line can have multiple returns →
**fan-out risk** when joining `orders` to `returns`.

### `suppliers` — one row per supplier
| column | meaning | dtype | notes |
|---|---|---|---|
| `supplier_id` | supplier key | string | **unique** |
| `supplier_name` | name | string | |
| `country` | sourcing country | category | |

Grain: **one row per `supplier_id`**.

## Known messiness (for cleaning/profiling examples)

- `product_name` arrives with mixed casing and stray whitespace.
- `unit_price` sometimes arrives as text with a `£` symbol and thousands separators.
- `customer_id` is null for guest checkout (legitimate), but also occasionally an
  empty string `""` (a different problem).
- `order_ts` arrives in inconsistent string formats across source files.
- `channel` sometimes arrives as `Web`, `WEB`, `web ` (casing + whitespace drift).
- Some extracts use `-1` or `999` as sentinel values for "unknown".

## Cardinality cheat-sheet (for join reasoning)

| relationship | cardinality |
|---|---|
| `orders` → `stores` | many-to-one |
| `orders` → `products` | many-to-one |
| `products` → `suppliers` | many-to-one |
| `orders` → `returns` | one-to-many (**fan-out**) |
