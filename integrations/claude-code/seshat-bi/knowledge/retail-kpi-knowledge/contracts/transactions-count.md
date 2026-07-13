# Transactions Count — Metric Contract

ID: KPI-MC-04

**Business question**
How many customer transactions (receipts) were processed in a given period?

**Business definition**
Count of distinct completed sales transactions (receipts) in the selected period,
excluding cancelled, void, and test transactions.

**Formula in business terms**
Transactions Count = count of distinct transaction id over qualifying transactions.

**Required fields**
- transaction id at header level *(confirmed concept — must be receipt-level, not line)*
- sale date key, branch key, channel key *(confirmed concept)*
- cancellation / void / test flags *(assumption)*

**Grain**
Transaction (receipt). Counted at any higher level.

**Additivity**
Semi-additive: safe to sum across branches and days when transaction id is globally
unique and time-bounded. Treat with care if the key is reused across branches or years —
use a composite key or distinct count, not a naive SUM of pre-counted rows.

**Recommended dimensions**
Date, time-of-day bucket, branch, region, channel, customer segment.

**Filters / exclusions**
- Exclude cancelled, void, and test transactions (A7).
- Optionally exclude return-only transactions (confirm — affects ATV and basket).

**Interpretation**
Proxy for completed-purchase traffic at POS. Combined with footfall it yields conversion;
it is the denominator for ATV and basket size.

**Common mistakes**
- Counting transaction lines instead of receipts (inflates the count).
- Counting returns as separate transactions for conversion purposes.
- Mixing transaction types (sales, returns, layaways) without filtering.

**Validation checks**
- Compare to POS end-of-day receipt counts.
- Check for zero transactions on known open days (anomaly).
- Confirm the id is header-level, not duplicated by line granularity.

**Implementation handoff notes (SQL / DAX / Python)**
Implement as a distinct count over the header key. If the sales fact is line-grained,
flag that a header table or a guaranteed-unique header key is needed so the distinct
count is correct. No DAX authored here.

**Dashboard use**
Sales Performance, Basket analysis, Store operations.

**Priority**
Core, MVP.

**Owner**
Operations and Sales.

**Status**
Seeded.
