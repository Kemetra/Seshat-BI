# Data Model: Per-Contract Ambiguity Decision Ledger

Conceptual model for the net-new `ambiguities` block on a metric contract. This is
DEFINE-layer authoring: the "model" is the field schema of a YAML block, not a database.

## Entity: Ambiguity ledger entry

One element of the contract's top-level `ambiguities` list. Records one recorded owner
ruling (or an explicit undecided) for one catalogued ambiguity on this contract's metric.

| Field | Type | Required | Rule |
|-------|------|----------|------|
| `id` | string | yes | A catalogued identifier in the A1..A11 range ONLY (A1 VAT, A2 returns, A3 date, A4 gross/net, A5 discount line/header, A6 cost method, A7 cancelled/void, A8 product key, A9 branch key, A10 inventory snapshot, A11 same-store). An id outside A1..A11 is a defect. |
| `decision_status` | string (enum) | yes | Drawn from an EXISTING recorded vocabulary; no fifth word invented. Recommended: the four readiness statuses (`not_started` / `blocked` / `warning` / `pass`); alternative: the catalogue's needs-business-definition flag. Final pick is a human carve-out (spec ## Clarifications). |
| `ruling` | string | yes when decided | Plain-language business INTENT of the ruling. NEVER DAX/SQL, a visual spec, or a `powerbi/` model path (rejected -- define/check boundary). |
| `evidence` | list[string] | yes when decided | Owner-and-date plus any committed support, e.g. `["ruled by <owner> on <YYYY-MM-DD>"]`. A decided status with empty evidence is a defect (mirrors the readiness `pass` rule). |

No `confidence`, `score`, `weight`, or any numeric-certainty field exists on the entry
(rule 9 / no fake confidence).

## States and transitions

```
(applicable ambiguity, no owner ruling)
        -> undecided entry  [records readiness blocking_reason; forces readiness.status: blocked]
        -> owner rules       -> decided entry (status + ruling + evidence)
                                [clears that ambiguity's blocking_reason]
(non-applicable ambiguity)
        -> omitted (optionally a one-line note); NOT a decided status; NOT a block
```

- **Undecided material ambiguity** -> a `blocking_reason` naming the ambiguity + contract
  `readiness.status: blocked`. Only a recorded owner ruling clears it. The agent may recommend
  but never self-grants a decided status (Principle I/V).
- **Decided ambiguity** -> `decision_status` decided + `ruling` + `evidence`; the block no
  longer contributes a blocking reason.
- **Non-applicable ambiguity** -> omitted. Omission of an APPLICABLE material ambiguity is a
  review defect, treated as undecided (Q1/FR-015).

## Relationships

- **Ambiguity catalogue (A1..A11)** -- read-only reference the `id` keys to; never edited by
  this feature.
- **Metric contract (host)** -- the `ambiguities` block is a SIBLING top-level block adjacent
  to `readiness`, never nested inside it (Q3/FR-017), so the verbatim readiness-block shape
  does not drift. An undecided material entry drives the host's `readiness.status` to
  `blocked` and adds a readiness `blocking_reason`.
- **KPI pack (downstream)** -- inherits a contract's block through the EXISTING rollup
  ("no more ready than its least-ready contract"); this feature adds no rollup logic (FR-009).

## Invariants (a reviewer enforces; there is no runtime check in scope)

1. Every `id` is within A1..A11 (no A1..A10 ceiling; A11 same-store never dropped).
2. No numeric confidence/score field anywhere.
3. No DAX/SQL/visual/model-path in `ruling` (or any field).
4. A decided status carries non-empty `evidence` (owner + date).
5. An applicable material ambiguity is present (decided or explicitly undecided); silence on
   one is a defect.
6. Generic-retail only: no domain-specific (e.g. pharmacy) ruling inlined; real rulings are
   cited via the worked example.
7. ASCII + UTF-8 no BOM; short repo-relative paths.
