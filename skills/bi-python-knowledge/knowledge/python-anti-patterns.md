# Python BI Anti-Patterns

Use this resource with `patterns/analyzer-rules.json`; end on
`checklists/python-pipeline-review-checklist.md`.

## Decision this route supports

Identify whether a proposed dataframe pipeline contains known correctness, evidence,
boundary, or performance failures.

## Required evidence

- pipeline or notebook steps;
- grain/schema/metric contracts;
- recorded profiles and reconciliation artifacts;
- observed runtime evidence for performance findings.

## Active review failures

| ID | Anti-pattern | Why it fails | Required response |
|---|---|---|---|
| PY-AP-026 | Merge without declared cardinality | fan-out is undetectable by intent | run merge checklist |
| PY-AP-027 | Validation expected value derived from actual path | shared defects cancel | use independent boundary |
| PY-AP-028 | Aggregate parity before key uniqueness | duplicate identities can preserve totals | test grain first |
| PY-AP-029 | Silent coercion | invalid literals disappear into nulls | attach rejection ledger |
| PY-AP-030 | Environment-dependent date parsing | locale/timezone changes output | declare parser policy |
| PY-AP-031 | Row-wise loop for column logic | slow and obscures semantics | use explicit vector expression |
| PY-AP-032 | Chunked global operation without state design | cross-chunk keys misaggregate | push down or reconcile globally |
| PY-AP-033 | Memory failure blamed on scale before fan-out check | wrong join drives false scale-out | diagnose cardinality |
| PY-AP-034 | Sample treated as reconciliation | population defects remain unseen | add full controls |
| PY-AP-035 | Clean Python verdict treated as readiness | bypasses governance | hand evidence to readiness |

## Reasoning sequence

1. Establish the pipeline phase and expected artifact.
2. Apply active rules only where required evidence exists.
3. Report rule ID, observed signal, evidence, consequence, and fix direction.
4. Mark absent evidence as `needs_evidence`, never as a detected defect.
5. Re-run the terminal checklist after corrections.

## Failure modes

- flagging code style with no BI consequence;
- inferring a violation from a function name alone;
- issuing an auto-fix that changes grain or metric meaning;
- using severity as a readiness score.

## Evidence-based verdict

- **NO ACTIVE FINDINGS** — all applicable rules have supporting clean evidence.
- **OPEN FINDINGS** — one or more rule signals are evidenced.
- **NEEDS EVIDENCE** — applicability cannot be determined.
- **BLOCKED** — a boundary or owner decision is missing.

## Stop and handoff

Rules reason about supplied artifacts; they do not run code, mutate a pipeline, or
grant approval.
