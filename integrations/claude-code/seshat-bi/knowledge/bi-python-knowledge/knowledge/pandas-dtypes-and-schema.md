# Pandas Dtypes and Schema Drift

Use this route when observed storage dtypes do not match expected field semantics or a
new extract changes schema. End on `checklists/dataframe-review-checklist.md`.

## Decision this route supports

Decide whether each field can be represented without losing identity, precision,
missingness, timezone, or domain meaning.

## Required evidence

- expected logical type and nullable policy per field;
- observed dtype and invalid-value counts;
- prior schema/profile revision for drift comparison;
- downstream precision and date/time requirements.

## Reasoning sequence

**PY-PB-013 — Type contract review**

- **PY-CN-105 — Logical type and storage dtype are separate.** An object/string column
  may represent an identifier, category, decimal, timestamp, or unparsed error.
- **PY-CN-106 — Identifiers remain identifiers.** Preserve leading zeros and avoid
  arithmetic coercion for store, SKU, invoice, or customer codes.
- **PY-CN-107 — Numeric precision follows the contract.** Binary floating point is not
  automatically suitable for currency reconciliation.
- **PY-CN-108 — Boolean parsing needs an explicit domain.** Map approved literals and
  retain invalid counts; truthiness is not a policy.
- **PY-CN-109 — Categories require observed-versus-allowed evidence.** Category dtype
  improves intent only after domain normalization.
- **PY-CN-110 — Schema drift is categorical.** Added, removed, renamed, reordered, and
  type-changed fields have different downstream consequences.

**PY-BP-011 — Coerce with a rejection ledger.** Record invalid literals, nulls created,
and precision changes for every conversion.

## Failure modes

- leading-zero IDs converted to integers;
- currency silently coerced to float;
- invalid booleans mapped to `True`;
- timezone removed during timestamp conversion;
- column rename treated as harmless because position is unchanged;
- `errors="coerce"` used without counting newly created nulls.

## Evidence-based verdict

- **CLEAN** — logical/storage types align and conversion losses are zero or approved.
- **BLOCKED** — expected type, nullable policy, or invalid-value disposition is missing.
- **HANDOFF** — route semantic policy to the owner; route scale-driven type handling to
  Big Data.

## Stop and handoff

Do not settle sentinel-versus-null or business category rollups here. Record the
observed values and request the named decision.
