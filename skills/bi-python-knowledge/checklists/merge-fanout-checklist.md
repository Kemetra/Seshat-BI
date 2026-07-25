# Merge and Fan-Out Checklist

Terminal artifact for dataframe join review.

## Before merge

- [ ] Left grain and right grain stated.
- [ ] Join keys and expected relationship declared.
- [ ] Uniqueness tested on every side expected to be one.
- [ ] Null-key counts recorded.
- [ ] Expected left-only/right-only behavior documented.

## After merge

- [ ] Input and output row counts attached.
- [ ] Key-level multiplicity distribution attached.
- [ ] Left-only/right-only counts reconciled to join type.
- [ ] Output grain tested for uniqueness.
- [ ] Overlapping columns have an authoritative source.
- [ ] Additive controls that should be conserved reconcile.

## Verdict

Choose exactly one:

- **MERGE SOUND** — cardinality holds and controls reconcile.
- **FAN-OUT DETECTED** — output multiplication violates expected cardinality.
- **UNMATCHED KEYS OPEN** — join loss/addition awaits disposition.
- **BLOCKED** — grain, key, or relationship is not declared.

Attach the cardinality statement, row-count ledger, unmatched-key counts, and one next
action. Never hide fan-out by aggregating first.
