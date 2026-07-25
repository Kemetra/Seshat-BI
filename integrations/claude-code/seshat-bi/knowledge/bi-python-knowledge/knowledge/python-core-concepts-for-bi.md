# Python Core Concepts for BI Source Preparation

This resource supplies the execution-independent concepts used by the Python routes.
It does not teach general Python or run a pipeline.

## Decision this route supports

Decide whether proposed dataframe work is deterministic, evidence-preserving, and
bounded to single-node source preparation.

## Required evidence

- declared input/output dataframe roles and grain;
- source/profile revision;
- proposed transformation sequence;
- expected schema and row-count controls;
- runtime/memory boundary when scale is uncertain.

## Reasoning sequence

- **PY-CN-092 — Pipeline phase is part of meaning.** Loading, profiling, cleaning,
  merging, aggregating, and validating have different evidence obligations.
- **PY-CN-093 — Provenance follows every frame.** Record source, extraction time or
  revision, transformation name, and parent frame.
- **PY-CN-094 — Determinism requires explicit inputs.** Locale, timezone, encoding,
  category maps, and calendar rules cannot depend on workstation defaults.
- **PY-CN-095 — Contracts precede coercion.** A conversion is justified by expected
  semantics and invalid-value handling, not by making an exception disappear.
- **PY-CN-096 — Domain checks complement dtypes.** `string` can hold invalid store
  codes; `float64` can hold impossible rates.
- **PY-CN-097 — Evidence ledgers survive handoff.** Before/after counts, rejected
  values, unmatched keys, and control totals travel with the result.

**PY-BP-009 — Prefer explicit, reviewable transforms:** one named purpose per step,
stable parameters, and a before/after evidence record.

## Failure modes

- environment-dependent parsing;
- silent coercion to null;
- chained operations with no intermediate evidence;
- dataframe work redefining metric meaning;
- memory pressure treated as a reason to skip validation.

## Evidence-based verdict

- **CLEAN** — inputs, phase, determinism, and evidence ledger are explicit.
- **BLOCKED** — required semantics or parsing policy is absent.
- **HANDOFF** — continue to the smallest task route in `INDEX.md`.

## Stop and handoff

Hand off distributed execution to `bi-bigdata-knowledge`, SQL transformation to
`bi-sql-knowledge`, and readiness decisions to the readiness system.
