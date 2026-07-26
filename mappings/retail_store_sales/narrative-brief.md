# Narrative brief -- retail_store_sales

<!--
  AGENT-AUTHORED DRAFT, awaiting owner review (issue #514, D1-D4).

  Derived via the `bi-analyst-knowledge` derivation route from EXACTLY TWO
  committed inputs: the 5 approved metric contracts (mappings/retail_store_sales/
  metrics/) and mappings/retail_store_sales/source-profile.md. No third artifact
  seeded any question -- `design/report-intent.yaml` was NOT used as an input
  (its own readiness is `blocked` pending report_intent_approval, and the
  derivation route permits "exactly two; nothing else").

  This is EVIDENCE FOR the named human design review. It grants nothing, sets no
  readiness stage, and the `Reviewed by:` line is deliberately empty.
-->

```yaml
schema: seshat.narrative-brief/v1
table: retail_store_sales
source_profile: mappings/retail_store_sales/source-profile.md

contracts:
  - id: TotalSales
    revision: f019492a4d10acbb6a57bf8cf3d7da850bd28c44
  - id: TransactionCount
    revision: 250309e6b75c86ae131e4ee99c8730e0cfffe35b
  - id: AvgTransactionValue
    revision: 506e449bc1cace4230ac83302a6772cfe00ce0ef
  - id: TotalQuantity
    revision: 221e385c504cabeb592b3c33951e9acc566cd23f
  - id: DiscountedTransactionRate
    revision: 7873eb89ad3a79185a78ebaea300ed19a6fbd23b

questions:
  - id: Q1
    decision: >-
      Whether this period's trading needs intervention at all, or the team can
      hold course.
    stage: overview
    framing: period-variance
    cites:
      measures: [TotalSales, TransactionCount, AvgTransactionValue]
      dimensions: [dim_date_rss.full_date]
    comparison: same period last year (YoY)
    guardrail:
      basis: same period last year
      window: three full years of history (2022-01-01 .. 2025-01-18)
    callout: >-
      Revenue is <+/-X%> (<+/-abs>) vs the same period last year, on <+/-Y%>
      transactions and a <+/-Z%> basket -- so the move is <volume-led /
      basket-led / broad-based>.

  - id: Q2
    decision: >-
      Whether a month's swing is a real change worth acting on, or ordinary
      variation to leave alone.
    stage: change
    framing: trend-anomaly
    cites:
      measures: [TotalSales]
      dimensions: [dim_date_rss.full_date]
    comparison: trailing band over the monthly series
    guardrail:
      basis: trailing mean +/- 2 x trailing SD of monthly TotalSales
      window: trailing 12 months, k=2
    callout: >-
      Monthly revenue is <inside / outside> its trailing band; <the flagged
      month> is <unusual / seasonal, not anomalous -- it recurs at the same
      phase last year>.

  - id: Q3
    decision: >-
      Which product categories to push, protect, or stop carrying.
    stage: why_where
    framing: contribution-mix
    cites:
      measures: [TotalSales, TotalQuantity]
      dimensions: [dim_product_rss.category]
    comparison: share of current total, and share vs same period last year
    guardrail:
      basis: same period last year for the share shift
    callout: >-
      <n> of 8 categories drive <X%> of revenue; <category> is <gaining /
      losing> share, and its units move <with / against> its revenue -- so the
      shift is <demand / price-mix>.

  - id: Q4
    decision: >-
      Whether to shift effort or spend between in-store and online.
    stage: why_where
    framing: contribution-mix
    cites:
      measures: [TotalSales, TransactionCount]
      dimensions: [dim_location_rss.location]
    comparison: share of current total, and share vs same period last year
    guardrail:
      basis: same period last year for the share shift
    callout: >-
      <channel> takes <X%> of revenue on <Y%> of transactions; its share is
      <rising / falling> vs last year, so the channel mix is <stable /
      shifting toward <channel>>.

  - id: Q5
    decision: >-
      Whether the discount posture is working, or is quietly funding volume.
    stage: action
    framing: benchmark-threshold
    cites:
      measures: [DiscountedTransactionRate, AvgTransactionValue]
      dimensions: [dim_date_rss.full_date]
    comparison: the period's own known-status discount rate
    guardrail:
      basis: the period average discount rate over known-status transactions
      min_sample_floor: 100
    callout: >-
      <X%> of KNOWN-STATUS transactions carried a discount (unknowns excluded,
      not counted as undiscounted); discounted baskets average <A> vs <B>
      undiscounted -- so discounting is <lifting / not lifting> basket value.

story_order:
  overview:  [Q1]
  change:    [Q2]
  why_where: [Q3, Q4]
  action:    [Q5]

gaps:
  - question: >-
      Which categories are actually profitable, not merely high-revenue?
    missing_source_fact: >-
      no cost or margin column exists in this source -- the profile records
      price_per_unit, quantity and total_spent only
    unlocking_feed: a supplier cost or purchase-price feed keyed to item

  - question: What is being returned, and why?
    missing_source_fact: >-
      no returns in this source -- the profile states "Returns population & how
      identified. NONE in this source. No negative or zero rows, no
      transaction-type / return-flag column" (RC8 N/A)
    unlocking_feed: a returns / credit-note feed carrying a transaction reference

  - question: >-
      Who are the highest-activity customers, and should we act on individual
      customer behaviour?
    missing_source_fact: >-
      customer_id is profiled (25 distinct, 0.00% missing) but the profile
      records its PII/publish-safety question as OPEN, with "Source-ready
      status: warning -- Not `pass` until the analyst confirms the semantics and
      governance rules on the PII column". No permitted input carries a ruling
      that customer-level publishing is approved.
    unlocking_feed: >-
      the governance ruling written THROUGH to source-profile.md (the Q1 keep
      decision of 2026-06-25 currently lives only in unresolved-questions.md and
      the readiness approvals[], neither of which is a derivation input)
```

## Q1 -- does this period need intervention? (overview)

The three headline measures answer one decision: hold course, or dig. Revenue
alone cannot, because the same revenue drop reads differently if transactions
held and baskets shrank than if traffic fell.

The comparison is **year-over-year**, not prior-month, and that choice is
grounded rather than conventional: the profile measures `transaction_date` at
0.00% missing with 1,114 distinct values spanning **2022-01-01 .. 2025-01-18**,
so there are three full years of history — enough for a same-phase comparison,
which is what the seasonality guardrail requires. A prior-month comparison on
retail trading would report seasonal shape as if it were news.

`AvgTransactionValue` is a **ratio and not additive** (its contract says so
plainly). It appears here as a headline recomputed at the current filter grain,
never summed and never pre-aggregated.

## Q2 -- is that swing real? (change)

A monthly series invites over-reading: one strong month becomes a narrative, and
the narrative reverses next month. The band is the discipline — trailing mean
±2×SD over a trailing 12 months, which is a **labeled display derivation** of
approved `TotalSales`, not a new metric.

Two withholding rules apply, and both should be honoured out loud rather than
quietly skipped. If the filtered series is too short for a stable band, the
brief says the basis is insufficient and shows the trend plain. And a spike that
recurs at the same phase last year is **seasonal, not anomalous** — the three
years of history make that check possible.

## Q3 -- which categories to push or drop? (why/where)

`category` is the strongest dimension in the profile: 8 distinct values, **0.00%
missing**. It is also clean structurally — `item` is 1:1 with `category` with
zero fan-out, so a category rollup does not double-count.

Revenue share and unit share are read **together** on purpose. Revenue share
rising while unit share is flat is a price-or-mix story; both rising is a demand
story. They imply different actions, which is why the question cites two
measures rather than one.

Two guardrails from the card: a member's share can rise simply because the total
shrank, so share-shift is read alongside the absolute before claiming a category
"gained"; and sub-1% categories are grouped rather than narrated individually.

One caveat this question must carry: `item` is **9.65% missing** (1,213 rows).
Those rows land on the `-1` unknown product member by design, so category-level
revenue is complete while item-level detail is not. A category reading is sound;
an item-level ranking would be quietly incomplete.

## Q4 -- in-store or online? (why/where)

`location` is fully populated (0.00% missing) with exactly two values, so the
channel split is a complete picture rather than a sample.

Revenue share is read against transaction share deliberately: a channel taking a
larger revenue share than its transaction share is selling bigger baskets, which
is a different decision from a channel simply having more traffic.

With only two members, the "group the tiny members" rule is moot — but the
composition caveat still bites, since with two members one share cannot move
without the other moving.

## Q5 -- is discounting working? (action)

This is the action-stage question, and the one most easily reported wrongly.

The approved `DiscountedTransactionRate` **excludes unknowns from both numerator
and denominator**, per the Q2 ruling that a blank `discount_applied` is UNKNOWN
rather than False. The contract records the current value as `4,219 / 8,376 =
50.37%` and explicitly flags that an earlier draft "wrongly framed the
denominator as ALL transactions / 33.55%".

So any callout here **must** say "of known-status transactions". The profile
measures `discount_applied` at **4,199 / 33.39% blank** and lists it as open item
1 — "blank semantics undecided (unknown vs False); drives every discount metric
downstream". A third of the data has no discount status, and a reader told "50%
of transactions were discounted" would be misled about a number the data does not
support.

The `min_sample_floor: 100` is the rate guardrail: below that count of
known-status transactions in a filter, the rate is reported as
**insufficient-sample** and withheld — never ranked, sorted, or narrated.

## Gaps

Three questions an owner would reasonably ask that this source cannot answer.
Each is recorded rather than dropped, and none appears as a `questions[]` entry —
you cannot frame what you cannot answer.

**Profitability** needs a cost feed; the profile carries price, quantity and
total only. **Returns** are absent outright — the profile states there are no
negative or zero rows and no return-flag column, and the data owner confirmed
returns live in a separate system.

**Customer-level analysis** is the one worth flagging to the reviewer, because it
looks answerable and is not. `customer_id` is profiled and clean (25 distinct,
0.00% missing), so a customer question is tempting. But the profile records the
PII/publish-safety question as **open**, with `Source-ready status: warning` for
that reason. The ruling that answers it (2026-06-25, data owner: keep
`customer_id` as `dim_customer`) exists — but in `unresolved-questions.md` and
the readiness `approvals[]`, **neither of which is a permitted derivation
input**. Deriving strictly, this brief cannot treat customer-level publishing as
approved, so the question is a gap rather than Q6.

The clean fix is an owner edit: write that Q1 outcome through to
`source-profile.md` so the permitted input carries the ruling that depends on it.
Then this gap becomes a question.

## Review

- **Authored by:** agent (`bi-analyst-knowledge` derivation route), 2026-07-26
- **Reviewed by:** <!-- empty: awaiting the named report owner's review of this draft (issue #514, D1-D4) -->

<!--
  The reviewer line records that a named human REVIEWED this brief. It is filled
  ONLY by transcribing a review a named human actually gave -- never invented,
  never self-supplied. A clean `seshat narrative-check` is evidence FOR that
  review, never the review itself, and never an approval.
-->
