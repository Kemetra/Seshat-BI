# Reference Retail Schema

> All DAX examples in this knowledge base use **this fictional retail star schema**.
> It is original to this knowledge base and is **not** taken from any book's sample model.
> Whenever the BI agent generates, reviews, or explains DAX, it should assume this schema
> unless the user supplies their own model. Map the user's real table/column names onto
> these roles before applying any pattern.

## Model overview

A classic single-fact-per-grain star schema for an omni-channel retailer.

```
            ┌─────────────┐      ┌──────────────┐      ┌────────────┐
            │   'Date'    │      │  'Customer'  │      │  'Product' │
            └──────┬──────┘      └──────┬───────┘      └─────┬──────┘
                   │ 1                  │ 1                  │ 1
                   │                    │                    │
                   ▼ *                  ▼ *                  ▼ *
            ┌───────────────────────────────────────────────────────┐
            │                        'Sales'  (fact)                 │
            └───────────────────────────────────────────────────────┘
                   ▲ *                  ▲ *
                   │                    │
                   │ 1                  │ 1
            ┌──────┴──────┐      ┌──────┴───────┐
            │  'Store'    │      │ 'Promotion'  │
            └─────────────┘      └──────────────┘

   'Inventory' (fact, daily snapshot)  →  related to 'Date', 'Product', 'Store'
   'Customer Segments' (config table, no relationship)
   'Currency' + 'ExchangeRate' (for currency conversion)
   'Measures' (empty table that hosts measures)
```

## Tables and key columns

### 'Sales' (fact — one row per order line)
| Column | Type | Notes |
|---|---|---|
| SalesKey | int | surrogate |
| OrderDate | date | relationship to 'Date'[Date] (active) |
| DeliveryDate | date | inactive relationship to 'Date'[Date] (role-playing) |
| ProductKey | int | → 'Product' |
| CustomerKey | int | → 'Customer' |
| StoreKey | int | → 'Store' |
| PromotionKey | int | → 'Promotion' |
| Quantity | int | units sold |
| Net Price | decimal | per-unit price after line discount |
| Unit Cost | decimal | per-unit cost |

### 'Product' (dimension)
ProductKey, Product Name, Category, Subcategory, Brand, Color, List Price, Standard Cost.

### 'Customer' (dimension)
CustomerKey, Customer Name, City, State, Country, Continent, Customer Segment (free text), Birth Year, Gender.

### 'Store' (dimension)
StoreKey, Store Name, Channel ('Online' | 'Reseller' | 'Retail'), City, Country, Open Date.

### 'Promotion' (dimension)
PromotionKey, Promotion Name, Discount Category, Start Date, End Date.

### 'Date' (marked as Date table)
Date (unique, contiguous Jan 1 → Dec 31), Year, Quarter (e.g. "Q3"), Year Quarter ("Q3-2025"), Year Quarter Number (sort), Month ("Aug"), Month Number, Year Month ("Aug 2025"), Year Month Number (sort), Day of Week ("Tue"), Day of Week Number, Working Day (bool), Fiscal Year, Fiscal Year Number, **DateWithSales** (bool — TRUE for dates on/before last date with a Sales transaction).

### 'Inventory' (fact — daily product/store snapshot, semi-additive)
Date, ProductKey, StoreKey, On Hand Quantity, Unit Cost.

### 'Customer Segments' (configuration table, NO relationship)
Segment ("Bronze" | "Silver" | "Gold" | "Platinum"), Min Sales, Max Sales, Segment Sort.

### 'Currency' / 'ExchangeRate'
'Currency'[Currency Code]; 'ExchangeRate'[Date], [Currency Code], [Rate] (rate to reporting currency).

### Date — custom-calendar columns (for the week / 4-4-5 pattern)
In addition to the Gregorian columns above, the Date table carries sequential keys for
non-Gregorian navigation: `Week Index` (contiguous integer per ISO/retail week), `Year Week`
("2025-W34"), `Period Index` (contiguous 4-4-5 period). These let week patterns navigate without
built-in time intelligence.

### 'Account' (dimension — parent-child, e.g. chart of accounts)
AccountKey, ParentAccountKey (self-reference), Account Name, Account Type. Used by the
parent-child hierarchy pattern (PATH-flattened into Level columns).

### 'Budget' (fact — coarser grain than Sales)
Year Month, Category, Budget Amount. Related to 'Date' and 'Product' **only at its grain**
(month / category) — not by day or ProductKey. Used by the budget-vs-actual pattern.

### 'Answers' + survey bridge (many-to-many)
'Answers'[RespondentKey], [QuestionKey], [AnswerKey]. A respondent has many answers and an answer
is shared by many respondents (many-to-many). Used by the survey pattern with distinct-respondent
counts.

### Disconnected helper tables (no relationships)
Used by what-if / virtual-relationship examples. Introduced as needed:
- 'Top N Param'[Top N] — integer slicer (1..50) for Top-N selectors.
- 'Category Bucket'[Category] — a disconnected list of categories applied to 'Product'[Category]
  via TREATAS to demonstrate virtual relationships.
- 'Product B'[ProductKey] — a second copy of products for the "bought-together" role in basket
  analysis (applied to 'Sales'[ProductKey] via TREATAS).
- 'Segment From'[Segment] / 'Segment To'[Segment] — disconnected from/to axes for the transition
  matrix.
- 'Answer Filter'[AnswerKey] — disconnected answer selector for survey filtering.

## Canonical base measures (assume these exist)

```dax
Sales Amount   := SUMX ( 'Sales', 'Sales'[Quantity] * 'Sales'[Net Price] )
Total Cost     := SUMX ( 'Sales', 'Sales'[Quantity] * 'Sales'[Unit Cost] )
Margin         := [Sales Amount] - [Total Cost]
Margin %       := DIVIDE ( [Margin], [Sales Amount] )
Quantity       := SUM ( 'Sales'[Quantity] )
# Customers    := DISTINCTCOUNT ( 'Sales'[CustomerKey] )
```

All higher-level patterns build on these base measures rather than re-deriving the arithmetic.
