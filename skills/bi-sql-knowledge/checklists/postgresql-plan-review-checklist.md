# PostgreSQL Plan Review Checklist

Use only for a supplied, sanitized PostgreSQL JSON plan. Do not execute the query or prescribe
automatic tuning.

## Evidence gate

- [ ] SQL purpose/fingerprint and PostgreSQL version are recorded.
- [ ] Full `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` evidence is attached.
- [ ] The statement is read-only; no secret, host, literal PII, or credential is present.
- [ ] Table-size/statistics context and representative parameter class are stated.
- [ ] Input and output grain are stated and result correctness is reconciled.

If the plan is absent or unsafe, stop with `needs-evidence` or `blocked`. Bare SQL cannot receive a
performance verdict.

## Interpretation

- [ ] Dominant root-to-leaf branch identified using actual time, rows, and loops.
- [ ] Estimated-versus-actual cardinality differences recorded at the relevant nodes.
- [ ] Per-loop work interpreted with total loops.
- [ ] Scan choices assessed against selectivity, table size, locality, and visibility.
- [ ] Join choices assessed against actual outer/build rows and repeated work.
- [ ] Rows removed by filters interpreted with input rows and loops.
- [ ] Sort/hash memory, batches, disk use, and temp blocks checked.
- [ ] Shared/local/temp buffer evidence checked.
- [ ] Planned/launched workers and worker skew checked where relevant.
- [ ] Statistics freshness, skew, correlation, and parameter sensitivity noted.

## Recommendation safety

- [ ] Observation is separated from plausible causes.
- [ ] Each recommendation names the missing or confirming evidence.
- [ ] Index advice includes read benefit plus write, storage, and maintenance cost.
- [ ] Configuration advice includes concurrency and workload-wide memory/capacity evidence.
- [ ] Before/after claims use equivalent results and comparable conditions.
- [ ] No readiness stage, approval, or metric policy is advanced.

## Terminal artifact

Return one verdict:

- `clean`: no material plan risk observed **within the supplied representative evidence**;
- `needs-evidence`: a useful hypothesis exists, but required evidence is missing;
- `blocked`: the artifact is unsafe, incomplete beyond interpretation, or correctness is not
  established.

Include evidence, observations, hypotheses, confirming checks, blockers, and next action. These
labels are diagnostic states, not scores and not readiness approvals.

