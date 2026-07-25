# DAX Diagnostic Checklist

## Contract and model gate

- [ ] Approved metric contract is cited; no business rule is invented.
- [ ] Result grain, dimension-specific additivity, and filter behavior are stated.
- [ ] Tables, keys, relationship cardinality/direction/state, and uniqueness are evidenced.
- [ ] Measure DAX, visual/query context, and expected behavior reproduce the symptom.
- [ ] Date/snapshot, blank/zero, and calculation-group policies are approved where relevant.

If required policy is undecided, stop with `blocked` and name the owner decision required.

## Focused diagnosis

- [ ] Actual filter paths are traced separately from intended business behavior.
- [ ] Physical and virtual relationship types, lineage, and unmatched populations are checked.
- [ ] Calculation groups are tested alone and in supported precedence combinations.
- [ ] Detail, subtotal, and grand-total contexts are compared.
- [ ] Missing row, `BLANK()`, numeric zero, and display suppression are distinguished.
- [ ] Numeric controls and affected-population/coverage controls reconcile.

## Terminal artifact

Return:

- `diagnosis`: observed behavior and the smallest evidenced cause;
- `evidence`: contract, metadata, expression, context, and reconciliation references;
- `fix_direction`: a safe shape, not an executed model change;
- `assumptions` and `blockers`;
- `destination_layer` and `next_action` when a cross-layer handoff is needed.

Verdict is `clean`, `needs-evidence`, or `blocked`. It is not a score, readiness pass, approval,
or execution authorization.
