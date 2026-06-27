# Join / Skew Checklist

Artifact for the distributed-join and skew routes. Ends on a verdict with the chosen
strategy, skew evidence, and a row-count reconciliation.

## A. Correctness first (BD-CN-034, reuses PY-CN-045/046/051)

- [ ] Each side's grain and key uniqueness stated.
- [ ] Intended cardinality declared; expected result row count stated.
- [ ] If a side's key is non-unique, fan-out is intended — or many-side pre-aggregated.
- [ ] Key hygiene: matching dtypes, no empty-string keys (BD-CN-040).

## B. Join strategy (BD-CN-035, BD-CN-036)

- [ ] Small side identified (post-pruning actual size, not just row count).
- [ ] Broadcast used when one side fits in executor memory.
- [ ] Broadcast size ceiling respected (won't OOM executors).
- [ ] Shuffle (sort-merge) join only where both sides are genuinely large.

## C. Skew (BD-CN-037..039)

- [ ] Skew checked: per-partition sizes / straggler task / key-frequency profile.
- [ ] Hot keys recorded.
- [ ] Fix chosen in order: AQE skew-join → broadcast → salting.
- [ ] Salting reserved for keys AQE/broadcast can't resolve.

## D. Reconciliation (BD-CN-041, reuses PY-CN-050)

- [ ] Result row count computed distributed (not via collect()).
- [ ] Actual vs expected reconciled; unmatched rows investigated.

## Verdict

- **BROADCAST** — small side broadcast; no large-side shuffle; reconciles.
- **SHUFFLE + AQE** — both large; AQE skew-join handled distribution; reconciles.
- **SALTED** — hot key salted and aggregated back; reconciles.
- **FAN-OUT DETECTED** — pre-aggregate many-side first (PY-CN-051) and re-run.
- **BLOCKED** — unmatched rows or key mismatch indicate a data problem; escalate.

Attach: strategy, skew evidence (offending keys / task spread), and row-count reconciliation.
