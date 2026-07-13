# ID Conventions

Stable ID families let routes, checklists, and analyzer rules cross-reference content
without fragile links. **IDs are durable**: once assigned, an ID is never reused,
renumbered, or repointed. Retired IDs are marked deprecated, not deleted.

## Families

| Family | Meaning | Example |
|---|---|---|
| `PY-CN-*` | **Concept** — a core conceptual unit other families refer back to | `PY-CN-007 Grain of a dataframe` |
| `PY-PB-*` | **Playbook** — a step-by-step diagnostic procedure for a symptom | `PY-PB-003 Rows multiplied after merge` |
| `PY-BP-*` | **Best practice** — a recommended default approach | `PY-BP-002 Profile before cleaning` |
| `PY-AP-*` | **Anti-pattern** — a named failure mode to flag in review | `PY-AP-011 Groupby without declared grain` |
| `PY-AR-*` | **Analyzer rule** — an active static-review rule applied to a pipeline | `PY-AR-005 Merge without validate=` |
| `PY-ARC-*` | **Analyzer rule candidate** — proposed, not yet promoted to `PY-AR-*` | `PY-ARC-009 Detect inplace= usage` |
| `PY-VP-*` | **Validation pattern** — reusable check bridging to SQL/readiness | `PY-VP-004 Row-count parity vs source` |
| `PY-EX-*` | **Example** — an original fictional-retail worked example | `PY-EX-006 Returns fan-out` |
| `PY-QA-*` | **Training question** — a Q&A item in the training/eval set | `PY-QA-021 Why did the sum double?` |

## Numbering

- Three-digit zero-padded sequence within each family (`PY-CN-001`, `PY-CN-002`, …).
- Numbers are assigned in creation order, not importance.
- Each analyzer rule (`PY-AR-*`) should name the anti-pattern (`PY-AP-*`) it detects.
- Each candidate (`PY-ARC-*`) keeps its ID when promoted only if it does not collide;
  otherwise it receives a fresh `PY-AR-*` and the candidate is marked promoted.

## Cross-referencing

Refer to content by ID in prose and in JSON `id` / `detects` / `refs` fields. A
checklist item may cite the concept and anti-pattern it enforces, e.g.
"(enforces PY-BP-002, guards PY-AP-004)".
