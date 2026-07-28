# Governed Statistical Evidence Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Seshat BI's complete governed statistical evidence engine for descriptive, inferential, regression, anomaly, change-point, and forecasting analysis.

**Architecture:** A stdlib-light statistical Product Module consumes approved specifications and rectangular data through a provider protocol. A separate read-only gold Database Adapter compiles restricted parameterized `SELECT` statements, while a local CSV provider supports offline execution. Closed lazy method registration produces immutable JSON evidence and a separate named-human review handoff without changing readiness.

**Tech Stack:** Python 3.13, PyYAML, NumPy 2.5.1, SciPy 1.18.0, statsmodels 0.14.6, ruptures 1.1.10, pytest, JSON Schema draft 2020-12 subset, existing Seshat dialect and readiness infrastructure.

**Spec:** `docs/superpowers/specs/2026-07-28-governed-statistical-evidence-engine-design.md`

## Global Constraints

- Python remains `>=3.13`; Windows with Python 3.13 remains the release gate.
- Base `dependencies` remains exactly PyYAML; numerical libraries live only in optional extras and lazy imports.
- Pin `numpy==2.5.1`, `scipy==1.18.0`, `statsmodels==0.14.6`, and `ruptures==1.1.10`.
- Preserve the seven readiness stages; no analysis outcome writes readiness or grants approval.
- Business analysis requires `gold_ready: pass`, cited live `retail validate` evidence, `semantic_model_ready: pass`, and approved metric contracts.
- Accept no arbitrary SQL, Python, callable path, dynamic plugin, or unbounded parameter bag.
- Database execution is `SELECT`-only against approved `gold.*` bindings with validated identifiers and parameterized values.
- Emit no raw observations, secrets, sensitive category labels, absolute local paths, JSON non-finite values, causal claims, or numeric readiness/confidence scores.
- Outcomes are exactly `computed`, `withheld`, `refused`, `failed`, and `unavailable`; their CLI exit codes are `0`, `1`, `2`, `3`, and `4`.
- Every stochastic method requires an explicit seed and records it.
- Every comparison reports effect magnitude and uncertainty; p-values never stand alone as conclusions.
- The current observation never contributes to its own anomaly baseline; forecast evaluation never reads beyond a fold cutoff.
- C086 remains an example, never a schema. All new templates and fixtures are domain-neutral and synthetic.
- All automation and log output is ASCII-safe.

---

## File Structure

Create the following focused runtime package:

```text
src/seshat/statistical/
  __init__.py             public stable types and version
  contracts.py            enums and immutable cross-component dataclasses
  schema.py               packaged schema resolution and strict YAML loading
  policy.py               readiness, approval, PII, and binding preflight
  evidence.py             canonical serialization and atomic writes
  render.py               evidence-to-review Markdown projection
  registry.py             closed lazy method descriptors
  runtime.py              orchestration and outcome conversion
  query.py                restricted DataRequest-to-SQL compiler
  providers/
    __init__.py
    base.py                provider protocol and resource limits
    local_csv.py           gitignored/local CSV provider
    gold.py                QueryRunner-backed read-only adapter
  methods/
    __init__.py
    common.py              finite conversion, missingness, role extraction
    descriptive.py         describe
    inference.py           intervals, corrections, effect-size primitives
    groups.py              compare_groups
    proportions.py         proportion
    correlation.py         correlate
    regression.py          regress
    time_index.py          ordered regular-series validation and folds
    anomaly.py             detect_anomalies
    changepoint.py         detect_change_points
    forecast.py            forecast and rolling-origin evaluation
src/seshat/cli/
  parser_analysis.py       argparse-only analyze family
  commands/analyze.py      lazy CLI handler
```

Tests mirror these responsibilities under `tests/unit/statistical/`, with
schema/package contracts under `tests/contract/`, optional live proof under
`tests/live_db/`, and synthetic fixtures under `tests/fixtures/statistical/`.

### Task 1: Pin Optional Numerical Environments and Extend Schema Validation

**Files:**
- Modify: `pyproject.toml`
- Modify: `dependency-environments.yaml`
- Modify: `.github/workflows/ci.yml`
- Modify: `src/seshat/ecosystem_contracts.py`
- Test: `tests/unit/test_ecosystem_contracts.py`
- Test: `tests/contract/test_statistical_package_contract.py`

**Interfaces:**
- Consumes: existing `validate_json_contract(value, schema, path="$")`.
- Produces: `validate_json_contract(value, schema, path="$", root_schema=None)` with local `$ref`, `oneOf`, `maximum`, and `maxItems` support.
- Produces optional extras `stats` and `stats-change` and a dedicated `statistics` CI marker/job.

- [ ] **Step 1: Write failing validator tests**

Add exact cases proving local references, one-of exclusivity, upper numeric
bounds, and array ceilings:

```python
def test_contract_validator_resolves_local_ref_and_exactly_one_branch() -> None:
    schema = {
        "$defs": {"id": {"type": "string", "pattern": "^[a-z]+$"}},
        "oneOf": [
            {"type": "object", "required": ["a"], "properties": {"a": {"$ref": "#/$defs/id"}}},
            {"type": "object", "required": ["b"], "properties": {"b": {"type": "integer"}}},
        ],
    }
    assert validate_json_contract({"a": "valid"}, schema) == []
    assert validate_json_contract({"a": "INVALID"}, schema)
    assert validate_json_contract({"a": "valid", "b": 1}, schema)


def test_contract_validator_enforces_maximum_and_max_items() -> None:
    schema = {
        "type": "object",
        "properties": {
            "n": {"type": "integer", "maximum": 10},
            "items": {"type": "array", "maxItems": 2},
        },
    }
    assert validate_json_contract({"n": 11, "items": [1, 2, 3]}, schema)
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```powershell
python -m pytest tests/unit/test_ecosystem_contracts.py -q
```

Expected: the new assertions fail because the validator ignores `$ref`,
`oneOf`, `maximum`, and `maxItems`.

- [ ] **Step 3: Extend the validator without changing existing behavior**

Use a root-schema argument through recursive calls:

```python
def validate_json_contract(
    value: object,
    schema: Mapping[str, Any],
    path: str = "$",
    root_schema: Mapping[str, Any] | None = None,
) -> list[str]:
    root = schema if root_schema is None else root_schema
    resolved = _resolve_local_ref(schema, root)
    branch_errors = _validate_one_of(value, resolved, path, root)
    if branch_errors:
        return branch_errors
    errors = _validate_type(value, resolved, path)
    # Existing scalar/object/array checks continue with root threaded downward.
    return errors
```

`_resolve_local_ref` accepts only `#/$defs/{name}` and fails closed on missing or
non-object definitions. `_validate_one_of` requires exactly one branch to
validate. Extend numeric and array checks with `maximum` and `maxItems`.

- [ ] **Step 4: Declare exact optional dependency environments**

Add:

```toml
stats = [
    "numpy==2.5.1",
    "scipy==1.18.0",
    "statsmodels==0.14.6",
]
stats-change = [
    "ruptures==1.1.10",
]
```

Add `statistics` to pytest markers. Add `root-stats`,
`root-stats-change`, and a `root-stats-plus-db` co-resolution product to
`dependency-environments.yaml`; add all four distributions to `governed_pins`.

- [ ] **Step 5: Add dependency and lazy-isolation contract tests**

```python
def test_statistics_extras_are_exact_and_base_stays_pyyaml_only() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == ["pyyaml>=6"]
    extras = project["project"]["optional-dependencies"]
    assert extras["stats"] == [
        "numpy==2.5.1",
        "scipy==1.18.0",
        "statsmodels==0.14.6",
    ]
    assert extras["stats-change"] == ["ruptures==1.1.10"]
```

The same file must launch a clean subprocess importing `seshat` and assert that
`numpy`, `scipy`, `statsmodels`, and `ruptures` are absent from `sys.modules`.

- [ ] **Step 6: Add the separate statistics CI job**

Keep the existing `check` job on `.[dev]`. Add a credential-free job installing:

```bash
pip install -e ".[dev,stats,stats-change]"
pytest -m statistics
```

This preserves the base-install isolation proof while making every numerical
test mandatory in CI.

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/test_ecosystem_contracts.py tests/contract/test_statistical_package_contract.py -q
python scripts/dep_coresolve.py --check
```

Commit:

```bash
git add pyproject.toml dependency-environments.yaml .github/workflows/ci.yml src/seshat/ecosystem_contracts.py tests/unit/test_ecosystem_contracts.py tests/contract/test_statistical_package_contract.py
git commit -m "build: add governed statistics dependency environment"
```

### Task 2: Define Analysis Schemas, Templates, and Strict Spec Loading

**Files:**
- Create: `schemas/statistical-analysis-spec.schema.json`
- Create: `schemas/statistical-analysis-evidence.schema.json`
- Create: `templates/statistical-analysis-spec.yaml`
- Create: `templates/statistical-analysis-review.md`
- Create: `src/seshat/statistical/__init__.py`
- Create: `src/seshat/statistical/contracts.py`
- Create: `src/seshat/statistical/schema.py`
- Modify: `pyproject.toml`
- Test: `tests/contract/test_statistical_schemas.py`
- Test: `tests/unit/statistical/test_schema.py`

**Interfaces:**
- Produces `Outcome`, `Blocker`, `ColumnBinding`, `MethodSpec`, `AnalysisSpec`.
- Produces `resolve_statistical_schema(repo_root, name) -> Path`.
- Produces `load_analysis_spec(path, repo_root) -> AnalysisSpec`.

- [ ] **Step 1: Write schema contract tests with one valid spec per method**

Use a shared base payload and parametrize over the eight IDs:

```python
@pytest.mark.parametrize(
    ("method_id", "parameters"),
    [
        ("describe", {"quantiles": ["0.25", "0.5", "0.75"], "outlier_rule": "mad"}),
        ("compare_groups", {"test": "welch_t", "alternative": "two-sided", "confidence_level": "0.95", "correction": "holm"}),
        ("proportion", {"interval": "wilson", "alternative": "two-sided", "confidence_level": "0.95"}),
        ("correlate", {"coefficient": "spearman", "confidence_level": "0.95", "correction": "benjamini-hochberg"}),
        ("regress", {"family": "ols", "covariance": "HC3", "confidence_level": "0.95"}),
        ("detect_anomalies", {"model": "seasonal_mad", "period": 12, "threshold": "3.5"}),
        ("detect_change_points", {"model": "l2", "penalty": "10", "min_segment": 6}),
        ("forecast", {"candidates": ["seasonal_naive", "ets_add"], "period": 12, "horizon": 6, "confidence_level": "0.95", "evaluation_metric": "mase", "initial_window": 24, "step": 1, "max_folds": 6}),
    ],
)
def test_method_variants_are_closed(method_id: str, parameters: dict) -> None:
    payload = valid_spec(method_id, parameters)
    assert validate_json_contract(payload, SPEC_SCHEMA) == []
    assert validate_json_contract({**payload, "unexpected": True}, SPEC_SCHEMA)
```

Also assert evidence outcome enumeration, decimal-string patterns,
`authority == "derived-evidence-only"`, and the fixed readiness effect.

- [ ] **Step 2: Run and confirm the schema tests fail**

Run:

```powershell
python -m pytest tests/contract/test_statistical_schemas.py -q
```

Expected: missing schema files.

- [ ] **Step 3: Create closed schemas and generic templates**

The spec schema requires:

```json
{
  "schema_version": "1.0",
  "analysis_id": "weekly_sales_signal",
  "revision": 1,
  "question": "Is the approved metric changing beyond normal variation?",
  "cadence": "weekly",
  "subject": "sample_orders",
  "owner": "Example Analyst (metric_owner)",
  "readiness_status": "mappings/sample_orders/readiness-status.yaml",
  "metric_contracts": ["mappings/sample_orders/metrics/TotalValue.yaml"],
  "provider": {"kind": "local_csv", "dataset_id": "weekly_metric"},
  "population": {"grain": "one row per completed week", "inclusion": [], "exclusion": []},
  "roles": {"response": {"column": "metric_value", "logical_type": "number"}},
  "method": {"id": "describe", "version": "1.0", "parameters": {"quantiles": ["0.25", "0.5", "0.75"], "outlier_rule": "mad"}},
  "missing_data": {"policy": "complete_case"},
  "minimum_data": {"observations": 12, "groups": 1, "seasonal_cycles": 0},
  "random_seed": 1729,
  "pii": {"classification": "none", "approval_evidence": [], "minimum_group_count": 5},
  "outputs": {"evidence": "mappings/sample_orders/analyses/weekly_sales_signal.evidence.json", "review": "mappings/sample_orders/analyses/weekly_sales_signal.review.md"}
}
```

Make every method parameter object closed and bounded. Use decimal strings for
thresholds and confidence levels. The evidence schema uses generic typed arrays
for estimates, intervals, tests, diagnostics, warnings, and blockers.

- [ ] **Step 4: Define immutable contracts**

```python
class Outcome(StrEnum):
    COMPUTED = "computed"
    WITHHELD = "withheld"
    REFUSED = "refused"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Blocker:
    code: str
    message: str
    recovery: str


@dataclass(frozen=True, slots=True)
class ColumnBinding:
    column: str
    logical_type: Literal["number", "integer", "boolean", "category", "date", "datetime", "identifier"]


@dataclass(frozen=True, slots=True)
class MethodSpec:
    method_id: str
    version: str
    parameters: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class AnalysisSpec:
    schema_version: str
    analysis_id: str
    revision: int
    subject: str
    question: str
    cadence: str
    owner: str
    readiness_status: PurePosixPath
    metric_contracts: tuple[PurePosixPath, ...]
    provider: Mapping[str, object]
    population: Mapping[str, object]
    roles: Mapping[str, ColumnBinding]
    method: MethodSpec
    missing_policy: str
    minimum_data: Mapping[str, int]
    random_seed: int
    pii: Mapping[str, object]
    outputs: Mapping[str, PurePosixPath]
```

Paths must be repo-relative, contain no `..`, and resolve under the repository.

- [ ] **Step 5: Implement packaged schema resolution and strict loading**

`resolve_statistical_schema` first checks the development repository and then
the force-included package path. `load_analysis_spec` reads UTF-8-sig YAML,
validates it, and normalizes it into the dataclass. It raises one
`SpecRefused(errors: tuple[str, ...])` with all concrete schema errors.

- [ ] **Step 6: Force-include schemas in the wheel**

Add:

```toml
"schemas/statistical-analysis-spec.schema.json" = "seshat/statistical/schemas/statistical-analysis-spec.schema.json"
"schemas/statistical-analysis-evidence.schema.json" = "seshat/statistical/schemas/statistical-analysis-evidence.schema.json"
```

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest tests/contract/test_statistical_schemas.py tests/unit/statistical/test_schema.py -q
```

Commit:

```bash
git add schemas/statistical-analysis-spec.schema.json schemas/statistical-analysis-evidence.schema.json templates/statistical-analysis-spec.yaml templates/statistical-analysis-review.md src/seshat/statistical pyproject.toml tests/contract/test_statistical_schemas.py tests/unit/statistical/test_schema.py
git commit -m "feat: define governed statistical analysis contracts"
```

### Task 3: Build Canonical Evidence, Atomic Writes, and Review Rendering

**Files:**
- Modify: `src/seshat/statistical/contracts.py`
- Create: `src/seshat/statistical/evidence.py`
- Create: `src/seshat/statistical/render.py`
- Test: `tests/unit/statistical/test_evidence.py`
- Test: `tests/unit/statistical/test_render.py`

**Interfaces:**
- Produces `Estimate`, `Interval`, `TestStatistic`, `Diagnostic`, `AnalysisEvidence`.
- Produces `decimal_text(value) -> str`.
- Produces `build_evidence(...) -> AnalysisEvidence`.
- Produces `write_evidence(path, evidence) -> Path`.
- Produces `render_review(evidence) -> str` and `write_review(path, evidence) -> Path`.

- [ ] **Step 1: Write failing evidence tests**

```python
def test_decimal_text_refuses_non_finite_values() -> None:
    assert decimal_text(Decimal("1.2500")) == "1.25"
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(NonFiniteResult):
            decimal_text(value)


def test_atomic_writer_leaves_no_partial_final_file(tmp_path: Path, monkeypatch) -> None:
    final = tmp_path / "result.json"
    monkeypatch.setattr(os, "replace", Mock(side_effect=OSError("interrupted")))
    with pytest.raises(OSError):
        write_evidence(final, sample_evidence())
    assert not final.exists()
```

Add assertions that serialized evidence contains no input rows, DSN fragments,
absolute paths, or JSON non-finite tokens.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest tests/unit/statistical/test_evidence.py tests/unit/statistical/test_render.py -q
```

Expected: missing modules and types.

- [ ] **Step 3: Implement generic evidence types**

```python
@dataclass(frozen=True, slots=True)
class Estimate:
    name: str
    value: str | None
    unit: str | None


@dataclass(frozen=True, slots=True)
class Interval:
    name: str
    low: str | None
    high: str | None
    level: str
    method: str


@dataclass(frozen=True, slots=True)
class TestStatistic:
    name: str
    statistic: str | None
    p_value: str | None
    adjusted_p_value: str | None
    alternative: str | None
    method: str


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    status: Literal["holds", "warning", "violated", "not_applicable"]
    observed: str | None
    message: str
```

`AnalysisEvidence` contains the exact schema fields, typed tuples, and
`review_state="pending"`.

- [ ] **Step 4: Define non-finite refusal**

```python
class NonFiniteResult(ValueError):
    """A numerical library returned a value JSON evidence cannot represent."""
```

- [ ] **Step 5: Implement finite canonical serialization and atomic writes**

Use sorted keys, UTF-8, two-space indentation, a trailing newline, and
`allow_nan=False`. Create the temporary file in `path.parent`, close it, then
call `os.replace`. Resolve the final path and refuse any output escaping the
repository root supplied to the writer.

- [ ] **Step 6: Implement a non-computing review renderer**

Render population, exclusions, method, estimates, intervals, effect sizes,
tests, diagnostics, warnings, and explicit human fields:

```markdown
## Human review decision

- [ ] accepted
- [ ] rejected
- [ ] changes requested

Reviewer:
Authority class:
Reviewed at:
Permitted narrative claim:
Required caveats:
```

The renderer must state that computation is derived evidence and readiness
effect is none.

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/statistical/test_evidence.py tests/unit/statistical/test_render.py -q
```

Commit:

```bash
git add src/seshat/statistical/contracts.py src/seshat/statistical/evidence.py src/seshat/statistical/render.py tests/unit/statistical/test_evidence.py tests/unit/statistical/test_render.py
git commit -m "feat: add immutable statistical evidence artifacts"
```

### Task 4: Enforce Readiness, Approval, Binding, and PII Policy

**Files:**
- Modify: `src/seshat/metric_contract_inventory.py`
- Create: `src/seshat/statistical/policy.py`
- Test: `tests/unit/test_metric_contract_inventory.py`
- Test: `tests/unit/statistical/test_policy.py`
- Create fixtures: `tests/fixtures/statistical/policy_repo/`

**Interfaces:**
- Extends `MetricContract` with `columns`, `pii_sensitive`, `grain`, `unit`, and `time_additivity`.
- Produces `PolicyContext` and `PolicyDecision`.
- Produces `evaluate_policy(repo_root, spec) -> PolicyDecision`.

- [ ] **Step 1: Write failing policy matrix tests**

Parametrize the exact refusal cases:

```python
@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("gold_not_pass", "STAT_GOLD_NOT_READY"),
        ("live_validate_missing", "STAT_LIVE_VALIDATION_MISSING"),
        ("semantic_not_pass", "STAT_SEMANTIC_NOT_READY"),
        ("contract_not_pass", "STAT_CONTRACT_NOT_APPROVED"),
        ("binding_not_gold", "STAT_NON_GOLD_BINDING"),
        ("pii_approval_missing", "STAT_PII_APPROVAL_MISSING"),
        ("grain_conflict", "STAT_GRAIN_CONFLICT"),
    ],
)
def test_policy_refuses_missing_authority(mutation: str, code: str, policy_repo: Path) -> None:
    apply_mutation(policy_repo, mutation)
    decision = evaluate_policy(policy_repo, load_fixture_spec(policy_repo))
    assert decision.allowed is False
    assert code in {blocker.code for blocker in decision.blockers}
```

Also prove a valid fixture resolves the exact approved contract and no stage is
written.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest tests/unit/test_metric_contract_inventory.py tests/unit/statistical/test_policy.py -q
```

- [ ] **Step 3: Extend the approved contract projection additively**

Read and validate:

```python
columns=tuple(raw["binds_to"].get("columns", [])),
pii_sensitive=raw["binds_to"].get("pii_sensitive") is True,
grain=raw["grain"],
unit=raw.get("unit"),
time_additivity=raw.get("time_additivity"),
```

Keep existing constructor use compatible by giving additive fields defaults.

- [ ] **Step 4: Define the policy result types**

```python
@dataclass(frozen=True, slots=True)
class PolicyContext:
    subject: str
    readiness_path: Path
    readiness_revision: str
    contracts: tuple[MetricContract, ...]
    approved_tables: frozenset[str]
    approved_columns: Mapping[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    blockers: tuple[Blocker, ...]
    context: PolicyContext | None
```

- [ ] **Step 5: Implement exact preflight policy**

`evaluate_policy`:

1. resolves the spec readiness file under the repo;
2. uses `build_status_projection` to locate the same subject;
3. requires `gold_ready.status == "pass"`;
4. requires gold evidence matching a case-insensitive
   `(?:seshat|retail) validate` plus `exit 0` or `PASS`;
5. requires `semantic_model_ready.status == "pass"`;
6. loads only named metric paths through `load_contract_inventory`;
7. requires every spec path to resolve to an approved contract in the subject;
8. requires every physical table to start `gold.`;
9. checks requested roles against approved bound columns/definitions;
10. refuses PII-sensitive inputs without cited approval evidence; and
11. compares declared observation grain with the approved grain.

Return every blocker in deterministic code order; never stop after the first.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/test_metric_contract_inventory.py tests/unit/statistical/test_policy.py -q
```

Commit:

```bash
git add src/seshat/metric_contract_inventory.py src/seshat/statistical/policy.py tests/unit/test_metric_contract_inventory.py tests/unit/statistical/test_policy.py tests/fixtures/statistical/policy_repo
git commit -m "feat: enforce statistical analysis authority gates"
```

### Task 5: Add the Provider Protocol and Local CSV Provider

**Files:**
- Create: `src/seshat/statistical/providers/__init__.py`
- Create: `src/seshat/statistical/providers/base.py`
- Create: `src/seshat/statistical/providers/local_csv.py`
- Test: `tests/unit/statistical/test_provider_contract.py`
- Test: `tests/unit/statistical/test_local_csv_provider.py`
- Create: `tests/fixtures/statistical/weekly_metric.csv`

**Interfaces:**
- Produces `Filter`, `Aggregate`, `Join`, `ResourceLimits`, `DataRequest`,
  `ProviderProvenance`, `RectangularData`.
- Produces `build_data_request(spec, policy_context) -> DataRequest`.
- Produces protocol `DataProvider.fetch(request) -> RectangularData`.
- Produces `LocalCsvProvider(path, limits).fetch(request)`.

- [ ] **Step 1: Write provider contract and resource-limit tests**

```python
def test_local_provider_returns_ordered_roles_and_digest(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "period,value\n2026-01,10\n2026-02,12\n")
    data = LocalCsvProvider(path, ResourceLimits(max_rows=10, max_bytes=1024)).fetch(
        DataRequest(columns=("period", "value"), logical_types=("date", "number"))
    )
    assert data.columns == ("period", "value")
    assert data.rows == (("2026-01", "10"), ("2026-02", "12"))
    assert len(data.provenance.data_digest) == 64
    assert str(tmp_path) not in data.provenance.safe_label


def test_local_provider_refuses_silent_sampling(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "value\n1\n2\n3\n")
    with pytest.raises(ProviderUnavailable, match="row ceiling"):
        LocalCsvProvider(path, ResourceLimits(max_rows=2, max_bytes=1024)).fetch(
            DataRequest(columns=("value",), logical_types=("number",))
        )
```

Cover duplicate/blank headers, ragged rows, missing role columns, byte ceiling,
UTF-8 failure, non-finite tokens, and sensitive absolute-path suppression.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest tests/unit/statistical/test_provider_contract.py tests/unit/statistical/test_local_csv_provider.py -q
```

- [ ] **Step 3: Implement stdlib-only provider contracts**

```python
@dataclass(frozen=True, slots=True)
class ResourceLimits:
    max_rows: int = 250_000
    max_bytes: int = 128 * 1024 * 1024
    timeout_seconds: int = 60


@dataclass(frozen=True, slots=True)
class Filter:
    column: str
    operator: str
    value: object | tuple[object, ...] | None


@dataclass(frozen=True, slots=True)
class Aggregate:
    output_column: str
    function: str
    source_column: str | None


@dataclass(frozen=True, slots=True)
class Join:
    table: str
    left_column: str
    right_column: str
    cardinality: str


@dataclass(frozen=True, slots=True)
class ProviderProvenance:
    kind: Literal["local_csv", "gold"]
    safe_label: str
    data_digest: str
    query_digest: str | None
    snapshot_id: str | None


@dataclass(frozen=True, slots=True)
class DataRequest:
    table: str | None
    columns: tuple[str, ...]
    logical_types: tuple[str, ...]
    roles: Mapping[str, str]
    filters: tuple[Filter, ...]
    aggregates: tuple[Aggregate, ...]
    group_by: tuple[str, ...]
    joins: tuple[Join, ...]
    privacy_floor: int


@dataclass(frozen=True, slots=True)
class RectangularData:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    total_count: int
    excluded_count: int
    exclusion_reasons: tuple[str, ...]
    provenance: ProviderProvenance
```

The protocol and dataclasses import no NumPy, SciPy, statsmodels, ruptures, DB
driver, or pandas.

Define:

```python
class ProviderUnavailable(RuntimeError):
    def __init__(self, blocker: Blocker) -> None:
        super().__init__(blocker.message)
        self.blocker = blocker
```

- [ ] **Step 4: Implement the spec-to-request boundary**

`build_data_request` projects only policy-approved tables, columns,
aggregations, typed filters, and roles. It carries
`pii.minimum_group_count` as `privacy_floor`, and refuses any spec role absent
from the approved `PolicyContext`.

- [ ] **Step 5: Implement deterministic local CSV acquisition**

Read raw UTF-8-sig CSV with the stdlib, validate the header, stream while
enforcing row and byte ceilings, select only requested columns, and hash the
normalized header plus rows. Refuse excess data rather than truncating or
sampling.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/statistical/test_provider_contract.py tests/unit/statistical/test_local_csv_provider.py -q
```

Commit:

```bash
git add src/seshat/statistical/providers tests/unit/statistical/test_provider_contract.py tests/unit/statistical/test_local_csv_provider.py tests/fixtures/statistical/weekly_metric.csv
git commit -m "feat: add offline statistical data provider"
```

### Task 6: Compile Restricted Gold Queries and Add the Read-Only Provider

**Files:**
- Create: `src/seshat/statistical/query.py`
- Create: `src/seshat/statistical/providers/gold.py`
- Modify: `src/seshat/statistical/providers/__init__.py`
- Modify: `src/seshat/validate.py`
- Test: `tests/unit/statistical/test_query.py`
- Test: `tests/unit/statistical/test_gold_provider.py`
- Test: `tests/unit/test_validate.py`

**Interfaces:**
- Consumes `Filter`, `Aggregate`, `Join`, and `DataRequest` from Task 5.
- Produces `CompiledQuery`.
- Produces `compile_count(request, dialect) -> CompiledQuery`.
- Produces `compile_select(request, dialect) -> CompiledQuery`.
- Produces `GoldProvider(runner, dialect, limits).fetch(request)`.
- Produces `make_psycopg2_runner(dsn, *, statement_timeout_ms=None)` while
  preserving the existing one-argument call.

- [ ] **Step 1: Write injection, binding, and dialect tests**

```python
@pytest.mark.parametrize("engine", ["postgres", "sqlserver", "mysql", "snowflake"])
def test_compiler_quotes_identifiers_and_binds_values(engine: str) -> None:
    request = grouped_request(
        table="gold.fct_sales",
        response="net_amount",
        time="sale_month",
        filters=(Filter("channel", "eq", "Store"),),
    )
    compiled = compile_select(request, get_dialect(engine))
    assert "Store" not in compiled.sql
    assert compiled.params == ("Store",)
    assert compiled.sql.lstrip().upper().startswith("SELECT")


@pytest.mark.parametrize(
    "unsafe",
    ["gold.fact; DROP TABLE x", "gold.fact --", "silver.fact", "gold.fact.extra"],
)
def test_compiler_refuses_unsafe_or_non_gold_relations(unsafe: str) -> None:
    with pytest.raises(QueryRefused):
        compile_select(single_table_request(unsafe), get_dialect("postgres"))
```

Cover unapproved columns, unrestricted operators, raw expressions, unapproved
joins, incorrect cardinality, and interpolated filter values.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest tests/unit/statistical/test_query.py tests/unit/statistical/test_gold_provider.py -q
```

- [ ] **Step 3: Implement closed query dataclasses and compiler**

```python
@dataclass(frozen=True, slots=True)
class CompiledQuery:
    sql: str
    params: tuple[object, ...]
    output_columns: tuple[str, ...]
    digest: str
```

Allow only:

```python
FILTER_OPS = frozenset({"eq", "ne", "lt", "lte", "gt", "gte", "in", "is_null", "is_not_null", "is_true", "is_false"})
AGGREGATIONS = frozenset({"sum", "count", "count_rows", "distinct_count", "average", "min", "max"})
JOIN_CARDINALITIES = frozenset({"many_to_one", "one_to_one"})
```

The compiler receives preflight-approved columns and relationships. It emits
one statement beginning with `SELECT`, contains no semicolon/comment token, and
uses dialect quoting plus bound value parameters. Grouping follows the declared
observation grain and the approved metric definition.

Unsafe or unsupported requests raise:

```python
class QueryRefused(ValueError):
    def __init__(self, blocker: Blocker) -> None:
        super().__init__(blocker.message)
        self.blocker = blocker
```

- [ ] **Step 4: Add an enforceable PostgreSQL statement timeout**

Extend the existing lazy PostgreSQL factory additively:

```python
def make_psycopg2_runner(
    dsn: str, *, statement_timeout_ms: int | None = None
) -> QueryRunner:
    kwargs = (
        {"options": f"-c statement_timeout={statement_timeout_ms}"}
        if statement_timeout_ms is not None
        else {}
    )
    conn = psycopg2.connect(dsn, **kwargs)
    conn.set_session(readonly=True, autocommit=True)
    return _Psycopg2Runner(conn)
```

Test the exact `options` argument and read-only session. The CLI gold provider
initially enables live acquisition for PostgreSQL; other engines return
`unavailable` with a recovery message until they have an equally enforceable
read-only timeout. Cross-dialect compiler tests remain mandatory.

- [ ] **Step 5: Implement count-first resource enforcement**

`GoldProvider.fetch` executes the compiled count request first. If the count
exceeds `max_rows`, return `ProviderUnavailable` with the measured count and
recovery action. Otherwise execute the data query, validate returned width, and
hash the normalized SQL, parameters, and returned shape without storing row
values in provenance. It also measures normalized returned bytes and refuses an
oversized result rather than emitting a partial sample.

- [ ] **Step 6: Prove the provider emits SELECT only**

Use a fake runner recording every statement:

```python
assert fake.statements
assert all(sql.lstrip().upper().startswith("SELECT") for sql, _ in fake.statements)
assert all(";" not in sql and "--" not in sql and "/*" not in sql for sql, _ in fake.statements)
```

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/statistical/test_query.py tests/unit/statistical/test_gold_provider.py tests/unit/test_validate.py -q
```

Commit:

```bash
git add src/seshat/statistical/query.py src/seshat/statistical/providers src/seshat/validate.py tests/unit/statistical/test_query.py tests/unit/statistical/test_gold_provider.py tests/unit/test_validate.py
git commit -m "feat: add restricted gold statistical adapter"
```

### Task 7: Add the Closed Lazy Registry and Runtime Orchestrator

**Files:**
- Create: `src/seshat/statistical/registry.py`
- Create: `src/seshat/statistical/runtime.py`
- Modify: `src/seshat/statistical/contracts.py`
- Test: `tests/unit/statistical/test_registry.py`
- Test: `tests/unit/statistical/test_runtime.py`

**Interfaces:**
- Produces `MethodDescriptor`, `MethodResult`, `MethodContext`.
- Produces `METHODS`, `get_descriptor(method_id)`, `load_runner(descriptor)`.
- Produces `run_analysis(repo_root, spec, provider) -> AnalysisEvidence`.

- [ ] **Step 1: Write registry closure and lazy-import tests**

```python
def test_registry_contains_only_the_governed_catalog() -> None:
    assert set(METHODS) == {
        "describe",
        "compare_groups",
        "proportion",
        "correlate",
        "regress",
        "detect_anomalies",
        "detect_change_points",
        "forecast",
    }


def test_importing_registry_does_not_import_numerical_libraries() -> None:
    script = "import sys; import seshat.statistical.registry; print(sorted(set(sys.modules) & {'numpy','scipy','statsmodels','ruptures'}))"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"
```

Add a rejection test showing a descriptor module outside
`seshat.statistical.methods` cannot load.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest tests/unit/statistical/test_registry.py tests/unit/statistical/test_runtime.py -q
```

- [ ] **Step 3: Define closed string descriptors**

```python
@dataclass(frozen=True, slots=True)
class MethodDescriptor:
    method_id: str
    version: str
    module: str
    function: str
    required_roles: frozenset[str]
    optional_dependency: str
```

The table uses literal internal modules/functions. `load_runner` imports only
after policy and provider preflight and verifies the resolved callable comes
from `seshat.statistical.methods`.

- [ ] **Step 4: Define the method boundary types**

```python
@dataclass(frozen=True, slots=True)
class MethodContext:
    spec: AnalysisSpec
    policy: PolicyContext
    data: RectangularData


@dataclass(frozen=True, slots=True)
class MethodResult:
    estimates: tuple[Estimate, ...] = ()
    intervals: tuple[Interval, ...] = ()
    tests: tuple[TestStatistic, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    warnings: tuple[str, ...] = ()
    interpretation_cautions: tuple[str, ...] = ()


class AnalysisWithheld(RuntimeError):
    def __init__(self, blockers: tuple[Blocker, ...]) -> None:
        super().__init__("; ".join(item.message for item in blockers))
        self.blockers = blockers
```

- [ ] **Step 5: Implement outcome-safe runtime orchestration**

`run_analysis` performs:

```python
decision = evaluate_policy(repo_root, spec)
if not decision.allowed:
    return refused_evidence(spec, decision.blockers)
descriptor = get_descriptor(spec.method.method_id)
data = provider.fetch(build_data_request(spec, decision.context))
result = load_runner(descriptor)(MethodContext(spec, decision.context, data))
return computed_evidence(spec, data.provenance, descriptor, result)
```

Convert `SpecRefused`, a disallowed `PolicyDecision`, `AnalysisWithheld`,
`ProviderUnavailable`, `ImportError`, and unexpected exceptions into the exact
outcomes. Redact unexpected messages and attach an invocation ID. Never catch
`KeyboardInterrupt` or `SystemExit`.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/statistical/test_registry.py tests/unit/statistical/test_runtime.py -q
```

Commit:

```bash
git add src/seshat/statistical/contracts.py src/seshat/statistical/registry.py src/seshat/statistical/runtime.py tests/unit/statistical/test_registry.py tests/unit/statistical/test_runtime.py
git commit -m "feat: add governed statistical runtime"
```

### Task 8: Implement Finite Numeric Preparation and Descriptive Statistics

**Files:**
- Create: `src/seshat/statistical/methods/__init__.py`
- Create: `src/seshat/statistical/methods/common.py`
- Create: `src/seshat/statistical/methods/descriptive.py`
- Test: `tests/unit/statistical/methods/test_common.py`
- Test: `tests/unit/statistical/methods/test_descriptive.py`

**Interfaces:**
- Produces `numeric_role(context, role) -> NumericSample`.
- Produces `finite_array(values, role) -> numpy.ndarray`.
- Produces `run_describe(context) -> MethodResult`.

- [ ] **Step 1: Write numerical preparation and oracle tests**

Mark numerical tests with `pytestmark = pytest.mark.statistics`.

```python
def test_describe_matches_numpy_and_scipy() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    result = run_describe(context_for(values, outlier_rule="mad"))
    assert estimate(result, "mean") == pytest.approx(np.mean(values))
    assert estimate(result, "std_sample") == pytest.approx(np.std(values, ddof=1))
    assert estimate(result, "skewness") == pytest.approx(stats.skew(values, bias=False))
    assert estimate(result, "kurtosis") == pytest.approx(stats.kurtosis(values, bias=False))
```

Add exact tests for median, variance, quantiles, IQR, MAD, minimum, maximum,
missing/excluded/distinct counts, grouped summaries, and declared
sample-versus-population dispersion.

For grouped output, include a group below `privacy_floor` and assert its label
and statistics are absent while a suppression diagnostic reports only the
number of suppressed groups.

- [ ] **Step 2: Add edge-case tests**

Cover empty input, all missing, singleton sample, constant sample, non-numeric
value, `NaN`, infinity, a group below the minimum count, and MAD equal to zero.
Undefined statistics must be `null` with a diagnostic or a `withheld` result,
never JSON non-finite text.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_common.py tests/unit/statistical/methods/test_descriptive.py -q
```

- [ ] **Step 4: Implement strict finite conversion and missingness**

```python
@dataclass(frozen=True, slots=True)
class NumericSample:
    values: object
    total_count: int
    retained_count: int
    excluded_count: int
    exclusion_reasons: tuple[str, ...]
```

Import NumPy inside the functions. Honor only `complete_case`, `pairwise`, and
`fail`. Record total, excluded, and retained counts. Convert `Decimal` and text
with explicit errors; reject booleans as numeric observations.

`safe_groups` suppresses every group below `DataRequest.privacy_floor` before
method execution. Evidence may report the suppressed-group count, never the
suppressed labels or values. All grouped methods reuse this helper.

- [ ] **Step 5: Implement descriptive and robust outlier summaries**

Use NumPy/SciPy primitives and explicit `ddof`. IQR outliers use declared
`k * IQR`; robust z-scores use `0.6744897501960817 * (x - median) / MAD`.
When MAD is zero, report a diagnostic and no robust outlier classification.
Never call an extreme value erroneous.

- [ ] **Step 6: Add translation/scale property tests**

For positive `a` and finite `b`, assert median/mean translate by `b`, dispersion
scales by `a`, and the IQR/MAD outlier membership is unchanged.

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_common.py tests/unit/statistical/methods/test_descriptive.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods tests/unit/statistical/methods/test_common.py tests/unit/statistical/methods/test_descriptive.py
git commit -m "feat: add governed descriptive statistics"
```

### Task 9: Implement Resampling, Multiplicity, and Effect-Size Primitives

**Files:**
- Create: `src/seshat/statistical/methods/inference.py`
- Test: `tests/unit/statistical/methods/test_inference.py`

**Interfaces:**
- Produces `bootstrap_interval(samples, statistic, level, seed, paired=False)`.
- Produces `adjust_pvalues(values, method) -> tuple[float, ...]`.
- Produces `hedges_g`, `paired_standardized_change`, `rank_biserial`,
  `omega_squared`, and `epsilon_squared`.

- [ ] **Step 1: Write direct SciPy oracle tests**

```python
def test_bootstrap_interval_is_seeded_and_matches_scipy() -> None:
    sample = np.array([2.0, 4.0, 5.0, 8.0, 9.0])
    expected = stats.bootstrap(
        (sample,),
        np.mean,
        method="BCa",
        confidence_level=0.95,
        n_resamples=9_999,
        rng=np.random.default_rng(1729),
    ).confidence_interval
    actual = bootstrap_interval((sample,), np.mean, "0.95", 1729)
    assert actual.low == pytest.approx(expected.low)
    assert actual.high == pytest.approx(expected.high)
```

Test Holm and Benjamini-Hochberg against hand-calculated vectors. Test each
effect-size formula on a small exact sample.

- [ ] **Step 2: Add degeneracy and bounds tests**

Cover constant bootstrap distributions, too-small BCa samples, zero pooled
variance, zero paired-difference variance, invalid p-values, empty vectors, and
resample counts above the schema maximum. A fixed seed must produce byte-identical
interval strings on repeated runs.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_inference.py -q
```

- [ ] **Step 4: Implement inference primitives**

Use SciPy bootstrap with `BCa`, a fixed `numpy.random.Generator`, and bounded
resamples. Implement Holm and Benjamini-Hochberg explicitly with stable
index-order restoration and values clipped to `[0, 1]`. Return typed finite
results or raise `AnalysisWithheld` with a concrete diagnostic.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_inference.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/inference.py tests/unit/statistical/methods/test_inference.py
git commit -m "feat: add statistical uncertainty primitives"
```

### Task 10: Implement Governed Group Comparisons

**Files:**
- Create: `src/seshat/statistical/methods/groups.py`
- Test: `tests/unit/statistical/methods/test_groups.py`

**Interfaces:**
- Produces `run_compare_groups(context) -> MethodResult`.
- Uses Task 9 effect sizes and p-value corrections.

- [ ] **Step 1: Write method-by-method oracle tests**

Parametrize over:

```python
CASES = {
    "welch_t": stats.ttest_ind,
    "paired_t": stats.ttest_rel,
    "mann_whitney": stats.mannwhitneyu,
    "wilcoxon": stats.wilcoxon,
    "welch_anova": stats.f_oneway,
    "kruskal_wallis": stats.kruskal,
}
```

For Welch ANOVA use SciPy's unequal-variance option available in the pinned
version. Assert statistic, p-value, sample counts, effect-size name/value,
confidence interval where supported, and correction metadata.

- [ ] **Step 2: Write pairing and multiplicity safeguards**

Prove paired methods require a declared identifier role, reject duplicated or
unmatched pair IDs, and preserve pair alignment. Prove group order reverses the
signed effect while preserving two-sided p-values. Prove multiple post-hoc
comparisons cannot run with `correction="none"`.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_groups.py -q
```

- [ ] **Step 4: Implement explicit dispatch without automatic test selection**

Use a literal dispatch table keyed by the schema enum. Do not run a normality
test to choose a branch. Require two groups for two-sample methods and at least
three for omnibus methods. Report:

- Hedges' g for Welch t;
- paired standardized change for paired t;
- rank-biserial correlation for Mann-Whitney/Wilcoxon;
- omega-squared for Welch ANOVA; and
- epsilon-squared for Kruskal-Wallis.

- [ ] **Step 5: Implement closed post-hoc comparisons**

Only run the declared pair list, reuse the selected compatible two-group method,
and apply the declared Holm or Benjamini-Hochberg correction across the complete
family. Record raw and adjusted p-values.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_groups.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/groups.py tests/unit/statistical/methods/test_groups.py
git commit -m "feat: add governed group comparisons"
```

### Task 11: Implement Proportion Evidence

**Files:**
- Create: `src/seshat/statistical/methods/proportions.py`
- Test: `tests/unit/statistical/methods/test_proportions.py`

**Interfaces:**
- Produces `run_proportion(context) -> MethodResult`.

- [ ] **Step 1: Write interval and comparison oracle tests**

```python
def test_wilson_interval_matches_binomtest() -> None:
    result = run_proportion(proportion_context(successes=42, trials=100, interval="wilson"))
    expected = stats.binomtest(42, 100).proportion_ci(method="wilson")
    assert interval(result, "proportion").low == pytest.approx(expected.low)
    assert interval(result, "proportion").high == pytest.approx(expected.high)
```

Add exact tests for binomial exact intervals, two-proportion comparison, risk
difference, risk ratio, odds ratio, chi-square, and Fisher exact.

- [ ] **Step 2: Write denominator and sparse-cell safeguards**

Cover zero denominator, successes greater than trials, missing-status policy,
minimum denominator, sparse expected cells, zero cells in ratios, and Haldane-
Anscombe correction only when explicitly selected. Chi-square with violated
expected-count diagnostics must be withheld rather than silently replaced by
Fisher.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_proportions.py -q
```

- [ ] **Step 4: Implement explicit proportion methods**

Use `scipy.stats.binomtest`, `chi2_contingency`, and `fisher_exact`. Calculate
risk difference, log-scale risk-ratio/odds-ratio intervals, and diagnostic cell
counts. Bind numerator and denominator roles from the approved specification;
never infer them from column names.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_proportions.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/proportions.py tests/unit/statistical/methods/test_proportions.py
git commit -m "feat: add governed proportion evidence"
```

### Task 12: Implement Correlation Evidence with Non-Causality Guardrails

**Files:**
- Create: `src/seshat/statistical/methods/correlation.py`
- Test: `tests/unit/statistical/methods/test_correlation.py`

**Interfaces:**
- Produces `run_correlate(context) -> MethodResult`.

- [ ] **Step 1: Write Pearson, Spearman, interval, and correction tests**

Compare coefficients and p-values directly with `scipy.stats.pearsonr` and
`scipy.stats.spearmanr`. Bootstrap paired rows for intervals. Test a family of
three correlations with Holm and Benjamini-Hochberg corrections.

```python
assert "association" in result.interpretation_cautions[0].lower()
assert "caus" in result.interpretation_cautions[0].lower()
```

- [ ] **Step 2: Write missing-pair, constant, and multiplicity safeguards**

Test pairwise versus complete-case policies, unequal column lengths, constant
input warnings, too few pairs, duplicate requested pairs, and correction
required for more than one pair.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_correlation.py -q
```

- [ ] **Step 4: Implement explicit correlation dispatch**

Use only the declared coefficient. Record paired sample count, raw/adjusted
p-value, seeded paired bootstrap interval, missing-pair exclusions, and the
mandatory association-not-causation caution. Never label correlation as a
driver or effect.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_correlation.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/correlation.py tests/unit/statistical/methods/test_correlation.py
git commit -m "feat: add governed correlation evidence"
```

### Task 13: Implement Associational Regression and Diagnostics

**Files:**
- Create: `src/seshat/statistical/methods/regression.py`
- Test: `tests/unit/statistical/methods/test_regression.py`

**Interfaces:**
- Produces `run_regress(context) -> MethodResult`.
- Supports families `ols`, `logit`, `poisson`, and `negative_binomial`.

- [ ] **Step 1: Write direct statsmodels oracle tests**

Use small deterministic synthetic datasets and compare coefficients, robust
standard errors, confidence intervals, fitted family, and fit statistics with
direct statsmodels calls:

```python
expected = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HC3")
actual = run_regress(regression_context(y, x, family="ols", covariance="HC3"))
assert estimate(actual, "coefficient:x") == pytest.approx(expected.params[1])
assert estimate(actual, "standard_error:x") == pytest.approx(expected.bse[1])
```

Add equivalent GLM tests for Binomial, Poisson, and NegativeBinomial families.

- [ ] **Step 2: Write diagnostics and refusal tests**

Cover singular design, perfect separation, non-binary logistic response,
negative count response, too few residual degrees of freedom, excessive
predictor count, near-zero variance predictors, high VIF, influential points,
non-finite fitted values, and missing response/predictor roles.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_regression.py -q
```

- [ ] **Step 4: Implement closed family dispatch**

Import statsmodels inside `run_regress`. Add an intercept unless the spec
explicitly disables it. Select only the declared family/covariance. Emit
coefficient estimates, intervals, standard errors, sample/exclusion counts,
AIC/deviance or R-squared as family-appropriate observed measures, and no
stepwise model search.

- [ ] **Step 5: Implement diagnostics**

For OLS record residual normality, heteroskedasticity, influence, condition
number, and VIF observations. For GLMs record convergence, deviance, Pearson
residual, separation/dispersion warnings as applicable. Diagnostics are
categorical facts, never a rolled-up score.

- [ ] **Step 6: Enforce associational language**

Every regression result contains:

```text
Associational model only; coefficients do not establish causality.
```

Reject a specification question or requested label containing causal verbs
such as `causes`, `caused`, `impact of`, or `drives` unless the review artifact
rewrites it as an association question.

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_regression.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/regression.py tests/unit/statistical/methods/test_regression.py
git commit -m "feat: add governed associational regression"
```

### Task 14: Validate Time Indexes and Detect Seasonality-Aware Anomalies

**Files:**
- Create: `src/seshat/statistical/methods/time_index.py`
- Create: `src/seshat/statistical/methods/anomaly.py`
- Test: `tests/unit/statistical/methods/test_time_index.py`
- Test: `tests/unit/statistical/methods/test_anomaly.py`

**Interfaces:**
- Produces `RegularSeries`, `regular_series(context)`, `rolling_origins(...)`.
- Produces `run_detect_anomalies(context) -> MethodResult`.

- [ ] **Step 1: Write time-index refusal tests**

Test duplicated, unsorted, missing, irregular, timezone-mixed, partial, and
unparseable timestamps. The normalized result must sort only after proving
there are no duplicates, preserve the declared frequency, and state any
excluded partial period.

- [ ] **Step 2: Write no-self-baseline and seasonal oracle tests**

Construct a deterministic monthly series with one injected residual spike.
Assert:

```python
assert baseline_for(result, spike_index).source_end == spike_index - 1
assert anomaly_at(result, spike_index) is True
```

Construct a recurring December peak and assert it is seasonal, not anomalous.
Compare STL decomposition components with
`statsmodels.tsa.seasonal.STL(..., robust=True)`.

- [ ] **Step 3: Write insufficiency and degeneracy tests**

Cover fewer than two seasonal cycles, zero residual MAD, gaps, a partial final
period, one-sided thresholds, exact threshold boundary, and a spike inside the
training portion of a later baseline.

- [ ] **Step 4: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_time_index.py tests/unit/statistical/methods/test_anomaly.py -q
```

- [ ] **Step 5: Implement regular-series normalization**

```python
@dataclass(frozen=True, slots=True)
class RegularSeries:
    timestamps: tuple[str, ...]
    values: object
    frequency: str
    seasonal_period: int
    excluded_partial_period: str | None
```

Parse the declared frequency, verify uniqueness/contiguity, apply the approved
partial-period policy, and require `minimum_data.seasonal_cycles`. Produce
rolling origins whose training endpoint is strictly before every evaluated
point.

- [ ] **Step 6: Implement anomaly modes**

`trailing_mad` uses prior-window median/MAD. `seasonal_mad` fits robust STL on
the permitted historical window and applies the declared MAD threshold to the
residual. Record baseline window, center, dispersion, threshold, seasonal
period, and evaluated point. Return `withheld` when the baseline cannot support
the claim.

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_time_index.py tests/unit/statistical/methods/test_anomaly.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/time_index.py src/seshat/statistical/methods/anomaly.py tests/unit/statistical/methods/test_time_index.py tests/unit/statistical/methods/test_anomaly.py
git commit -m "feat: add seasonality-aware anomaly evidence"
```

### Task 15: Implement Offline Change-Point Detection

**Files:**
- Create: `src/seshat/statistical/methods/changepoint.py`
- Test: `tests/unit/statistical/methods/test_changepoint.py`

**Interfaces:**
- Produces `run_detect_change_points(context) -> MethodResult`.

- [ ] **Step 1: Write ruptures oracle and reproducibility tests**

Use a piecewise constant synthetic series with known regime boundaries.
Compare exact breakpoint indexes with:

```python
expected = rpt.Pelt(model="l2", min_size=6, jump=1).fit(values).predict(pen=10)
actual = run_detect_change_points(change_context(values, model="l2", penalty="10", min_segment=6))
assert breakpoint_indexes(actual) == tuple(expected[:-1])
```

Test the explicitly declared fixed-count dynamic-programming route separately.

- [ ] **Step 2: Write boundary tests**

Cover absent optional dependency, unsorted/irregular time, segment shorter than
`min_segment`, excessive candidate complexity, terminal-length sentinel removal,
no detected changes, and non-finite values. Every result must say candidate
regime change, never event cause.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_changepoint.py -q
```

- [ ] **Step 4: Implement closed ruptures dispatch**

Support PELT with declared penalty and dynamic programming with declared change
count. Support only schema-enumerated models. Remove ruptures' terminal length
sentinel, translate indexes to time labels, and record library version,
algorithm, model, penalty/count, minimum segment, and jump.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_changepoint.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/changepoint.py tests/unit/statistical/methods/test_changepoint.py
git commit -m "feat: add governed change-point evidence"
```

### Task 16: Implement Forecast Baselines, Rolling-Origin Evaluation, and Intervals

**Files:**
- Create: `src/seshat/statistical/methods/forecast.py`
- Test: `tests/unit/statistical/methods/test_forecast.py`
- Create: `tests/fixtures/statistical/seasonal_series.csv`

**Interfaces:**
- Produces `ForecastCandidate`, `BacktestFold`, `ForecastEvaluation`.
- Produces `mase`, `smape`, `evaluate_candidate`, and `run_forecast`.

- [ ] **Step 1: Write metric and baseline tests**

Test MASE and sMAPE against hand-calculated vectors. Test naive and seasonal-
naive forecasts exactly. Require a seasonal-naive baseline whenever `period > 1`.

```python
def test_seasonal_naive_repeats_the_last_complete_cycle() -> None:
    values = np.arange(1.0, 25.0)
    forecast = seasonal_naive(values, period=12, horizon=3)
    assert forecast.tolist() == [13.0, 14.0, 15.0]
```

- [ ] **Step 2: Write no-future-leakage tests**

Instrument candidate fit calls and assert every fold receives only
`series[:cutoff]`. Mutate observations after a fold cutoff and prove that fold's
forecast and metrics remain byte-identical.

- [ ] **Step 3: Write statsmodels oracle tests**

For additive ETS/state-space variants, compare fitted forecasts and interval
bounds with the same pinned statsmodels class and parameters. Cover trend,
damped trend, additive seasonality, and a no-seasonality variant.

- [ ] **Step 4: Write model-governance edge tests**

Cover insufficient cycles, horizon over schema limit, fewer than two backtest
folds, candidate fit failure, residual autocorrelation warning, zero MASE
denominator, zeros in sMAPE, nonpositive data with a requested multiplicative
variant, baseline not beaten, and all candidates failed.

- [ ] **Step 5: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_forecast.py -q
```

- [ ] **Step 6: Implement rolling-origin evaluation**

```python
@dataclass(frozen=True, slots=True)
class ForecastCandidate:
    candidate_id: str
    trend: Literal["add", "none"]
    damped: bool
    seasonal: Literal["add", "none"]
    period: int


@dataclass(frozen=True, slots=True)
class BacktestFold:
    cutoff_index: int
    horizon: int
    actual: tuple[str, ...]
    predicted: tuple[str, ...]
    mase: str | None
    smape: str | None


@dataclass(frozen=True, slots=True)
class ForecastEvaluation:
    candidate_id: str
    folds: tuple[BacktestFold, ...]
    mean_mase: str | None
    mean_smape: str | None
    diagnostics: tuple[Diagnostic, ...]
    failure: str | None
```

Generate deterministic folds from the declared initial window, step, horizon,
and maximum fold count. Compute MASE and sMAPE per fold and aggregate them with
the declared criterion. Record every candidate, every fold cutoff, metric, and
failure; no candidate disappears from evidence.

- [ ] **Step 7: Implement the closed candidate family**

Support:

- `naive`;
- `seasonal_naive`;
- `ets_add`;
- `ets_add_trend`;
- `ets_add_damped`; and
- `ets_add_seasonal`.

Use statsmodels state-space prediction APIs for intervals. Fit the selected
declared candidate to the full permitted series only after backtest ranking.
Selection uses the declared metric and stable tie order from the specification.

- [ ] **Step 8: Enforce baseline and diagnostics posture**

If the selected model does not beat the declared baseline, retain its forecast
but emit a warning that no endorsement is warranted. If diagnostics or history
invalidate forecasting, return `withheld`. Always emit prediction interval
method/level and residual diagnostics.

- [ ] **Step 9: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/unit/statistical/methods/test_forecast.py -q
```

Commit:

```bash
git add src/seshat/statistical/methods/forecast.py tests/unit/statistical/methods/test_forecast.py tests/fixtures/statistical/seasonal_series.csv
git commit -m "feat: add governed forecast evidence"
```

### Task 17: Expose the Lazy `seshat analyze` Command Family

**Files:**
- Create: `src/seshat/cli/parser_analysis.py`
- Create: `src/seshat/cli/commands/analyze.py`
- Modify: `src/seshat/cli/parser.py`
- Modify: `src/seshat/cli/__init__.py`
- Test: `tests/unit/test_cli_analyze.py`
- Test: `tests/unit/test_cli_context.py`
- Test: `tests/unit/test_cli_help_snapshot.py`

**Interfaces:**
- Produces commands:
  - `seshat analyze validate --spec PATH --repo ROOT --format text|json`
  - `seshat analyze run --spec PATH --repo ROOT --provider local_csv|gold --input PATH --format text|json`
  - `seshat analyze render --evidence PATH --repo ROOT --format text|json`
- Produces handler `analyze_main(args) -> int`.

- [ ] **Step 1: Write parser and lazy-dispatch tests**

```python
def test_analyze_help_exposes_exact_closed_family(capsys) -> None:
    parser = _build_parser(prog="seshat")
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["analyze", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert all(name in out for name in ("validate", "run", "render"))


def test_cli_import_does_not_load_statistics() -> None:
    import seshat.cli
    assert "numpy" not in sys.modules
    assert "scipy" not in sys.modules
    assert "statsmodels" not in sys.modules
    assert "ruptures" not in sys.modules
```

- [ ] **Step 2: Write exact outcome/exit-code tests**

Use monkeypatched runtime outputs and assert:

```python
EXPECTED = {
    "computed": 0,
    "withheld": 1,
    "refused": 2,
    "failed": 3,
    "unavailable": 4,
}
```

Text output must include analysis ID, outcome, evidence path when written, and
recovery actions. JSON output must be one stable object. Expected failures emit
no traceback or secret.

- [ ] **Step 3: Run and confirm failure**

Run:

```powershell
python -m pytest tests/unit/test_cli_analyze.py tests/unit/test_cli_context.py tests/unit/test_cli_help_snapshot.py -q
```

- [ ] **Step 4: Add the argparse-only family**

Follow `parser_dbt.py`: keep parser imports stdlib-only, require subcommands,
use `--repo`, `--format`, and `--spec` consistently, and make `--input`
required only for `local_csv`. `gold` resolves DB config from `.env`; secrets
never appear in arguments or output.

- [ ] **Step 5: Add lazy dispatch**

In `_DISPATCH`:

```python
"analyze": _lazy(".commands.analyze", "analyze_main"),
```

In `analyze_main`, delay imports of `seshat.statistical` until after command
selection. Reuse workspace `.env`, `_current_engine`, `get_dialect`,
`_ensure_driver`, `_make_runner`, `_extra_install_hint`, and dialect redaction.

- [ ] **Step 6: Implement validate, run, and render flows**

- `validate` loads the spec and runs policy without acquiring data.
- `run` selects local or gold provider, runs the engine, atomically writes
  evidence/review for any schema-valid outcome, and prints paths.
- `render` validates existing evidence and rewrites only the review artifact.

An invalid spec with no safe output path returns a machine response to stdout
but does not invent a committed evidence location.

- [ ] **Step 7: Verify and commit**

Run:

```powershell
python -m pytest tests/unit/test_cli_analyze.py tests/unit/test_cli_context.py tests/unit/test_cli_help_snapshot.py -q
```

Commit:

```bash
git add src/seshat/cli/parser_analysis.py src/seshat/cli/commands/analyze.py src/seshat/cli/parser.py src/seshat/cli/__init__.py tests/unit/test_cli_analyze.py tests/unit/test_cli_context.py tests/unit/test_cli_help_snapshot.py
git commit -m "feat: expose governed statistical analysis CLI"
```

### Task 18: Exercise the End-to-End Flow with Synthetic Evidence and Human Review

**Files:**
- Create: `tests/fixtures/statistical/full_flow/mappings/sample_orders/readiness-status.yaml`
- Create: `tests/fixtures/statistical/full_flow/mappings/sample_orders/metrics/TotalValue.yaml`
- Create: `tests/fixtures/statistical/full_flow/mappings/sample_orders/analyses/weekly_signal.analysis.yaml`
- Create: `tests/fixtures/statistical/full_flow/data/weekly_metric.csv`
- Create: `tests/integration/test_statistical_artifact_flow.py`
- Create: `docs/worked-examples/statistical-evidence-engine.md`

**Interfaces:**
- Exercises `load_analysis_spec -> evaluate_policy -> LocalCsvProvider -> run_analysis -> write_evidence -> render_review`.
- Produces a domain-neutral worked example with review state pending.

- [ ] **Step 1: Write the failing full-flow integration test**

```python
@pytest.mark.statistics
def test_synthetic_full_flow_writes_valid_derived_evidence(tmp_path: Path) -> None:
    root = copy_fixture_repo(tmp_path, "full_flow")
    rc = main([
        "analyze", "run",
        "--repo", str(root),
        "--spec", "mappings/sample_orders/analyses/weekly_signal.analysis.yaml",
        "--provider", "local_csv",
        "--input", "data/weekly_metric.csv",
        "--format", "json",
    ])
    assert rc == 0
    evidence = load_json(root / "mappings/sample_orders/analyses/weekly_signal.evidence.json")
    assert validate_json_contract(evidence, EVIDENCE_SCHEMA) == []
    assert evidence["authority"] == "derived-evidence-only"
    assert evidence["review_state"] == "pending"
    assert evidence["readiness_effect"] == "none; named-human approval required"
```

Snapshot readiness bytes before and after and assert equality.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest -m statistics tests/integration/test_statistical_artifact_flow.py -q
```

- [ ] **Step 3: Create the synthetic governed fixture**

Use a fictional sample-orders subject, 36 completed weekly observations, no PII,
an approved additive metric contract, gold/semantic pass evidence, and an
explicit metric-owner approval. Keep all values synthetic and generic.

- [ ] **Step 4: Write the worked example**

Document the exact commands, normalized spec, evidence interpretation, why
`computed` is not approval, and how the named human completes the separate
review. Cite the fixture rather than copying client-specific data.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
python -m pytest -m statistics tests/integration/test_statistical_artifact_flow.py -q
```

Commit:

```bash
git add tests/fixtures/statistical/full_flow tests/integration/test_statistical_artifact_flow.py docs/worked-examples/statistical-evidence-engine.md
git commit -m "test: prove the governed statistical evidence flow"
```

### Task 19: Reconcile Knowledge Routing, Architecture, Packaging, and Public Bundles

**Files:**
- Create: `docs/architecture/statistical-evidence-engine.md`
- Modify: `skills/bi-analyst-knowledge/SKILL.md`
- Modify: `skills/bi-analyst-knowledge/INDEX.md`
- Create: `skills/bi-analyst-knowledge/statistical-evidence-workflow.md`
- Modify: `skills/bi-analyst-knowledge/framing-signal-vs-noise.md`
- Modify: `skills/bi-analyst-knowledge/framing-trend-anomaly.md`
- Modify: `COMPASS.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/roadmap/roadmap.md`
- Modify: `docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md`
- Modify: `docs/install/user-install.md`
- Modify: `docs/install/agent-install.md`
- Modify: `docs/install/developer-install.md`
- Modify: `docs/install/client-quickstart.md`
- Modify: `docs/install/support-matrix.md`
- Modify: `docs/capabilities/capabilities.yaml`
- Modify: `docs/quality/status-claims.yaml`
- Modify: `distribution/public-knowledge-allowlist.yaml`
- Regenerate: `integrations/claude-code/seshat-bi/`
- Regenerate: `integrations/codex/seshat-bi/`
- Test: `tests/contract/test_statistical_documentation.py`
- Test: `tests/contract/test_public_knowledge_allowlist.py`
- Test: `tests/contract/test_generated_agent_bundles.py`

**Interfaces:**
- Routes statistical requests from the analyst knowledge layer to
  `seshat analyze`.
- Declares the Product Module / Database Adapter authority split.
- Publishes the workflow through generated Claude and Codex bundles.

- [ ] **Step 1: Write documentation and routing contract tests**

```python
def test_active_docs_route_governed_statistics_instead_of_declaring_them_absent() -> None:
    analyst = (ROOT / "skills/bi-analyst-knowledge/SKILL.md").read_text(encoding="utf-8")
    assert "statistical-evidence-workflow.md" in analyst
    assert "seshat analyze" in analyst
    assert "no regression, forecasting" not in analyst.lower()


def test_install_docs_publish_exact_pinned_statistics_commands() -> None:
    user = (ROOT / "docs/install/user-install.md").read_text(encoding="utf-8")
    assert 'pipx install "seshat-bi[stats]"' in user
    assert 'numpy==2.5.1' in user
    assert 'scipy==1.18.0' in user
    assert 'statsmodels==0.14.6' in user
```

Add tests for capability state, schema force-includes, workflow allowlist
entries, architecture authority wording, and changelog supersession.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m pytest tests/contract/test_statistical_documentation.py -q
```

- [ ] **Step 3: Write the architecture and agent workflow**

The architecture doc fills both authority declarations:

- statistical core: Product Module, execution-capable locally, derived evidence;
- gold provider: read-only Execution Adapter, gold-only `SELECT`, no truth creation.

It also publishes the exact eight method IDs, their required roles, supported
parameters, minimum-data behavior, diagnostics, dependency extra, outcome
semantics, and the PostgreSQL-only initial live-adapter boundary.

`statistical-evidence-workflow.md` routes:

1. confirm the decision question and approved metric;
2. validate readiness/contract preconditions;
3. draft the committed analysis spec without self-approval;
4. run `seshat analyze validate`;
5. run with local or gold provider;
6. inspect evidence and blockers;
7. stop for named-human review;
8. allow the narrative brief to cite only accepted review evidence.

- [ ] **Step 4: Reconcile every active out-of-scope statement**

Replace current universal exclusions with the precise boundary: governed methods
are available through the engine; knowledge cards do not compute them; autonomous
ML/deployment and causal claims remain excluded. Keep historical changelog and
historical rejected-idea records unchanged, then add a new changelog entry stating
the superseding capability.

- [ ] **Step 5: Update install, dependency, capability, and status surfaces**

Document:

```text
pipx install "seshat-bi[stats]"
pipx inject seshat-bi --force "numpy==2.5.1" "scipy==1.18.0" "statsmodels==0.14.6"
pipx inject seshat-bi --force "ruptures==1.1.10"
```

Add one shipped capability for the statistical core and one shipped read-only
gold adapter, both locally verified and `not-stage-scoped`. Add a status claim
anchored on the architecture doc and runtime package.

- [ ] **Step 6: Add the workflow file to the public allowlist**

Map the canonical source to:

```text
knowledge/bi-analyst-knowledge/statistical-evidence-workflow.md
```

for both Claude and Codex. Update existing allowlisted analyst files from their
canonical sources only.

- [ ] **Step 7: Regenerate bundles rather than hand-editing integrations**

Run:

```powershell
python scripts/export_agent_bundles.py
python scripts/export_agent_bundles.py --check
```

- [ ] **Step 8: Verify and commit**

Run:

```powershell
python -m pytest tests/contract/test_statistical_documentation.py tests/contract/test_public_knowledge_allowlist.py tests/contract/test_generated_agent_bundles.py -q
python scripts/export_agent_bundles.py --check
```

Commit:

```bash
git add docs skills COMPASS.md README.md CHANGELOG.md distribution/public-knowledge-allowlist.yaml integrations/claude-code/seshat-bi integrations/codex/seshat-bi tests/contract/test_statistical_documentation.py
git commit -m "docs: publish governed statistical analysis workflow"
```

### Task 20: Add Optional Live Proof and Complete the Acceptance Audit

**Files:**
- Create: `tests/live_db/test_statistical_adapter.py`
- Modify: `docs/worked-examples/statistical-evidence-engine.md`
- Modify: `docs/capabilities/capabilities.yaml` only if verification changes the recorded state
- Modify: `CHANGELOG.md` only for findings discovered during verification

**Interfaces:**
- Proves live gold acquisition when the DB/statistics environment is available.
- Produces the final requirement-by-requirement verification record in test output
  and the worked-example live-boundary section.

- [ ] **Step 1: Write the optional live PostgreSQL smoke test**

Using the existing `live_db` testcontainers fixture, materialize a synthetic gold
table and execute a governed `describe` analysis through `GoldProvider`. Assert:

```python
assert evidence.outcome is Outcome.COMPUTED
assert evidence.provider["kind"] == "gold"
assert evidence.input_count == expected_rows
assert fake_or_captured_sql_is_select_only()
```

Also assert the runner session is read-only and no statement contains DDL/DML.
Mark the test `live_db` and `statistics`.

- [ ] **Step 2: Run focused non-live verification**

Run:

```powershell
python -m pytest tests/contract/test_statistical_schemas.py tests/contract/test_statistical_package_contract.py tests/contract/test_statistical_documentation.py -q
python -m pytest -m statistics tests/unit/statistical tests/integration/test_statistical_artifact_flow.py -q
python -m ruff format --check src tests scripts
python -m ruff check src tests scripts
```

Expected: every command passes with no skipped statistical method.

- [ ] **Step 3: Run the live boundary or record honest deferral**

With extras and a live harness:

```powershell
python -m pytest -m "live_db and statistics" tests/live_db/test_statistical_adapter.py -q
```

If Docker, the DB driver, or a DSN is unavailable, retain:

```text
[PENDING LIVE PROFILE]
Enable with: pip install -e ".[dev,stats,stats-change,db,livetest]"
```

in the worked example. Do not claim a live pass.

- [ ] **Step 4: Run repository-wide gates**

Run:

```powershell
python -m pytest -m unit
python -m pytest -m statistics
python scripts/dep_coresolve.py --check
python scripts/export_agent_bundles.py --check
seshat check
python -m pytest
```

Interpret `seshat check` exit 0 as static evidence only; it is not statistical
correctness or live-DB proof.

- [ ] **Step 5: Audit all fourteen design acceptance criteria**

Create a temporary checklist outside tracked source and point each criterion in
Section 19 of the design spec to:

- exact schema/template paths;
- provider isolation and adapter tests;
- every method's oracle/edge/property test;
- evidence schema and golden result;
- refusal/security tests;
- forecast leakage tests;
- CLI tests;
- human review artifact;
- documentation searches;
- generated bundle checks;
- full-flow synthetic example; and
- live evidence or the explicit pending marker.

Any missing or indirect evidence means the feature remains incomplete and the
corresponding task is reopened.

- [ ] **Step 6: Commit live-proof or verification corrections**

If the live test/document changed:

```bash
git add tests/live_db/test_statistical_adapter.py docs/worked-examples/statistical-evidence-engine.md docs/capabilities/capabilities.yaml CHANGELOG.md
git commit -m "test: verify statistical analysis acceptance"
```

If no tracked correction is needed, do not create an empty commit.

## Spec Coverage Map

| Design section | Implementation evidence |
|---|---|
| 1-3 context, goals, non-goals | Global constraints; Tasks 17 and 19 |
| 4 readiness placement | Task 4 policy matrix; Task 18 readiness immutability |
| 5 authority classification | Tasks 5-6 separation; Task 19 architecture contract |
| 6 architecture | Tasks 2-7 |
| 7 committed artifacts | Tasks 2-3 and 18 |
| 8 analysis specification | Task 2 schemas, loader, and method variants |
| 9 evidence contract | Task 3 schema/serialization; Task 18 full-flow validation |
| 10 outcomes and CLI | Tasks 7 and 17 |
| 11.1 describe | Task 8 |
| 11.2 compare groups | Tasks 9-10 |
| 11.3 proportions | Tasks 9 and 11 |
| 11.4 correlation | Tasks 9 and 12 |
| 11.5 regression | Task 13 |
| 11.6 anomalies | Task 14 |
| 11.7 change points | Task 15 |
| 11.8 forecasts | Tasks 14 and 16 |
| 12 dependencies | Task 1 |
| 13 security, privacy, resources | Tasks 2, 4-6, 8, and 17 |
| 14 error handling | Tasks 3, 5-7, and 17 |
| 15 human review | Tasks 3, 18, and 19 |
| 16 testing strategy | Every task's failing/passing cycle; Task 20 audit |
| 17 documentation and compatibility | Task 19 |
| 18 delivery slices | Tasks 1-19 in dependency order |
| 19 acceptance criteria | Task 20 requirement-by-requirement audit |

## Completion Evidence

The implementation is complete only after Task 20 proves every acceptance
criterion from the design. Required final evidence includes:

```text
pytest -m unit                                      PASS
pytest -m statistics                                PASS, no method skipped
python scripts/dep_coresolve.py --check             PASS
python scripts/export_agent_bundles.py --check      PASS
seshat check                                        exit 0, static evidence only
python -m pytest                                    PASS
live statistical adapter                            PASS or [PENDING LIVE PROFILE]
git status --short                                  clean
```
