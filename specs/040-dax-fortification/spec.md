# Spec 040 -- DAX Fortification

- **Status:** Proposed consolidation / next hardening spec
- **Layer:** Metrics & Semantic Model / Power BI DAX governance
- **Related:** ADR 0007, `retail check`, `retail semantic-check`, metric contracts
- **Intent:** Keep DAX governed as the analytical backbone without weakening the stdlib-only core.

## Summary

DAX is the final expression of business truth in Power BI. A model can be syntactically clean, visually polished, and still answer the business question incorrectly if a measure uses the wrong denominator, wrong filter set, hardcoded dates, undocumented logic, or inconsistent patterns.

This spec consolidates the current DAX fortification state and defines the next safe work. It is not a reimplementation of completed phases. It turns the existing implementation into an explicit product contract and separates what is already shipped from what should be done next.

## Product rule

```text
Metric contracts define business truth.
DAX implements that truth.
retail check enforces lexical/model hygiene.
retail semantic-check enforces contract-to-DAX drift for recognized measure shapes.
Uncertainty escalates to humans; it must not silently pass and must not become false drift.
```

## Current delivered baseline

The following items are already part of the product baseline and must be preserved:

| Area | Delivered behavior |
|------|--------------------|
| DAX lexical governance | `retail check` runs registered DAX/TMDL rules. |
| D1 | Measure names are PascalCase. |
| D2 | Every measure has a display folder. |
| D3 | Duplicate normalized measure logic is flagged. |
| D4 | Measures use `DIVIDE()` instead of bare `/`. |
| D5 | Numeric implicit aggregation is warned. |
| D6 | Bidirectional relationships are rejected. |
| D7 | Time-intelligence requires a marked date table. |
| D8 | Power BI model sourcing is `gold` only. |
| D9 | Hardcoded date literals in measures are warned. |
| D10 | `FILTER(ALL(...))` full-table scan pattern is warned. |
| D11 | Measures require a `///` documentation comment. |
| L3 semantic drift | `retail semantic-check` compares recognized denominator filter sets to metric contracts. |
| CI integration | CI runs `retail check` and then `retail semantic-check`. |
| Escalation posture | `drift` fails; `escalate` warns; `pass` and `skip` are silent. |

## Non-negotiable invariants

### 1. Stdlib-only core

`retail check` must stay dependency-light and stdlib-only at import time. The import chain:

```text
retail.cli -> retail.rules -> retail.rules.dax
```

must not import `yaml`, database drivers, Power BI clients, or any optional dependency.

Any YAML-dependent behavior belongs in a lazy path such as `retail semantic-check`, not in a registered D-rule.

### 2. Drift is not escalation

| Verdict | Meaning | Severity | CI effect |
|---------|---------|----------|-----------|
| `drift` | Recognized mismatch against contract | ERROR | Fail |
| `escalate` | Cannot judge safely | WARNING | Do not fail |
| `pass` | Recognized match | none | Silent |
| `skip` | No structured definition yet | none | Silent |

The system must never pass on uncertainty and must never mark uncertain logic as drift.

### 3. Lexical scope only for D-rules

Rules in `src/retail/rules/dax.py` must remain lexical and local to committed model text. They can inspect TMDL, M source, relationships, names, comments, and simple DAX text patterns.

They must not require a full DAX AST, live Power BI connection, database access, or semantic evaluation.

### 4. Contract truth beats DAX shape

The metric contract is the source of business truth. DAX shape is implementation. If prose and DAX imply something different from the structured contract, the structured contract wins until a human owner changes it.

## What this spec does next

This spec should drive the next PRs in this order.

### Workstream A -- documentation sync

Update all docs and agents that still describe the DAX gate as D1-D8 only.

Required updates:

```text
docs/readiness/semantic-model-ready.md
.claude/agents/powerbi-analyst.md
docs/conventions.md
docs/decisions/0007-dax-governance-layers.md
```

Acceptance criteria:

- Semantic Model Ready describes D1-D11 plus `retail semantic-check`.
- The Power BI analyst agent knows D9-D11 and the L3 drift gate exist.
- `docs/conventions.md` points to DAX governance, not just PascalCase/display folders.
- ADR 0007 is amended or superseded to record that L3 has been promoted into CI.

### Workstream B -- DAX pattern library

Add a reusable DAX pattern library so agents do not invent measures from scratch.

Proposed structure:

```text
docs/dax/
  dax-governance.md
  measure-catalog.md
  patterns/
    base-measures.md
    ratio-measures.md
    time-intelligence.md
    ranking.md
    contribution.md
    retail-kpis.md
```

Pattern library rules:

- Every pattern states its intended grain.
- Every pattern states whether it needs a structured metric contract `definition` block.
- Ratio patterns must use `DIVIDE()`.
- Time-intelligence patterns must depend on the marked date table.
- Derived measures should reference base measures where possible.
- Patterns are examples and templates, not owner approvals.

### Workstream C -- measure catalog

Add a measure catalog that records the intended measure layers.

Recommended layers:

```text
Base measures
  -> Direct aggregations over gold columns.

Derived measures
  -> Measures built from base measures.

Ratio measures
  -> Measures requiring denominator/filter governance.

Time-intelligence measures
  -> MTD/QTD/YTD/LY/YoY, gated by the date table marker.

Decision measures
  -> ranking, contribution, segmentation, exception flags.
```

Acceptance criteria:

- The catalog is documentation-first.
- It does not self-approve metrics.
- It points each governed KPI back to its metric contract.
- It tells the agent which pattern family to use before writing DAX.

### Workstream D -- semantic-check hardening

Keep new contract-aware checks in `retail semantic-check`, not `retail check`, whenever YAML contracts are required.

Candidate next checks:

| Candidate | Location | Gate posture |
|-----------|----------|--------------|
| Measure has matching contract | `semantic-check` | warning first, later owner decision |
| Contract exists but measure missing | `semantic-check` | warning first |
| Measure contract is not approved | `semantic-check` | warning/blocker depending on readiness stage |
| DAX pattern family matches contract type | `semantic-check` | warning/escalate |
| Duplicate contract names | `semantic-check` or contract-store validation | error if deterministic |

Do not implement these as D12 in `retail check` if they require reading YAML.

### Workstream E -- optional future D12+

Only add D12+ to `retail check` when the rule is lexical, low false-positive, and stdlib-pure.

Potential candidates:

| Rule | Candidate behavior | Notes |
|------|--------------------|-------|
| D12 | Warn on `FORMAT()` inside numeric measures | Useful, but avoid false positives for display-only measures. |
| D13 | Warn on `SELECTEDVALUE()` without fallback | Good lexical signal, but verify pattern quality first. |
| D14 | Warn on broad `ALL(Table)` outside documented exceptions | Must avoid repeating the S8 false-positive lesson. |

Rejected for D-rules unless a real parser exists:

- circular dependency detection,
- exact filter-context correctness,
- return type / format-string type validation,
- live numeric reconciliation.

## Acceptance criteria for this spec

This spec is complete when:

1. Docs and agents describe the actual shipped DAX governance baseline.
2. ADR 0007 no longer claims L3 CI gating is only deferred.
3. A DAX pattern library exists under `docs/dax/`.
4. A measure catalog exists and tells the agent which pattern family to choose.
5. Any future D12+ proposal states whether it belongs in stdlib `retail check` or YAML-aware `retail semantic-check`.
6. `retail check` remains stdlib-only at import time.
7. `retail semantic-check` continues to fail only on deterministic `drift`, not on uncertainty.

## Out of scope

- Full DAX parser integration.
- Tabular Editor BPA as a required dependency.
- Live Power BI refresh, publish, or execution.
- Database-backed value reconciliation for DAX measures.
- Automatic owner approval of metric contracts.
- Generating dashboards before metric contracts and semantic readiness are clean.

## Recommended first PR from this spec

```text
docs: sync DAX fortification status and add pattern library skeleton
```

Suggested contents:

```text
- update semantic-model-ready.md from D1-D8 to D1-D11 + semantic-check
- update powerbi-analyst agent with D9-D11 + L3 gate
- amend ADR 0007 with the delivered CI promotion
- create docs/dax/dax-governance.md
- create docs/dax/measure-catalog.md
- create docs/dax/patterns/*.md skeletons
```
