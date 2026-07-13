# Contract: Source-to-KPI Answerability Schema

**Feature**: `124-generic-kpi-contract-authoring` -- US2, FR-007..FR-009, FR-041..FR-043

The answerability artifact is one row per (source scope x KPI). It reuses the five KPI Coverage Scorecard statuses exactly and is STRUCTURALLY lintable by SL1 (spec 056). SL1 checks structure; it never decides the truth of a `Covered`. Path/wire-format is plan-time decision D2.

## The five coverage statuses (closed set, ASCII `--`)

```
Covered
Blocked -- missing field
Blocked -- needs business definition
Planned
Out of scope
```

- `Covered` -- eligible to begin a Checkpoint-A draft. NOT approved, NOT Semantic-Model-Ready, NOT Dashboard-Ready. Grants no readiness.
- `Blocked -- missing field` -- a required source role/field is absent (or only an unverified assumption). Name the field/role.
- `Blocked -- needs business definition` -- a required policy (VAT, returns, cost method, date basis, same-store, snapshot) is unresolved; the meaning is undecided.
- `Planned` -- no seeded contract for this KPI; route to the deferred note; never fabricate a contract.
- `Out of scope` -- the KPI's domain the source cannot serve (e.g. an inventory KPI against a sales-only fact).

## Row field contract

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `scope` | string | yes | project/source scope (table or subject area); no leaked physical value |
| `kpi` | string | yes | a `KPI-MC-NN` (generic) or a custom-request label |
| `status` | enum(5) | yes | exactly one of the five strings above |
| `blockers` | list[string] | conditional | non-empty and not a bare `--` when `status` begins `Blocked` |
| `evidence` | list[string] | yes | repo-relative source-profile / source-map references |
| `next_action` | string | yes | the next allowed action |

## Decision rules (how status is derived; fail closed)

1. If the registry `lifecycle` is `planned` -> `Planned`.
2. Else if the KPI's domain cannot be served by the source's roles -> `Out of scope`.
3. Else if any required `source_role`/field is absent -> `Blocked -- missing field` (name every absent role; FR-042).
4. Else if any required governing policy (`policy_ruling`/`missing_value_rule`/`pii_handling`) is unresolved, OR a field's meaning is only inferred from a lookalike name -> `Blocked -- needs business definition` (FR-009).
5. Else if any cited evidence is missing or its recorded identity no longer matches -> fail closed: NOT `Covered`; name stale/missing evidence as the blocker (FR-041).
6. Else -> `Covered` (eligible to draft only).

## Forbidden content (FR-008, SC-003)

- No numeric coverage percentage, confidence score, or ranking. No digit-immediately-followed-by-`%` token (a literal `%` inside a KPI name is allowed, matching SL1 rule 4).
- No readiness grant. No physical value leakage.

## SL1 alignment (spec 056)

The artifact is shaped so SL1's four structural checks apply unchanged:
1. every `status` cell is in the closed five-value set;
2. a `Blocked -- ...` row names a blocker;
3. a `Covered` row cites a resolvable `knowledge_contract_ref` / contract path (`Planned` / `Out of scope` exempt);
4. no percentage token.

SL1 normalizes em-dash/en-dash to `--` before comparing (`src/seshat/rules/scorecard.py:86`), so this artifact's ASCII `--` strings lint correctly and unchanged. This feature does NOT modify SL1 and does NOT re-adjudicate coverage.
