# Main Review Remediation and Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task in the
> prepared worktree. Use `superpowers:test-driven-development` for every code
> change and `superpowers:verification-before-completion` before any completion
> claim. Do not dispatch subagents unless the user separately authorizes them.

**Goal:** Close every agent-authorized defect found in the 2026-07-22 review,
strengthen the Dagster and semantic/readiness boundaries, and land the
highest-value maintainability and operational enhancements without crossing a
human approval or live-execution seam.

**Architecture:** Consolidate Dagster boundary safety into small shared helpers
for output handling, child environments, and run-path identity. Make semantic
readiness depend on a validated approved-contract inventory plus an actual
semantic drift gate. Add repository consistency gates and evidence freshness
signals, then reduce the highest-churn CLI hotspot behind behavior-preserving
tests. Later delivery slices enrich run evidence, portfolio visibility, and
live preflight without executing Power BI or self-granting readiness.

**Tech Stack:** Python 3.11+, argparse, PyYAML loaded lazily at command/rule
boundaries, pytest, Ruff, Dagster 1.13.14, JSON Schema 2020-12, GitHub Actions.

## Global Constraints

- Baseline is committed `main` at
  `29ca82c75bcc72c835f54740eaffd045cfb29eb6` (`v0.6.0`).
- Implement only in `C:\Users\user\Documents\GitHub\Seshat-BI\.worktrees\review-hardening`
  on branch `fix/main-review-hardening`.
- Never execute the Power BI adapter and never write readiness approvals.
- Never change a stage to `pass`; rules and orchestration may only read, block,
  warn, or report named-owner actions.
- Mapping must remain `CLEARED` before silver work and live validation remains
  `[PENDING LIVE PROFILE]` when no DSN/driver is present.
- C086 is an example, never a generic schema. The real-client-name decision in
  Task 10 is owner-only and must not be inferred by an agent.
- Redaction always happens before truncation, serialization, logging, or
  exception rendering.
- Child processes receive a positive environment allowlist, never an ambient
  copy of `os.environ`.
- Filesystem-derived inputs are repository-contained and tracked-only by
  default in Git workspaces; non-Git workspaces retain a documented fallback.
- No numeric confidence, maturity, or health score may enter readiness or run
  evidence.
- Official CodeScene MCP is not connected. Do not claim an official Code Health
  score; use Ruff, tests, Git churn, and local complexity evidence until the MCP
  server is configured.

## Baseline Evidence

- Ruff: all checks passed; 644 files already formatted.
- Unit selection: 3198 passed, 21 skipped, 194 deselected.
- Worktree was clean before this plan file was added.

## Delivery Order and Progress Checklist

### Delivery A -- release-blocking correctness and security

- [x] Task 1: one redact-before-tail primitive used by both Dagster runners
- [x] Task 2: positive child-environment allowlist
- [x] Task 3: run-id validation and path containment
- [x] Task 4: non-executing Dagster doctor metadata probe
- [x] Task 5: approved metric-contract inventory
- [x] Task 6: complete tracked semantic binding gate
- [x] Task 7: Dagster contract and semantic STOP edges

### Delivery B -- repository and governance consistency

- [x] Task 8: readiness audit-freshness warning and owner handoff
- [x] Task 9: GitHub Actions pinning and inactive Spec Kit state
- [ ] Task 10: owner-gated C086 confidentiality disposition
- [x] Task 11: behavior-preserving CLI parser hotspot split

### Delivery C -- operational enhancements

- [x] Task 12: tamper-evident Dagster run evidence
- [x] Task 13: portfolio contract/live/run visibility
- [x] Task 14: safe live-preflight diagnostics
- [x] Task 15: full verification and completion audit

---

### Task 1: Centralize redact-before-tail output handling

**Files:**
- Modify: `src/seshat/dagster_adapter/redaction.py`
- Modify: `src/seshat/dagster_adapter/runner.py`
- Modify: `orchestration/dagster/src/tower_bi_orchestration/commands.py`
- Test: `tests/unit/test_dagster_redaction.py`
- Create: `orchestration/dagster/tests/test_command_boundary.py`

**Interfaces:**
- Produces: `redact_and_tail(text: str, max_chars: int) -> str`
- Consumed by: parent `execute_run` and inner `run_gate_command`

- [x] **Step 1: Add failing unit tests for boundary-straddling secrets**

Add to `tests/unit/test_dagster_redaction.py`:

```python
def test_redact_and_tail_removes_partial_dsn_before_slicing(monkeypatch) -> None:
    from seshat.dagster_adapter import redaction

    monkeypatch.setattr(redaction, "_secret_env_values", lambda: [])
    secret = "postgresql://alice:s3cretpw@db.example.internal/gold"
    raw_tail = secret[-40:]
    assert "://" not in raw_tail and "s3cretpw" in raw_tail
    cleaned = redaction.redact_and_tail(secret, 40)
    assert "s3cretpw" not in cleaned
    assert "REDACTED" in cleaned


def test_redact_and_tail_zero_limit_is_empty() -> None:
    from seshat.dagster_adapter.redaction import redact_and_tail

    assert redact_and_tail("visible", 0) == ""
```

Create `orchestration/dagster/tests/test_command_boundary.py`:

```python
from __future__ import annotations

import subprocess

from tower_bi_orchestration import commands


def test_gate_command_redacts_full_output_before_tail(monkeypatch, tmp_path) -> None:
    secret = "postgresql://alice:s3cretpw@db.example.internal/gold"
    monkeypatch.setattr(commands, "_TAIL_CHARS", 40)
    monkeypatch.setattr(
        commands.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="prefix" * 20, stderr=secret
        ),
    )
    code, output = commands.run_gate_command(["gate"], tmp_path)
    assert code == 1
    assert "s3cretpw" not in output
```

- [x] **Step 2: Verify the new tests fail**

```powershell
$env:PYTHONPATH = "$PWD\src;$PWD\orchestration\dagster\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_dagster_redaction.py orchestration/dagster/tests/test_command_boundary.py -q -p no:cacheprovider --no-cov
```

Expected: fail because `redact_and_tail` does not exist and the inner runner
still slices first.

- [x] **Step 3: Implement and adopt the shared helper**

Add to `src/seshat/dagster_adapter/redaction.py`:

```python
def redact_and_tail(text: str, max_chars: int) -> str:
    """Redact the complete payload, then return at most ``max_chars`` chars."""
    if max_chars < 0:
        raise ValueError("max_chars must be non-negative")
    if max_chars == 0:
        return ""
    return redact_text(text).strip()[-max_chars:]
```

Replace the direct `redact_text(...)[-_TAIL_CHARS:]` logic in both runners with:

```python
output=redact_and_tail(combined, _TAIL_CHARS)
```

and:

```python
return proc.returncode, redact_and_tail(combined, _TAIL_CHARS)
```

- [x] **Step 4: Run focused tests and Ruff**

Run the Step 2 command, followed by:

```powershell
C:\Users\user\miniforge3\python.exe -m ruff check src/seshat/dagster_adapter orchestration/dagster/src orchestration/dagster/tests/test_command_boundary.py tests/unit/test_dagster_redaction.py
C:\Users\user\miniforge3\python.exe -m ruff format --check src/seshat/dagster_adapter orchestration/dagster/src orchestration/dagster/tests/test_command_boundary.py tests/unit/test_dagster_redaction.py
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add src/seshat/dagster_adapter/redaction.py src/seshat/dagster_adapter/runner.py orchestration/dagster/src/tower_bi_orchestration/commands.py tests/unit/test_dagster_redaction.py orchestration/dagster/tests/test_command_boundary.py
git commit -m "fix: redact Dagster output before truncation"
```

---

### Task 2: Allowlist the Dagster child environment

**Files:**
- Create: `src/seshat/dagster_adapter/environment.py`
- Modify: `src/seshat/dagster_adapter/runner.py`
- Modify: `tests/unit/test_dagster_runner.py`
- Modify: `tests/unit/test_cli_dagster.py`
- Modify: `docs/integrations/dagster-adapter.md`

**Interfaces:**
- Produces: `allowed_child_environment(source: Mapping[str, str]) -> dict[str, str]`
- Consumed by: `runner._child_env`

- [x] **Step 1: Add failing least-privilege tests**

Add to `tests/unit/test_dagster_runner.py`:

```python
def test_child_environment_drops_unrelated_ambient_secrets(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("UNRELATED_REVIEW_SECRET", "must-not-cross")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    monkeypatch.setenv("SESHAT_DBT_HOST", "db.internal")
    env = runner._child_env(tmp_path, "run-001", "orders", "csv")
    assert "UNRELATED_REVIEW_SECRET" not in env
    assert env["DATABASE_URL"] == "postgresql://u:p@h/db"
    assert env["SESHAT_DBT_HOST"] == "db.internal"


def test_child_environment_keeps_required_windows_and_tls_keys(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
    monkeypatch.setenv("PATH", r"C:\Python")
    monkeypatch.setenv("SSL_CERT_FILE", r"C:\certs\ca.pem")
    env = runner._child_env(tmp_path, "run-001", None, "csv")
    assert env["SYSTEMROOT"] == r"C:\Windows"
    assert env["PATH"] == r"C:\Python"
    assert env["SSL_CERT_FILE"] == r"C:\certs\ca.pem"
```

- [x] **Step 2: Verify failure**

Run:

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_dagster_runner.py tests/unit/test_cli_dagster.py -q -p no:cacheprovider --no-cov
```

Expected: the unrelated secret is currently present.

- [x] **Step 3: Implement the allowlist**

Create `src/seshat/dagster_adapter/environment.py`:

```python
from __future__ import annotations

from collections.abc import Mapping

_EXACT_KEYS = frozenset(
    {
        "COMSPEC",
        "DAGSTER_HOME",
        "DATABASE_URL",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "PYTHONIOENCODING",
        "PYTHONPATH",
        "PYTHONUTF8",
        "REQUESTS_CA_BUNDLE",
        "SESHAT_RAW_LANDING_DIR",
        "SSL_CERT_FILE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
)
_PREFIXES = ("ANALYTICS_DB_", "SESHAT_DBT_")


def allowed_child_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Return only OS runtime and governed Seshat connection variables."""
    return {
        key: value
        for key, value in source.items()
        if key in _EXACT_KEYS or key.startswith(_PREFIXES)
    }
```

Change `_child_env` to start with:

```python
env = allowed_child_environment(os.environ)
```

Retain the existing run-scoped overrides and default-mode `pop` behavior.

- [x] **Step 4: Update docs and test the `.env` overlay contract**

Document that only governed connection/runtime keys cross into the orchestration
child. Update the existing CLI `.env` propagation test to assert a governed key
crosses and an unrelated key does not.

- [ ] **Step 5: Run focused tests, Ruff, and commit**

Expected: focused tests pass and the captured child environment contains no
unrelated secret.

```powershell
git add src/seshat/dagster_adapter/environment.py src/seshat/dagster_adapter/runner.py tests/unit/test_dagster_runner.py tests/unit/test_cli_dagster.py docs/integrations/dagster-adapter.md
git commit -m "fix: allowlist Dagster child environment"
```

---

### Task 3: Validate run identity and contain every evidence path

**Files:**
- Create: `src/seshat/dagster_adapter/run_identity.py`
- Modify: `src/seshat/dagster_adapter/evidence.py`
- Modify: `src/seshat/dagster_adapter/evidence_render.py`
- Modify: `schemas/dagster-run-evidence.schema.json`
- Modify: `tests/unit/test_dagster_evidence.py`
- Modify: `tests/contract/test_dagster_evidence_schema.py`
- Modify: `tests/unit/test_cli_dagster.py`

**Interfaces:**
- Produces: `validate_run_id(value: str) -> str`
- Produces: `contained_path(root: Path, *parts: str) -> Path`

- [x] **Step 1: Add failing traversal and schema tests**

Add to `tests/unit/test_dagster_evidence.py`:

```python
@pytest.mark.parametrize(
    "run_id",
    ("../escape", "..\\escape", ".", "..", "C:drive", "/absolute", "a/b"),
)
def test_run_id_rejects_path_syntax(tmp_path: Path, run_id: str) -> None:
    with pytest.raises(ValueError, match="run id"):
        evidence.evidence_out_path(tmp_path, run_id)


def test_safe_legacy_run_id_remains_supported(tmp_path: Path) -> None:
    path = evidence.evidence_out_path(tmp_path, "run-001")
    assert path.is_relative_to(tmp_path.resolve())
```

Add contract assertions that both summary and record `run_id` schemas use:

```text
^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$
```

- [x] **Step 2: Verify failure**

Run:

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_dagster_evidence.py tests/contract/test_dagster_evidence_schema.py tests/unit/test_cli_dagster.py -q -p no:cacheprovider --no-cov
```

- [x] **Step 3: Implement identity and containment helpers**

Create `src/seshat/dagster_adapter/run_identity.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def validate_run_id(value: str) -> str:
    if not isinstance(value, str) or not _RUN_ID_RE.fullmatch(value):
        raise ValueError(
            "run id must be 1-128 ASCII letters, digits, dot, underscore, or dash"
        )
    return value


def contained_path(root: Path, *parts: str) -> Path:
    base = Path(root).resolve()
    candidate = base.joinpath(*parts).resolve(strict=False)
    if candidate != base and not candidate.is_relative_to(base):
        raise ValueError("run evidence path escapes its governed root")
    return candidate
```

Use these helpers in `run_dir`, `evidence_out_path`, and `load_run`. Validate
before any `mkdir`, read, or write. Update both JSON Schema locations with the
same regex.

- [x] **Step 4: Add an existing-symlink containment regression**

Where symlink creation is available, create a symlink inside `run-evidence`
pointing outside and assert `contained_path` refuses it. Mark only the symlink
creation capability as skipped on restricted Windows; traversal tests must
always run.

- [ ] **Step 5: Run focused tests, Ruff, and commit**

```powershell
git add src/seshat/dagster_adapter/run_identity.py src/seshat/dagster_adapter/evidence.py src/seshat/dagster_adapter/evidence_render.py schemas/dagster-run-evidence.schema.json tests/unit/test_dagster_evidence.py tests/contract/test_dagster_evidence_schema.py tests/unit/test_cli_dagster.py
git commit -m "fix: contain Dagster run evidence paths"
```

---

### Task 4: Make Dagster doctor a non-executing metadata probe

**Files:**
- Modify: `src/seshat/dagster_adapter/doctor.py`
- Modify: `tests/unit/test_dagster_doctor.py`
- Modify: `tests/unit/dagster_adapter/test_doctor_engine_mode.py`
- Modify: `docs/integrations/dagster-adapter.md`

**Interfaces:**
- Produces: `_venv_site_packages(venv: Path) -> tuple[Path, ...]`
- Produces: `_distribution_metadata_present(venv: Path, name: str) -> bool`

- [x] **Step 1: Add failing no-execution tests**

Add tests that create:

```text
orchestration/dagster/.venv/Lib/site-packages/dbt_core-1.12.0.dist-info/METADATA
```

and the POSIX equivalent under `lib/python3.13/site-packages`. Monkeypatch
`doctor.subprocess.run` to raise `AssertionError("doctor executed repository code")`.
Assert `_dbt_runtime_present(root)` is true for the metadata fixture and false
when the metadata directory is absent.

- [x] **Step 2: Verify the tests fail**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_dagster_doctor.py tests/unit/dagster_adapter/test_doctor_engine_mode.py -q -p no:cacheprovider --no-cov
```

Expected: existing code calls the planted interpreter through
`subprocess.run`.

- [x] **Step 3: Replace interpreter execution with metadata inspection**

Add:

```python
def _venv_site_packages(venv: Path) -> tuple[Path, ...]:
    candidates = [venv / "Lib" / "site-packages"]
    candidates.extend(sorted((venv / "lib").glob("python*/site-packages")))
    return tuple(path for path in candidates if path.is_dir())


def _distribution_metadata_present(venv: Path, name: str) -> bool:
    normalized = name.replace("-", "_")
    return any(
        any(site.glob(f"{normalized}-*.dist-info/METADATA"))
        for site in _venv_site_packages(venv)
    )
```

Change `_dbt_runtime_present` to inspect the `.venv` directory derived from
`orchestration_dir(root)` and remove the executable probe. `orchestration_python`
remains for the explicitly executable `dagster run` command.

- [x] **Step 4: Update documentation and run focused verification**

Document that doctor reads project, venv, and distribution metadata only; it
does not execute the venv.

```powershell
git add src/seshat/dagster_adapter/doctor.py tests/unit/test_dagster_doctor.py tests/unit/dagster_adapter/test_doctor_engine_mode.py docs/integrations/dagster-adapter.md
git commit -m "fix: keep Dagster doctor non-executing"
```

---

### Task 5: Build a reusable approved metric-contract inventory

**Files:**
- Create: `src/seshat/metric_contract_inventory.py`
- Create: `tests/unit/test_metric_contract_inventory.py`
- Modify: `src/seshat/cli/commands/semantic.py`

**Interfaces:**
- Produces: `MetricContract(name, path, definition, evidence)`
- Produces: `ContractInventory(approved, errors)`
- Produces: `load_contract_inventory(paths: Iterable[Path], root: Path) -> ContractInventory`

- [x] **Step 1: Add failing inventory tests**

Cover these exact cases:

1. approved contract: stem equals `name`, readiness is `pass`, evidence is
   nonempty, definition is a mapping;
2. zero contracts;
3. unreadable YAML;
4. stem/name mismatch;
5. duplicate contract name;
6. `blocked`, `warning`, or `not_started` readiness;
7. `pass` without evidence;
8. missing structured definition.

The approved fixture must result in one `MetricContract`; every other fixture
must produce a concrete repo-relative error and never enter `approved`.

- [x] **Step 2: Verify tests fail**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_metric_contract_inventory.py -q -p no:cacheprovider --no-cov
```

- [x] **Step 3: Implement immutable inventory types and lazy YAML loading**

Create:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MetricContract:
    name: str
    path: Path
    definition: dict
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ContractInventory:
    approved: dict[str, MetricContract]
    errors: tuple[str, ...]


def load_contract_inventory(paths: Iterable[Path], root: Path) -> ContractInventory:
    import yaml

    approved: dict[str, MetricContract] = {}
    errors: list[str] = []
    seen_names: set[str] = set()
    resolved_root = root.resolve()
    for path in sorted(paths):
        try:
            relative = path.resolve().relative_to(resolved_root).as_posix()
        except ValueError:
            errors.append(f"{path}: metric contract escapes repository root")
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: unreadable metric contract: {exc}")
            continue
        if not isinstance(raw, dict):
            errors.append(f"{relative}: metric contract must be a mapping")
            continue
        name = raw.get("name")
        readiness = raw.get("readiness")
        definition = raw.get("definition")
        if not isinstance(name, str) or name != path.stem:
            errors.append(f"{relative}: contract name must equal file stem")
            continue
        if name in seen_names:
            errors.append(f"{relative}: duplicate metric contract name {name!r}")
            continue
        seen_names.add(name)
        if not isinstance(readiness, dict) or readiness.get("status") != "pass":
            errors.append(f"{relative}: metric contract is not owner-approved pass")
            continue
        evidence = readiness.get("evidence")
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) and item.strip() for item in evidence
        ):
            errors.append(f"{relative}: approved contract requires evidence[]")
            continue
        if not isinstance(definition, dict):
            errors.append(f"{relative}: approved contract requires definition mapping")
            continue
        approved[name] = MetricContract(name, path, definition, tuple(evidence))
    return ContractInventory(approved, tuple(errors))
```

Refactor semantic command contract loading to consume the inventory rather
than calling `load_definition` directly.

- [x] **Step 4: Run focused tests and Ruff**

```powershell
git add src/seshat/metric_contract_inventory.py src/seshat/cli/commands/semantic.py tests/unit/test_metric_contract_inventory.py
git commit -m "feat: validate approved metric contract inventory"
```

---

### Task 6: Enforce complete tracked semantic bindings

**Files:**
- Modify: `src/seshat/cli/parser.py`
- Modify: `src/seshat/cli/commands/semantic.py`
- Modify: `src/seshat/semantic.py`
- Modify: `tests/unit/test_cli_semantic.py`
- Modify: `tests/unit/test_semantic.py`
- Modify: `docs/readiness/semantic-model-ready.md`

**Interfaces:**
- Produces: tracked-by-default semantic input discovery in Git repositories
- Produces: error findings for missing, orphaned, unapproved, or invalid bindings
- CLI escape hatch: `--include-untracked` for deliberate local inspection

- [x] **Step 1: Change the previously permissive negative test**

Replace `test_semantic_check_measure_without_contract_is_skipped` with a test
expecting exit 1 and a message naming `AvgTransactionValue` and `no approved
metric contract`. Add tests for:

- an approved contract with no corresponding TMDL measure;
- an unapproved contract;
- an invalid contract inventory;
- an untracked drift file ignored by default in an initialized Git repo;
- the same untracked file included and detected with `--include-untracked`;
- non-Git filesystem fallback still working.

- [x] **Step 2: Verify the tests fail**

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = "*"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_cli_semantic.py tests/unit/test_semantic.py -q -p no:cacheprovider --no-cov
```

- [x] **Step 3: Implement tracked input discovery**

Add a private helper in the semantic command:

```python
def _semantic_files(repo: Path, include_untracked: bool) -> tuple[Path, ...]:
    def is_input(path: Path) -> bool:
        rel = path.relative_to(repo).as_posix()
        if rel.startswith("tests/") or "/tests/" in rel:
            return False
        return (
            "/metrics/" in f"/{rel}" and rel.endswith(".yaml")
        ) or (
            ".SemanticModel/definition/" in rel and rel.endswith(".tmdl")
        )

    if not include_untracked:
        from seshat.gitutil import git_output

        try:
            raw = git_output(repo, "ls-files", "-z")
        except RuntimeError:
            raw = ""
        else:
            return tuple(
                repo / rel
                for rel in raw.split("\0")
                if rel and is_input(repo / rel)
            )
    candidates = sorted(repo.rglob("*.yaml")) + sorted(repo.rglob("*.tmdl"))
    return tuple(path for path in candidates if is_input(path))
```

Filter the fallback to contract and SemanticModel locations before parsing.
Use the hardened `gitutil.git_output`; do not invoke raw Git from this command.

- [x] **Step 4: Enforce binding completeness**

Build `measure_names` from parsed TMDL. Emit an L3 `Severity.ERROR` for every:

- measure not present in approved inventory;
- approved inventory name not present in TMDL;
- inventory validation error.

Continue running denominator drift for the intersection. Exit 1 when any error
exists. Add `--include-untracked` to `_add_semantic_and_value_check_parsers` and
read it with `getattr(args, "include_untracked", False)` for compatibility.

- [x] **Step 5: Correct the stale readiness documentation**

Change the status note from “Planning” to “Built” and document that complete
bindings, approved contracts, and clean semantic drift are required together.

- [ ] **Step 6: Run focused tests, the CLI contract tests, and commit**

```powershell
git add src/seshat/cli/parser.py src/seshat/cli/commands/semantic.py src/seshat/semantic.py tests/unit/test_cli_semantic.py tests/unit/test_semantic.py docs/readiness/semantic-model-ready.md
git commit -m "fix: require complete approved semantic bindings"
```

---

### Task 7: Enforce contract and semantic STOP edges in Dagster

**Files:**
- Modify: `orchestration/dagster/src/tower_bi_orchestration/commands.py`
- Modify: `orchestration/dagster/src/tower_bi_orchestration/assets/downstream.py`
- Modify: `orchestration/dagster/tests/conftest.py`
- Modify: `orchestration/dagster/tests/test_human_seam.py`
- Create: `orchestration/dagster/tests/test_semantic_gate.py`
- Modify: `docs/integrations/dagster-adapter.md`

**Interfaces:**
- Produces: `semantic_argv() -> list[str]`
- Metric-contract asset blocks on zero/invalid/unapproved contracts
- Semantic-model asset requires static check, semantic check, and human approval

- [x] **Step 1: Add failing orchestration tests**

Create tests proving:

1. removing the fixture `metrics` directory makes `metric_contracts` raise a
   Dagster `Failure`, recording `blocked`, `contracts_found: 0`, and owner
   `the metric owner`;
2. a contract with `readiness.status: blocked` blocks;
3. semantic command exit 1 records `failed` and prevents approval materialization;
4. static check exit 1 prevents semantic command execution;
5. both commands green plus an existing approval materialize the asset;
6. no test helper silently creates a contract unless the test requests one.

Update the default fixture contract to a complete approved contract instead of
the current shape-only `metric: A` file:

```yaml
name: "AMetric"
definition:
  additive: true
  numerator: {aggregation: sum, filter: []}
  denominator: null
readiness:
  status: "pass"
  evidence: ["approved by M. Owner (metric_owner) on 2026-01-01"]
  blocking_reasons: []
```

Store it as `metrics/AMetric.yaml` so stem and `name` agree.

- [x] **Step 2: Verify failure**

```powershell
$env:PYTHONPATH = "$PWD\src;$PWD\orchestration\dagster\src"
C:\Users\user\miniforge3\python.exe -m pytest orchestration/dagster/tests/test_semantic_gate.py orchestration/dagster/tests/test_human_seam.py -q -p no:cacheprovider --no-cov
```

- [x] **Step 3: Add the semantic command and fail-closed inventory read**

In `commands.py`:

```python
def semantic_argv() -> list[str]:
    return [
        sys.executable,
        "-m",
        "seshat.cli",
        "semantic-check",
        "--repo",
        ".",
        "--metrics-dir",
        "mappings",
    ]
```

In `metric_contracts`, load only `mappings/<table>/metrics/*.yaml` through
`load_contract_inventory`. Halt with a concrete blocking reason when there are
no approved contracts or inventory errors. Record both `contracts_found` and
`approved_contracts`.

- [x] **Step 4: Execute both machine gates before reading approval**

Keep `seshat check` first. Run `semantic_argv` only after it succeeds. On a
semantic nonzero exit, record `failed` with redacted output tail. Read the
committed `semantic_model_ready` approval only after both gates pass.

- [x] **Step 5: Update docs and run the full orchestration suite**

```powershell
$env:PYTHONPATH = "$PWD\src;$PWD\orchestration\dagster\src"
C:\Users\user\miniforge3\python.exe -m pytest orchestration/dagster/tests -q -p no:cacheprovider --no-cov
git add orchestration/dagster/src/tower_bi_orchestration/commands.py orchestration/dagster/src/tower_bi_orchestration/assets/downstream.py orchestration/dagster/tests docs/integrations/dagster-adapter.md
git commit -m "fix: enforce Dagster semantic contract gates"
```

---

### Task 8: Surface stale readiness audit metadata without self-attestation

**Files:**
- Modify: `src/seshat/rules/readiness_status.py`
- Modify: `tests/unit/test_readiness_status.py`
- Modify: `docs/readiness/readiness-model.md`
- Human-only after implementation: `mappings/retail_store_sales/readiness-status.yaml`

**Interfaces:**
- Produces: RS1 warning when `last_checked_at` predates the latest valid approval
- Does not update any date, approval, stage, or evidence itself

- [x] **Step 1: Add failing freshness tests**

Add tests for valid ISO dates, missing/invalid `last_checked_at`, invalid
approval dates, equal dates, and an approval later than `last_checked_at`.
The stale case must produce `Severity.WARNING`, name both dates, and preserve
exit-zero behavior when no ERROR exists.

- [x] **Step 2: Implement date parsing and comparison**

Use `datetime.date.fromisoformat`. Only shape-valid approvals participate.
Malformed dates produce RS1 ERROR because freshness cannot be established.
A valid but older `last_checked_at` produces WARNING:

```text
last_checked_at 2026-06-25 predates latest approval 2026-07-05; a named human
must recompute the audit metadata
```

- [x] **Step 3: Run focused tests and static governance**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_readiness_status.py -q -p no:cacheprovider --no-cov
C:\Users\user\miniforge3\python.exe -m seshat.cli check
```

Expected: static check exits 0 but reports the existing retail example warning.

- [x] **Step 4: Record the owner-only action without changing audit metadata**

Do not edit `last_checked_at` or `checked_by`. Present the latest approval date,
the files reviewed, and the exact owner action required. Only after a named
human confirms that a recomputation occurred may that human-authored change be
included.

- [ ] **Step 5: Commit code and docs separately from any owner-authored record**

```powershell
git add src/seshat/rules/readiness_status.py tests/unit/test_readiness_status.py docs/readiness/readiness-model.md
git commit -m "feat: report stale readiness audit metadata"
```

---

### Task 9: Restore supply-chain pinning and represent no active Spec Kit plan

**Files:**
- Modify: `.github/workflows/dagster-smoke.yml`
- Modify: `.specify/feature.json`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `tests/contract/test_dbt_documentation.py`
- Create: `tests/unit/test_workflow_security.py`

**Interfaces:**
- Dagster workflow uses the same reviewed action SHAs as other workflows
- Spec Kit state supports either one active existing plan or explicit `null`

- [x] **Step 1: Add failing workflow and active-plan tests**

The workflow test must assert:

```python
assert "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0" in text
assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in text
assert "permissions:" in text and "contents: read" in text
assert "actions/checkout@v" not in text
assert "actions/setup-python@v" not in text
```

Change the active-plan contract test to load `.specify/feature.json`. When
`feature_directory` is `null`, AGENTS and CLAUDE must both contain exactly
`No active Spec Kit implementation plan.` inside their fences and contain no
plan reference. When it is a string, both references must agree, the plan and
tasks files must exist, and at least one task must be unchecked.

- [x] **Step 2: Verify tests fail**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_workflow_security.py tests/contract/test_dbt_documentation.py -q -p no:cacheprovider --no-cov
```

- [x] **Step 3: Pin the workflow and minimize permissions**

At workflow top level set `permissions: {}`. At the job set:

```yaml
permissions:
  contents: read
```

Use the exact checkout/setup-python SHAs asserted above, matching `ci.yml`.

- [x] **Step 4: Clear the completed active-plan pointer**

Set:

```json
{"feature_directory": null}
```

Replace both SPECKIT fenced bodies with the exact no-active sentence. Do not
alter the SESHAT-KIT generated region.

- [x] **Step 5: Run kit gates and focused verification**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_workflow_security.py tests/contract/test_dbt_documentation.py -q -p no:cacheprovider --no-cov
C:\Users\user\miniforge3\python.exe -m seshat.cli kit-lint --repo .
git add .github/workflows/dagster-smoke.yml .specify/feature.json AGENTS.md CLAUDE.md tests/unit/test_workflow_security.py tests/contract/test_dbt_documentation.py
git commit -m "fix: restore workflow and active-plan governance"
```

---

### Task 10: Resolve the C086 confidentiality item only through owner authority

**Implementation status (2026-07-22): BLOCKED.** The disclosure inventory was
re-run. The named owner must choose authorize or anonymize before any shipped
identity wording, generated bundle, or security record is changed.

**Files inspected:**
- `docs/security/security-scan-2026-07-15.md`
- `integrations/claude-code/seshat-bi/templates/metric-contract.yaml`
- `integrations/codex/seshat-bi/templates/metric-contract.yaml`
- other matches returned by the command below

**Human decision:** choose exactly one disposition.

- **Authorize:** retain the client name and internal code, with an owner-authored
  decision artifact that names scope and publication surfaces.
- **Anonymize:** replace public/generic shipped references with neutral example
  language while keeping the filled C086 worked example clearly separated.

- [ ] **Step 1: Produce the non-mutating disclosure inventory**

```powershell
rg -n --hidden --glob '!.git/**' 'El Ezaby|C086|c086' integrations templates docs .claude .agents
```

Record path, line, shipped surface, and whether the reference is a generic
template or the explicitly filled worked example.

- [ ] **Step 2: Stop for the owner ruling**

No agent may select authorize/anonymize. If no named owner ruling is supplied,
record this task as `blocked` with the inventory and continue only with tasks
that do not publish or edit the identity.

- [ ] **Step 3A: If the owner authorizes retention**

Add the owner-authored decision artifact under `docs/security/decisions/`, cite
it from the security scan, and add a contract test requiring the authorization
artifact whenever a generic distributed template contains the identity.

- [ ] **Step 3B: If the owner requires anonymization**

Change only public/generic template prose to `C086 worked example` or `example
retail client` as the owner directs. Regenerate Claude/Codex bundles through the
existing exporter and run the generated-bundle contract tests. Do not rewrite
historical security or release records that truthfully describe the past.

- [ ] **Step 4: Verify the selected disposition**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/contract/test_generated_agent_bundles.py tests/contract/test_public_knowledge_allowlist.py -q -p no:cacheprovider --no-cov
```

Commit message must name the owner-approved disposition, not claim an agent
made the confidentiality judgment.

---

### Task 11: Split the CLI parser hotspot without changing the public CLI

**Files:**
- Create: `src/seshat/cli/parser_core.py`
- Create: `src/seshat/cli/parser_validation.py`
- Create: `src/seshat/cli/parser_dagster.py`
- Modify: `src/seshat/cli/parser.py`
- Modify: `tests/unit/test_cli.py`
- Modify: `tests/unit/test_cli_dagster.py`
- Modify: `tests/unit/test_cli_semantic.py`

**Interfaces:**
- Each new module exports one `add_*_parsers(sub)` function
- `_build_parser` remains the only root parser constructor
- Command names, defaults, aliases, help, exit codes, and lazy imports remain
  byte-for-byte compatible where user-visible

- [ ] **Step 1: Add parser-surface characterization tests**

Capture for every moved command:

- parsed namespace for minimal valid argv;
- `--help` exit and critical option text;
- default values;
- alias behavior;
- no YAML/Dagster/db driver import during root parser import.

- [ ] **Step 2: Extract validation parsers**

Move `_add_check_parser`, `_add_validate_parser`, `_add_profile_parser`,
`_add_drift_parser`, and `_add_semantic_and_value_check_parsers` to
`parser_validation.py`. Pass only the subparser action; do not import command
handlers from parser modules.

- [ ] **Step 3: Extract Dagster and core workflow parsers**

Move `_add_dagster_parser` to `parser_dagster.py`. Move the first-arrival,
status, next-action, approvals, blockers, and evidence-pack builders to
`parser_core.py`. Keep PBIR/theme, ecosystem, adoption, and dbt parsers in their
existing modules/slices.

- [ ] **Step 4: Verify behavior and measure the result**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_cli.py tests/unit/test_cli_dagster.py tests/unit/test_cli_semantic.py tests/unit/test_cli_value_check.py tests/unit/test_cli_profile.py tests/unit/test_cli_drift.py -q -p no:cacheprovider --no-cov
(Get-Content src/seshat/cli/parser.py | Measure-Object -Line).Lines
```

Acceptance: focused tests pass and `parser.py` is below 800 lines without
duplicating parser definitions.

- [ ] **Step 5: Ruff and commit**

```powershell
git add src/seshat/cli/parser.py src/seshat/cli/parser_core.py src/seshat/cli/parser_validation.py src/seshat/cli/parser_dagster.py tests/unit/test_cli.py tests/unit/test_cli_dagster.py tests/unit/test_cli_semantic.py
git commit -m "refactor: split CLI parser by command family"
```

---

### Task 12: Make Dagster run evidence tamper-evident and comparable

**Files:**
- Modify: `src/seshat/dagster_adapter/evidence.py`
- Modify: `src/seshat/dagster_adapter/evidence_render.py`
- Modify: `schemas/dagster-run-evidence.schema.json`
- Modify: `templates/dagster-run-evidence.md`
- Modify: `tests/unit/test_dagster_evidence.py`
- Modify: `tests/contract/test_dagster_evidence_schema.py`
- Modify: `orchestration/dagster/tests/test_evidence_records.py`

**Interfaces:**
- Summary gains `workspace_dirty: bool`, `records_sha256: str`, and
  `input_artifacts: {relative_path: sha256}`
- No secret, absolute path, readiness score, or approval is recorded

- [ ] **Step 1: Add failing digest tests**

Tests must prove:

- changing one records byte changes `records_sha256`;
- input digests cover the selected table's source map, readiness status,
  approved metric contracts, warehouse migrations, and tracked TMDL;
- paths are repo-relative POSIX paths;
- dirty workspace is recorded as a boolean, never interpreted as approval;
- rendered evidence refuses a digest mismatch;
- secrets remain absent from paths and values.

- [ ] **Step 2: Implement hardened Git state and SHA-256 helpers**

Reuse `seshat.gitutil.git_output` for tracked files and revision state. Use
`hashlib.sha256(path.read_bytes()).hexdigest()` only after containment and
tracked-file filtering. Sort keys before serialization.

- [ ] **Step 3: Bind summary to records**

Write records first, calculate their digest, then atomically write summary.
During `load_run`, recompute the records digest and reject mismatch before
rendering.

- [ ] **Step 4: Update schema/template and compatibility tests**

Require 64 lowercase hexadecimal characters for every digest. Existing raw
fixtures must be upgraded deliberately; do not silently default missing hashes.

- [ ] **Step 5: Run evidence suites and commit**

```powershell
$env:PYTHONPATH = "$PWD\src;$PWD\orchestration\dagster\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_dagster_evidence.py tests/contract/test_dagster_evidence_schema.py orchestration/dagster/tests/test_evidence_records.py -q -p no:cacheprovider --no-cov
git add src/seshat/dagster_adapter/evidence.py src/seshat/dagster_adapter/evidence_render.py schemas/dagster-run-evidence.schema.json templates/dagster-run-evidence.md tests/unit/test_dagster_evidence.py tests/contract/test_dagster_evidence_schema.py orchestration/dagster/tests/test_evidence_records.py
git commit -m "feat: bind Dagster evidence to inputs and records"
```

---

### Task 13: Add contract, live-boundary, and last-run visibility to portfolio watch

**Files:**
- Modify: `src/seshat/portfolio_watch.py`
- Modify: `src/seshat/agent_next.py`
- Create: `tests/unit/test_portfolio_watch_semantic_run.py`
- Modify: `tests/unit/test_agent_next.py`
- Modify: `docs/tools/portfolio-watch.md`

**Interfaces:**
- Each governed scope gains categorical fields:
  `contract_binding_state`, `live_validation_state`, `last_dagster_run`
- Allowed values remain categorical; no numeric score is added

- [ ] **Step 1: Add failing mixed-state fixtures**

Cover:

- no metrics directory -> `missing`;
- approved complete contracts and clean semantic evidence -> `verified`;
- unapproved/missing binding -> `blocked` with metric owner;
- no DSN/live evidence -> `pending_live`;
- stale Dagster input digest or older source revision -> `stale`;
- no run evidence -> `unavailable`, not failure.

- [ ] **Step 2: Compose existing readers rather than duplicate policy**

Use the Task 5 inventory, Task 12 evidence verifier, existing
`_is_stale_captured_at`, and existing readiness/agent-next vocabulary. Do not
open a DB and do not infer an approval from a green machine gate.

- [ ] **Step 3: Make next action deterministic**

When semantic contracts are incomplete, return the existing
`kpi-contract-builder`/metric-owner action and explicitly forbid dashboard
design. When live proof is absent after Gold, return `retail-validate` with
`[PENDING LIVE PROFILE]` enable steps. Preserve stage ordering.

- [ ] **Step 4: Run portfolio/next tests and commit**

```powershell
$env:PYTHONPATH = "$PWD\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/unit/test_portfolio_watch_semantic_run.py tests/unit/test_portfolio_watch_next_action.py tests/unit/test_portfolio_watch_stale.py tests/unit/test_agent_next.py -q -p no:cacheprovider --no-cov
git add src/seshat/portfolio_watch.py src/seshat/agent_next.py tests/unit/test_portfolio_watch_semantic_run.py tests/unit/test_agent_next.py docs/tools/portfolio-watch.md
git commit -m "feat: surface semantic and run evidence in portfolio state"
```

---

### Task 14: Improve live preflight without crossing the live execution boundary

**Files:**
- Modify: `src/seshat/dagster_adapter/doctor.py`
- Modify: `src/seshat/cli/commands/dagster.py`
- Modify: `src/seshat/cli/parser.py` or `src/seshat/cli/parser_dagster.py`
- Modify: `tests/unit/test_dagster_doctor.py`
- Modify: `tests/unit/test_cli_dagster.py`
- Modify: `docs/integrations/dagster-adapter.md`

**Interfaces:**
- Adds `seshat dagster doctor --live-readiness`
- Reads configuration and import metadata only; performs no connection or query
- Emits engine, driver availability, credential-source presence, and exact
  enable steps with all values redacted

- [ ] **Step 1: Add failing diagnostics tests**

Test PostgreSQL, SQL Server, Snowflake, absent DSN, malformed `.env`, missing
driver, and complete configuration. Assert no socket/driver connect function is
called and no configured value appears in text or JSON.

- [ ] **Step 2: Implement categorical diagnostic records**

Return only `available`, `missing`, `invalid`, or `pending_live`. Read engine
resolution through existing dialect/config helpers and inspect driver import
metadata without importing optional drivers into the static core.

- [ ] **Step 3: Render enable steps**

Use existing documented commands:

```text
pipx inject seshat-bi psycopg2-binary
pip install "seshat-bi[db]"
set DATABASE_URL or ANALYTICS_DB_* in the gitignored .env
```

Do not claim the connection or live values are valid until `retail validate`
actually runs.

- [ ] **Step 4: Run tests, docs checks, and commit**

```powershell
git add src/seshat/dagster_adapter/doctor.py src/seshat/cli/commands/dagster.py src/seshat/cli/parser_dagster.py tests/unit/test_dagster_doctor.py tests/unit/test_cli_dagster.py docs/integrations/dagster-adapter.md
git commit -m "feat: add non-connecting Dagster live preflight"
```

---

### Task 15: Full verification and requirement-by-requirement completion audit

**Files:** no new source behavior; verification and evidence only.

- [ ] **Step 1: Confirm branch and clean review scope**

```powershell
git status --short --branch
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected: only files named by this plan plus owner-authorized artifacts.

- [ ] **Step 2: Ruff all touched Python scopes**

```powershell
C:\Users\user\miniforge3\python.exe -m ruff check src tests scripts orchestration/dagster/src orchestration/dagster/tests
C:\Users\user\miniforge3\python.exe -m ruff format --check src tests scripts orchestration/dagster/src orchestration/dagster/tests
```

- [ ] **Step 3: Run the full normalized unit baseline**

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:GIT_CONFIG_GLOBAL = "NUL"
$env:GIT_CONFIG_SYSTEM = "NUL"
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = "*"
C:\Users\user\miniforge3\python.exe -m pytest -m unit -q -p no:cacheprovider --no-cov
```

Expected: no failures; skips must be explained, not converted into passes.

- [ ] **Step 4: Run contract, orchestration, and governance gates**

```powershell
$env:PYTHONPATH = "$PWD\src;$PWD\orchestration\dagster\src"
C:\Users\user\miniforge3\python.exe -m pytest tests/contract orchestration/dagster/tests -q -p no:cacheprovider --no-cov
C:\Users\user\miniforge3\python.exe -m seshat.cli check
C:\Users\user\miniforge3\python.exe -m seshat.cli semantic-check --repo . --metrics-dir mappings
C:\Users\user\miniforge3\python.exe -m seshat.cli kit-lint --repo .
```

- [ ] **Step 5: Run explicit adversarial reproductions**

Prove all of the following from tests or one-off read-only probes:

- partial DSN cannot survive either runner;
- unrelated ambient secret never reaches the child;
- traversal/absolute/symlink run IDs cannot read or write outside roots;
- doctor does not execute repository venv code;
- zero/unapproved contracts block Dagster;
- missing/orphan measures fail semantic readiness;
- untracked semantic files are ignored by default and included only explicitly;
- tampered evidence is refused;
- no stage or approval was written.

- [ ] **Step 6: Audit human seams**

The completion report must list the C086 disposition and readiness timestamp as
one of:

- owner-authorized and evidenced;
- explicitly blocked with named owner and concrete reason.

Neither may be silently marked complete by test success.

- [ ] **Step 7: Compare against the original finding list**

Create a table mapping all nine findings and the enhancement tasks to exact
test/command evidence. Any missing or indirect evidence keeps the plan
incomplete.

- [ ] **Step 8: Commit final documentation/evidence only after all gates**

Use a commit message that describes the actual verified change. Do not push or
open a PR unless the user separately authorizes publication.

---

## Self-Review

**Spec/finding coverage:** redaction ordering (Task 1); ambient environment
(Task 2); path traversal (Task 3); doctor execution (Task 4); contract validity
(Task 5); tracked/full semantic binding (Task 6); Dagster hard stop (Task 7);
stale audit timestamp (Task 8 + human seam); mutable Actions and stale active
plan (Task 9); client identity (Task 10 + owner seam); CLI hotspot (Task 11);
tamper-evident evidence (Task 12); portfolio/deterministic next action (Task
13); live diagnostics (Task 14); full/adversarial proof (Task 15). Every review
finding is mapped.

**Placeholder scan:** no implementation step contains an unspecified error
handler, test request, or unnamed file. Human decisions are explicit governance
stops with closed choices, not implementation placeholders.

**Type consistency:** `redact_and_tail` is shared by both process layers;
`allowed_child_environment` feeds `_child_env`; `validate_run_id` and
`contained_path` are used by both raw and rendered evidence; `MetricContract`
and `ContractInventory` feed both semantic CLI and Dagster; evidence digest
fields agree between dataclass/dict, schema, renderer, and tests.

**Execution boundary:** this document is planning only. Product-code
implementation starts with Task 1 and must not begin until the user transfers
the worktree to the Terra model.
