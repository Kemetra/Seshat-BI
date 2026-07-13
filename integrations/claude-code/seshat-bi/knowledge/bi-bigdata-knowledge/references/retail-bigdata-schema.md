# Retail Big-Data Schema (fictional, at scale)

Every example in this skill uses this fictional retail dataset, scaled up. It is original
and exists only to ground explanations. It extends the single-node schema used by
`bi-python-knowledge` (Meridian Outfitters) to volumes that justify distributed compute.

Company: **Meridian Outfitters**, a fictional multi-store + online apparel retailer, now
at scale: ~2,000 stores, tens of millions of customers, billions of order lines and
clickstream events per year.

## Datasets (distributed tables)

### `orders` — one row per order line  (≈ billions of rows / year)
Same columns as the single-node schema (`order_line_id`, `order_id`, `order_ts`,
`store_id`, `customer_id`, `sku`, `quantity`, `unit_price`, `discount_amt`, `channel`).
- Grain: **one row per `order_line_id`**.
- Typically stored partitioned by **event date** (e.g. `order_date=YYYY-MM-DD`).

### `clickstream` — one row per web/app event  (≈ tens of billions of rows / year)
| column | meaning | notes |
|---|---|---|
| `event_id` | event key | unique |
| `event_ts` | event timestamp | high volume; UTC |
| `customer_id` | customer (nullable) | null for anonymous |
| `session_id` | session | many events per session |
| `sku` | product viewed | nullable |
| `event_type` | view / add_to_cart / checkout | category |
- Grain: **one row per `event_id`**. Partitioned by **event date**, often by **hour**.

### `inventory_snapshots` — one row per SKU per store per snapshot  (periodic)
| column | meaning | notes |
|---|---|---|
| `snapshot_date` | snapshot day | partition key |
| `store_id` | store | |
| `sku` | product | |
| `on_hand_qty` | units on hand | |
| `on_hand_cost` | cost value | |
- Grain: **one row per (`snapshot_date`,`store_id`,`sku`)**. **Semi-additive** over time.

### Dimensions (small, broadcastable)
- `products` (one row per `sku`), `stores` (one row per `store_id`),
  `suppliers` (one row per `supplier_id`), `customers` (one row per `customer_id`).
- `products`, `stores`, `suppliers` are **small** → broadcast-join candidates.
- `customers` is **large** (tens of millions) → usually a shuffle join, not broadcast.

## Scale facts that drive reasoning

| fact | consequence |
|---|---|
| `orders` partitioned by `order_date` | date-filtered reads prune partitions cheaply |
| a few flagship stores carry a huge share of rows | **store_id is skewed** → skewed joins/groupbys |
| `products`/`stores` are small | broadcast joins avoid shuffle |
| `customers` is large | customer joins shuffle; watch skew on power-buyers |
| `clickstream` >> `orders` in volume | sessionization/aggregation is the costly step |
| returns are one-to-many to order lines | **fan-out risk** (reuses PY-CN-046) |

## Known messiness (same spirit as single-node, at scale)

- Late-arriving order/clickstream events land after the day partition was first written.
- Occasional duplicate events on producer retries (idempotency concern).
- `channel` casing/whitespace drift; `customer_id` null (anonymous) vs `""` (defect).
- A handful of skewed keys (flagship stores, bot sessions, a placeholder `sku`).

## Cardinality & skew cheat-sheet (for join/skew reasoning)

| relationship | cardinality | broadcast? | skew risk |
|---|---|---|---|
| `orders` → `stores` | many-to-one | yes (small dim) | high (flagship stores) |
| `orders` → `products` | many-to-one | yes (small dim) | medium (hero SKUs) |
| `orders` → `customers` | many-to-one | no (large dim) | medium (power buyers) |
| `orders` → `returns` | one-to-many | n/a | fan-out (PY-CN-046) |
| `clickstream` → `customers` | many-to-one | no | high (bots/anon) |
