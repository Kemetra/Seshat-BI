# Data Model: shipped-ideas.yaml

**Feature**: 052-idea-bank-memory-seam | **Date**: 2026-06-30

The ledger is a single YAML mapping keyed by the idea's existing backlog short-code. It is a
hand-curated record of what a human has already shipped or settled; it is NOT a live status
feed and carries no git-derived state.

## Top-level shape

```text
<idea-id>:
  status: shipped | settled
  pr_sha: <string evidence -- PR number and/or commit SHA>
  f_row:  <roadmap F-row label, e.g. F062>  |  none
```

- The top-level keys are idea-ids (backlog short-codes such as `A1`, `B2`, `F7`, `IL1`).
  Keys are unique (a mapping). The id is the SAME token used by the prose appendix and by
  Ground's ship-status, so the Memory reader can match across all three sources without a
  translation table.

## Fields

| Field    | Required | Domain                                   | Meaning |
|----------|----------|------------------------------------------|---------|
| `status` | yes      | `shipped` \| `settled`                   | Whether the idea was built (shipped) or rejected-and-settled. Drives the Memory reader's `current_state` (`shipped` -> `shipped`; `settled` -> `rejected-settled`). |
| `pr_sha` | yes      | non-empty string (PR # and/or commit SHA) | The evidence the row exists. The Memory reader uses it as `state_citation`. A row without evidence is invalid (fail-loud). |
| `f_row`  | yes      | F-row label (e.g. `F062`) \| `none`      | The roadmap F-row a HUMAN already placed the idea at, or `none` if a human placed none. Records placement; never assigns it. |

## Invariants

- **Evidence-of-shipped only**: `f_row` records a placement a human already made. No code
  path may write, assign, or promote an F-row from this file (spec FR-003). `f_row: none` is
  a first-class honest value (shipped-but-unmapped, e.g. the idea-engine workflows themselves).
- **Generic identifiers only** (spec FR-007): values are idea-ids, PR numbers, commit SHAs,
  and F-row labels. No sample data, metric values, mapping content, or domain (C086/pharmacy)
  specifics may appear. A guard test asserts this.
- **Both lifecycles recorded**: `settled` rejections (e.g. F5/F6) are recorded alongside
  `shipped` so the Memory reader stops re-litigating settled REJECTs as well as re-pitching
  shipped ideas.
- **Authoritative on conflict**: when the ledger and the prose "## SHIPPED / SETTLED" appendix
  disagree on an id, the ledger wins for the machine read and the disagreement is surfaced
  (never silently auto-fixed).

## Relationship to existing sources

- **Prose appendix** (`idea-backlog.md` "## SHIPPED / SETTLED"): remains in place under this
  feature's scope. The ledger sits alongside it as the authoritative structured source for the
  machine read. (Whether the yaml ultimately REPLACES the prose is a human scope call left
  open -- spec ## Clarifications.)
- **Ground ship-status** (in-session git read): unchanged and still the ONLY git-derived
  source. The ledger is a curated human record, not a duplicate of Ground.

## Seed contents (illustrative -- exact rows curated in implementation)

Drawn from the existing prose appendix:

- `A1`, `B1`, `B2`, `F7`, `F8` -> `status: shipped`, each with its cited PR/SHA; `f_row`
  set to the F-row a human placed (or `none` -- e.g. the idea-engine planning workflows are
  verified to sit in NO roadmap F-row, so they are honestly `f_row: none`).
- `F5`, `F6` -> `status: settled`, each citing the rejection rationale location.
