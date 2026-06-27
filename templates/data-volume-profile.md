# Data Volume Profile -- `<source-id>`

> **Template.** A repeatable, per-source record of **measured** volume facts used to
> assess scale. Fill every `<placeholder>` from real figures (query the source / read
> the file); never guess. This profile feeds the large-source review
> (`checklists/large-source-review-checklist.md`), which produces a verdict. This file
> records evidence only — it adopts no tooling and grants no readiness. Delete this
> blockquote when filling it in.

| Field | Value |
|-------|-------|
| Source id | `<source-id>` (e.g. `raw.sales`, a CSV path, a table) |
| Date assessed | `<YYYY-MM-DD>` |
| Author | `<name>` |
| Measured from | `<how the figures were obtained: row count query, file size, catalog stats>` |

## Measured volume facts (evidence — no guesses)

| Metric | Value | Note |
|--------|-------|------|
| Row count | `<N rows, or "not measured -> BLOCKED">` | exact or sampled-and-extrapolated (say which) |
| On-disk / uncompressed size | `<e.g. 850 MB / 12 GB, or "not measured">` | the figure that drives memory pressure |
| Column count / width | `<e.g. 42 columns; wide text?>` | wide rows raise memory cost |
| Growth rate | `<e.g. +2 GB/month, +5M rows/day, or "unknown">` | trend matters more than today's size |
| Refresh cadence | `<e.g. daily full / hourly incremental>` | drives latency pressure |
| Latency requirement | `<e.g. dashboard refresh < 10 min, or "none stated">` | the SLA, if any |
| Current processing path | `<single-node Python / SQL view / warehouse / none yet>` | where it runs today |

## Single-node reach check

| Question | Answer | Note |
|----------|--------|------|
| Does the uncompressed size fit comfortably in one machine's memory (with headroom)? | `<yes / no / unknown>` | "unknown" -> gather the figure |
| Can it be read in chunks / out-of-core on one machine if it does not fully fit? | `<yes / no / unknown>` | single-node large-file, not distribution |
| Is the heavy work a join/aggregation that the warehouse could do (push-down)? | `<yes / no / unknown>` | push-down often beats scale-out |

## Large-source signals (any "yes" -> fill the large-source profile)

- [ ] Size or growth is large enough that single-node headroom is in doubt.
- [ ] Latency requirement cannot be met on the current path.
- [ ] Join fan-out / skew is a known risk at this volume.
- [ ] Refresh cadence + volume together strain the current path.

## Preliminary indication (not the verdict)

> The verdict is produced by `checklists/large-source-review-checklist.md`, not here.
> This is only a first read of the evidence.

`<LOCAL_OK-likely / WAREHOUSE-likely / SCALE_REVIEW-likely / BLOCKED (evidence missing)>`
— `<one-line reason citing the measured facts above>`

## See also

- `docs/big-data/data-volume-assessment.md` — how this profile is used + the verdict vocabulary.
- `templates/large-source-profile.md` — the deeper detail when a signal trips.
- `checklists/large-source-review-checklist.md` — the review that issues the verdict.
