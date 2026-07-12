# Portfolio Survey: synthetic analytics

**Status**: warning
**Source kind**: db-schema
**Source identity**: analytics
**Reachable tables total**: 5
**Surveyed tables total**: 5

## Coverage limits

- analytics.categories approximate row count is [PENDING LIVE PROFILE]: relation statistics permission denied; grant metadata-statistics access

## Candidate domain evidence

- Orders, order items, products, categories, and customers suggest a retail sales domain; hint only.

## Candidate first-scope tables

- analytics.orders and analytics.order_items share declared order keys; proposal input only.

## Table: analytics.orders

**Columns**:
| Column | Declared type |
|--------|---------------|
| order_id | bigint |
| customer_id | bigint |
| order_date | date |
| total_amount | numeric |
**Declared PK**: order_id (declared metadata; candidate only)
**Declared FKs**: customer_id -> analytics.customers.customer_id (declared metadata; candidate only)
**Candidate grain hint**: one row per order_id; unverified metadata hint
**Approx row count**: 125000 (catalog estimate only)
**Date hints**: order_date name/type hint only
**PII suspicion hints**: customer_id name/type hint only; no values inspected
**Structural role hint**: candidate fact
**Unavailable**: none

## Table: analytics.order_items

**Columns**:
| Column | Declared type |
|--------|---------------|
| order_item_id | bigint |
| order_id | bigint |
| product_id | bigint |
| quantity | integer |
**Declared PK**: order_item_id (declared metadata; candidate only)
**Declared FKs**: order_id -> analytics.orders.order_id; product_id -> analytics.products.product_id (declared metadata; candidate only)
**Candidate grain hint**: one row per order_item_id; unverified metadata hint
**Approx row count**: 480000 (catalog estimate only)
**Date hints**: none from names or declared types
**PII suspicion hints**: none from names or declared types
**Structural role hint**: candidate fact
**Unavailable**: none

## Table: analytics.customers

**Columns**:
| Column | Declared type |
|--------|---------------|
| customer_id | bigint |
| customer_email | varchar |
| created_at | timestamp |
**Declared PK**: customer_id (declared metadata; candidate only)
**Declared FKs**: none declared
**Candidate grain hint**: one row per customer_id; unverified metadata hint
**Approx row count**: 42000 (catalog estimate only)
**Date hints**: created_at name/type hint only
**PII suspicion hints**: customer_email name/type hint only; no values inspected
**Structural role hint**: candidate dimension
**Unavailable**: none

## Table: analytics.products

**Columns**:
| Column | Declared type |
|--------|---------------|
| product_id | bigint |
| category_id | bigint |
| product_name | varchar |
**Declared PK**: product_id (declared metadata; candidate only)
**Declared FKs**: category_id -> analytics.categories.category_id (declared metadata; candidate only)
**Candidate grain hint**: one row per product_id; unverified metadata hint
**Approx row count**: 8500 (catalog estimate only)
**Date hints**: none from names or declared types
**PII suspicion hints**: none from names or declared types
**Structural role hint**: candidate dimension
**Unavailable**: none

## Table: analytics.categories

**Columns**:
| Column | Declared type |
|--------|---------------|
| category_id | bigint |
| category_name | varchar |
**Declared PK**: category_id (declared metadata; candidate only)
**Declared FKs**: none declared
**Candidate grain hint**: one row per category_id; unverified metadata hint
**Approx row count**: [PENDING LIVE PROFILE] estimate unavailable: permission denied
**Date hints**: none from names or declared types
**PII suspicion hints**: none from names or declared types
**Structural role hint**: candidate dimension
**Unavailable**: approximate row count: permission denied; grant metadata-statistics access
