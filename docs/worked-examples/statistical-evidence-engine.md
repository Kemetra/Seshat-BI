# Governed statistical evidence: synthetic weekly example

This example uses only the fictional `sample_orders` fixture. It demonstrates
how Seshat BI derives statistical evidence from an already approved metric
without changing metric truth, readiness, or approval state.

The governed inputs are:

- [readiness status](../../tests/fixtures/statistical/full_flow/mappings/sample_orders/readiness-status.yaml)
- [approved TotalValue metric contract](../../tests/fixtures/statistical/full_flow/mappings/sample_orders/metrics/TotalValue.yaml)
- [weekly analysis specification](../../tests/fixtures/statistical/full_flow/mappings/sample_orders/analyses/weekly_signal.analysis.yaml)
- [36-row synthetic extract](../../tests/fixtures/statistical/full_flow/data/weekly_metric.csv)

No fixture value represents a client, production system, or real person.

## Run the workflow

From the fixture root, validate the specification and its committed authority
references without acquiring data:

```console
seshat analyze validate \
  --repo . \
  --spec mappings/sample_orders/analyses/weekly_signal.analysis.yaml \
  --format json
```

Then run the closed local CSV provider:

```console
seshat analyze run \
  --repo . \
  --spec mappings/sample_orders/analyses/weekly_signal.analysis.yaml \
  --provider local_csv \
  --input data/weekly_metric.csv \
  --format json
```

The normalized specification identifies:

- subject `sample_orders`, revision `1`, and owner `Example Analyst`;
- the approved `TotalValue` contract and completed-week observation grain;
- one numeric `response` role bound to `metric_value`;
- method `describe` version `1.0`, fixed quantiles, no outlier
  classification, complete-case handling, and random seed `1729`;
- repo-relative evidence and review output paths.

The run writes immutable JSON evidence plus a deterministic Markdown review.
It records all 36 input observations as a count and digest, never as raw rows.
The evidence contains descriptive estimates, the explicit
`STAT_OUTLIER_RULE_NONE` diagnostic, the numerical method identity, input
provenance, and hashes of the cited governance artifacts.

To recreate a lost or stale Markdown projection without recomputing statistics
or rewriting evidence:

```console
seshat analyze render \
  --repo . \
  --evidence mappings/sample_orders/analyses/weekly_signal.evidence.json \
  --format json
```

## Interpret the boundary

`outcome: computed` means the governed engine completed the declared numerical
method and produced schema-valid derived evidence. It does not mean the
analysis, interpretation, metric, dashboard, or readiness stage was approved.
The evidence therefore remains:

- `authority: derived-evidence-only`;
- `review_state: pending`;
- `readiness_effect: none; named-human approval required`.

A named human reviewer completes the separate checklist in the generated
review, records their identity and authority class, chooses accepted, rejected,
or changes requested, and states the permitted narrative claim and caveats.
The agent must not fill that decision on the reviewer's behalf. Any accepted
narrative cites the reviewed evidence; it does not alter the approved metric
contract or readiness status.
