# Contract: Ambiguity Ledger Block (`ambiguities[]`)

The field contract for the net-new top-level `ambiguities` block on
`templates/metric-contract.yaml`. This is an authoring contract (schema + invariants a
reviewer applies), NOT a runtime schema validated by code -- there is no check rule in scope.

## Shape

```yaml
# top-level block on a metric contract, SIBLING of `readiness` (not nested in it).
ambiguities:                          # zero or more entries; only APPLICABLE ambiguities
  - id: "A7"                          # A1..A11 ONLY (A10 inventory snapshot, A11 same-store)
    decision_status: "blocked"        # existing vocabulary only; no invented 5th word
    ruling: ""                        # plain-language INTENT once decided; never DAX/SQL/model path
    evidence: []                      # owner+date once decided: ["ruled by <owner> on <YYYY-MM-DD>"]
  - id: "A4"
    decision_status: "pass"
    ruling: "Discount rate denominator counts known-status transactions only (excludes cancelled/void/blank)."
    evidence: ["ruled by <metric owner> on <YYYY-MM-DD>"]
```

## Field rules

- `id` -- REQUIRED. String matching one of A1, A2, ..., A11. Any other value is a defect.
  The full A1..A11 range is in play; narrowing to A1..A10 (dropping A11 same-store) is a
  defect (SC-005).
- `decision_status` -- REQUIRED. Reuses an existing recorded vocabulary; the RECOMMENDED
  pick is the four readiness statuses (`not_started` / `blocked` / `warning` / `pass`), with
  the catalogue's needs-business-definition flag as the alternative. The final choice is a
  human carve-out (spec ## Clarifications, FR-006). No fifth status word may be invented.
- `ruling` -- REQUIRED when the status is decided. Plain-language business INTENT only.
  A DAX expression, SQL, a visual/page spec, or a `powerbi/` path is REJECTED (define/check
  boundary, FR-003).
- `evidence` -- REQUIRED (non-empty) when the status is decided. Records the owner-and-date
  and any committed support. A decided status with empty evidence is a defect (mirrors the
  readiness `pass` rule).

## Cross-field / cross-artifact invariants

1. **Blocker propagation (FR-004)**: an undecided MATERIAL ambiguity records a
   `blocking_reason` on the contract's `readiness` (naming the ambiguity) and forces
   `readiness.status: blocked`. The agent may recommend but never self-grants a decided
   status; only a recorded owner ruling clears it.
2. **No fake confidence (FR-005)**: no `confidence` / `score` / numeric-certainty field on any
   entry.
3. **Applicability (FR-015/FR-016)**: only applicable ambiguities are recorded; non-applicable
   ones are omitted (optionally with a one-line note), never marked with a decided status.
   Omission of an applicable material ambiguity is a review defect (treated as undecided).
4. **Sibling placement (FR-017)**: the block is a top-level sibling of `readiness`, never
   nested inside it; the readiness block's verbatim shape does not drift.
5. **Define/check boundary (FR-008/FR-010)**: no field carries implementation or a check; the
   ledger is INTENT + ruling + evidence, honored by a human reviewer, not a program.
6. **Generic-retail only (FR-007/FR-012)**: the template block uses generic placeholders and
   the generic discounted-transaction-rate motivating case; no domain-specific ruling is
   inlined -- real rulings are cited via the worked example.
7. **Encoding (FR-011)**: ASCII + UTF-8 no BOM; `--` and `->` not glyphs; short paths.

## Reviewer acceptance (maps to spec scenarios)

- US1: a decided entry reads end-to-end (id + status + ruling + evidence) with no numeric
  confidence.
- US2: an undecided material entry carries a blocking reason and the contract is `blocked`,
  with no author path to `pass` without a recorded owner ruling.
- US3: a pack whose member is blocked is no more ready than that member, via the existing
  rollup rule, with no new rollup logic present.
