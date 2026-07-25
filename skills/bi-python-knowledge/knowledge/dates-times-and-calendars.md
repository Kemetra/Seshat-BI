# Dates, Times, and Calendars

Use this route to parse event timestamps, derive business dates, or attach governed
calendar attributes. End on `checklists/dataframe-review-checklist.md`.

## Decision this route supports

Decide whether date/time fields can support the required business calendar without
silent parse loss, timezone drift, or period-label ambiguity.

## Required evidence

- raw formats and invalid counts;
- source timezone and daylight-saving behavior;
- business-date cutoff policy;
- governed calendar/fiscal definition;
- metric contract's time role and snapshot policy.

## Reasoning sequence

**PY-PB-017 — Date and calendar review**

- **PY-CN-125 — Parse validity is evidence.** Count unparsed, ambiguous, and out-of-range
  values; do not accept parser success on a sample.
- **PY-CN-126 — Timezone is part of the timestamp.** Localize known naive values before
  conversion; never guess the source timezone.
- **PY-CN-127 — Event time and business date can differ.** Apply only an approved
  cutoff/trading-day policy.
- **PY-CN-128 — Date dimensions own calendar attributes.** Prefer governed joins over
  independent weekday/month/fiscal logic in each pipeline.
- **PY-CN-129 — Fiscal and ISO periods are explicit contracts.**
- **PY-CN-130 — DST creates missing or repeated local times.** Record the handling rule.
- **PY-CN-131 — Period labels are derived, not keys.** Retain sortable date/period keys.
- **PY-CN-132 — Invalid dates are findings.** Quarantine or block; silent coercion hides
  source quality.

**PY-BP-014 — Preserve raw and parsed fields through validation** so rejected values
remain explainable.

## Failure modes

- day/month order inferred from workstation locale;
- naive timestamps treated as UTC;
- fiscal year derived as calendar year;
- month names used as sort keys;
- snapshot measure summed across dates;
- invalid timestamps dropped before freshness analysis.

## Evidence-based verdict

- **CLEAN** — parse validity, timezone, business date, and calendar roles are governed.
- **BLOCKED** — timezone, cutoff, fiscal calendar, or snapshot policy is missing.
- **HANDOFF** — route undecided time policy to the metric/source owner.

## Stop and handoff

This layer applies approved calendar semantics; it does not define them.
