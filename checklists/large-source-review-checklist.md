# Large-Source Review Checklist

> **Checklist.** Turns a filled data-volume profile (and, if a signal tripped, a
> large-source profile) into one **verdict** — a status + named blockers, never a
> numeric score. It applies the boundaries in
> `docs/big-data/big-data-capability-report.md`: assess from evidence; adopt no
> tooling; keep the medallion flow; leave platform adoption to a human. Run it per
> source; record the verdict and its evidence. Delete this blockquote when using it.

## Inputs

| Input | Path | Present? |
|-------|------|----------|
| Data-volume profile (filled, measured) | `templates/data-volume-profile.md` -> `<filled path>` | `<yes / no>` |
| Large-source profile (if a signal tripped) | `templates/large-source-profile.md` -> `<filled path or "n/a">` | `<yes / n/a>` |

> If the volume profile is missing or its core figures are unmeasured, the verdict is
> **`BLOCKED`** — do not guess.

## Review steps

- [ ] The volume profile's **row count and size are measured** (not guessed).
- [ ] **Growth rate and refresh cadence** are recorded.
- [ ] The **latency requirement** (or "none stated") is recorded.
- [ ] The **single-node reach check** is answered (fits / chunked / unknown).
- [ ] The **push-down question** is answered (is the heavy work a warehouse-able join/aggregation?).
- [ ] If any large-source signal tripped, the **large-source profile is filled** (partition key, skew, fan-out, format, incremental key, latency gap).
- [ ] Every **material unknown** is listed as a blocker.

## Verdict (choose exactly one)

| Verdict | Choose when |
|---------|-------------|
| `LOCAL_OK` | Size/growth fit comfortably single-node (or chunked on one machine), latency is met, no unresolved large-source signal. |
| `WAREHOUSE_RECOMMENDED` | The heavy join/aggregation belongs in SQL/the warehouse; push it down rather than scaling out. |
| `SCALE_REVIEW_REQUIRED` | Single-node **and** push-down are both in doubt on the evidence; escalate to a human scale review (which alone may later consider distributed capability). |
| `BLOCKED` | Required evidence (measured size/growth/latency) is missing; gather it before deciding. |

**Verdict:** `<LOCAL_OK / WAREHOUSE_RECOMMENDED / SCALE_REVIEW_REQUIRED / BLOCKED>`

**Named blockers / reasons (required — cite the measured facts):**

- `<the specific evidence or missing figure behind the verdict>`

## What a verdict is NOT

- **Not a score.** No percentage, no confidence number — status + blockers only.
- **Not a platform decision.** `SCALE_REVIEW_REQUIRED` requests a human ruling; it
  does not adopt Spark/Fabric/Databricks/Snowflake/BigQuery.
- **Not a readiness gate.** No readiness/dashboard/publish stage is advanced.
- **Not a Big Data implementation.** This checklist assesses; it builds nothing.

## See also

- `docs/big-data/data-volume-assessment.md` — the verdict vocabulary in context.
- `templates/data-volume-profile.md`, `templates/large-source-profile.md` — the inputs.
- `docs/big-data/big-data-capability-report.md` — the strategy/boundaries.
