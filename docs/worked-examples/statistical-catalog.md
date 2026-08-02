# Governed statistical evidence: the remaining six methods

This example completes end-to-end coverage of the
[closed method catalog](../architecture/statistical-evidence-engine.md#closed-method-catalog).
`describe` is shown in the [first example](statistical-evidence-engine.md) and
`forecast` in the [forecast example](statistical-forecast.md); the six methods
below are demonstrated here against the shared `catalog_flow` fixture.

Every number on this page was produced by running the committed fixture. No
value represents a client, production system, or real person.

The governed inputs are:

- [readiness status](../../tests/fixtures/statistical/catalog_flow/mappings/sample_orders/readiness-status.yaml)
- [TotalValue contract](../../tests/fixtures/statistical/catalog_flow/mappings/sample_orders/metrics/TotalValue.yaml) (weekly grain)
- [RegionalValue contract](../../tests/fixtures/statistical/catalog_flow/mappings/sample_orders/metrics/RegionalValue.yaml) (region-week grain)
- [48-week series](../../tests/fixtures/statistical/catalog_flow/data/weekly_series.csv) and [96 region-weeks](../../tests/fixtures/statistical/catalog_flow/data/regional_weeks.csv)

## Run any of them

`--repo .` and the relative paths resolve against the fixture root, so change
into it first:

```console
cd tests/fixtures/statistical/catalog_flow
seshat analyze run \
  --repo . \
  --spec mappings/sample_orders/analyses/visits_regression.analysis.yaml \
  --provider local_csv \
  --input data/weekly_series.csv \
  --format text
```

Substitute any analysis id below. The two grouped analyses
(`regional_comparison`, `conversion_rate`) read `data/regional_weeks.csv`; the
other four read `data/weekly_series.csv`.

## Three refusals worth knowing before you author

These are the governance boundaries an author meets first. Each is a refusal,
not a warning: the engine stops rather than guessing.

**The analysis grain must match its contract.** `RegionalValue` exists because
a grouped analysis runs at region-week grain while `TotalValue` is declared
weekly. Pointing the grouped analyses at the weekly contract gives:

```text
Outcome: refused
Blocker STAT_GRAIN_CONFLICT: The analysis observation grain conflicts with its approved contract.
```

**A new contract is not trusted just because it exists.** Adding
`RegionalValue.yaml` is not enough -- the readiness record must carry a
named-human approval whose note names *that* contract:

```text
Blocker STAT_CONTRACT_NOT_APPROVED: Metric-contract authority is incomplete:
mappings/sample_orders/metrics/RegionalValue.yaml: approved contract requires
named-human approval with metric_owner authority whose note names this contract
```

**A time index must be contiguous at the declared cadence.** Weekly dates that
skip from the 28th to the next month's 7th are refused with
`STAT_TIME_IRREGULAR`, and duplicate timestamps with `STAT_TIME_DUPLICATE`. A
grouped extract therefore cannot carry a `time` role at region-week grain --
each week appears once per region.

## compare_groups

Welch's t on two regions, Holm-corrected, with a standardised effect size:

| Output | Value |
|---|---|
| `welch_t` statistic | 9.6547 |
| p-value (Holm-adjusted) | 9.997e-16 |
| `hedges_g` | 1.9550 |
| group counts | 48 north, 48 south |

The effect size is reported beside the p-value because significance alone does
not state magnitude.

## proportion

A Wilson interval over approved numerator and denominator columns:

| Output | Value |
|---|---|
| `successes` / `trials` | 4697 / 45192 |
| `proportion` | 0.10393 |
| 95% Wilson interval | 0.101154 -- 0.106781 |

`minimum_denominator` and `zero_cell_correction` are optional; the privacy
floor `minimum_group_count` is enforced regardless.

## correlate

Pearson correlation with its paired-case accounting:

| Output | Value |
|---|---|
| `correlation` | 0.8800 |
| `paired_count` | 48 |
| `excluded_pair_count` | 0 |

Correlation evidence always retains the association-not-causation caution. The
engine cannot promote a coefficient to a causal claim, and neither may a
narrative citing it.

## regress

OLS with HC1 robust covariance:

| Output | Value |
|---|---|
| `coefficient:predictor` | 0.19290 |
| `standard_error:predictor` | 0.03105 |

Five diagnostics are recorded alongside the fit and are the point of the
method, not decoration: `STAT_RESIDUAL_NORMALITY`, `STAT_HETEROSKEDASTICITY`,
`STAT_INFLUENCE`, `STAT_REGRESSION_CONDITION`, `STAT_REGRESSION_VIF`.

## detect_anomalies

`trailing_mad` compares each week against a baseline built only from prior
weeks. The fixture carries one genuine excursion:

| Week | Observed | Baseline center | Threshold | Flagged |
|---|---|---|---|---|
| 2025-09-01 | 146 | 112 | 7.784 | yes |
| 2025-11-17 | 109 | 112.5 | 2.595 | yes |

23 of 48 weeks are evaluated -- the earliest weeks have no prior-only history
and are never judged against themselves.

Two properties matter when reading this output. The second flag is a real
borderline call: a deviation of 3.5 against a 2.595 threshold in an unusually
quiet stretch, where the robust dispersion is small so the bar is low. That is
the rule behaving correctly, not noise to tune away.

And `trailing_mad` is only meaningful on a level series. On a trending series
the trailing center systematically lags the current level, so a sustained trend
reports a run of anomalies. Detrending, or choosing `seasonal_mad`, is the
analyst's decision -- the engine computes the model you declare and does not
substitute another.

## detect_change_points

PELT with an L2 cost, `min_segment: 6`, `penalty: 12.0`. This is the only
method requiring the separate `stats-change` extra (for `ruptures`); without it
the outcome is `unavailable`, never a silent skip.

Detected breakpoint indices: **12, 19, 29, 35, 41**.

`STAT_CANDIDATE_REGIME_CHANGE` is recorded per candidate boundary, so the
segmentation is auditable rather than a bare list.

## The boundary is unchanged

Every run above ends `computed` -- the declared numerical method completed.
None of them approved anything. All six evidence files carry
`authority: derived-evidence-only`, `review_state: pending`, and
`readiness_effect: none; named-human approval required`, and none altered the
readiness record. A named human reviews each one, records their identity and
authority class, and states the permitted narrative claim.
