# DAX Retail Examples

> Worked, **original** examples on the reference retail schema (see
> `references/retail-schema.md`). These are teaching examples written for this knowledge base —
> not reproductions of any book's code. Each shows the canonical *shape* of a pattern plus the
> reasoning. The agent should adapt table/column names to the user's model.

Base measures assumed (from the schema doc):

```dax
Sales Amount := SUMX ( 'Sales', 'Sales'[Quantity] * 'Sales'[Net Price] )
Total Cost   := SUMX ( 'Sales', 'Sales'[Quantity] * 'Sales'[Unit Cost] )
Margin       := [Sales Amount] - [Total Cost]
Quantity     := SUM ( 'Sales'[Quantity] )
# Customers  := DISTINCTCOUNT ( 'Sales'[CustomerKey] )
```

---

## 1. Year-to-date (and the future-date guard)

```dax
Sales YTD :=
IF (
    MIN ( 'Date'[DateWithSales] ),                 -- only past dates have data
    CALCULATE ( [Sales Amount], DATESYTD ( 'Date'[Date] ) )
)
```
Reasoning: `DATESYTD` is a TI **table** function, so it lives in a `CALCULATE` filter argument
(BP-031). The `IF (MIN(...DateWithSales))` stops the YTD line from flat-lining into future
months (AP-006). Date table is marked, so `REMOVEFILTERS('Date')` is implicit.

Fiscal variant: `DATESYTD ( 'Date'[Date], "06-30" )` for a fiscal year ending June 30.

---

## 2. Same period last year and YOY %

```dax
Sales PY :=
CALCULATE ( [Sales Amount], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Sales YOY :=
VAR Curr = [Sales Amount]
VAR Prev = [Sales PY]
RETURN IF ( NOT ISBLANK ( Curr ) && NOT ISBLANK ( Prev ), Curr - Prev )

Sales YOY % :=
DIVIDE ( [Sales YOY], [Sales PY] )
```
Reasoning: compose from base + `Sales PY` (BP-020). `DIVIDE` guards the zero/blank denominator
(BP-021). Capturing `Curr`/`Prev` in variables avoids recomputation and makes the blank guard
readable (BP-022).

---

## 3. Rolling 12 months (moving annual total)

```dax
Sales MAT :=
IF (
    MIN ( 'Date'[DateWithSales] ),
    VAR LastDate = MAX ( 'Date'[Date] )
    VAR FirstDate = EDATE ( LastDate, -12 ) + 1
    RETURN
        CALCULATE (
            [Sales Amount],
            DATESBETWEEN ( 'Date'[Date], FirstDate, LastDate )
        )
)
```
Reasoning: `EDATE` is a **scalar** date function used correctly in a row/scalar position
(BP-032), feeding `DATESBETWEEN` (a table function) inside `CALCULATE`.

---

## 4. Running total (cumulative)

```dax
Sales RT :=
VAR LastVisibleDate = MAX ( 'Date'[Date] )
VAR LastDateWithData =
    CALCULATE ( MAX ( 'Sales'[OrderDate] ), REMOVEFILTERS () )
VAR Result =
    CALCULATE ( [Sales Amount], 'Date'[Date] <= LastVisibleDate )
RETURN
    IF ( MIN ( 'Date'[Date] ) <= LastDateWithData, Result )
```
Reasoning: the filter `'Date'[Date] <= LastVisibleDate` replaces the existing Date filter
(that's intended). If you must keep, say, a Day-of-Week slicer, re-apply it (BP-025):
add `, VALUES ( 'Date'[Day of Week] )` is wrong — instead wrap the running-total filter so the
weekday filter survives:

```dax
Sales RT Weekdays :=
VAR LastVisibleDate = MAX ( 'Date'[Date] )
RETURN
CALCULATE (
    [Sales Amount],
    'Date'[Date] <= LastVisibleDate,
    VALUES ( 'Date'[Day of Week] )      -- re-apply the weekday selection that the date filter would clear
)
```

---

## 5. Semi-additive: end-of-period inventory

```dax
Units On Hand (EOP) :=
CALCULATE (
    SUM ( 'Inventory'[On Hand Quantity] ),
    LASTNONBLANK ( 'Date'[Date], CALCULATE ( SUM ( 'Inventory'[On Hand Quantity] ) ) )
)
```
Reasoning: stock is **semi-additive** — you sum across products/stores but take the *last*
value across time, never the sum across time. `LASTNONBLANK` picks the last date in context
that actually has a balance. Showing this measure summed across months would be wrong (AP-005).

---

## 6. Static segmentation (banding by a fixed table)

Use the `'Customer Segments'` config table (Segment, Min Sales, Max Sales). A **static**
assignment (customer's lifetime spend) is a calculated column on Customer:

```dax
Customer[Segment] =                        -- calculated column
VAR LifetimeSales =
    CALCULATE ( [Sales Amount], ALLEXCEPT ( 'Customer', 'Customer'[CustomerKey] ) )
RETURN
    CALCULATE (
        VALUES ( 'Customer Segments'[Segment] ),
        FILTER (
            'Customer Segments',
            'Customer Segments'[Min Sales] <= LifetimeSales
                && 'Customer Segments'[Max Sales] > LifetimeSales
        )
    )
```
Reasoning: a calculated column is correct here because the band is row-fixed and used as a
slicer axis (BP-011). The config table has no relationship; we look up the matching band.

---

## 7. Dynamic segmentation (banding by a measure, respecting filters)

```dax
Customers in Segment :=
SUMX (
    VALUES ( 'Date'[Year] ),                      -- evaluate per year so a customer isn't double-counted
    VAR SegMin = MIN ( 'Customer Segments'[Min Sales] )
    VAR SegMax = MAX ( 'Customer Segments'[Max Sales] )
    VAR CustomersInSeg =
        FILTER (
            VALUES ( 'Customer'[CustomerKey] ),
            VAR CustSales = [Sales Amount]
            RETURN CustSales > SegMin && CustSales <= SegMax
        )
    RETURN
        CALCULATE (
            DISTINCTCOUNT ( 'Sales'[CustomerKey] ),
            KEEPFILTERS ( CustomersInSeg )         -- intersect with current selection
        )
)
```
Reasoning: dynamic because the band depends on filtered `[Sales Amount]`. `KEEPFILTERS`
(BP-024) makes the computed customer set intersect the user's slicers. The `SUMX` over years
fixes the non-additive total (AP-005). The config table must have non-overlapping ranges.

---

## 8. Static ABC classification (calculated column)

```dax
Product[ABC Class] =                       -- calculated column
VAR ProductSales =
    CALCULATE ( [Sales Amount], ALLEXCEPT ( 'Product', 'Product'[ProductKey] ) )
VAR AllProductsSales =
    CALCULATE ( [Sales Amount], ALL ( 'Product' ) )
VAR CumulatedSalesDownTo =
    CALCULATE (
        [Sales Amount],
        ALL ( 'Product' ),
        FILTER (
            ALL ( 'Product' ),
            CALCULATE ( [Sales Amount], ALLEXCEPT ( 'Product', 'Product'[ProductKey] ) ) >= ProductSales
        )
    )
VAR CumPct = DIVIDE ( CumulatedSalesDownTo, AllProductsSales )
RETURN
    SWITCH ( TRUE (), CumPct <= 0.7, "A", CumPct <= 0.9, "B", "C" )
```
Reasoning: ABC is a running share of total, ranked high→low. Static version = calculated column
so class is a stable slicer axis (BP-011). For per-year ABC, use a **snapshot table** keyed by
(Year, ProductKey) instead (snapshot guidance).

---

## 9. New and returning customers

```dax
New Customers :=
VAR CustomersThisPeriod = VALUES ( 'Sales'[CustomerKey] )
VAR FirstDateInContext = MIN ( 'Date'[Date] )
VAR NewOnes =
    FILTER (
        CustomersThisPeriod,
        VAR FirstEver =
            CALCULATE ( MIN ( 'Sales'[OrderDate] ), ALLEXCEPT ( 'Sales', 'Sales'[CustomerKey] ) )
        RETURN FirstEver >= FirstDateInContext
    )
RETURN COUNTROWS ( NewOnes )
```
Reasoning: a customer is "new" if their **first-ever** purchase falls inside the visible period.
`ALLEXCEPT('Sales','Sales'[CustomerKey])` computes each customer's global first order regardless
of the period filter. Decide up front whether category/store filters should affect "new"
(AP: define new/returning precisely before coding — performance and meaning both change).

---

## 10. Ranking — static column and dynamic measure

```dax
-- Static: rank does not react to slicers (calculated column on Product)
Product[Product Rank] =
RANKX ( ALL ( 'Product' ), [Sales Amount],, DESC, DENSE )

-- Dynamic: rank reacts to filters (measure)
Product Rank :=
IF (
    HASONEVALUE ( 'Product'[ProductKey] ),
    RANKX ( ALLSELECTED ( 'Product'[Product Name] ), [Sales Amount],, DESC, DENSE )
)
```
Reasoning: static rank = calculated column over `ALL('Product')`; dynamic rank = measure over
`ALLSELECTED` so it ranks among the products the user is currently viewing. `HASONEVALUE`
guards the total row (don't rank a total).

---

## 11. Events in progress (open orders on a date)

```dax
Open Orders :=
VAR RefDate = MAX ( 'Date'[Date] )
RETURN
CALCULATE (
    DISTINCTCOUNT ( 'Sales'[SalesKey] ),
    'Sales'[OrderDate] <= RefDate
        && 'Sales'[DeliveryDate] > RefDate,
    REMOVEFILTERS ( 'Date' )                 -- the date axis is used as the reference point, not a filter
)
```
Reasoning: "in progress at date D" = started on/before D and not yet finished. We turn the Date
context into a single reference point (`RefDate`), then clear the Date filter and re-express the
condition as an event-overlap predicate.

---

## 12. Parameter table / what-if (disconnected slicer)

```dax
-- 'Top N Param'[Top N] is a disconnected slicer table (1..50)
Sales Top N Products :=
VAR N = SELECTEDVALUE ( 'Top N Param'[Top N], 10 )
VAR TopProducts = TOPN ( N, VALUES ( 'Product'[ProductKey] ), [Sales Amount], DESC )
RETURN
    CALCULATE ( [Sales Amount], KEEPFILTERS ( TopProducts ) )
```
Reasoning: a disconnected parameter table feeds a value via `SELECTEDVALUE` (BP-027). `TOPN`
builds the dynamic set; `KEEPFILTERS` keeps the user's other selections intact (BP-024).

---

## 13. Currency conversion

```dax
Sales (Reporting Currency) :=
SUMX (
    VALUES ( 'Date'[Date] ),
    VAR DailyRate =
        CALCULATE (
            SELECTEDVALUE ( 'ExchangeRate'[Rate] ),
            'ExchangeRate'[Date] = MAX ( 'Date'[Date] )
        )
    RETURN [Sales Amount] * DailyRate
)
```
Reasoning: convert at the **daily** rate, then sum — never convert an aggregate at one rate.
Iterating `VALUES('Date'[Date])` keeps the conversion at the correct grain. Choose the rate
policy (transaction-date vs. end-of-period) deliberately with the business.

---

## 14. Week-to-date on a custom (4-4-5) calendar

```dax
Sales WTD :=
VAR CurrentWeek = MAX ( 'Date'[Year Week] )       -- sequential week key on a custom calendar
RETURN
    CALCULATE (
        [Sales Amount],
        'Date'[Year Week] = CurrentWeek,
        'Date'[Date] <= MAX ( 'Date'[Date] )
    )

Sales Prior Week :=
VAR PrevWeekIndex = MAX ( 'Date'[Week Index] ) - 1
RETURN CALCULATE ( [Sales Amount], 'Date'[Week Index] = PrevWeekIndex )
```
Reasoning: built-in time intelligence assumes a Gregorian calendar, so on a 4-4-5 / week calendar
we navigate with our own **sequential index columns** (`Week Index`, `Year Week`) instead of
`DATESYTD`/`SAMEPERIODLASTYEAR`. Keep the index contiguous so `-1` always means "previous week."

---

## 15. Parent-child hierarchy (chart of accounts)

```dax
Account[Path]    = PATH ( 'Account'[AccountKey], 'Account'[ParentAccountKey] )
Account[Level 1] = LOOKUPVALUE ( 'Account'[Account Name], 'Account'[AccountKey], PATHITEM ( 'Account'[Path], 1, INTEGER ) )
Account[Level 2] = LOOKUPVALUE ( 'Account'[Account Name], 'Account'[AccountKey], PATHITEM ( 'Account'[Path], 2, INTEGER ) )
Account[Depth]   = PATHLENGTH ( 'Account'[Path] )
```
Reasoning: a self-referencing `AccountKey`/`ParentAccountKey` becomes browsable by flattening the
`PATH` into level columns. For ragged hierarchies (a leaf shallower than the deepest level), repeat
the leaf name or blank deeper levels so the matrix doesn't show empty rows. Calculated columns are
correct here because the levels are a fixed browsing axis.

---

## 16. Transition matrix (customer segment migration)

```dax
Customers Moved :=
VAR FromSeg = SELECTEDVALUE ( 'Segment From'[Segment] )   -- disconnected from-axis
VAR ToSeg   = SELECTEDVALUE ( 'Segment To'[Segment] )     -- disconnected to-axis
RETURN
    COUNTROWS (
        FILTER (
            VALUES ( 'Customer'[CustomerKey] ),
            [Segment Last Year] = FromSeg && [Segment This Year] = ToSeg
        )
    )
```
Reasoning: two **disconnected** axes supply the "from" and "to" classes; per customer we evaluate
the class measure at each period boundary and count those whose pair matches the cell. The class
measures (`[Segment Last Year]`, `[Segment This Year]`) must each fix their own period context.

---

## 17. Survey analysis (many-to-many answers)

```dax
Respondents := DISTINCTCOUNT ( 'Answers'[RespondentKey] )

Respondents Choosing Answer :=
CALCULATE (
    [Respondents],
    TREATAS ( VALUES ( 'Answer Filter'[AnswerKey] ), 'Answers'[AnswerKey] )
)
```
Reasoning: surveys are many-to-many (a respondent has many answers; an answer is shared by many
respondents). Always count **distinct respondents**, not answer rows, and route the filter across
the many-to-many explicitly (here with `TREATAS`) rather than enabling bidirectional relationships.

---

## 18. Basket analysis (bought-together)

```dax
Orders with A and B :=
VAR OrdersWithA = CALCULATETABLE ( VALUES ( 'Sales'[OrderKey] ) )   -- A comes from the normal Product filter
RETURN
    CALCULATE (
        DISTINCTCOUNT ( 'Sales'[OrderKey] ),
        OrdersWithA,
        TREATAS ( VALUES ( 'Product B'[ProductKey] ), 'Sales'[ProductKey] )   -- "and also contains B"
    )
```
Reasoning: a second **disconnected** `'Product B'` table provides the "and also" role; we first
capture the orders containing A, then count distinct orders that also contain B (applied via
`TREATAS`). Count distinct **orders**, not lines, and make sure A and B aren't the same product.

---

## 19. Budget vs actual (mixed granularity)

```dax
Budget Amount := SUM ( 'Budget'[Budget Amount] )      -- budget stored at Month x Category grain
Variance      := [Sales Amount] - [Budget Amount]
Variance %    := DIVIDE ( [Variance], [Budget Amount] )
```
Reasoning: actuals are at day×product but the budget exists only at month×category. Relate `'Budget'`
at *its* grain and slice it only by columns it supports (Month, Category) — filtering by Product or
Date day would return blank. Align the two through shared higher-grain attributes; guard `Variance %`
with `DIVIDE`.
