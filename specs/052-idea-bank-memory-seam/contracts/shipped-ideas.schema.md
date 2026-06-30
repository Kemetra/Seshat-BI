# Contract: shipped-ideas.yaml field contract

**Feature**: 052-idea-bank-memory-seam | **Date**: 2026-06-30

This is a DOC contract (not an executable schema) describing the required shape of
`docs/roadmap/shipped-ideas.yaml`. A guard test enforces the load-bearing parts.

## Contract

- The file is a YAML mapping at the top level.
- Each key is an idea-id string (backlog short-code; e.g. `A1`, `IL1`). Keys are unique.
- Each value is a mapping with EXACTLY these keys:
  - `status`: one of the string literals `shipped` or `settled`. No other value is valid.
  - `pr_sha`: a non-empty string citing PR-number and/or commit-SHA evidence.
  - `f_row`: either a roadmap F-row label string (e.g. `F062`) or the literal `none`.
- No additional keys are permitted on an entry.
- No value may contain sample data, metric values, mapping/contract content, or domain
  (C086/pharmacy) specifics -- generic governance identifiers only.

## Read-side behavior contract (Memory stage)

- **Absent or empty file**: the reader treats it as "no structured history" and continues on
  the prose appendix + Ground ship-status. NOT an error.
- **Present but malformed** (invalid YAML, missing a required key, or an out-of-domain
  `status`): the reader FAILS LOUD with a clear error. It MUST NOT silently proceed as if no
  history existed.
- **Per entry**: `status: shipped` maps to Memory `current_state: shipped`; `status: settled`
  maps to `current_state: rejected-settled`. `state_citation` is built from `pr_sha` (and
  `f_row` when not `none`).
- **No write-back**: the reader never writes the ledger, never writes the roadmap, and never
  re-reads git.

## Valid example (generic placeholders)

```yaml
A1:
  status: shipped
  pr_sha: "PR #62 abbbd73"
  f_row: none
F5:
  status: settled
  pr_sha: "idea-backlog.md PARK (ML/statistical boundary)"
  f_row: none
```

## Invalid examples (each MUST fail the guard / fail loud)

```yaml
# missing pr_sha evidence -> invalid
X1:
  status: shipped
  f_row: F010
```

```yaml
# out-of-domain status -> invalid
X2:
  status: maybe
  pr_sha: "PR #99"
  f_row: none
```
