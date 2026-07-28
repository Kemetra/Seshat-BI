# Governed statistical evidence engine

## Authority

The statistical core is an execution-capable local **Product Module**. It
validates a committed analysis specification, reads already approved metric and
readiness authority, runs one closed numerical method, and emits immutable
**derived evidence** plus a deterministic human-review projection. Its
authority is deliberately narrower than business truth:

- it cannot define or revise a metric contract;
- it cannot grant grain, PII, rollup, evidence, or publication approval;
- it cannot change a readiness status;
- it cannot promote association to causation;
- `computed` is a numerical completion state, not acceptance.

The Gold provider is a read-only **Execution Adapter**. It accepts only a
compiler-produced, parameterized, Gold-only `SELECT`; it count-checks before
acquisition, enforces row and byte ceilings, and never exposes connection
details or raw rows in evidence. It performs **no truth creation**: all tables,
columns, grain, and metric meaning must already be authorized by the cited
contracts. The initial supported live-adapter boundary is **PostgreSQL-only**.
Other database dialects remain unsupported for statistical Gold acquisition
until separately verified.

The offline local CSV provider is part of the Product Module test and analysis
surface. It selects only approved role columns, refuses transformations and
ragged/non-finite input, and records a content digest instead of a local path or
row payload.

## Closed method catalog

All methods are version `1.0`. Any identifier, role, or parameter outside this
table is refused by schema or runtime policy.

| Method ID | Required roles | Supported parameters |
|---|---|---|
| `describe` | `response` | `quantiles`; `outlier_rule`: `none`, `iqr`, or `mad` |
| `compare_groups` | `response`, `group` | `test`: `welch_t`, `paired_t`, `mann_whitney`, `wilcoxon`, `welch_anova`, or `kruskal_wallis`; `alternative`; `confidence_level`; `correction`: `none`, `holm`, or `benjamini-hochberg`; optional `group_order`, `post_hoc_pairs` |
| `proportion` | `numerator`, `denominator` | `interval`: `wilson` or `exact_binomial`; `alternative`; `confidence_level`; optional `comparison`: `none`, `chi_square`, or `fisher_exact`; `zero_cell_correction`; `minimum_denominator` |
| `correlate` | `response`, `predictor` | `coefficient`: `pearson` or `spearman`; `confidence_level`; `correction` |
| `regress` | `response`, `predictor` | `family`: `ols`, `logistic`, `poisson`, or `negative_binomial`; `covariance`: `classical`, `HC0`, `HC1`, `HC2`, or `HC3`; `confidence_level` |
| `detect_anomalies` | `response`, `time` | `model`: `trailing_mad` or `seasonal_mad`; `period`; `threshold`; optional `direction`; `final_period`; `partial_period_policy` |
| `detect_change_points` | `response`, `time` | `model`: `l1`, `l2`, or `rbf`; `min_segment`; `algorithm`: `pelt` with `penalty`, or `dynamic_programming` with `change_count`; optional `jump` |
| `forecast` | `response`, `time` | closed `candidates`: `naive`, `seasonal_naive`, `ets_add`, `ets_add_trend`, `ets_add_damped`, `ets_add_seasonal`; `period`; `horizon`; `confidence_level`; `evaluation_metric`: `mase` or `smape`; `initial_window`; `step`; `max_folds`; `final_period`; `partial_period_policy` |

`group` is optional for `describe` and `proportion` where the method supports a
governed grouped projection. `pair` may be used by paired group comparison.
No method accepts arbitrary Python, formulas, SQL, model names, or dynamically
loaded callables.

## Minimum data and withholding

Every specification declares `minimum_data.observations`, `groups`, and
`seasonal_cycles`. The engine applies the relevant floor before claiming a
result. Method-specific checks also enforce, as applicable:

- non-constant and identified samples;
- valid denominators and privacy floors;
- compatible group count and paired lengths;
- strict, duplicate-free, regular time order and supported cadence;
- sufficient prior-only seasonal history, rolling-origin folds, and segment
  length;
- finite estimates, intervals, tests, diagnostics, and evidence size.

If a valid method cannot support an estimate after data acquisition, the
outcome is `withheld` with concrete blockers and recovery. Policy or authority
violations are `refused`. A missing optional dependency or unavailable provider
is `unavailable`. Unexpected safe-boundary failures are `failed`. Only a fully
completed method is `computed`.

## Diagnostics and interpretation

Diagnostics use stable `STAT_*` codes and one categorical state: `holds`,
`warning`, `violated`, or `not_applicable`. Evidence may include estimates,
effect sizes, decimal-string intervals, hypothesis-test statistics,
multiplicity-adjusted p-values, forecast fold evidence, anomaly/change-point
labels, and resource-limit diagnostics. Each method records interpretation
cautions; correlation and regression always retain the association-not-
causation boundary.

Time methods are prior-only: an observation is never included in its own
anomaly baseline, rolling-origin evaluation never trains on future values, and
partial final periods must be explicitly declared and either excluded or
refused.

An anomaly baseline is judged degenerate whenever its robust dispersion is not
distinguishable from the numerical noise of its own values -- the test is
relative to the baseline's magnitude, not an absolute epsilon. An exactly
reproducible series therefore reports `STAT_ANOMALY_BASELINE_DEGENERATE` rather
than emitting flags that float round-off would decide.

## Dependencies and commands

The base install imports no numerical library. Install the pinned `stats` extra
for NumPy, SciPy, and statsmodels. Change-point detection additionally needs
`stats-change` for ruptures. Gold acquisition also needs the PostgreSQL `db`
extra and connection settings in the gitignored `.env`.

The public commands are:

```text
seshat analyze validate --repo ROOT --spec PATH --format text|json
seshat analyze run --repo ROOT --spec PATH --provider local_csv|gold [--input PATH] --format text|json
seshat analyze render --repo ROOT --evidence PATH --format text|json
```

Exit codes are categorical: computed `0`, withheld `1`, refused `2`, failed
`3`, unavailable `4`. Evidence always records
`authority: derived-evidence-only`, `review_state: pending`, and
`readiness_effect: none; named-human approval required`.

See the
[synthetic worked example](../worked-examples/statistical-evidence-engine.md)
for the complete validate, run, render, and human-review flow.
