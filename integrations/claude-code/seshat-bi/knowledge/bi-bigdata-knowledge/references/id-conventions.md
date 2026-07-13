# ID Conventions

Stable ID families let routes, checklists, and analyzer rules cross-reference content
without fragile links. **IDs are durable**: once assigned, an ID is never reused,
renumbered, or repointed. Retired IDs are marked deprecated, not deleted.

The `BD-` prefix namespaces this layer; the Python layer uses `PY-`. When this layer
relies on an engine-independent concept, it cites the Python ID (e.g. `PY-CN-007 grain`)
rather than minting a duplicate — see `references/cross-layer-map.md`.

## Families

| Family | Meaning | Example |
|---|---|---|
| `BD-CN-*` | **Concept** — a core distributed-reasoning unit | `BD-CN-004 Partition` |
| `BD-PB-*` | **Playbook** — a step-by-step diagnostic procedure | `BD-PB-002 Diagnosing skew` |
| `BD-BP-*` | **Best practice** — a recommended default approach | `BD-BP-003 Single-node first` |
| `BD-AP-*` | **Anti-pattern** — a named failure mode to flag in review | `BD-AP-005 collect() in production` |
| `BD-AR-*` | **Analyzer rule** — an active static-review rule | `BD-AR-005 collect on large frame` |
| `BD-ARC-*` | **Analyzer rule candidate** — proposed, not yet promoted | `BD-ARC-002 Detect coalesce(1)` |
| `BD-VP-*` | **Validation pattern** — reusable scale-appropriate check | `BD-VP-003 Control-total parity` |
| `BD-PAT-*` | **Pattern** — a recommended positive design pattern (JSON) | `BD-PAT-002 Broadcast small dim` |
| `BD-EX-*` | **Example** — an original fictional retail-at-scale example | `BD-EX-004 Skewed store join` |
| `BD-QA-*` | **Training question** — a Q&A item in the training/eval set | `BD-QA-010 Why did one task hang?` |

## Numbering

- Three-digit zero-padded sequence within each family (`BD-CN-001`, `BD-CN-002`, …).
- Numbers are assigned in creation order, not importance.
- Each analyzer rule (`BD-AR-*`) names the anti-pattern (`BD-AP-*`) it detects.
- Candidates (`BD-ARC-*`) keep their number on promotion only if there is no collision.

## Cross-referencing

Refer to content by ID in prose and in JSON `id` / `detects` / `refs` fields. A check may
cite both a local concept and a borrowed Python concept, e.g.
"(applies BD-CN-009; reuses PY-CN-046 fan-out)".
