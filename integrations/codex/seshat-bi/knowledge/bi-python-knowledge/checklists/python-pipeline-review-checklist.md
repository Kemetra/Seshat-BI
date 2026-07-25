# Python Pipeline Review Checklist

Terminal artifact for active-rule and recommended-pattern review.

## Grounding

- [ ] Source/profile revision, dataframe roles, and grain are declared.
- [ ] Metric meaning references an approved upstream contract.
- [ ] Every transformation has purpose, inputs, output grain, and evidence.

## Correctness and evidence

- [ ] Dtype coercions attach a rejection ledger.
- [ ] Missing-value changes cite approved dispositions.
- [ ] Merges pass the merge/fan-out checklist.
- [ ] Aggregations pass the aggregation/grain checklist.
- [ ] Dates/timezones/calendars cite governed policy.
- [ ] Validation uses independent expectations and predeclared tolerances.

## Performance and boundaries

- [ ] Performance claims cite stage timing and memory evidence.
- [ ] Projection/filtering precede expensive operations where valid.
- [ ] SQL pushdown and single-node/Big Data boundary were considered.
- [ ] No active rule finding is auto-fixed across a semantic boundary.

## Verdict

Choose exactly one:

- **PIPELINE REVIEW CLEAN** — applicable controls have evidence.
- **OPEN FINDINGS** — active findings list rule, evidence, consequence, and fix direction.
- **NEEDS EVIDENCE** — applicability cannot be determined.
- **BLOCKED** — metric, mapping, grain, or approval is unresolved.

This is a reasoning artifact. It does not execute the pipeline or grant readiness.
