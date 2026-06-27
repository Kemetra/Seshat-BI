# Data Volume Assessment

How to assess a real source's **volume and large-source risk** so that any scale
decision is evidence-based and repeatable — never anticipated. This applies the
boundaries set in `docs/big-data/big-data-capability-report.md`: Big Data is a
scale/latency *condition*, and tooling is a response to a measured problem, not a
default.

This is **assessment language only**. It adds no runtime code, no dependency, no
Python performance slice, no distributed/lakehouse platform guidance beyond
assessment, and it does not create `analytics-scale-knowledge`. It does not claim
Big Data support has been implemented.

## What this assessment answers

For one source/table, with evidence (row counts, byte size, growth rate, refresh
cadence, latency need):

- Does this fit and run comfortably on a **single machine** today?
- Should the heavy work be **pushed down to the warehouse**?
- Does it need a **human scale review** because single-node + push-down are in doubt?
- Is it **blocked** for want of the evidence needed to decide?

## How to use it

1. Fill `templates/data-volume-profile.md` from real, measured figures (never
   guessed) — size, rows, growth, cadence, latency requirement.
2. If the profile trips any large-source signal, fill
   `templates/large-source-profile.md` with the deeper detail (partitioning,
   skew risk, join fan-out at scale, format).
3. Run `checklists/large-source-review-checklist.md` to reach one **verdict** (see
   the vocabulary below).
4. A verdict is a status + named blockers, **never a numeric score or percentage**.

## Verdict vocabulary

| Verdict | Meaning | Typical next step |
|---------|---------|-------------------|
| `LOCAL_OK` | Fits and runs comfortably single-node today (within Python's single-machine reach). | Proceed on the existing path; no scale action. |
| `WAREHOUSE_RECOMMENDED` | The heavy join/aggregation belongs in SQL / the warehouse (push-down), not scaled out. | Push the computation down; no distributed tooling. |
| `SCALE_REVIEW_REQUIRED` | Single-node and push-down are both in doubt on the evidence; a human scale review is needed. | Human ruling on the trade-off; only then consider a future `analytics-scale-knowledge` step. |
| `BLOCKED` | The evidence required to decide (real size/growth/latency figures) is missing. | Gather the measured figures; do not guess a verdict. |

A verdict never adopts a platform and never grants readiness. `SCALE_REVIEW_REQUIRED`
is a request for a human decision, not an authorization to install Spark/Fabric/
Databricks/Snowflake/BigQuery.

## Boundaries

- **No tooling adopted.** This is assessment, not a platform decision.
- **No fake confidence.** Verdicts are statuses + blockers; missing evidence is
  `BLOCKED`, never a silent pass.
- **Medallion preserved.** A verdict changes *how* a stage is computed, never the
  Source → Mapping → Silver → Gold → Semantic Model → Dashboard → Publish order.
- **Human-gated.** Adopting any scale capability remains a named human decision.

## See also

- `docs/big-data/big-data-capability-report.md` — the strategy/boundaries this
  assessment applies.
- `templates/data-volume-profile.md`, `templates/large-source-profile.md`,
  `checklists/large-source-review-checklist.md` — the fill-in artifacts.
- `skills/bi-bigdata-knowledge/` — the reasoning layer that informs a
  `SCALE_REVIEW_REQUIRED` discussion (reasoning only; it runs nothing).
