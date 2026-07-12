# Portfolio Survey: <source identity>

**Status**: <warning | blocked | pending | pass>
**Source kind**: <db-schema | csv | excel | file-folder>
**Source identity**: <schema or folder identity; never credentials or a connection string>
**Reachable tables total**: <integer>
**Surveyed tables total**: <integer>

## Coverage limits

- <none, or exact unavailable metadata + reason + enabling step>

## Candidate domain evidence

- <metadata observation only; hint, not an approved business meaning>

## Candidate first-scope tables

- <table identifier + metadata reason; proposal input only>

## Table: <table identifier>

**Columns**:

| Column | Declared type |
|--------|---------------|
| <column> | <declared type> |

**Declared PK**: <metadata value or `[PENDING LIVE PROFILE]` + reason>
**Declared FKs**: <metadata values or `[PENDING LIVE PROFILE]` + reason>
**Candidate grain hint**: <declared-key-based hint; never a verified ruling>
**Approx row count**: <metadata estimate or `[PENDING LIVE PROFILE]` + reason>
**Date hints**: <column-name/type hints only; never measured date coverage>
**PII suspicion hints**: <column-name/type hints only; never source values>
**Structural role hint**: <candidate fact | dimension | bridge | unknown>
**Unavailable**: <none, or item + exact reason + enabling step>

<!-- Repeat the Table section for every reachable table. Silent omission is forbidden. -->

## Boundary

- This Layer-A survey contains metadata observations and candidate hints only.
- Value-backed uniqueness, nullability, missingness, date coverage, samples,
  and returns-population checks belong to the existing Layer-B per-table profile.
- Discovery evidence is not business approval or readiness by itself.
