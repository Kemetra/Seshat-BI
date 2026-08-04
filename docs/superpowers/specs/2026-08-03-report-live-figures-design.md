# Report live figures (Increment B) — design

> Successor to `2026-08-03-report-surfaces-design.md`, whose Increment B was one
> sentence: "`bundle.py` reads gold through the `db` extra and a DSN, replacing
> the fixture source." Building it surfaced three facts that change its shape.
> This document records them and the design that follows.

**Status:** DRAFT — awaiting review.

## What Increment A left open

`seshat report` renders from an `--observations` file that carries six fields per
figure: `visual_id`, `contract_id`, `metric`, `unit_kind`, `label`, `value`.

That file is trusted for all six. Two of them should not be:

- `value` is a number nobody computed from data. It is the whole reason
  Increment B exists.
- `contract_id` is a **binding**, and a binding is a governed decision. Nothing
  stops an `--observations` file from claiming `visual_id: kpi_total_sales` cites
  `DiscountedTransactionRate`. Increment A would render it, cite it, and be
  wrong in a way that looks fully attributed.

## Three findings

### 1. The governed binding already exists, and it is machine-readable

`mappings/<table>/design/visual-contract-binding-map.md` carries a fenced
`seshat.binding-map/v1` front section — a **frozen** schema — listing every
measure-bearing visual and the one approved contract it binds to:

```yaml
schema: seshat.binding-map/v1
table: retail_store_sales
visuals:
  - visual_id: v01
    page: executive_overview
    contract: TotalSales
    decision_questions: [Q1]
    headline: true
```

This is the artifact the design review signs off. It is therefore the authority
on visual→contract, and the report has no business accepting a different answer
from a file an operator wrote.

**Sign-off note.** The committed map's header records the front section as added
under issue #514 Phase B and **awaiting owner re-sign (D5)**. What this design
consumes — `visual_id` and `contract` — is identical in the front section and in
the signed prose table below it; the unratified addition is the
`decision_questions` leg, which reports do not read. This design therefore does
not depend on the unratified part, and does not resolve D5.

### 2. A grouped figure is not derivable, and must refuse

The fixture's `by_region` section carries labelled figures — North, South, East.
A label means a `GROUP BY`, and the grouping column appears **only in the map's
prose table** (`[TotalSales]` by `dim_product_rss[category]`), never in the
machine-readable front section and never in a metric contract.

So a labelled figure cannot be resolved from governed, machine-readable state.
The options were to infer the grouping, to add it to a frozen schema, or to
refuse. **It refuses**, naming what is missing. Inferring a grouping would make
the report the place a breakdown is decided, which is the exact failure the
bundle arrangement exists to prevent; extending a frozen schema is an owner
action, not an implementation detail.

Consequence, stated plainly: Increment B resolves the five whole-table KPIs from
gold and cannot resolve the three regional figures. A live run of the shipped
fixture renders five real numbers and refuses rather than inventing three.

### 3. `unit_kind` stays declared, because inferring it is an open owner question

`ratio` is derivable — a contract with `definition.numerator`/`denominator` is a
ratio, and this design asserts that agreement rather than trusting it.

`currency` versus `count` is **not** derivable. The unit lives in
`source-map.yaml`'s `columns[].unit`/`currency`, and `rules/currency_unit.py`
(HR11) documents at length that how to treat an *undeclared* unit is spec 103
FR-014 — an explicit open Principle-V governance question that the rule "MUST
NOT and does NOT resolve on its own authority."

This design does not resolve it either. `unit_kind` remains a declared
rendering choice, and the one thing that *is* derivable is checked: a ratio
contract rendered as currency is refused.

## Design

Two new modules, both driver-free, and no change to any surface.

```
binding map ──┐
              ├─→ figure requests ──→ observe.py ──→ observations ──→ bundle.py
contracts ────┘                          │                              │
                                    QueryRunner                    (unchanged)
                                     (Protocol)
                                         │
                              psycopg2, built in the CLI only
```

### `report/binding.py`

Parses the front section; refuses a missing file, a file with no fenced block
carrying the expected `schema`, a schema value other than
`seshat.binding-map/v1`, an empty `visuals` list, a visual with no `visual_id` or
no `contract`, a duplicate `visual_id`, and a `table` that disagrees with the
table being rendered.

Yields `BindingMap.contract_for(visual_id)`, which raises rather than returning
`None` — an unbound visual is a refusal, not an absence.

### `report/observe.py`

Compiles one approved contract's `definition` + `binds_to` into SQL and runs it
through the `QueryRunner` Protocol already defined in `validate.py`. It imports
no driver, exactly as `validate.py` and `value_proxy.py` do not, which is what
keeps the static core `pyyaml`-only and lets the whole module be tested with an
injected fake.

Two definition families, matching what the committed contracts actually use:

| Family | Definition | SQL |
|---|---|---|
| base | `{kind: base, aggregation: …, filter: []}` | one scalar aggregate, with a `WHERE` if filtered |
| ratio | `{numerator: {…}, denominator: {…}}` | both sides as conditional aggregates in **one** statement, divided as `Decimal` |

A ratio's two sides may aggregate **differently**. That is not a hypothetical:
`DiscountedTransactionRate` is count-over-count, and `AvgTransactionValue` — one
of the three headline KPIs — is sum-over-filtered-count. Restricting a ratio to
count-over-count would have left a headline card permanently unable to go live,
so each side compiles independently.

Both sides are emitted in **one** statement. `value_proxy` runs its two sides as
separate queries, which is fine for a tolerance check; a published figure is
stricter, because two statements can straddle a write and yield a ratio that was
never true of any single state of the table.

A filtered column aggregate uses `agg(CASE WHEN … THEN col END)` rather than an
engine-specific `FILTER` clause: it is portable across every dialect here, and the
missing `ELSE` is load-bearing — excluded rows must contribute *nothing*, not
zero, or an average is dragged down by every row it was supposed to ignore.

Aggregate names reuse `value_proxy._AGG_SQL`. Filter ops reuse the
`metric_drift` whitelist — `is_not_null` and `is_true` — and **anything else is
refused**, never silently dropped, because a dropped filter changes the number
without changing the citation.

Identifiers are quoted through the `Dialect` seam, which validates before any
SQL is built.

**Every no-answer path yields `None`, which `bundle.py` already renders as
`[PENDING LIVE DATA]`:** no rows, a NULL scalar, an unparseable scalar, a zero
ratio denominator. A report that cannot reach a number says so.

### CLI

Three flags, and exactly one figure source per run:

- `--observations FILE` — figures **with** values, read offline (Increment A).
- `--from-gold --figure-plan FILE` — the plan says which figures to render and
  how to format them; the warehouse supplies every value.
- `--dsn` — the connection, falling back to the same environment resolution
  `validate` uses.

A **figure plan** is not an observations file with the numbers deleted, and the
distinction is enforced: a plan carrying a `value` is **refused**, not quietly
ignored. An operator who reuses a stale observations file would otherwise believe
those numbers had been checked against the warehouse when they were discarded.

A plan does not get to state a `contract_id` that differs from the signed binding
map. It may omit it; if it states one and disagrees, the render refuses rather
than silently using the governed answer — a silent override leaves the operator
believing the citation they wrote is the one on the page.

Every incoherent combination refuses rather than resolving: both sources, neither
source, `--from-gold` without a plan, and a plan without `--from-gold`.

The psycopg2 runner is constructed in the command handler, lazily, and nowhere
else. Without the `db` extra, `--from-gold` refuses and names the extra; rendering
from `--observations` needs no driver at all.

## What this design does and does not verify

**Verified here:** SQL compilation for both families, every refusal, every
`None` path, the binding-map parser against the real committed artifact, and the
ratio/`unit_kind` agreement check — all with an injected fake runner.

**Not verified here:** that the compiled SQL returns the right answer from a
real Postgres. This repo has no database, and provisioning one is out of scope
by standing rule. This is the same boundary `validate.py` and `value_proxy.py`
already sit behind, and the same remedy applies: the `livetest` extra and
`tests/live_db/`, whose tests self-skip when the harness is absent.

`tests/live_db/test_live_report_observe.py` is that test. It asserts the seeded
penny-exact total, the seeded row count, that a mixed-aggregate ratio is valid
SQL **and divides the right way round** (65.50/3 and 3/65.50 are both numbers;
only one is an average), that an empty table yields pending rather than zero —
`sum` over no rows is SQL `NULL`, and rendering it `0` would state the business
took nothing, which is a different claim from having no data — and that the
engine accepts every shipped statement at all.

**It has never been executed.** This machine has no Docker daemon, so the module
collection-skips. The test is written and honest; treat its assertions as unproven
until a run with the `livetest` extra reports them passing.

## Out of scope

Grouped/labelled figures (finding 2 — owner action). Unit inference (finding 3 —
spec 103 FR-014). Engines other than Postgres. Any write to a readiness status:
a successful live read does not advance a stage and never grants an approval.
