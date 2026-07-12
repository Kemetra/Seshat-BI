# Portfolio Survey: synthetic drop

**Status**: warning
**Source kind**: file-folder
**Source identity**: synthetic-drop
**Reachable tables total**: 2
**Surveyed tables total**: 2

## Coverage limits

- File formats do not declare PK/FK metadata; use selected-table onboarding for value-backed evidence.

## Candidate domain evidence

- Order and product filenames suggest a retail sales domain; hint only.

## Candidate first-scope tables

- orders.csv and products.xlsx share product-shaped identifiers; proposal input only.

## Table: orders.csv

**Columns**:
| Column | Declared type |
|--------|---------------|
| order_id | integer |
| order_date | date |
| amount | decimal |
**Declared PK**: [PENDING LIVE PROFILE] CSV has no declared key metadata; run selected-table onboarding
**Declared FKs**: [PENDING LIVE PROFILE] CSV has no declared relationship metadata; run selected-table onboarding
**Candidate grain hint**: order_id name hint only; unverified
**Approx row count**: [PENDING LIVE PROFILE] not available from directory metadata; run selected-table onboarding
**Date hints**: order_date name/type hint only
**PII suspicion hints**: none from names or declared types
**Structural role hint**: candidate fact
**Unavailable**: key, relationship, and row-count metadata: file format limitation; run selected-table onboarding

## Table: products.xlsx

**Columns**:
| Column | Declared type |
|--------|---------------|
| product_id | integer |
| product_name | text |
**Declared PK**: [PENDING LIVE PROFILE] Excel has no declared key metadata; run selected-table onboarding
**Declared FKs**: [PENDING LIVE PROFILE] Excel has no declared relationship metadata; run selected-table onboarding
**Candidate grain hint**: product_id name hint only; unverified
**Approx row count**: [PENDING LIVE PROFILE] not available from directory metadata; run selected-table onboarding
**Date hints**: none from names or declared types
**PII suspicion hints**: none from names or declared types
**Structural role hint**: candidate dimension
**Unavailable**: key, relationship, and row-count metadata: file format limitation; run selected-table onboarding
