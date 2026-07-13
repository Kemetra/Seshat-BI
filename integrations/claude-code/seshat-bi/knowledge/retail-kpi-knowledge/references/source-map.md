# Source Map

How a logical KPI field maps to a physical source is **out of scope for this layer** and
owned by the SQL knowledge layer. This file records the *placeholder* mapping intent only,
so contracts stay source-agnostic.

## Principle

Contracts reference **logical** fields (e.g., "net sales amount", "transaction id"). The
mapping from logical field → physical column in a specific source system is recorded and
maintained by the SQL layer, not here. This keeps KPI meaning portable across sources.

## Status

No physical source bindings are defined in this seed. In particular:

- No source-specific schema (including any `C086`-style schema) is treated as universal.
  A field that happens to exist in one source must not be assumed present in others.
- All field references in `references/source-field-requirements.md` are logical and
  carry a confidence marker.

## Mapping table (placeholder)

| Logical field | Physical source | Notes |
|---------------|-----------------|-------|
| (to be filled by SQL layer) | — | bind during source mapping, not here |

## Handoff

When a source is selected, the SQL layer fills the mapping and confirms which
**assumption** fields actually exist. This layer then updates affected contracts'
required-field confidence markers and re-runs the metric-contract-review-checklist.
