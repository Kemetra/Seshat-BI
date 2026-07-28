# Governed Statistical Evidence Engine

**Date:** 2026-07-28  
**Status:** Approved design; implementation not started  
**Product:** Seshat BI  
**Scope:** Governed descriptive, inferential, regression, anomaly, change-point,
and forecasting evidence

## 1. Context

Seshat BI currently provides owner-grade statistical guardrails in the
`bi-analyst-knowledge` layer: trailing bands, seasonality-aware comparisons,
minimum-sample caveats, and correlation-versus-causation warnings. It explicitly
routes regression, forecasting, significance testing, and confidence intervals
to a human `[GAP]`. The package has no numerical runtime dependency beyond
PyYAML.

This design deliberately changes that product boundary. Seshat BI will gain a
governed statistical evidence engine without becoming an autonomous ML platform,
creating business meaning, bypassing readiness, or granting approval.

## 2. Goals

The engine must:

1. Compute reproducible statistical evidence from governed data.
2. Cover descriptive statistics, uncertainty, group comparisons, proportions,
   association, regression, anomaly detection, change points, and forecasting.
3. Bind every business analysis to approved metric contracts and validated gold
   data.
4. Refuse or withhold unsupported analyses with concrete reasons.
5. Preserve method, parameter, data, exclusion, and runtime provenance.
6. Produce machine-readable evidence and a human-readable review handoff.
7. Keep the base Seshat installation lightweight through lazy optional
   dependencies.
8. Preserve the existing seven readiness stages and all named-human approval
   boundaries.

## 3. Non-goals

The engine will not:

- define metrics, mappings, grains, rollups, thresholds, or business meaning;
- execute DDL, DML, warehouse transformations, or Power BI operations;
- train or deploy continuously operating ML models;
- perform opaque automatic feature engineering or unrestricted model search;
- accept arbitrary SQL, Python, or dynamically imported user code;
- claim causality from observational analysis;
- emit a health, maturity, readiness, or confidence score;
- write a readiness status, approval, metric contract, or source map;
- persist raw observations or sensitive values in its evidence artifacts.

Numeric confidence intervals are statistical results and are not the forbidden
fabricated confidence score. Their confidence level, method, assumptions, and
sampling interpretation must always be explicit.

## 4. Placement in the readiness system

There is no eighth readiness stage.

Business statistical analysis sits downstream of approved metric meaning and
validated data:

```text
gold_ready: pass + live retail validate evidence
                         |
semantic_model_ready: pass + approved metric contracts
                         |
committed statistical analysis specification
                         |
read-only data acquisition -> statistical core
                         |
immutable statistical evidence
                         |
named-human analytical review
                         |
narrative brief / dashboard design may cite reviewed evidence
```

Business analysis fails closed unless:

- `gold_ready` is `pass`;
- the readiness evidence cites a successful live `retail validate`;
- `semantic_model_ready` is `pass`;
- every referenced metric contract is `pass`;
- the requested physical binding resolves to validated `gold.*` objects; and
- required analysis decisions are explicit in the committed specification.

Source-quality profiling may continue to compute mechanical source facts before
gold, but it is a separate profiling concern. It must not use this engine to make
business claims from bronze or silver data.

An evidence result never changes readiness. A narrative or dashboard may consume
it only after a named human records an analytical review.

## 5. Authority classification

The implementation is split because Seshat's architecture classifies any
database connection as an Adapter, even when it is read-only.

### 5.1 Statistical core

- **Category:** Product Module
- **Capability:** execution-capable against supplied in-memory rectangular data
- **Reads:** approved specifications, metric-contract projections, readiness
  projections, and rectangular observations supplied through a protocol
- **Writes:** derived statistical evidence only
- **Cannot:** connect to a database, external service, or Power BI

### 5.2 Gold data adapter

- **Category:** read-only Execution Adapter
- **Connectivity:** database read only
- **Reads:** `.env`-resolved connection configuration, validated contract
  bindings, source-map relationship metadata, and approved analysis specifications
- **Executes:** parameterized `SELECT` operations against validated `gold.*`
  objects
- **Cannot:** define analysis meaning, modify data, grant approval, or publish

### 5.3 Local extract provider

- **Category:** local execution seam
- **Reads:** a user-supplied local CSV extract
- **Constraint:** the extract is gitignored by default; evidence records its
  content digest and shape, not raw values or a sensitive absolute path
- **Purpose:** reproducible offline runs, fixtures, and environments without a DSN

Parquet support is a future provider addition behind its own optional dependency;
it is not part of the v1 dependency contract.

Both providers satisfy the same narrow rectangular-data protocol. The statistical
core cannot tell whether observations came from a database, a local extract, or
an in-memory test fixture.

## 6. Architecture

```text
analysis spec
    |
    v
spec loader/schema validator
    |
    v
policy preflight --------------------------+
    |                                      |
    | resolves approved bindings           | refused evidence
    v                                      |
data request compiler                      |
    |                                      |
    v                                      |
rectangular-data provider protocol         |
    |                                      |
    v                                      |
data-quality and sufficiency preflight ----+----> withheld evidence
    |
    v
explicit method registry
    |
    v
method implementation + diagnostics -------+----> failed evidence
    |
    v
canonical evidence builder
    |
    +----> analysis-evidence.json
    |
    +----> analysis-review.md (pending human review)
```

### 6.1 Specification loader

Loads a committed YAML specification and validates it against
`schemas/statistical-analysis-spec.schema.json`. It rejects unknown fields,
unknown method IDs, malformed identifiers, ambiguous roles, unsupported
parameters, and incomplete provenance.

### 6.2 Policy preflight

Loads the minimum required readiness and contract artifacts. It confirms stage
state, named approval evidence, gold-only binding, method compatibility, PII
policy, grain compatibility, and the presence of every required human decision.
It reuses existing readers and approval predicates rather than creating a second
readiness or approval engine.

### 6.3 Data request compiler

Compiles a restricted, typed request from approved bindings. A specification
cannot carry SQL. The compiler supports:

- validated table and column identifiers;
- an allowlist of aggregations;
- typed equality, range, membership, null, and boolean filters;
- declared time, group, response, predictor, numerator, denominator, weight,
  and identifier roles;
- joins only when a committed source map declares the relationship and
  cardinality.

Identifiers are dialect-quoted. Values are bound as query parameters. The
compiler rejects comments, statement separators, expressions, unapproved joins,
non-gold relations, and any binding that exceeds the approved metric contract.

### 6.4 Rectangular-data provider

Returns:

- ordered column roles and logical types;
- rows or bounded columnar batches;
- total and excluded row counts;
- a stable data/query digest;
- provider identity and version;
- source timestamps or snapshot identifiers when available; and
- non-sensitive acquisition warnings.

The first implementation may materialize bounded data in memory. The provider
must enforce configurable row and memory ceilings and return `unavailable` or
`withheld` rather than silently sampling. A future streaming implementation can
replace it without changing method or evidence contracts.

### 6.5 Method registry

Maps stable method IDs and method-schema versions to internal callables. The
registry is closed: there is no dotted-path import, `eval`, plugin execution, or
arbitrary callable field. Every method declares required roles, supported logical
types, parameters, minimum data, assumptions, outputs, diagnostics, and
dependency requirements.

### 6.6 Evidence builder and review renderer

The evidence builder serializes a canonical result conforming to
`schemas/statistical-analysis-evidence.schema.json`. The renderer creates a
review handoff from that evidence without recomputing statistics.

Machine evidence is immutable derived evidence. Human review is a separate
artifact so a reviewer cannot accidentally alter the recorded computation.

## 7. Committed artifacts

Recommended per-subject layout:

```text
mappings/<subject>/analyses/
  <analysis-id>.analysis.yaml
  <analysis-id>.evidence.json
  <analysis-id>.review.md
```

Generic contracts:

```text
schemas/statistical-analysis-spec.schema.json
schemas/statistical-analysis-evidence.schema.json
templates/statistical-analysis-spec.yaml
templates/statistical-analysis-review.md
docs/architecture/statistical-evidence-engine.md
```

The filled `retail_store_sales` example may demonstrate the feature after its
contracts and readiness artifacts satisfy the preconditions. Its schema and
answers must never become generic defaults.

## 8. Analysis specification

The canonical specification contains:

- `schema_version`
- `analysis_id` and revision
- decision question and intended decision cadence
- `subject` and named owner/reviewer role
- referenced readiness status and metric-contract paths
- provider kind and logical dataset binding
- population, observation grain, inclusion/exclusion policy
- role bindings for response, predictor, group, time, numerator, denominator,
  weight, and identifier columns as applicable
- explicit method ID and method version
- explicit parameters, including alternatives, confidence level, correction,
  seasonal period, forecast horizon, backtest windows, or change-point penalty
- missing-data policy
- minimum sample/history rules
- random seed when the method is stochastic
- PII classification and approved handling evidence
- expected output artifact paths

There is no generic `options` bag. Each method has a closed parameter schema.
Defaults that affect interpretation are written into the normalized
specification and evidence; they are never invisible runtime defaults.

## 9. Evidence contract

Every result contains:

- schema and engine version;
- authority marker `derived-evidence-only`;
- invocation ID and timestamps;
- analysis specification path, revision, and SHA-256 digest;
- readiness and metric-contract paths, revisions, digests, and observed states;
- provider kind, source/query digest, observation grain, input/excluded counts,
  and exclusion reasons;
- method ID, method version, library names and versions, normalized parameters,
  and random seed;
- outcome;
- estimates and test statistics;
- intervals with level and construction method;
- effect sizes where a comparison is made;
- adjusted and unadjusted p-values where applicable;
- assumptions and diagnostics as observed facts, not a global score;
- warnings, blocking reasons, and recovery actions;
- interpretation cautions;
- `readiness_effect: "none; named-human approval required"`; and
- review state `pending`.

Finite decimal results are serialized as decimal strings to avoid platform
float drift. Missing results use JSON `null`. JSON `NaN`, positive infinity, and
negative infinity are forbidden and force a withheld or failed result with a
reason.

Evidence does not include raw rows, category members that would disclose a
person, connection strings, hostnames, credentials, or sensitive local paths.

## 10. Outcomes and CLI behavior

The exact outcome vocabulary is:

- `computed`: computation and required diagnostics completed;
- `withheld`: data was acquired, but sufficiency or assumptions do not support
  the requested evidence;
- `refused`: an authority, readiness, contract, binding, PII, or specification
  precondition failed;
- `failed`: an unexpected execution or numerical error occurred; and
- `unavailable`: an optional dependency, provider, driver, or live connection is
  absent.

`computed` means only that the method ran. It is not a business approval,
readiness pass, or instruction to act.

The agent drives these helper commands:

```text
seshat analyze validate --spec <path>
seshat analyze run --spec <path> [provider arguments]
seshat analyze render --evidence <path>
```

The `retail` console alias exposes the same commands for compatibility.

Exit codes follow the existing CLI posture:

- `0`: computed;
- `1`: withheld;
- `2`: refused or invalid invocation/specification;
- `3`: failed;
- `4`: unavailable.

Every nonzero path prints a concise ASCII-safe explanation and recovery action,
never a traceback by default. Machine-readable output remains available.

## 11. Statistical capability catalog

All methods require explicit selection. The engine does not silently choose a
test based on a normality test or search an unrestricted model space.

### 11.1 `describe`

Produces:

- observed, missing, excluded, and distinct counts;
- minimum, maximum, configurable quantiles, mean, median, variance, standard
  deviation, IQR, MAD, skewness, and kurtosis;
- explicit sample-versus-population dispersion convention;
- robust univariate outlier counts under a declared IQR or MAD rule; and
- optional group summaries subject to minimum group size.

It does not label an extreme value erroneous or recommend deletion.

### 11.2 `compare_groups`

Supports explicit:

- independent Welch t-test;
- paired t-test;
- Mann-Whitney U;
- Wilcoxon signed-rank;
- one-way Welch ANOVA;
- Kruskal-Wallis; and
- declared post-hoc comparisons.

Every comparison reports an effect size and interval where the selected method
supports one. The governed defaults are Hedges' g for independent mean
comparisons, paired standardized mean change for paired t-tests, rank-biserial
correlation for Mann-Whitney/Wilcoxon, omega-squared for Welch ANOVA, and
epsilon-squared for Kruskal-Wallis. Declared post-hoc work is a closed set of
pairwise comparisons using the selected two-group method. Multiple comparisons
require a declared correction such as Benjamini-Hochberg or Holm. A p-value
alone is never emitted as the conclusion.

### 11.3 `proportion`

Supports:

- Wilson and exact binomial intervals;
- one- and two-sample proportion comparisons;
- contingency-table chi-square with expected-cell diagnostics;
- Fisher exact tests when explicitly selected;
- risk difference, risk ratio, and odds ratio with intervals.

The numerator, denominator, missing-status policy, and minimum denominator are
mandatory and bind to approved metric meaning.

### 11.4 `correlate`

Supports Pearson and Spearman association with sample count, interval, p-value,
missing-pair policy, and multiplicity correction when several pairs are tested.
Every result carries an explicit association-not-causation caution.

### 11.5 `regress`

Supports a governed initial family:

- ordinary least squares;
- logistic generalized linear models; and
- Poisson or negative-binomial generalized linear models when the response
  contract supports count analysis.

Specifications must name response and predictors. Implementations provide
coefficient estimates and intervals, robust standard errors where selected,
residual diagnostics, influence warnings, multicollinearity diagnostics, and
fit measures. Automatic stepwise selection, causal wording, and coefficients
without unit/grain context are forbidden.

### 11.6 `detect_anomalies`

Supports:

- trailing robust bands;
- seasonal decomposition with robust residual bands; and
- explicit one-sided or two-sided rules.

The current observation cannot contribute to its own baseline. Seasonal methods
require a declared period, regular time index, contiguous history, and a minimum
of two complete cycles by default. Recurring same-phase behavior is seasonal,
not anomalous. Insufficient history yields `withheld`.

### 11.7 `detect_change_points`

Supports explicit offline change-point detection through a maintained optional
library. The specification declares cost/model, penalty or requested number of
changes, minimum segment size, and time ordering. Results are candidate regime
changes for review, not causal events.

### 11.8 `forecast`

Always includes a seasonal-naive or naive baseline appropriate to the declared
frequency. The initial governed candidate set is deliberately closed: naive,
seasonal naive, and declared additive ETS/state-space variants with optional
trend, damping, and additive seasonality. Multiplicative variants are withheld
when zero or negative observations violate their domain and are not part of the
initial automatic comparison set.

Requirements:

- regular, ordered time index;
- declared frequency, seasonal period, horizon, and partial-period policy;
- minimum history tied to seasonal cycles and backtest windows;
- rolling-origin evaluation with no future leakage;
- declared evaluation measures including MASE and sMAPE;
- residual diagnostics;
- point forecasts and prediction intervals; and
- comparison against the baseline.

Candidate selection is limited to the declared set and declared evaluation
criterion. The evidence records every candidate and its backtest result. A model
that does not beat the declared baseline or fails diagnostics is reported
honestly; the engine does not manufacture a forecast endorsement.

## 12. Dependency policy

The base package remains PyYAML-only.

The optional `stats` extra adds compatible pinned ranges for:

- NumPy;
- SciPy; and
- statsmodels.

A separate optional change-point extra adds the maintained `ruptures` package
without making it a base or general statistics requirement. All imports remain
inside adapter or method factories. Importing `seshat`, running static checks,
or using unrelated CLI commands must not import numerical or DB libraries.

The implementation plan must select and test concrete version ranges against the
repository's supported Python versions. It must record installed runtime
versions in every evidence artifact.

Primary references:

- SciPy statistics API: <https://docs.scipy.org/doc/scipy/reference/stats.html>
- SciPy bootstrap API:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html>
- statsmodels state-space API:
  <https://www.statsmodels.org/stable/statespace.html>
- ruptures documentation: <https://centre-borelli.github.io/ruptures-docs/>

## 13. Security, privacy, and resource controls

- Secrets remain in gitignored `.env` files.
- The adapter reuses shared DSN redaction.
- SQL identifiers pass existing identifier and dialect validators.
- Query values are parameters, never interpolated.
- Only `SELECT` requests against approved `gold.*` objects are allowed.
- A read-only DB role and statement timeout are required for live use.
- Query row count, byte estimate, wall-clock, and in-memory ceilings are explicit.
- Silent sampling is forbidden.
- Group outputs below a declared privacy/minimum-count floor are suppressed.
- Raw row values and sensitive category labels never enter evidence or logs.
- Local extracts are gitignored by default; tracked examples use synthetic data.
- Stochastic methods use an explicit reproducible seed.
- Denial-of-service parameters such as resample count, forecast horizon, lag
  count, candidate count, and change-point complexity have bounded schemas.

## 14. Error handling

Expected precondition failures become structured `refused`, `withheld`, or
`unavailable` evidence. Unexpected exceptions are caught at the CLI boundary,
redacted, assigned an invocation ID, and returned as `failed`.

Examples:

- missing approved metric contract -> `refused`;
- semantic model stage not passed -> `refused`;
- no DSN or DB extra -> `unavailable` with enable steps;
- fewer observations than the declared floor -> `withheld`;
- insufficient seasonal cycles -> `withheld`;
- constant sample makes an interval undefined -> `withheld`;
- singular regression design -> `withheld` with diagnostic details;
- provider timeout -> `unavailable` or `failed` according to provider response;
- non-finite library result -> `failed` or `withheld`, never invalid JSON.

No error path writes partial output to the final evidence path. Writers use an
atomic temporary-file replacement within the intended output directory.

## 15. Human review

The review template asks the named reviewer to record:

- accepted, rejected, or changes-requested;
- whether the population, grain, exclusions, and method answer the decision
  question;
- whether assumptions and diagnostics are acceptable;
- whether effect magnitude matters in the metric's own unit;
- whether multiplicity, seasonality, and uncertainty are represented honestly;
- whether wording remains associational rather than causal;
- permitted narrative claim and required caveats;
- reviewer identity, authority class, date, and evidence reference.

The agent may draft the review questions but cannot fill the reviewer decision.
Only reviewed evidence can be cited as a finding in a narrative brief.

## 16. Testing strategy

### 16.1 Contract and policy tests

- JSON Schema positive and negative fixtures for specifications and evidence.
- Unknown-field rejection and closed method-parameter schemas.
- Readiness, approval, gold-only, PII, and metric-binding refusal cases.
- Evidence immutability and readiness-effect invariants.

### 16.2 Method oracle tests

Each method receives deterministic synthetic fixtures with known properties.
Results are compared directly with the selected SciPy or statsmodels primitive
within declared tolerances. Tests cover estimates, intervals, p-values, effect
sizes, corrections, diagnostics, and evidence serialization.

### 16.3 Edge and adversarial tests

- empty, singleton, tiny, and constant samples;
- missing, non-finite, duplicated, or badly typed values;
- unequal groups, unequal variance, and extreme imbalance;
- zero denominators and sparse contingency tables;
- singular and nearly singular regression designs;
- duplicated, unsorted, gapped, and irregular timestamps;
- partial periods and insufficient seasonal cycles;
- outliers at the baseline boundary;
- parameters at every resource limit;
- unsafe identifiers, filters, paths, and sensitive strings.

### 16.4 Statistical property tests

Where mathematically applicable:

- translation and positive-scale invariance;
- group-order symmetry or expected sign reversal;
- permutation reproducibility from a fixed seed;
- interval ordering and estimate containment where guaranteed;
- adjusted p-values not smaller than their governed correction permits;
- anomaly baselines exclude the evaluated point;
- forecast folds never read observations after their cutoff.

### 16.5 Architecture and CLI tests

- fake providers prove the core never connects externally;
- import tests prove base installs do not load optional dependencies;
- query compiler and dialect contract tests;
- no raw observation or secret leakage in evidence and errors;
- CLI exit-code and ASCII output golden tests;
- atomic-write and interrupted-run tests;
- generated Claude/Codex bundle parity and public allowlist checks;
- focused tests followed by the complete repository test suite.

### 16.6 Optional live evidence

Live DB smoke tests require the `stats` extra, the relevant DB driver, and a DSN.
When absent, the implementation reports:

```text
[PENDING LIVE PROFILE]
```

with the existing installation and `.env` guidance. It never fabricates a live
pass or emits a traceback.

## 17. Documentation and compatibility changes

Implementation must update active documentation that currently states all
regression, forecasting, significance testing, and confidence intervals are out
of scope:

- `skills/bi-analyst-knowledge/SKILL.md`;
- `skills/bi-analyst-knowledge/framing-signal-vs-noise.md`;
- `skills/bi-analyst-knowledge/framing-trend-anomaly.md`;
- active roadmap and architecture documents;
- COMPASS and command-routing documentation;
- public knowledge allowlist and generated integration bundles; and
- package installation and CLI documentation.

The revised analyst layer routes governed statistical questions to this engine
and consumes reviewed evidence. It still does not compute inside a knowledge
skill or invent metric meaning.

Historical changelog entries and historical rejected ideas remain historical.
A new changelog entry explains that the new governed engine supersedes the old
product boundary without rewriting the prior record.

Existing commands, readiness files, metric contracts, and base installations
remain compatible. Statistical fields are additive; no existing contract becomes
invalid merely because it lacks an analysis specification.

## 18. Delivery slices

The full objective is one governed platform delivered in dependency order:

1. contracts, result models, registry, policy preflight, local provider, CLI, and
   `describe`;
2. intervals, group comparisons, proportions, correlation, and multiplicity;
3. regression and diagnostics;
4. time-series normalization, anomaly detection, and change points;
5. forecasting, rolling-origin evaluation, baselines, and intervals;
6. gold DB adapter, review integration, worked example, public bundles, and full
   documentation reconciliation.

These are implementation slices, not scope reductions. The feature is complete
only when all six slices and the acceptance criteria below are satisfied.

## 19. Acceptance criteria

The expansion is complete only when:

1. Both schemas and generic templates are committed and contract-tested.
2. The statistical core and provider protocol are isolated from DB connectivity.
3. The local provider and read-only gold adapter satisfy the same provider
   contract.
4. Every method in Section 11 is registered, documented, and covered by
   deterministic oracle and edge-case tests.
5. Evidence contains the provenance, diagnostics, exclusions, and authority
   markers specified in Section 9.
6. All gate, approval, gold-only, PII, security, and resource-limit refusals are
   verified.
7. Forecast tests prove rolling-origin evaluation has no future leakage and every
   forecast is compared with a declared baseline.
8. The CLI implements validate, run, and render with the specified outcomes and
   exit codes.
9. A named-human review artifact is required before narrative consumption.
10. Active documentation no longer incorrectly describes the governed
    capabilities as universally out of scope.
11. Generated public bundles and allowlists include the new capability without
    hand-edited drift.
12. Focused tests, distribution checks, `seshat check`, and the complete test
    suite pass.
13. A synthetic worked example exercises the full flow without client-specific
    assumptions.
14. Live DB verification is either evidenced or explicitly remains
    `[PENDING LIVE PROFILE]` with enable steps; it is never claimed implicitly.
