# Knowledge-Layer Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand all six Seshat BI knowledge layers with live routed capabilities, consistent cross-layer handoffs, deterministic public distribution, and verified governance boundaries.

**Architecture:** Canonical knowledge remains under `skills/`, with concise `SKILL.md` entry contracts, task/symptom routing in `INDEX.md`, focused knowledge resources, and terminal checklists or verdicts. A shared YAML handoff envelope under `contracts/knowledge/` connects the layers without duplicating ownership; generated Claude and Codex copies are rebuilt only through `scripts/export_agent_bundles.py`.

**Tech Stack:** Markdown skill packs, YAML contracts and routing fixtures, JSON pattern catalogs, Python 3.11+ export/validation tooling, pytest 8.

## Global Constraints

- Work only in `C:\Users\user\Documents\GitHub\Seshat-BI\.worktrees\knowledge-layers-expansion`.
- Commit every completed task independently with `git commit --no-gpg-sign`.
- Preserve `SKILL.md -> INDEX.md -> named resource -> artifact` progressive disclosure.
- Knowledge layers reason and validate; they never execute SQL, Python, Spark, DAX, or Power BI.
- Never grant readiness or a named-human approval and never emit a numeric readiness/confidence score.
- Retail KPI owns business meaning; implementation layers reference it and never redefine it.
- Do not promote owner-dependent KPI policy to seeded knowledge.
- Do not generalize C086 or any other worked example into a universal schema.
- Edit canonical `skills/` sources only; regenerate integration bundles with the exporter.
- Use a repository-local ignored pytest base directory on Windows:
  `--basetemp .pytest_cache/knowledge-expansion`.

---

### Task 0: Build the knowledge-route contract validator

**Files:**
- Create: `scripts/validate_knowledge_routes.py`
- Create: `tests/unit/test_knowledge_route_validator.py`
- Create: `tests/fixtures/knowledge-route-scenarios.yaml`

**Interfaces:**
- Consumes: repository root plus scenario records with `layer`, `task_contains`,
  `expect_resources`, and `terminal_contains`.
- Produces: `list[RouteFinding]`; CLI exit 0 when every route selects existing
  resources and names its terminal artifact, exit 1 with JSON findings otherwise.

- [ ] **Step 1: Write failing validator tests**

```python
import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_knowledge_routes.py"


def run_validator(repo: Path, scenarios: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--scenarios",
            str(scenarios),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_missing_routed_resource_returns_finding(tmp_path: Path) -> None:
    layer = tmp_path / "skills" / "example-knowledge"
    layer.mkdir(parents=True)
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile data | `knowledge/profile.md` | profile verdict |\n",
        encoding="utf-8",
    )
    scenarios = tmp_path / "scenarios.yaml"
    scenarios.write_text(
        yaml.safe_dump({"schema_version": 1, "scenarios": [{
            "layer": "example-knowledge",
            "task_contains": "Profile data",
            "expect_resources": ["knowledge/profile.md"],
            "terminal_contains": "profile verdict",
        }]}),
        encoding="utf-8",
    )

    result = run_validator(tmp_path, scenarios)

    assert result.returncode == 1
    assert [
        (item["code"], item["resource"]) for item in json.loads(result.stdout)
    ] == [
        ("missing_resource", "knowledge/profile.md")
    ]


def test_complete_route_returns_no_findings(tmp_path: Path) -> None:
    layer = tmp_path / "skills" / "example-knowledge"
    (layer / "knowledge").mkdir(parents=True)
    (layer / "knowledge" / "profile.md").write_text("# Profile\n", encoding="utf-8")
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile data | `knowledge/profile.md` | profile verdict |\n",
        encoding="utf-8",
    )
    scenarios = tmp_path / "scenarios.yaml"
    scenarios.write_text(
        yaml.safe_dump({"schema_version": 1, "scenarios": [{
            "layer": "example-knowledge",
            "task_contains": "Profile data",
            "expect_resources": ["knowledge/profile.md"],
            "terminal_contains": "profile verdict",
        }]}),
        encoding="utf-8",
    )

    result = run_validator(tmp_path, scenarios)

    assert result.returncode == 0
    assert json.loads(result.stdout) == []
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
```

Expected: both tests FAIL because the missing script returns exit 2 instead of the
contractual exits 1 and 0.

- [ ] **Step 3: Implement the minimal validator**

Implement:

```python
@dataclass(frozen=True)
class RouteFinding:
    code: str
    layer: str
    task: str
    resource: str
    message: str


def validate_repository(
    repo_root: Path, scenarios: list[dict[str, object]]
) -> list[RouteFinding]:
    """Match each scenario to one INDEX task row and validate its resources/end artifact."""
```

Parse Markdown table rows only inside `INDEX.md`; normalize backtick-quoted
repo-relative paths; reject missing, ambiguous, or duplicate task matches; check every
expected resource resolves from `skills/<layer>/` to a path that remains inside the
repository (safe `../../contracts/` and `../../templates/` references are valid); and
verify the matched terminal cell contains the expected artifact text. Do not infer
routes from prose outside tables.

- [ ] **Step 4: Add the initial six-layer scenario fixture**

Seed one existing route per layer so the validator is useful before expansion:

```yaml
schema_version: 1
scenarios:
  - layer: bi-python-knowledge
    task_contains: Review a dataframe groupby
    expect_resources: [knowledge/groupby-aggregation-and-grain.md]
    terminal_contains: aggregation-grain-checklist
```

Add corresponding existing rows for SQL validation, DAX measure review, KPI contract
definition, Big Data engine selection, and Analyst narrative brief authoring.

- [ ] **Step 5: Verify GREEN and commit**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
git add scripts/validate_knowledge_routes.py `
  tests/unit/test_knowledge_route_validator.py `
  tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "test: validate knowledge route contracts"
```

---

### Task 1: Activate the Python foundation routes

**Files:**
- Create: `skills/bi-python-knowledge/knowledge/dataframe-mental-model.md`
- Create: `skills/bi-python-knowledge/knowledge/python-core-concepts-for-bi.md`
- Create: `skills/bi-python-knowledge/knowledge/profiling-and-source-inspection.md`
- Create: `skills/bi-python-knowledge/knowledge/pandas-dtypes-and-schema.md`
- Create: `skills/bi-python-knowledge/knowledge/nulls-missing-values-and-blanks.md`
- Create: `skills/bi-python-knowledge/knowledge/joins-merge-and-fanout.md`
- Create: `skills/bi-python-knowledge/knowledge/dates-times-and-calendars.md`
- Create: `skills/bi-python-knowledge/checklists/dataframe-review-checklist.md`
- Create: `skills/bi-python-knowledge/checklists/merge-fanout-checklist.md`
- Modify: `skills/bi-python-knowledge/SKILL.md`
- Modify: `skills/bi-python-knowledge/INDEX.md`
- Modify: `skills/bi-python-knowledge/README.md`
- Modify: `skills/bi-python-knowledge/references/id-conventions.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: source-profile evidence, declared row grain, expected schema, source-map null/sentinel decisions.
- Produces: dataframe profile verdict, dtype/schema verdict, null-policy blocker, merge fan-out verdict, and a handoff to validation.

- [ ] **Step 1: Add failing Python route scenarios**

Append scenarios for the following task/resource/artifact triples:

```yaml
- layer: bi-python-knowledge
  task_contains: Profile a freshly loaded dataframe
  expect_resources: [knowledge/profiling-and-source-inspection.md]
  terminal_contains: dataframe-review-checklist
- layer: bi-python-knowledge
  task_contains: Judge dtypes or schema drift
  expect_resources: [knowledge/pandas-dtypes-and-schema.md]
  terminal_contains: dataframe-review-checklist
- layer: bi-python-knowledge
  task_contains: Merge two dataframes safely
  expect_resources: [knowledge/joins-merge-and-fanout.md]
  terminal_contains: merge-fanout-checklist
- layer: bi-python-knowledge
  task_contains: Parse dates and periods
  expect_resources: [knowledge/dates-times-and-calendars.md]
  terminal_contains: dataframe-review-checklist
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
```

Expected: FAIL because the named live resources do not exist.

- [ ] **Step 3: Write the seven focused knowledge resources**

Use these stable concept IDs and headings:

Every resource uses its real capability name as the H1 and these exact sections:

```markdown
## Decision this route supports
## Required evidence
## Reasoning sequence
## Failure modes
## Evidence-based verdict
## Stop and handoff
```

Assign:

- `PY-DF-001..006` to dataframe/grain concepts;
- `PY-PROFILE-001..008` to source inspection;
- `PY-DTYPE-001..008` to dtype/schema drift;
- `PY-NULL-001..008` to null/blank/sentinel handling;
- `PY-MERGE-001..010` to cardinality and fan-out;
- `PY-DATE-001..008` to date/time/calendar preparation.

Each resource must require a declared grain, distinguish observed evidence from
assumptions, and end with `clean`, `blocked`, or `handoff` plus named evidence.

- [ ] **Step 4: Add the dataframe and merge checklists**

The dataframe checklist must cover grain, shape, field presence, dtype, null/sentinel
policy, category normalization, date validity, uniqueness, and evidence provenance.
The merge checklist must record left/right grain, key uniqueness, expected
cardinality, before/after row counts, unmatched keys, multiplicity distribution,
and aggregate control totals.

- [ ] **Step 5: Promote the routes from planned to live**

Move the seven implemented rows out of `INDEX.md`'s planned table into task and
symptom routes. Update `SKILL.md` and `README.md` so the coverage statement names
live profiling, dtypes, nulls, joins, and dates while leaving validation,
performance, analyzer, patterns, worked example, and pipeline review explicitly
planned for Task 2.

- [ ] **Step 6: Run focused validation**

Run:

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py tests/unit/test_knowledge_contracts.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add skills/bi-python-knowledge tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "feat: activate Python dataframe reasoning routes"
```

---

### Task 2: Complete Python validation, diagnostics, and review artifacts

**Files:**
- Create: `skills/bi-python-knowledge/knowledge/validation-and-reconciliation.md`
- Create: `skills/bi-python-knowledge/knowledge/performance-and-memory.md`
- Create: `skills/bi-python-knowledge/knowledge/python-anti-patterns.md`
- Create: `skills/bi-python-knowledge/knowledge/python-retail-examples.md`
- Create: `skills/bi-python-knowledge/patterns/validation-patterns.json`
- Create: `skills/bi-python-knowledge/patterns/analyzer-rules.json`
- Create: `skills/bi-python-knowledge/patterns/python-patterns.json`
- Create: `skills/bi-python-knowledge/checklists/validation-reconciliation-checklist.md`
- Create: `skills/bi-python-knowledge/checklists/python-pipeline-review-checklist.md`
- Modify: `skills/bi-python-knowledge/INDEX.md`
- Modify: `skills/bi-python-knowledge/README.md`
- Modify: `skills/bi-python-knowledge/SKILL.md`
- Modify: `skills/bi-python-knowledge/references/id-conventions.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: Task 1 profile/merge artifacts and expected source/control totals.
- Produces: validation/reconciliation verdict, performance/memory verdict, analyzer-style findings, pipeline review.

- [ ] **Step 1: Add failing scenarios for the remaining live routes**

Add scenario rows for validation/reconciliation, performance/memory diagnosis,
anti-pattern review, the worked example, and the pipeline review. Each scenario names
all route resources and its exact terminal checklist or verdict.

- [ ] **Step 2: Run and confirm failure**

Run `tests/unit/test_knowledge_route_validator.py`. Expected: FAIL with
`missing_route` or `missing_resource` findings for the new scenarios.

- [ ] **Step 3: Author validation and performance knowledge**

Use `PY-VAL-001..012` for grain-aware row counts, uniqueness, null distribution,
domain/range, unmatched keys, additive controls, stratified reconciliation, and
sample limitations. Use `PY-PERF-001..010` for vectorization, copy amplification,
object dtype, categorical encoding, chunking, pushdown, and the single-node-to-Big
Data boundary.

- [ ] **Step 4: Author patterns and anti-patterns**

`validation-patterns.json` must use objects with:

```json
{
  "id": "PY-VP-001",
  "name": "row_count_control",
  "requires": ["expected_grain", "source_row_count"],
  "evidence": ["observed_row_count", "variance_reason"],
  "blocked_when": ["expected_grain_missing"]
}
```

`analyzer-rules.json` must contain categorical findings only. `python-patterns.json`
must name positive patterns and their evidence. Validate every JSON file with
`python -m json.tool`.

- [ ] **Step 5: Add the worked example and terminal checklists**

The example uses only the fictional schema from
`references/retail-dataframe-schema.md` and demonstrates profile -> dtype -> merge
-> aggregate -> reconcile. Label all outputs as illustrative, never observed.

- [ ] **Step 6: Promote all remaining core Python routes**

Update `INDEX.md`, `README.md`, and `SKILL.md`. The planned section may retain only
future capabilities that are not named as success criteria; it must not list any of
the eleven routes completed in Tasks 1-2.

- [ ] **Step 7: Verify and commit**

Run JSON validation plus navigation/knowledge tests, then:

```powershell
git add skills/bi-python-knowledge tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "feat: complete Python validation knowledge"
```

---

### Task 3: Define and adopt the shared knowledge-layer handoff

**Files:**
- Create: `contracts/knowledge/knowledge-layer-handoff.yaml`
- Modify: `contracts/README.md`
- Modify: `skills/retail-kpi-knowledge/INDEX.md`
- Modify: `skills/bi-sql-knowledge/INDEX.md`
- Modify: `skills/bi-dax-knowledge/INDEX.md`
- Modify: `skills/bi-python-knowledge/INDEX.md`
- Modify: `skills/bi-bigdata-knowledge/INDEX.md`
- Modify: `skills/bi-analyst-knowledge/INDEX.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_contracts.py`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: terminal artifacts from any of the six layers.
- Produces: `seshat.knowledge-layer-handoff/v1`, a non-approving envelope for the next layer.

- [ ] **Step 1: Add a failing contract-shape test**

```python
def test_knowledge_layer_handoff_contract_is_closed_and_safe() -> None:
    path = ROOT / "contracts/knowledge/knowledge-layer-handoff.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["schema"] == "seshat.knowledge-layer-handoff/v1"
    assert data["layers"] == [
        "retail-kpi", "sql", "dax", "python", "bigdata", "analyst"
    ]
    def all_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return {
                str(key)
                for key in value
            } | set().union(*(all_keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(all_keys(item) for item in value))
        return set()

    assert all_keys(data).isdisjoint({"score", "confidence_score", "readiness_score"})
    assert data["authority"]["grants_approval"] is False
    assert set(data["required_fields"]) == {
        "origin_layer", "terminal_artifact", "input_grain", "output_grain",
        "evidence", "assumptions", "blockers", "destination_layer", "next_action"
    }
```

- [ ] **Step 2: Run and confirm missing-file failure**

- [ ] **Step 3: Write the handoff contract**

Include the required fields above plus optional metric contract reference, physical
bindings, null/sentinel decisions, exclusions, additivity, and reconciliation
obligations. Encode:

```yaml
authority:
  grants_approval: false
  advances_readiness: false
  executes_workload: false
stop_rules:
  - unresolved_owner_decision
  - missing_required_evidence
  - destination_boundary_unclear
```

- [ ] **Step 4: Add an inbound and outbound handoff row to all six routers**

Each row references the shared contract and names the layer-specific artifact used
to fill it. Do not duplicate the YAML field descriptions in each index. Add one
`Prepare a cross-layer handoff` scenario per layer to
`tests/fixtures/knowledge-route-scenarios.yaml`; each expects
`../../contracts/knowledge/knowledge-layer-handoff.yaml` and ends on
`knowledge-layer handoff`.

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_contracts.py tests/unit/test_knowledge_route_validator.py -q
git add contracts/knowledge/knowledge-layer-handoff.yaml contracts/README.md `
  skills/*-knowledge/INDEX.md tests/fixtures/knowledge-route-scenarios.yaml `
  tests/unit/test_knowledge_contracts.py
git commit --no-gpg-sign -m "feat: standardize knowledge layer handoffs"
```

---

### Task 4: Add PostgreSQL execution-plan reasoning to SQL

**Files:**
- Create: `skills/bi-sql-knowledge/knowledge/postgresql-execution-plans.md`
- Create: `skills/bi-sql-knowledge/checklists/postgresql-plan-review-checklist.md`
- Create: `skills/bi-sql-knowledge/patterns/postgresql-plan-patterns.json`
- Modify: `skills/bi-sql-knowledge/SKILL.md`
- Modify: `skills/bi-sql-knowledge/INDEX.md`
- Modify: `skills/bi-sql-knowledge/README.md`
- Modify: `skills/bi-sql-knowledge/references/id-conventions.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: supplied `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` evidence with secrets removed.
- Produces: plan-review checklist and `clean`/`needs-evidence`/`blocked` diagnostic verdict.

- [ ] **Step 1: Add a failing SQL plan scenario**

```yaml
- layer: bi-sql-knowledge
  task_contains: Review a PostgreSQL execution plan
  expect_resources:
    - knowledge/postgresql-execution-plans.md
    - patterns/postgresql-plan-patterns.json
  terminal_contains: postgresql-plan-review-checklist
```

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Author `EP-001..EP-014` plan concepts**

Cover plan shape, actual/estimated rows and loops, scan choice, nested-loop/hash/merge
join interpretation, filters removed, sort/hash memory and spill, buffers, parallelism,
statistics uncertainty, parameter sensitivity, and before/after evidence. Do not
prescribe indexes without workload and write-cost evidence.

- [ ] **Step 4: Add machine-readable symptom patterns and checklist**

Pattern objects use `EP-PAT-*`, required evidence, observation, plausible causes,
confirming checks, and stop rule. The checklist must refuse a performance verdict
from bare SQL text with no plan evidence.

- [ ] **Step 5: Remove the deferred seam wording and promote routes**

Update the SKILL description and boundaries to say this is supplied-plan reasoning,
not database execution or automatic tuning.

- [ ] **Step 6: Validate and commit**

```powershell
python -m json.tool skills/bi-sql-knowledge/patterns/postgresql-plan-patterns.json
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
git add skills/bi-sql-knowledge tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "feat: add PostgreSQL plan reasoning"
```

---

### Task 5: Expand DAX relationship and semantic diagnostics

**Files:**
- Create: `skills/bi-dax-knowledge/knowledge/dax-relationships-and-virtual-filters.md`
- Create: `skills/bi-dax-knowledge/knowledge/dax-calculation-groups-and-precedence.md`
- Create: `skills/bi-dax-knowledge/knowledge/dax-semi-additive-and-blank-semantics.md`
- Create: `skills/bi-dax-knowledge/checklists/dax-diagnostic-checklist.md`
- Modify: `skills/bi-dax-knowledge/INDEX.md`
- Modify: `skills/bi-dax-knowledge/SKILL.md`
- Modify: `skills/bi-dax-knowledge/patterns/analyzer-rule-candidates.json`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: approved metric contract, model relationships, measure definition, calculation-group metadata.
- Produces: diagnostic verdict and semantic-model prerequisite handoff.

- [ ] **Step 1: Add failing DAX route scenarios**

Add five scenarios covering ambiguous relationships, virtual filters,
calculation-group precedence, semi-additive totals, and blank-versus-zero display.
Each scenario names one focused knowledge resource and ends on
`dax-diagnostic-checklist`.

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Author the three diagnostic resources**

Use IDs `DX-REL-001..010`, `DX-CG-001..008`, and `DX-SA-001..010`. Every diagnostic
sequence must start with contract and model metadata, distinguish filter propagation
from business definition, and stop if the snapshot/date policy is undecided.

- [ ] **Step 4: Add candidate findings and checklist**

Add analyzer candidates for bidirectional ambiguity, unsupported virtual relationship,
calculation-item precedence conflict, semi-additive time summation, and blank coerced
to zero. Preserve the existing JSON schema.

- [ ] **Step 5: Verify and commit**

```powershell
python -m json.tool skills/bi-dax-knowledge/patterns/analyzer-rule-candidates.json
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
git add skills/bi-dax-knowledge tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "feat: expand DAX semantic diagnostics"
```

---

### Task 6: Add KPI sufficiency and policy-decision packets

**Files:**
- Create: `skills/retail-kpi-knowledge/knowledge/kpi-sufficiency-and-policy-decisions.md`
- Create: `skills/retail-kpi-knowledge/checklists/kpi-policy-decision-checklist.md`
- Create: `skills/retail-kpi-knowledge/references/implementation-handoff-template.md`
- Modify: `skills/retail-kpi-knowledge/INDEX.md`
- Modify: `skills/retail-kpi-knowledge/SKILL.md`
- Modify: `skills/retail-kpi-knowledge/README.md`
- Modify: `skills/retail-kpi-knowledge/registry.yaml`
- Modify: `skills/retail-kpi-knowledge/references/kpi-derivation-lineage.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`
- Test: `tests/unit/test_knowledge_contracts.py`

**Interfaces:**
- Consumes: candidate KPI, source-field evidence, ambiguity ledger, named authority.
- Produces: sufficiency verdict, owner decision packet, or implementation handoff; never approval.

- [ ] **Step 1: Add failing route and policy-lifecycle tests**

Add a route scenario for `Prepare an owner policy decision packet` ending on
`kpi-policy-decision-checklist`. Add a registry test that loads `registry.yaml` and
asserts `same-store-sales-growth` remains in its existing planned lifecycle with its
owner-policy blockers; derive the expected lifecycle and blocker IDs as literals from
the approved design, not from the registry loader.

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Author sufficiency and policy reasoning**

Define categorical statuses `answerable`, `blocked_by_source`, `blocked_by_policy`,
and `not_applicable`. The decision packet records question, business consequence,
available evidence, alternatives, refutation evidence, named authority, and downstream
artifacts affected.

- [ ] **Step 4: Add the implementation handoff template**

Reference the shared handoff contract from Task 3 and add KPI-specific fields:
contract ID/revision, formula in business terms, additivity, time behavior, filters,
exclusions, required source fields, and unresolved policy. Do not include SQL or DAX.

- [ ] **Step 5: Reconcile registry/router counts and lineage**

Do not change `same-store-sales-growth` or other owner-dependent entries from planned.
Fix only factual count drift and add decision-packet routes.

- [ ] **Step 6: Verify and commit**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_contracts.py tests/unit/test_knowledge_route_validator.py -q
git add skills/retail-kpi-knowledge tests/fixtures/knowledge-route-scenarios.yaml `
  tests/unit/test_knowledge_contracts.py
git commit --no-gpg-sign -m "feat: add governed KPI decision packets"
```

---

### Task 7: Add Big Data operational evidence reasoning

**Files:**
- Create: `skills/bi-bigdata-knowledge/knowledge/observability-and-partial-failures.md`
- Create: `skills/bi-bigdata-knowledge/knowledge/backfills-and-partition-evolution.md`
- Create: `skills/bi-bigdata-knowledge/checklists/operational-evidence-checklist.md`
- Modify: `skills/bi-bigdata-knowledge/INDEX.md`
- Modify: `skills/bi-bigdata-knowledge/SKILL.md`
- Modify: `skills/bi-bigdata-knowledge/patterns/analyzer-rule-candidates.json`
- Modify: `skills/bi-bigdata-knowledge/references/id-conventions.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: run metadata, partition/file evidence, retry history, control totals, declared grain.
- Produces: operational evidence packet and backfill/partition-evolution review.

- [ ] **Step 1: Add failing Big Data route scenarios**

Add scenarios for partial output after retry, backfill safety, partition evolution,
compaction evidence, and cost/performance evidence packets. End each on
`operational-evidence-checklist`.

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Author scale-specific operational knowledge**

Use `BD-OPS-001..012` and `BD-BF-001..010`. Cover stage/task/run identifiers,
input/output partition manifests, partial commits, retry idempotency, quarantine,
backfill windows, late data, partition-spec evolution, compaction, and control totals.
Do not duplicate generic grain or null concepts.

- [ ] **Step 4: Add checklist and analyzer candidates**

The checklist records evidence presence, not a health score. Findings include partial
output visible, retry duplicated data, backfill overlaps live window, partition-spec
drift, and compaction changed control totals.

- [ ] **Step 5: Verify and commit**

```powershell
python -m json.tool skills/bi-bigdata-knowledge/patterns/analyzer-rule-candidates.json
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
git add skills/bi-bigdata-knowledge tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "feat: add Big Data operational evidence"
```

---

### Task 8: Expand Analyst diagnostic and narrative-change reasoning

**Files:**
- Create: `skills/bi-analyst-knowledge/diagnostic-question-tree.md`
- Create: `skills/bi-analyst-knowledge/narrative-change-review.md`
- Create: `skills/bi-analyst-knowledge/action-and-review-cadence.md`
- Create: `skills/bi-analyst-knowledge/checklists/narrative-judgment-review-checklist.md`
- Modify: `skills/bi-analyst-knowledge/INDEX.md`
- Modify: `skills/bi-analyst-knowledge/SKILL.md`
- Modify: `skills/bi-analyst-knowledge/derivation-route.md`
- Test: `tests/fixtures/knowledge-route-scenarios.yaml`
- Test: `tests/unit/test_knowledge_route_validator.py`

**Interfaces:**
- Consumes: approved contracts, source profile, prior narrative brief, contract/profile drift evidence.
- Produces: ranked diagnostic question tree, narrative-change verdict, action-owner/cadence handoff.

- [ ] **Step 1: Add failing Analyst route scenarios**

Add scenarios for "headline changed, what should we investigate?", "contract revision
changed the story", "source drift invalidated a question", and "insight has no owner or
review cadence". End them respectively on a diagnostic question tree,
narrative-change verdict, or action/cadence handoff.

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Author the diagnostic question tree**

Use the sequence overview -> change -> driver -> segment -> exception -> action.
Every node cites an approved contract and available dimension; unavailable nodes become
`[GAP]`. The tree ranks by owner decision relevance and evidence availability, never a
numeric score.

- [ ] **Step 4: Author narrative-change and action/cadence guidance**

Require revision SHAs, identify affected questions and framings, and return
`unchanged`, `revise`, or `blocked`. Action handoffs record owner role, decision,
trigger, review cadence, evidence refresh, and escalation condition without assigning
an owner who has not been named.

- [ ] **Step 5: Add the terminal checklist and update derivation**

The checklist verifies grounding, comparisons, guardrails, gaps, story order, owner,
cadence, revision freshness, and no invented metrics.

- [ ] **Step 6: Verify and commit**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/unit/test_knowledge_route_validator.py -q
git add skills/bi-analyst-knowledge tests/fixtures/knowledge-route-scenarios.yaml
git commit --no-gpg-sign -m "feat: expand analyst narrative reasoning"
```

---

### Task 9: Reconcile the six-layer public contract and Compass

**Files:**
- Modify: `COMPASS.md`
- Modify: `docs/knowledge-map.md`
- Modify: `docs/routing/routes.yaml`
- Modify: `CONTRIBUTING.md`
- Modify: `distribution/public-command-surface.yaml`
- Modify: `scripts/export_agent_bundles.py`
- Modify: `tests/fixtures/nav-scenarios.yaml`
- Modify: `tests/fixtures/knowledge-route-scenarios.yaml`
- Modify: `tests/contract/test_public_knowledge_allowlist.py`
- Modify: `tests/contract/test_generated_agent_bundles.py`
- Modify: `tests/contract/test_public_command_surface.py`
- Modify: `tests/unit/test_navigation_regression.py`

**Interfaces:**
- Consumes: all canonical layer routes from Tasks 1-8.
- Produces: one truthful six-layer routing and canonical-root contract.

- [ ] **Step 1: Change tests to require six canonical roots**

Update assertions and messages from the original five to:

```python
EXPECTED_CANONICAL_ROOTS = {
    "skills/bi-sql-knowledge/SKILL.md",
    "skills/bi-dax-knowledge/SKILL.md",
    "skills/bi-python-knowledge/SKILL.md",
    "skills/bi-bigdata-knowledge/SKILL.md",
    "skills/retail-kpi-knowledge/SKILL.md",
    "skills/bi-analyst-knowledge/SKILL.md",
}
```

- [ ] **Step 2: Run public-surface tests and confirm failure**

Run the three contract test modules. Expected: FAIL because exporter and allowlist
canonical roots still contain five.

- [ ] **Step 3: Update routing prose and registries**

Add Analyst as the sixth canonical layer, add Python's now-live routes, add SQL plan
review and the other new routes, and preserve readiness/approval hard stops.

- [ ] **Step 4: Update exporter and public command surface**

Change `CANONICAL_ROOTS` in `scripts/export_agent_bundles.py` to the exact six-path set
above. Update validation errors to say "six Seshat skills". Ensure
`distribution/public-command-surface.yaml` exposes every layer once.

- [ ] **Step 5: Run focused tests and commit**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/contract/test_public_knowledge_allowlist.py `
  tests/contract/test_public_command_surface.py `
  tests/contract/test_generated_agent_bundles.py `
  tests/unit/test_navigation_regression.py `
  tests/unit/test_knowledge_route_validator.py -q
git add COMPASS.md docs/knowledge-map.md docs/routing/routes.yaml CONTRIBUTING.md `
  distribution/public-command-surface.yaml scripts/export_agent_bundles.py `
  tests/fixtures/nav-scenarios.yaml tests/contract tests/unit/test_navigation_regression.py
git commit --no-gpg-sign -m "fix: reconcile six knowledge layer surfaces"
```

---

### Task 10: Classify every new public knowledge resource

**Files:**
- Modify: `distribution/public-knowledge-allowlist.yaml`
- Test: `tests/contract/test_public_knowledge_allowlist.py`

**Interfaces:**
- Consumes: every new canonical file from Tasks 1-8.
- Produces: explicit literal Claude/Codex destinations for each reviewed public file.

- [ ] **Step 1: Run the exporter in check mode and capture unlisted sources**

```powershell
python scripts/export_agent_bundles.py --check
```

Expected: FAIL naming canonical files absent from the allowlist.

- [ ] **Step 2: Add literal allowlist entries**

Add one entry per new public Markdown/JSON/YAML resource. Continue the existing `kb-*`
sequence without reuse. Use:

```yaml
classification: public_knowledge
transform: copy-normalized-v1
required: true
generated_notice: manifest
review_reason: Required canonical Seshat Knowledge Base content for public agent reasoning.
```

Targets must mirror the existing per-layer destination structure.

- [ ] **Step 3: Validate allowlist closure**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/contract/test_public_knowledge_allowlist.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add distribution/public-knowledge-allowlist.yaml
git commit --no-gpg-sign -m "build: classify expanded public knowledge"
```

---

### Task 11: Regenerate Claude and Codex bundles

**Files:**
- Modify generated files under: `integrations/claude-code/seshat-bi/`
- Modify generated files under: `integrations/codex/seshat-bi/`
- Modify generated provenance manifests selected by the exporter

**Interfaces:**
- Consumes: canonical skills, wrapper templates, public allowlist.
- Produces: deterministic public bundles with matching source digests.

- [ ] **Step 1: Generate bundles**

```powershell
python scripts/export_agent_bundles.py
```

Expected: both integration trees update from canonical inputs.

- [ ] **Step 2: Prove deterministic regeneration**

```powershell
python scripts/export_agent_bundles.py --check
```

Expected: PASS and no diff from a second generation.

- [ ] **Step 3: Run bundle contract tests**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/contract/test_generated_agent_bundles.py `
  tests/contract/test_codex_plugin_bundle.py `
  tests/contract/test_claude_plugin_bundle.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit generated output**

Stage only the two generated integration trees and their provenance manifests:

```powershell
git add integrations/claude-code/seshat-bi integrations/codex/seshat-bi
git commit --no-gpg-sign -m "build: regenerate expanded agent knowledge"
```

---

### Task 12: Run completion audit and broad verification

**Files:**
- Modify only if verification exposes a defect in a prior task.
- Review: `docs/superpowers/specs/2026-07-25-knowledge-layer-expansion-design.md`
- Review: `docs/superpowers/plans/2026-07-25-knowledge-layer-expansion.md`

**Interfaces:**
- Consumes: all task commits.
- Produces: requirement-by-requirement evidence and a clean isolated branch.

- [ ] **Step 1: Audit design success criteria**

Create a temporary checklist outside tracked files and verify:

```text
[ ] Python core deferred routes are live
[ ] all six layers have inbound/outbound handoffs
[ ] SQL has supplied-plan reasoning
[ ] DAX has relationship/calculation-group/semi-additive diagnostics
[ ] KPI has policy-safe decision packets
[ ] Big Data has operational evidence reasoning
[ ] Analyst has diagnostic and narrative-change reasoning
[ ] every new resource is routed and allowlisted
[ ] generated bundles match canonical inputs
[ ] no approval/score/execution boundary regression
```

- [ ] **Step 2: Run static format and export checks**

```powershell
git diff --check f803c0257a3b11aefd4085847b67ccf58b0207c3..HEAD
python scripts/export_agent_bundles.py --check
```

- [ ] **Step 3: Run focused verification**

```powershell
python -m pytest --no-cov --basetemp .pytest_cache/knowledge-expansion `
  tests/contract/test_public_knowledge_allowlist.py `
  tests/contract/test_public_command_surface.py `
  tests/contract/test_generated_agent_bundles.py `
  tests/contract/test_codex_plugin_bundle.py `
  tests/contract/test_claude_plugin_bundle.py `
  tests/unit/test_compass_project.py `
  tests/unit/test_navigation_regression.py `
  tests/unit/test_knowledge_route_validator.py `
  tests/unit/test_knowledge_contracts.py -q
```

- [ ] **Step 4: Run the broad unit suite**

```powershell
$env:GIT_CONFIG_COUNT='1'
$env:GIT_CONFIG_KEY_0='safe.directory'
$env:GIT_CONFIG_VALUE_0='C:/Users/user/Documents/GitHub/Seshat-BI/.worktrees/knowledge-layers-expansion'
python -m pytest -m unit --no-cov --basetemp .pytest_cache/knowledge-expansion -q
```

Expected: all selected tests pass; only pre-existing platform skips are acceptable.

- [ ] **Step 5: Confirm clean state and unsigned history**

```powershell
git status --short
git log --show-signature --oneline -12
```

Expected: empty status; each task has a distinct commit; no commit carries a signature.

- [ ] **Step 6: Close any verification-only correction**

If verification exposes a defect, return to the task that owns the failing artifact,
apply the smallest correction there, rerun that task's exact verification command,
stage only the paths listed in that task, and commit unsigned with that task's commit
message prefixed by `fix:`. If no edits are required, do not create an empty commit.
