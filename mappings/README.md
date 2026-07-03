# mappings/

Per-table **source-mapping artifacts** -- the committed inputs to the source-mapping gate
(constitution Principle IV: a source must be profiled and mapped into reviewed artifacts
**before** any `silver.*` SQL is written).

## Layout

One folder per source table, holding that table's five filled artifacts:

```
mappings/
`-- <table>/                      # table id, snake_case, short (Windows MAX_PATH)
    |-- source-profile.md         # Phase 1 profile (the numbers)
    |-- source-map.yaml           # the spine: grain/PK/columns/gold placement
    |-- assumptions.md            # ADR 0002 (RC1-RC16) adopted vs deviated
    |-- unresolved-questions.md   # build-blocking decisions (stop-and-ask)
    `-- reconciliation-report.md  # live-acceptance results (retail validate)
```

## How to use

1. Copy the five blanks from [`../templates/`](../templates/) into `mappings/<table>/`.
2. Fill them by running the playbook (`../docs/medallion-playbook.md`): profile -> map ->
   record assumptions/questions -> review gate -> build silver/gold -> reconcile.
3. The folder is reviewed as a unit at the Phase-4 review gate, before any `silver.*` SQL.

## See also

- **Decision:** [`../docs/decisions/0003-mapping-artifact-location.md`](../docs/decisions/0003-mapping-artifact-location.md) -- why `mappings/<table>/`.
- **Blanks:** [`../templates/`](../templates/) -- the generic templates to copy.
- **Full-spine instance (narrated):** [`../docs/worked-examples/retail-store-sales.md`](../docs/worked-examples/retail-store-sales.md) -- a complete set, end to end through Dashboard Ready (+ Publish `warning`).
- **All examples (index):** [`../docs/worked-examples/README.md`](../docs/worked-examples/README.md) -- compares the examples and says which to read when.
- **The gate:** [`../docs/architecture/tower-bi-agent-kit.md`](../docs/architecture/tower-bi-agent-kit.md) Sec 5.
