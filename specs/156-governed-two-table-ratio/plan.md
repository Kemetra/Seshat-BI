# Governed Two-Table Ratio Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a verified actual-to-target ratio across two gold tables and
fail closed when the metric definition disagrees with its governed bindings.

**Architecture:** Keep the existing `kind: ratio` emitter and drift verifier.
A new pure stdlib-only validator owns top-level contract/definition coherence;
the CLI generator and approved-contract inventory both call it. Templates expose
the owner-approved scalar `compares_to` sibling and a generatable example.

**Tech Stack:** Python 3.13, stdlib typing, PyYAML behind existing lazy
boundaries, pytest, Markdown/YAML templates.

**Spec:** `specs/156-governed-two-table-ratio/spec.md`

## Global Constraints

- Named-owner ratification and the singleton spec fence are required before Task 1.
- `binds_to` stays scalar; `compares_to` is optional and scalar.
- Reuse `definition.kind: ratio`; do not add a `variance` kind.
- Existing one-table contracts and output remain unchanged.
- Refuse malformed or incoherent input; never repair or infer it.
- No database, DAX execution, Power BI write, target value, grain ruling, RAG
  threshold, missing-target ruling, or approval is in scope.
- Imports of `seshat`, `seshat.cli`, and `seshat.rules` remain free of PyYAML.
- Every product change follows RED -> verify RED -> GREEN -> focused regression.

## File Structure

```text
src/seshat/metric_contract_bindings.py
src/seshat/metric_contract_inventory.py
src/seshat/cli/commands/generate.py
tests/unit/test_metric_contract_bindings.py
tests/unit/test_metric_contract_inventory.py
tests/unit/test_dax_gen.py
tests/fixtures/contracts/ratio_two_table.yaml
tests/unit/test_two_table_ratio_contract.py
templates/metric-contract.yaml
templates/metric-contract-shape.variance-vs-target.yaml
integrations/{codex,claude-code}/seshat-bi/templates/metric-contract.yaml
specs/156-governed-two-table-ratio/evidence/validation.md
docs/roadmap/{idea-backlog.md,shipped-ideas.yaml}
```

### Task 0: Ratify and Move the Singleton Fence

**Files:**
- Modify: `specs/156-governed-two-table-ratio/spec.md`
- Modify: `specs/156-governed-two-table-ratio/tasks.md`
- Create: `specs/156-governed-two-table-ratio/ratify-ledger.md`
- Modify: `.specify/feature.json`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Test: `tests/contract/test_dbt_documentation.py`

**Interfaces:**
- Active feature directory: `specs/156-governed-two-table-ratio`
- Ratification record: named human, authority `owner`, date, and exact FR scope

- [ ] **Step 1: Record the human action**

Write the named ratifier and exact authorization into `spec.md` and
`ratify-ledger.md`. State that spec 141 is paused, not completed or rejected.

- [ ] **Step 2: Move the one active pointer**

Set `.specify/feature.json` to:

```json
{"feature_directory": "specs/156-governed-two-table-ratio"}
```

Replace each `SPECKIT` body with exactly one reference to
`specs/156-governed-two-table-ratio/plan.md` plus the ratification summary.

- [ ] **Step 3: Verify the lifecycle contract**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\contract\test_dbt_documentation.py::test_active_spec_kit_markers_agree_and_resolve -q
```

Expected: PASS with feature JSON and both prose fences resolving to this plan.

- [ ] **Step 4: Commit**

```powershell
git add .specify/feature.json AGENTS.md CLAUDE.md specs/156-governed-two-table-ratio
git -c commit.gpgsign=false commit -m "docs: ratify governed two-table ratios"
```

### Task 1: Add the Pure Binding-Coherence Validator

**Files:**
- Create: `src/seshat/metric_contract_bindings.py`
- Create: `tests/unit/test_metric_contract_bindings.py`

**Interfaces:**
- Produces: `definition_binding_errors(contract: Mapping[str, object]) -> tuple[str, ...]`
- Consumes only Python mappings, lists, and scalars; imports no YAML or rules.

- [ ] **Step 1: Write the failing tests**

Define a valid generic two-table helper, then cover valid sum/sum,
`count_rows` filter columns, missing `compares_to`, table mismatch, missing bound
columns, non-gold table, malformed columns, malformed `pii_sensitive`, and an
unchanged one-table contract:

```python
def test_two_table_ratio_bindings_are_coherent() -> None:
    assert definition_binding_errors(_two_table_contract()) == ()

def test_missing_compares_to_is_refused() -> None:
    contract = _two_table_contract()
    del contract["compares_to"]
    assert definition_binding_errors(contract) == (
        "two-table ratio requires compares_to",
    )

def test_one_table_contract_is_unchanged() -> None:
    assert definition_binding_errors({"definition": _one_table_ratio()}) == ()
```

- [ ] **Step 2: Run RED**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_metric_contract_bindings.py -q
```

Expected: collection failure because `seshat.metric_contract_bindings` is absent.

- [ ] **Step 3: Implement the minimal validator**

Implement focused helpers for mapping coercion, source-table extraction, used
columns, binding validation, and stable error ordering. Activate new checks only
when `compares_to` exists or two valid ratio-side table strings differ:

```python
from collections.abc import Mapping

def definition_binding_errors(
    contract: Mapping[str, object],
) -> tuple[str, ...]:
    definition = contract.get("definition")
    if not isinstance(definition, Mapping):
        return ()
    numerator = definition.get("numerator")
    denominator = definition.get("denominator")
    compares_to = contract.get("compares_to")
    if not isinstance(numerator, Mapping) or not isinstance(denominator, Mapping):
        return (
            ("compares_to requires a ratio numerator and denominator",)
            if compares_to is not None
            else ()
        )
    numerator_table = _source_table(numerator)
    denominator_table = _source_table(denominator)
    is_two_table = compares_to is not None or (
        numerator_table is not None
        and denominator_table is not None
        and numerator_table != denominator_table
    )
    if not is_two_table:
        return ()
    return _validate_two_table_ratio(contract, numerator, denominator)
```

`_validate_two_table_ratio` reports structural errors in stable order and checks
every `_side_columns` value against the appropriate binding column set.

- [ ] **Step 4: Run GREEN and import guard**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_metric_contract_bindings.py tests\unit\test_dax_gen.py::test_dax_gen_import_is_stdlib_only -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/seshat/metric_contract_bindings.py tests/unit/test_metric_contract_bindings.py
git -c commit.gpgsign=false commit -m "feat: validate two-table metric bindings"
```

### Task 2: Integrate the Refusal into Inventory and Generation

**Files:**
- Modify: `src/seshat/metric_contract_inventory.py`
- Modify: `src/seshat/cli/commands/generate.py`
- Modify: `tests/unit/test_metric_contract_inventory.py`
- Modify: `tests/unit/test_dax_gen.py`
- Create: `tests/fixtures/contracts/ratio_two_table.yaml`

**Interfaces:**
- Consumes: `definition_binding_errors(contract)` from Task 1.
- CLI: any error becomes `[refused] <name>: <first error>`, exit 1, empty stdout.
- Inventory: any error is prefixed with the repo-relative contract path.

- [ ] **Step 1: Write RED inventory tests**

Add an approved two-table contract helper and assert matching input is admitted
while missing or mismatched comparison bindings never enter `approved`:

```python
def test_approved_two_table_ratio_requires_coherent_comparison_binding(tmp_path: Path) -> None:
    _write_approval(tmp_path, "sales", ("TotalSales",))
    path = _write(_contract_path(tmp_path, "sales"), _approved_two_table())
    inventory = load_contract_inventory([path], tmp_path)
    assert inventory.errors == ()
    assert ("sales", "TotalSales") in inventory.approved
```

- [ ] **Step 2: Write RED CLI tests and fixture**

The valid fixture declares actuals in `binds_to`, targets in `compares_to`, and
the matching ratio definition. Add success plus temporary-file mutations:

```python
def test_cli_generate_two_table_ratio_roundtrips() -> None:
    result = _run_cli("generate", "--contract", str(CONTRACTS / "ratio_two_table.yaml"))
    assert result.returncode == 0
    assert "DIVIDE(SUM('gold fct_actuals'[amount]), SUM('gold fct_targets'[amount]))" in result.stdout
    assert result.stderr == ""
```

- [ ] **Step 3: Verify RED**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_metric_contract_inventory.py tests\unit\test_dax_gen.py -q
```

Expected: mismatch cases pass incorrectly because callers do not invoke the validator.

- [ ] **Step 4: Add minimal integrations**

In inventory, call the validator from `_definition_error` after existing checks:

```python
binding_errors = definition_binding_errors(raw)
if binding_errors:
    return f"{relative}: {binding_errors[0]}"
```

In `run_generate`, call it after name validation and before generation:

```python
binding_errors = definition_binding_errors(contract)
if binding_errors:
    print(f"[refused] {name}: {binding_errors[0]}", file=sys.stderr)
    return 1
```

- [ ] **Step 5: Run GREEN and compatibility regression**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_metric_contract_bindings.py tests\unit\test_metric_contract_inventory.py tests\unit\test_dax_gen.py tests\unit\test_metric_drift.py -q
```

Expected: PASS, including existing one-table fixtures and round-trip tests.

- [ ] **Step 6: Commit**

```powershell
git add src/seshat/metric_contract_inventory.py src/seshat/cli/commands/generate.py tests/unit/test_metric_contract_inventory.py tests/unit/test_dax_gen.py tests/fixtures/contracts/ratio_two_table.yaml
git -c commit.gpgsign=false commit -m "feat: generate governed two-table ratios"
```

### Task 3: Publish the Contract Shape and Generatable Example

**Files:**
- Create: `tests/unit/test_two_table_ratio_contract.py`
- Modify: `templates/metric-contract.yaml`
- Modify: `templates/metric-contract-shape.variance-vs-target.yaml`
- Regenerate: `integrations/codex/seshat-bi/templates/metric-contract.yaml`
- Regenerate: `integrations/claude-code/seshat-bi/templates/metric-contract.yaml`

**Interfaces:**
- `compares_to` has exactly `gold_table`, `columns`, `pii_sensitive`.
- The variance example has `definition.kind == "ratio"` and matching sources.

- [ ] **Step 1: Write RED template tests**

```python
def test_variance_shape_uses_scalar_comparison_binding_and_ratio_definition() -> None:
    doc = yaml.safe_load(VARIANCE.read_text(encoding="utf-8"))
    assert set(doc["compares_to"]) == {"gold_table", "columns", "pii_sensitive"}
    assert doc["definition"]["kind"] == "ratio"
    assert doc["definition"]["numerator"]["source"]["table"] == doc["binds_to"]["gold_table"]
    assert doc["definition"]["denominator"]["source"]["table"] == doc["compares_to"]["gold_table"]
```

Also assert no concrete target value, RAG boundary, retail table, or C086 token.

- [ ] **Step 2: Run RED**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_two_table_ratio_contract.py -q
```

Expected: FAIL because the root contract lacks `compares_to` and the variance shape lacks a definition.

- [ ] **Step 3: Update the authored templates**

Add the optional comparison block after `binds_to`. Replace pre-ruling comments
with the actual block and add the exact ratio definition from the approved design.
Keep all Principle-V blockers and placeholders unchanged.

- [ ] **Step 4: Regenerate integration copies and inspect scope**

```powershell
C:\Users\user\miniforge3\python.exe scripts\export_agent_bundles.py
git -c safe.directory=C:/Users/user/Documents/GitHub/Seshat-BI diff -- integrations/codex/seshat-bi/templates/metric-contract.yaml integrations/claude-code/seshat-bi/templates/metric-contract.yaml
```

Expected: generated copies mirror only the authored metric-contract change.

- [ ] **Step 5: Run GREEN and bundle drift check**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_two_table_ratio_contract.py -q
C:\Users\user\miniforge3\python.exe scripts\export_agent_bundles.py --check
```

Expected: PASS and zero generated drift.

- [ ] **Step 6: Commit**

```powershell
git add templates/metric-contract.yaml templates/metric-contract-shape.variance-vs-target.yaml integrations/codex/seshat-bi/templates/metric-contract.yaml integrations/claude-code/seshat-bi/templates/metric-contract.yaml tests/unit/test_two_table_ratio_contract.py
git -c commit.gpgsign=false commit -m "docs: publish two-table ratio contract shape"
```

### Task 4: Acceptance, Tracker Reconciliation, and Fence Closure

**Files:**
- Create: `specs/156-governed-two-table-ratio/evidence/validation.md`
- Modify: `specs/156-governed-two-table-ratio/ratify-ledger.md`
- Modify: `specs/156-governed-two-table-ratio/tasks.md`
- Modify: `docs/roadmap/idea-backlog.md`
- Modify: `docs/roadmap/shipped-ideas.yaml`
- Modify: `.specify/feature.json`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run focused and repository gates**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_metric_contract_bindings.py tests\unit\test_metric_contract_inventory.py tests\unit\test_dax_gen.py tests\unit\test_metric_drift.py tests\unit\test_two_table_ratio_contract.py tests\contract\test_dbt_documentation.py -q
C:\Users\user\miniforge3\python.exe -m pytest -m unit -q
C:\Users\user\miniforge3\python.exe -m seshat.cli check
git -c safe.directory=C:/Users/user/Documents/GitHub/Seshat-BI diff --check
```

Record commands, exit codes, pass counts, and environmental limitations in evidence.

- [ ] **Step 2: Reconcile the c19 state**

Add c19 to `shipped-ideas.yaml` with the implementation commit SHA. Update only
the backlog's current-status note so c35 is the sole open ADOPT; preserve the
historical panel body.

- [ ] **Step 3: Close the active spec**

Mark T001-T006 complete only after evidence exists. Set feature JSON to:

```json
{"feature_directory": null}
```

Set both `SPECKIT` bodies to `No active Spec Kit implementation plan.` Spec 157
remains parked until its own ratification.

- [ ] **Step 4: Verify closure and commit**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\contract\test_dbt_documentation.py::test_active_spec_kit_markers_agree_and_resolve -q
git add specs/156-governed-two-table-ratio docs/roadmap/shipped-ideas.yaml docs/roadmap/idea-backlog.md .specify/feature.json AGENTS.md CLAUDE.md
git -c commit.gpgsign=false commit -m "docs: accept governed two-table ratios"
```
