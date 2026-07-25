# Dataframe Review Checklist

Terminal artifact for dataframe semantics, profiling, dtype, missing-value, and
date/calendar routes.

## Source and role

- [ ] Source artifact/revision and extraction boundary recorded.
- [ ] Frame role named: raw, profiled, cleaned, joined, or aggregated.
- [ ] One-row meaning and candidate identity stated (PY-CN-086..088).

## Structure and schema

- [ ] Full field inventory includes logical type, observed dtype, and nullable policy.
- [ ] Shape is recorded but not used as proof of grain.
- [ ] Candidate key uniqueness and null-key counts are attached.
- [ ] Schema drift is classified as add/remove/rename/reorder/type change.

## Values and missingness

- [ ] Cardinality, frequency concentration, ranges, and invalid counts are recorded.
- [ ] Null, blank, whitespace, and sentinels are counted separately where observed.
- [ ] No zero-fill, `Unknown` member, or sentinel mapping lacks approved disposition.

## Dates and provenance

- [ ] Parse failures, timezone, business-date cutoff, and calendar source are explicit.
- [ ] Raw values remain traceable through coercion.
- [ ] Before/after row counts and rejected-value ledger are attached.

## Verdict

Choose exactly one:

- **CLEAN** — evidence supports the declared grain and proposed preparation.
- **OPEN FINDINGS** — non-blocking data issues have owner and next check.
- **GRAIN VIOLATED** — identity evidence contradicts the declared row meaning.
- **BLOCKED** — source semantics, disposition, or named approval is missing.

Attach evidence and one exact next action. This checklist grants no readiness.
