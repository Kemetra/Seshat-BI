# Contract: Gate Verdicts and the Blocking Matrix

**Feature**: `specs/121-business-knowledge-interview` | Anchors: FR-032 to FR-035, clarify Q1

## Verdict semantics (FR-033)

| Verdict | Meaning | Obligations |
|---|---|---|
| `pass` | Every required decision for the requested stage is approved with complete, valid metadata and resolvable evidence; no blocking condition applies. | MUST cite evidence. A pass with no citable evidence is a defect (DS5). |
| `warn` | Progress allowed; non-fatal issues exist. | MUST list each issue: accepted deviations, stale evidence on non-critical decisions, open low-risk questions. |
| `blocked` | At least one required decision is unresolved, invalid, conflicting, or missing evidence. | MUST name each concrete blocking decision (id + reason) and what unblocks it. |

Fail-closed inputs (FR-035): malformed record, unknown status, unknown decision type
inside a blocking category, unreadable store, absent store => `blocked`, never `pass`.

Determinism (FR-034): verdicts are recomputed from committed artifacts only (store +
cited evidence). No hidden state. Alignment with the readiness spine: `warn` maps to
the spine's `warning` (non-fatal, does not stop the next stage); `blocked` stops;
the spine remains the sole stage-state authority (verdicts contribute
`blocking_reasons[]` / `warning` entries, R-6).

## Blocking matrix (FR-032)

| Unresolved decision (in scope) | Blocks |
|---|---|
| `pii_handling` | cleaning of affected columns; ANY report exposure of affected columns |
| `table_grain` | Silver/Gold modeling of the affected table |
| `primary_key` | modeling that depends on the affected table's key |
| `relationship_cardinality` | modeling that depends on the affected relationship |
| `kpi_definition` | that KPI's contract, DAX measure, dashboard use, PBIP readiness |
| `policy_ruling` (VAT / returns / discount / cost) | every KPI contract the policy affects |
| `missing_value_rule` (KPI/financial/quantity/date fields) | cleaning and KPI contracts consuming the affected fields |
| `data_exclusion` | modeling and KPI contracts over the affected rows/tables |
| `dashboard_blueprint_approval` | PBIP prototype readiness |
| missing / unresolvable evidence on ANY approval | the approval is invalid; everything that depended on it |

## Staleness (clarify Q1)

Evidence changed since approval -- detected by comparing each cited artifact's
current identity against the approval's recorded `evidence_identity` (research R-10)
-- => approval is **stale**:

- critical decision type => dependent verdicts `blocked` until the owner re-confirms
  or supersedes the decision;
- non-critical => listed under `warn`.

Never a silent pass.

## Stage projection (R-6)

| Decision categories | Feeds spine stage |
|---|---|
| interview coverage, PII handling, grain, PK, relationships | Source Ready / Mapping Ready |
| KPI meaning, policy rulings, missing-value rules | Semantic Model Ready prerequisites |
| dashboard blueprint approval | Dashboard Ready |
| publish/export | Publish Ready |

## Future PBIP safety (FR-036 to FR-038)

PBIP prototype readiness `pass` requires: approved KPI meanings, grains, keys,
relationships, PII rulings, missing-value rules, and an approved dashboard blueprint.
This slice defines the gate only; generation arrives later as Blueprint -> Compiler ->
Validation, never freehand. Publish/export remains a human decision; F016 stays
deferred and gated.
