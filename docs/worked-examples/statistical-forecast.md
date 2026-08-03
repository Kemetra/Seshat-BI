# Governed statistical evidence: synthetic forecast example

This example uses only the fictional `sample_orders` fixture. It demonstrates
the `forecast` method end to end: candidate selection by rolling-origin
backtest, prediction intervals, and the human-review gate. It is the companion
to the [`describe` example](statistical-evidence-engine.md), which covers the
same validate / run / render flow for a non-time method.

The governed inputs are:

- [readiness status](../../tests/fixtures/statistical/forecast_flow/mappings/sample_orders/readiness-status.yaml)
- [approved TotalValue metric contract](../../tests/fixtures/statistical/forecast_flow/mappings/sample_orders/metrics/TotalValue.yaml)
- [weekly forecast specification](../../tests/fixtures/statistical/forecast_flow/mappings/sample_orders/analyses/weekly_forecast.analysis.yaml)
- [36-row synthetic extract](../../tests/fixtures/statistical/forecast_flow/data/weekly_metric.csv)

No fixture value represents a client, production system, or real person.

## The time column must be an approved column

A time method binds two roles: `response` and `time`. Both are checked against
the cited metric contracts. A contract that binds only the measure column is
enough for `describe`, but refuses `forecast`:

```text
Outcome: refused
Blocker STAT_CONTRACT_NOT_APPROVED: Analysis roles use columns outside approved contracts: week_start.
Recovery: Add the columns to an approved contract or revise the analysis roles.
```

The fixture contract therefore binds both columns:

```yaml
binds_to:
  gold_table: gold.sample_orders
  columns: [metric_value, week_start]
```

This applies to every time method -- `forecast`, `detect_anomalies`, and
`detect_change_points`. Widening a contract is a metric-owner decision, not an
analyst one; the engine refuses rather than silently reading an unapproved
column.

## All ten forecast parameters are required

`forecast` declares no optional parameters. Omitting any one refuses the whole
specification before data is acquired:

```text
Outcome: refused
Blocker STAT_SPEC_REFUSED: $.method.parameters: missing required property 'final_period'
Blocker STAT_SPEC_REFUSED: $.method.parameters: missing required property 'partial_period_policy'
Recovery: Correct and revalidate the governed analysis specification.
```

`final_period` and `partial_period_policy` are *optional* for
`detect_anomalies` and *required* here, so a forecast specification cannot be
produced by copying an anomaly one. See the
[closed method catalog](../architecture/statistical-evidence-engine.md#closed-method-catalog)
for the full required/optional split per method.

## Run the workflow

`--repo .` and the relative paths below resolve against the fixture root, so
change into it first:

```console
cd tests/fixtures/statistical/forecast_flow
```

```console
seshat analyze run \
  --repo . \
  --spec mappings/sample_orders/analyses/weekly_forecast.analysis.yaml \
  --provider local_csv \
  --input data/weekly_metric.csv \
  --format text
```

```text
Analysis: weekly_forecast
Outcome: computed
Evidence: mappings/sample_orders/analyses/weekly_forecast.evidence.json
Review: mappings/sample_orders/analyses/weekly_forecast.review.md
Recovery: none
```

## What the evidence records

Four declared candidates are scored by mean MASE over rolling-origin folds.
Each fold trains only on prior values and is evaluated on withheld actuals:

| Candidate | Mean MASE |
|---|---|
| `naive` | 0.851 |
| `seasonal_naive` | 0.970 |
| `ets_add` | 0.833 |
| `ets_add_trend` | **0.221** (selected) |

Selection is recorded as a diagnostic, not left implicit:

```text
STAT_FORECAST_SELECTED: Selected by lowest declared mean mase with stable tie order.
STAT_FORECAST_RESIDUAL_AUTOCORRELATION: Ljung-Box residual autocorrelation p-value at lag 4.
```

Evidence stores every fold as `fold_actual:<candidate>:<fold>:<step>` beside its
`fold_predicted` counterpart, so the backtest is auditable rather than
summarised. Horizon points carry intervals at the declared level:

| Step | Point | 95% interval |
|---|---|---|
| 1 | 138.367 | 136.255 -- 140.479 |
| 2 | 139.396 | 137.284 -- 141.508 |
| 3 | 140.425 | 138.313 -- 142.537 |
| 4 | 141.453 | 139.341 -- 143.566 |

Interval `method` is recorded as `statsmodels-state-space`, alongside the exact
installed library versions and the declared `random_seed`, so the run is
reproducible.

## The boundary is unchanged

`outcome: computed` means the declared numerical method completed. It does not
mean anyone accepted the forecast. Evidence remains
`authority: derived-evidence-only`, `review_state: pending`, and
`readiness_effect: none; named-human approval required`.

Forecast evidence always carries the caution
`Forecasts are derived scenarios with uncertainty, not guarantees.` A named
human completes the generated review, records their identity and authority
class, and states the permitted narrative claim. The agent must not fill that
decision on the reviewer's behalf, and an accepted forecast still changes no
metric contract and no readiness stage.
