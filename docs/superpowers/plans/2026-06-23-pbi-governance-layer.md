# Power BI Governance Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `retail check` — a dependency-light Python CLI that parses committed TMDL/PBIR/SQL/git artifacts and fails the build on any violation of Retail Tower's Power BI conventions, turning advisory prose into an enforced gate.

**Architecture:** A new `src/retail/` package (src-layout) with a rule-registry runner: each rule is a small function returning `Finding`s; the runner aggregates them and sets the exit code. Static checks only this pass — no `pbi-cli`, no Power BI Desktop, no .NET, no network. TMDL is parsed by a hand-rolled indentation/block tokenizer; PBIR/JSON via stdlib `json` (BOM-tolerant); SQL by a lightweight lexer; git rules shell out to `git`.

**Tech Stack:** Python 3.13, pytest (+pytest-cov), ruff + black (line-length 88), stdlib `json`/`re`/`subprocess`/`pathlib`. No runtime dependency on `pbi-cli`.

**Spec:** `docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md` (read it — this plan implements its §5 catalog and §9 milestones).

## Global Constraints

- **No `pbi-cli` / Desktop / .NET / network dependency** in the `retail` package — it must run headless in CI on any OS.
- **Python ≥ 3.13** (machine interpreter: miniforge3 3.13.12). Type annotations on every function signature.
- **src-layout:** package at `src/retail/`, tests at `tests/` (with `tests/unit/` + `tests/integration/`). Matches the global verify commands (`ruff … src tests`, `pytest --cov=src`).
- **Line length 88** (ruff default); `ruff` for lint+isort, `black` for format.
- **Immutable DTOs:** `@dataclass(frozen=True)` for `Finding` and rule metadata.
- **TMDL parsed hand-rolled** (no PyPI TMDL lib — all are immature; TOM/sempy are .NET/Fabric → disqualified). **PBIR via stdlib `json` opened `encoding="utf-8-sig"`** (Power BI writes UTF-8-with-BOM; `json.load` chokes on a BOM).
- **Schema-token matching is position-sensitive** (S2/D8): only flag `marts`/`raw`/`bronze`/`silver` in schema-qualifying positions (`CREATE SCHEMA <id>`, `schema.object`, M `Schema="…"`, native-SQL `FROM <schema>.<obj>`) — never the English word "raw".
- **Windows 260-char path limit:** keep new paths short.
- **Commit message convention:** `<type>: <description>`, `type ∈ {feat, fix, refactor, docs, chore}`.
- **23 static rules** (ids fixed): S1 S2 S3 S4a S4b · D1 D2 D3 D4 D5 D6 D7 D8 · R1 · C1 C2 · G1 G2 G3 G4 G5 · P1 P2. (Count = 5+8+1+2+5+2 = 23; the earlier "22" predated splitting S4 → S4a/S4b.) Errors fail the build; **S4b and D5 are warnings** (do not fail).

---

## The runner contract (every rule depends on this — defined once here)

All rule tasks import from `src/retail/core.py`. These are the exact shared types; later tasks reference them verbatim.

```python
# src/retail/core.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable


class Severity(str, Enum):
    ERROR = "error"      # fails the build (non-zero exit)
    WARNING = "warning"  # reported, does NOT fail the build
    INFO = "info"        # informational only (e.g. "no PBIP project present")


@dataclass(frozen=True)
class Finding:
    rule_id: str               # e.g. "D8"
    severity: Severity
    message: str               # human-readable, one line
    locator: str               # "path:line" when in-file; else a path, git ref, or SHA
    # locator is the "most specific available" per spec §11 — never invent a line number.


@dataclass(frozen=True)
class RuleContext:
    repo_root: Path            # absolute path to the repo being checked
    tracked_files: tuple[str, ...]  # `git ls-files` output, repo-relative POSIX paths
    # --- invocation state (contract v2) — populated by the CLI, consumed by P2 ---
    commit_range: str | None = None   # e.g. "origin/main..HEAD" in CI; None otherwise
    commit_message: str | None = None # the incoming message in the commit-msg hook; None otherwise


# A rule is a function of context: read-only, no MUTATION. (Git rules legitimately shell
# out to `git` — "pure" here means no side effects, not no I/O. All invocation state a rule
# needs — including the commit range/message for P2 — arrives via RuleContext, never via
# env/argv read inside the rule. This is a deliberate trade: 21 rules ignore commit_range/
# commit_message, but routing them through context keeps every rule a function of context.)
Rule = Callable[[RuleContext], Iterable[Finding]]


@dataclass(frozen=True)
class RegisteredRule:
    id: str
    rule: Rule
    title: str
```

```python
# src/retail/registry.py  — rules self-register here; the runner iterates this list.
from __future__ import annotations

from .core import RegisteredRule, Rule

_RULES: list[RegisteredRule] = []

def register(rule_id: str, title: str) -> Callable[[Rule], Rule]:
    def deco(fn: Rule) -> Rule:
        _RULES.append(RegisteredRule(id=rule_id, rule=fn, title=title))
        return fn
    return deco

def all_rules() -> tuple[RegisteredRule, ...]:
    return tuple(_RULES)
```

The runner (`src/retail/runner.py`) builds a `RuleContext`, runs every registered rule, prints findings, and exits non-zero iff any `Finding.severity is Severity.ERROR`.

**`build_context` is mode-aware:** `build_context(repo_root, commit_range=None, commit_message=None)` populates the v2 fields from CLI flags. The CLI grows two flags: `--commit-range ORIGIN..HEAD` (CI mode for P2) and `--commit-msg-file PATH` (commit-msg-hook mode; reads the message from the file). When neither is given, both fields are `None` and P2 no-ops.

**Registry wiring (required — else the registry runs empty):** `src/retail/rules/__init__.py` imports every rule module so the `@register` decorators fire. The runner imports `retail.rules` once at startup. The Final Integration Gate (after M5) asserts `all_rules()` equals the 23-element `EXPECTED_RULE_IDS` set — keyed to `len(EXPECTED_RULE_IDS)`, never a hard-coded number, so the id-set is the single source of truth.

**Dependency boundary (important):** the `retail` package has **no runtime dependencies** beyond the standard library. Polars / PyArrow / DuckDB are **data-pipeline** dependencies (Spec 2 / `pipelines/`), NOT checker dependencies — they live in a separate `[project.optional-dependencies] data` group and are never imported by `retail/`. The checker stays stdlib-only so it runs anywhere.

---

## Milestone 1 — Package Bootstrap + Runner

### Task M1.1: Project configuration (pyproject.toml, .gitignore, .gitattributes)

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\pyproject.toml`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\.gitignore`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\.gitattributes`

**Interfaces:**
- Consumes: nothing (root scaffolding).
- Produces: build metadata for the `retail` package — `[project.scripts] retail = "retail.cli:main"`, the `dev` optional-dependency group, and the ruff/black/pytest tool config that every later task's commands depend on (`pytest -m unit`, `--cov=src`, `pythonpath=["src"]`).

- [ ] **Step 1: Write `pyproject.toml` at the repo root.** This step is configuration, not testable code, so there is no failing-test sub-step — Step 2's `pip install -e .[dev]` verifies it. Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\pyproject.toml` with exactly:
  ```toml
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [project]
  name = "retail"
  version = "0.1.0"
  description = "Static governance checker for Retail Tower Power BI conventions."
  requires-python = ">=3.13"
  dependencies = []

  [project.scripts]
  retail = "retail.cli:main"

  [project.optional-dependencies]
  dev = [
      "pytest>=8.0",
      "pytest-cov>=5.0",
      "ruff>=0.6",
      "black>=24.0",
  ]

  [tool.hatch.build.targets.wheel]
  packages = ["src/retail"]

  [tool.ruff]
  line-length = 88

  [tool.ruff.lint]
  select = ["E", "F", "I"]

  [tool.black]
  line-length = 88

  [tool.pytest.ini_options]
  markers = ["unit", "integration"]
  testpaths = ["tests"]
  pythonpath = ["src"]
  addopts = "--cov=src --cov-report=term-missing"
  ```
  (`[tool.hatch.build.targets.wheel] packages = ["src/retail"]` is required so hatchling locates the package under src-layout; without it the editable install fails with "Unable to determine which files to ship".)

- [ ] **Step 2: Run-to-pass — install the package editable.** From the repo root run:
  ```
  pip install -e .[dev]
  ```
  Expect the install to finish with a line like `Successfully installed retail-0.1.0` (plus pytest/pytest-cov/ruff/black). It will fail here only if `pyproject.toml` is malformed — fix the TOML and re-run before continuing. Note: `src/retail/` does not exist yet, but hatchling builds an editable mapping to the declared path without requiring files to be present, so this succeeds. (If your environment objects to the empty package, proceed to Task M1.2 Step 2 which creates `src/retail/__init__.py`, then re-run this command — it will pass.)

- [ ] **Step 3: Append the Python build/test ignore entries to `.gitignore`.** The file currently ends after the OS/editor block. Add a new section at the end (after line 24, `!.vscode/extensions.json`):
  ```
  # ── Python build / test / lint caches ──
  .pytest_cache/
  .ruff_cache/
  *.egg-info/
  .coverage
  htmlcov/
  dist/
  build/
  .mypy_cache/
  ```
  Do not remove or reorder the existing PBIP/secrets blocks — `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`, and `.env` must remain (CLAUDE.md hard rule; G1 will later assert them).

- [ ] **Step 4: Add the config-file EOL globs to `.gitattributes`.** The file currently ends after `*.svg text eol=lf` (line 17). Insert these four lines immediately before the `# Binary artifacts` comment (line 13), keeping them grouped with the text rules:
  ```
  *.toml   text eol=lf
  *.yml    text eol=lf
  *.yaml   text eol=lf
  *.cfg    text eol=lf
  ```
  Leave the existing `* text=auto` catch-all and all `*.tmdl`/`*.pbir`/`*.pbism`/`*.json`/`*.sql`/`*.md`/`*.py` entries untouched (G4 asserts them as a subset).

- [ ] **Step 5: Commit the configuration.** From the repo root:
  ```
  git add pyproject.toml .gitignore .gitattributes
  git commit -m "chore: bootstrap retail package config (pyproject, gitignore, gitattributes)"
  ```
  Co-Authored-By trailer per repo convention. Expect `3 files changed` (1 new, 2 modified) in the commit summary.

---

### Task M1.2: Shared contract types — `core.py`

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\__init__.py`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\core.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_core.py`

**Interfaces:**
- Consumes: nothing.
- Produces (the exact shared contract — every later milestone imports these verbatim):
  - `class Severity(str, Enum)` with members `ERROR = "error"`, `WARNING = "warning"`, `INFO = "info"`.
  - `@dataclass(frozen=True) class Finding` — fields `rule_id: str`, `severity: Severity`, `message: str`, `locator: str`.
  - `@dataclass(frozen=True) class RuleContext` — **4 fields**: `repo_root: Path`, `tracked_files: tuple[str, ...]`, `commit_range: str | None = None`, `commit_message: str | None = None` (the two contract-v2 invocation fields default to `None`).
  - `Rule = Callable[[RuleContext], Iterable[Finding]]`.
  - `@dataclass(frozen=True) class RegisteredRule` — fields `id: str`, `rule: Rule`, `title: str`.

- [ ] **Step 1: Write the failing test for the contract types.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_core.py`:
  ```python
  import dataclasses
  from pathlib import Path

  import pytest

  from retail.core import Finding, RegisteredRule, RuleContext, Severity


  @pytest.mark.unit
  def test_severity_values():
      assert Severity.ERROR.value == "error"
      assert Severity.WARNING.value == "warning"
      assert Severity.INFO.value == "info"


  @pytest.mark.unit
  def test_finding_is_frozen_dataclass():
      f = Finding(
          rule_id="D8",
          severity=Severity.ERROR,
          message="reads bronze",
          locator="model.tmdl:12",
      )
      assert f.rule_id == "D8"
      assert f.severity is Severity.ERROR
      assert dataclasses.is_dataclass(f)
      with pytest.raises(dataclasses.FrozenInstanceError):
          f.rule_id = "S2"  # type: ignore[misc]


  @pytest.mark.unit
  def test_rule_context_holds_root_and_tracked_files():
      ctx = RuleContext(repo_root=Path("/repo"), tracked_files=("a.sql", "b.tmdl"))
      assert ctx.repo_root == Path("/repo")
      assert ctx.tracked_files == ("a.sql", "b.tmdl")


  @pytest.mark.unit
  def test_rule_context_v2_fields_default_to_none():
      # Built with only the two required fields: the contract-v2 invocation
      # fields default to None (the local `retail check` mode).
      ctx = RuleContext(repo_root=Path("/repo"), tracked_files=("a.sql",))
      assert ctx.commit_range is None
      assert ctx.commit_message is None


  @pytest.mark.unit
  def test_rule_context_v2_fields_preserved_when_supplied():
      # Built with all four fields: commit_range and commit_message round-trip.
      ctx = RuleContext(
          repo_root=Path("/repo"),
          tracked_files=("a.sql",),
          commit_range="origin/main..HEAD",
          commit_message="feat: a thing",
      )
      assert ctx.commit_range == "origin/main..HEAD"
      assert ctx.commit_message == "feat: a thing"


  @pytest.mark.unit
  def test_registered_rule_holds_id_callable_title():
      def dummy(ctx: RuleContext):
          return ()

      rr = RegisteredRule(id="X1", rule=dummy, title="dummy")
      assert rr.id == "X1"
      assert rr.title == "dummy"
      assert rr.rule is dummy
  ```

- [ ] **Step 2: Run-to-fail.** From the repo root:
  ```
  pytest -m unit tests/unit/test_core.py -v
  ```
  Expect a collection error: `ModuleNotFoundError: No module named 'retail'` (neither `src/retail/__init__.py` nor `core.py` exists yet).

- [ ] **Step 3: Create the package marker.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\__init__.py` with exactly:
  ```python
  """Retail Tower static governance checker."""
  ```

- [ ] **Step 4: Implement `core.py` (the exact contract).** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\core.py`:
  ```python
  from __future__ import annotations

  from dataclasses import dataclass
  from enum import Enum
  from pathlib import Path
  from typing import Callable, Iterable


  class Severity(str, Enum):
      ERROR = "error"  # fails the build (non-zero exit)
      WARNING = "warning"  # reported, does NOT fail the build
      INFO = "info"  # informational only


  @dataclass(frozen=True)
  class Finding:
      rule_id: str
      severity: Severity
      message: str
      locator: str


  @dataclass(frozen=True)
  class RuleContext:
      repo_root: Path
      tracked_files: tuple[str, ...]
      commit_range: str | None = None
      commit_message: str | None = None


  # A rule is a pure function: context in, findings out. No side effects.
  Rule = Callable[[RuleContext], Iterable[Finding]]


  @dataclass(frozen=True)
  class RegisteredRule:
      id: str
      rule: Rule
      title: str
  ```

- [ ] **Step 5: Run-to-pass.** From the repo root:
  ```
  pytest -m unit tests/unit/test_core.py -v
  ```
  Expect `6 passed` (test_severity_values, test_finding_is_frozen_dataclass, test_rule_context_holds_root_and_tracked_files, test_rule_context_v2_fields_default_to_none, test_rule_context_v2_fields_preserved_when_supplied, test_registered_rule_holds_id_callable_title) and the coverage summary table.

- [ ] **Step 6: Commit.** From the repo root:
  ```
  git add src/retail/__init__.py src/retail/core.py tests/unit/test_core.py
  git commit -m "feat: add retail.core contract types (Severity, Finding, RuleContext, Rule)"
  ```

---

### Task M1.3: Rule registry — `registry.py`

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\registry.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_registry.py`

**Interfaces:**
- Consumes: `retail.core.RegisteredRule`, `retail.core.Rule`.
- Produces:
  - `register(rule_id: str, title: str) -> Callable[[Rule], Rule]` — decorator appending a `RegisteredRule` to a module-level list and returning the function unchanged.
  - `all_rules() -> tuple[RegisteredRule, ...]` — snapshot of registered rules in registration order.

- [ ] **Step 1: Write the failing test.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_registry.py`:
  ```python
  import pytest

  from retail import registry
  from retail.core import Finding, RuleContext, Severity


  @pytest.fixture(autouse=True)
  def _clear_registry():
      # registry uses a module-global list; isolate each test.
      registry._RULES.clear()
      yield
      registry._RULES.clear()


  @pytest.mark.unit
  def test_register_adds_rule_and_returns_function():
      @registry.register("X1", "example rule")
      def my_rule(ctx: RuleContext):
          return ()

      assert my_rule.__name__ == "my_rule"  # decorator returns fn unchanged
      rules = registry.all_rules()
      assert len(rules) == 1
      assert rules[0].id == "X1"
      assert rules[0].title == "example rule"
      assert rules[0].rule is my_rule


  @pytest.mark.unit
  def test_all_rules_preserves_registration_order():
      @registry.register("A", "first")
      def a(ctx: RuleContext):
          return ()

      @registry.register("B", "second")
      def b(ctx: RuleContext):
          return [Finding("B", Severity.INFO, "ok", "x")]

      assert [r.id for r in registry.all_rules()] == ["A", "B"]


  @pytest.mark.unit
  def test_all_rules_returns_tuple_snapshot():
      assert registry.all_rules() == ()
      assert isinstance(registry.all_rules(), tuple)
  ```

- [ ] **Step 2: Run-to-fail.** From the repo root:
  ```
  pytest -m unit tests/unit/test_registry.py -v
  ```
  Expect `ModuleNotFoundError: No module named 'retail.registry'`.

- [ ] **Step 3: Implement `registry.py`.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\registry.py`:
  ```python
  from __future__ import annotations

  from typing import Callable

  from .core import RegisteredRule, Rule

  _RULES: list[RegisteredRule] = []


  def register(rule_id: str, title: str) -> Callable[[Rule], Rule]:
      def deco(fn: Rule) -> Rule:
          _RULES.append(RegisteredRule(id=rule_id, rule=fn, title=title))
          return fn

      return deco


  def all_rules() -> tuple[RegisteredRule, ...]:
      return tuple(_RULES)
  ```

- [ ] **Step 4: Run-to-pass.** From the repo root:
  ```
  pytest -m unit tests/unit/test_registry.py -v
  ```
  Expect `3 passed` (test_register_adds_rule_and_returns_function, test_all_rules_preserves_registration_order, test_all_rules_returns_tuple_snapshot).

- [ ] **Step 5: Commit.** From the repo root:
  ```
  git add src/retail/registry.py tests/unit/test_registry.py
  git commit -m "feat: add retail.registry (register decorator, all_rules)"
  ```

---

### Task M1.4: Runner — `runner.py`

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\runner.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_runner.py`

**Interfaces:**
- Consumes: `retail.core.{Finding, RuleContext, Severity, RegisteredRule}`, `retail.registry.all_rules`.
- Produces:
  - `_git_ls_files(repo_root: Path) -> tuple[str, ...]` — runs `git ls-files` in `repo_root` (via `subprocess.run`, no shell), splits stdout into repo-relative POSIX paths. Factored out so M1.7's widened `build_context` reuses the exact same discovery.
  - `build_context(repo_root: Path) -> RuleContext` — calls `_git_ls_files(repo_root)` and returns a `RuleContext`.
  - `run(rules: tuple[RegisteredRule, ...], ctx: RuleContext) -> int` — runs every rule, prints each `Finding` as `[<severity>] <rule_id> <message> (<locator>)`, returns `1` iff any finding has `severity is Severity.ERROR`, else `0`. Rules are injected as an argument (not read from the global registry) so the test can supply its own and the registry stays untouched.

- [ ] **Step 1: Write the failing test (this is the milestone's required exit-code test).** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_runner.py`:
  ```python
  from pathlib import Path

  import pytest

  from retail.core import Finding, RegisteredRule, RuleContext, Severity
  from retail.runner import build_context, run


  def _ctx() -> RuleContext:
      return RuleContext(repo_root=Path("."), tracked_files=())


  @pytest.mark.unit
  def test_run_exits_1_when_any_error_finding(capsys):
      def bad(ctx: RuleContext):
          return [Finding("E1", Severity.ERROR, "boom", "f.sql:1")]

      rules = (RegisteredRule(id="E1", rule=bad, title="bad"),)
      code = run(rules, _ctx())
      assert code == 1
      out = capsys.readouterr().out
      assert "[error] E1 boom (f.sql:1)" in out


  @pytest.mark.unit
  def test_run_exits_0_when_no_error_findings(capsys):
      def warn(ctx: RuleContext):
          return [Finding("W1", Severity.WARNING, "heads up", "f.sql:2")]

      def clean(ctx: RuleContext):
          return ()

      rules = (
          RegisteredRule(id="W1", rule=warn, title="warn"),
          RegisteredRule(id="C0", rule=clean, title="clean"),
      )
      code = run(rules, _ctx())
      assert code == 0
      out = capsys.readouterr().out
      assert "[warning] W1 heads up (f.sql:2)" in out


  @pytest.mark.unit
  def test_run_exits_0_when_no_findings_at_all(capsys):
      def clean(ctx: RuleContext):
          return ()

      rules = (RegisteredRule(id="C0", rule=clean, title="clean"),)
      assert run(rules, _ctx()) == 0


  @pytest.mark.unit
  def test_build_context_uses_git_ls_files(tmp_path):
      import subprocess

      subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
      (tmp_path / "a.sql").write_text("select 1\n", encoding="utf-8")
      sub = tmp_path / "sub"
      sub.mkdir()
      (sub / "b.tmdl").write_text("table T\n", encoding="utf-8")
      subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

      ctx = build_context(tmp_path)
      assert ctx.repo_root == tmp_path
      # POSIX-separated, repo-relative, regardless of OS.
      assert "a.sql" in ctx.tracked_files
      assert "sub/b.tmdl" in ctx.tracked_files
  ```

- [ ] **Step 2: Run-to-fail.** From the repo root:
  ```
  pytest -m unit tests/unit/test_runner.py -v
  ```
  Expect `ModuleNotFoundError: No module named 'retail.runner'`.

- [ ] **Step 3: Implement `runner.py`.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\runner.py`.

  > **Note (factored helper, consumed by M1.7):** the `git ls-files` discovery is
  > factored into `_git_ls_files(repo_root: Path) -> tuple[str, ...]` so M1.7 Step 3
  > can reuse the exact same tracked-files logic when it widens `build_context`'s
  > signature (M1.7 Step 3 calls `_git_ls_files(repo_root)` — this is where that
  > helper is defined).

  ```python
  from __future__ import annotations

  import subprocess
  from pathlib import Path

  from .core import Finding, RegisteredRule, RuleContext, Severity


  def _git_ls_files(repo_root: Path) -> tuple[str, ...]:
      result = subprocess.run(
          ["git", "ls-files"],
          cwd=repo_root,
          check=True,
          capture_output=True,
          text=True,
      )
      # git ls-files already emits forward slashes; split on newlines, drop blanks.
      return tuple(line for line in result.stdout.splitlines() if line)


  def build_context(repo_root: Path) -> RuleContext:
      return RuleContext(repo_root=repo_root, tracked_files=_git_ls_files(repo_root))


  def _format(finding: Finding) -> str:
      return (
          f"[{finding.severity.value}] {finding.rule_id} "
          f"{finding.message} ({finding.locator})"
      )


  def run(rules: tuple[RegisteredRule, ...], ctx: RuleContext) -> int:
      exit_code = 0
      for registered in rules:
          for finding in registered.rule(ctx):
              print(_format(finding))
              if finding.severity is Severity.ERROR:
                  exit_code = 1
      return exit_code
  ```

- [ ] **Step 4: Run-to-pass.** From the repo root:
  ```
  pytest -m unit tests/unit/test_runner.py -v
  ```
  Expect `4 passed` (test_run_exits_1_when_any_error_finding, test_run_exits_0_when_no_error_findings, test_run_exits_0_when_no_findings_at_all, test_build_context_uses_git_ls_files).

- [ ] **Step 5: Commit.** From the repo root:
  ```
  git add src/retail/runner.py tests/unit/test_runner.py
  git commit -m "feat: add retail.runner (build_context, run with ERROR-gated exit code)"
  ```

---

### Task M1.5: CLI entrypoint — `cli.py`

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\cli.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_cli.py`

**Interfaces:**
- Consumes: `retail.runner.{build_context, run}`, `retail.registry.all_rules`.
- Produces:
  - `main(argv: list[str] | None = None) -> int` — argparse entrypoint with a single `check` subcommand (optional `--repo PATH`, default `.`). `retail check` builds the context, runs `all_rules()`, and returns the runner's exit code. Registered as the `retail` console script in `pyproject.toml`.

- [ ] **Step 1: Write the failing test.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_cli.py`:
  ```python
  import subprocess
  from pathlib import Path

  import pytest

  from retail import cli, registry


  @pytest.fixture(autouse=True)
  def _clear_registry():
      registry._RULES.clear()
      yield
      registry._RULES.clear()


  def _init_repo(tmp_path: Path) -> None:
      subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
      (tmp_path / "a.sql").write_text("select 1\n", encoding="utf-8")
      subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)


  @pytest.mark.unit
  def test_check_returns_0_when_no_rules(tmp_path):
      _init_repo(tmp_path)
      assert cli.main(["check", "--repo", str(tmp_path)]) == 0


  @pytest.mark.unit
  def test_check_returns_1_when_a_rule_errors(tmp_path):
      _init_repo(tmp_path)
      from retail.core import Finding, RuleContext, Severity

      @registry.register("E9", "always errors")
      def boom(ctx: RuleContext):
          return [Finding("E9", Severity.ERROR, "nope", "a.sql:1")]

      assert cli.main(["check", "--repo", str(tmp_path)]) == 1


  @pytest.mark.unit
  def test_no_subcommand_returns_2(capsys):
      # argparse error path: missing required subcommand.
      assert cli.main([]) == 2
  ```

- [ ] **Step 2: Run-to-fail.** From the repo root:
  ```
  pytest -m unit tests/unit/test_cli.py -v
  ```
  Expect `ModuleNotFoundError: No module named 'retail.cli'`.

- [ ] **Step 3: Implement `cli.py`.** Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\cli.py`:
  ```python
  from __future__ import annotations

  import argparse
  from pathlib import Path

  from .registry import all_rules
  from .runner import build_context, run


  def main(argv: list[str] | None = None) -> int:
      parser = argparse.ArgumentParser(prog="retail")
      sub = parser.add_subparsers(dest="command", required=True)
      check = sub.add_parser("check", help="run static governance checks")
      check.add_argument("--repo", default=".", help="repo root to check")

      try:
          args = parser.parse_args(argv)
      except SystemExit as exc:
          # argparse exits 2 on bad/missing args; surface it as a return code.
          return int(exc.code or 0)

      if args.command == "check":
          ctx = build_context(Path(args.repo))
          return run(all_rules(), ctx)

      return 0
  ```

- [ ] **Step 4: Run-to-pass.** From the repo root:
  ```
  pytest -m unit tests/unit/test_cli.py -v
  ```
  Expect `3 passed` (test_check_returns_0_when_no_rules, test_check_returns_1_when_a_rule_errors, test_no_subcommand_returns_2).

- [ ] **Step 5: Verify the installed console script and full suite.** From the repo root run both:
  ```
  retail check --repo .
  pytest -m unit -q
  ```
  `retail check --repo .` exits `0` and prints nothing (no rules registered in the package yet — `all_rules()` is empty until later milestones import their rule modules). `pytest -m unit -q` reports all unit tests passing across `test_core.py`, `test_registry.py`, `test_runner.py`, `test_cli.py` (16 passed — `test_core.py` contributes 6 after the M1.2 contract-v2 default/preserve tests) with the coverage table. If `retail` is not found on PATH, re-run `pip install -e .[dev]` (Task M1.1 Step 2).

- [ ] **Step 6: Lint and format gate, then commit.** From the repo root:
  ```
  black --check src tests
  ruff check src tests
  git add src/retail/cli.py tests/unit/test_cli.py
  git commit -m "feat: add retail.cli check entrypoint (argparse, ERROR-gated exit)"
  ```
  `black --check` reports `All done!` / `would reformat 0 files`; `ruff check` reports `All checks passed!`. If either reports issues, run `black src tests` / `ruff check --fix src tests`, re-run the unit suite, then commit.


---

## M1 — contract-v2 revisions

> These tasks **augment** the existing M1 core tasks (M1.1–M1.5, which already define `src/retail/core.py`, `src/retail/registry.py`, `src/retail/runner.py`, and `src/retail/cli.py`). They do **not** restate that code. They add the registry import-wiring seam (M1.6) and make context-building mode-aware with the two new CLI flags (M1.7).

> **RESOLVED (count = 23):** an earlier draft said "22 rules"; that predated the adversarial review splitting S4 into S4a + S4b. The enumerated id-set `{S1,S2,S3,S4a,S4b,D1,D2,D3,D4,D5,D6,D7,D8,R1,C1,C2,G1,G2,G3,G4,G5,P1,P2}` has **23** ids (S=5, D=8, R=1, C=2, G=5, P=2 = 23) and is the single source of truth. The Final Integration Gate asserts set-equality with `EXPECTED_RULE_IDS` and keys any count to `len(EXPECTED_RULE_IDS)` — never a hard-coded number. Spec + plan headers now both say 23.

---

### Task M1.6: Registry import wiring + rule-package skeleton

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\__init__.py`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\sql.py`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\pbir.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_rules_wiring.py`

**Interfaces:**
- Consumes (from M1.2 registry, already exists — exact signatures): `retail.registry.register(rule_id: str, title: str) -> Callable[[Rule], Rule]` and `retail.registry.all_rules() -> tuple[RegisteredRule, ...]`; `RegisteredRule(id: str, rule: Rule, title: str)` from `retail.core`.
- Produces:
  - `src/retail/rules/__init__.py` — importing `retail.rules` triggers `from . import git_meta, sql, dax, pbir`, so every `@register` decorator in those submodules fires exactly once at import time. The runner (M1.5) does `import retail.rules` at startup before calling `all_rules()`.
  - Four submodules `git_meta.py`, `sql.py`, `dax.py`, `pbir.py` — created here as **stubs** so the explicit imports resolve and this task's commit is green. M2–M5 fill them with `@register(...)`-decorated rule functions in `src/retail/rules/<group>.py`.
- **Scope note:** This task's own test is the *wiring smoke test* (importing `retail.rules` succeeds and `all_rules()` is a tuple). The "exactly N rules / exact id-set" assertion is **NOT** here — it is the separate **Final Integration Gate (after M5)** at the end of this file, because it can only pass once all 23 rule functions exist.

- [ ] **Step 1: Write the failing smoke test**

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_rules_wiring.py`:

```python
"""M1.6 wiring smoke test: importing retail.rules must load every submodule."""

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_import_retail_rules_succeeds() -> None:
    # Importing the package must not raise — every submodule import resolves.
    pkg = importlib.import_module("retail.rules")
    assert pkg is not None


def test_all_submodules_importable() -> None:
    for sub in ("git_meta", "sql", "dax", "pbir"):
        mod = importlib.import_module(f"retail.rules.{sub}")
        assert mod is not None


def test_all_rules_returns_a_tuple() -> None:
    import retail.rules  # noqa: F401  (import for the registration side effect)
    from retail.registry import all_rules

    rules = all_rules()
    assert isinstance(rules, tuple)
    # Every entry carries a non-empty string id (RegisteredRule.id).
    assert all(isinstance(r.id, str) and r.id for r in rules)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_rules_wiring.py -v`
Expected: FAIL — collection/import error `ModuleNotFoundError: No module named 'retail.rules'` (the `retail.rules` package does not exist yet).

- [ ] **Step 3: Create the four stub submodules**

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`:

```python
"""Git-metadata rules (G1–G5). Rule functions added in M4; stub for M1.6 wiring."""

from __future__ import annotations
```

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\sql.py`:

```python
"""SQL rules (S1–S4b, plus D8 schema tokens). Added in M2; stub for M1.6 wiring."""

from __future__ import annotations
```

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`:

```python
"""DAX/TMDL rules (D1–D7). Rule functions added in M3; stub for M1.6 wiring."""

from __future__ import annotations
```

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\pbir.py`:

```python
"""PBIR/JSON + R/C/P rules (R1, C1, C2, P1, P2). Added in M5; stub for M1.6 wiring."""

from __future__ import annotations
```

- [ ] **Step 4: Create the package `__init__.py` that imports every submodule**

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\__init__.py`:

```python
"""Rule package.

Importing this package imports every rule submodule so that each module's
``@register(...)`` decorators fire exactly once. The runner does
``import retail.rules`` at startup before calling ``registry.all_rules()``.

Add a new submodule to the import list below when you add a new rule group;
that is the *only* wiring step required for new rules to be discovered.
"""

from __future__ import annotations

# Side-effecting imports: each module registers its rules on import.
from . import dax, git_meta, pbir, sql  # noqa: F401  (imported for side effects)

__all__ = ["dax", "git_meta", "pbir", "sql"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_rules_wiring.py -v`
Expected: PASS — 3 passed. (`all_rules()` may return an empty tuple at this milestone; the smoke test only asserts it is a tuple and that any present ids are non-empty strings.)

- [ ] **Step 6: Confirm the runner imports the package at startup**

The runner (`src/retail/runner.py`, from M1.5) must `import retail.rules` before it calls `all_rules()`, else the registry is empty. Verify the line is present:

Run: `python -c "import pathlib,sys; t=pathlib.Path('src/retail/runner.py').read_text(encoding='utf-8'); sys.exit(0 if 'import retail.rules' in t else 1)"`
Expected: exit code 0 (the import line is present). If it exits 1, add `import retail.rules  # noqa: F401` near the top of `runner.py` (just before `all_rules()` is first used) and re-run this step until it exits 0.

- [ ] **Step 7: Lint and format the new files**

Run: `ruff check src/retail/rules tests/unit/test_rules_wiring.py && black --check src/retail/rules tests/unit/test_rules_wiring.py`
Expected: `All checks passed!` from ruff and `4 files would be left unchanged.` / `All done!` from black. If black reports reformatting, run `black src/retail/rules tests/unit/test_rules_wiring.py` then re-run the check.

- [ ] **Step 8: Commit**

```bash
git add src/retail/rules/__init__.py src/retail/rules/git_meta.py src/retail/rules/sql.py src/retail/rules/dax.py src/retail/rules/pbir.py tests/unit/test_rules_wiring.py
git commit -m "feat: wire rule-package imports so @register fires on retail.rules import"
```

---

### Task M1.7: mode-aware `build_context` + `--commit-range` / `--commit-msg-file` CLI flags

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\runner.py` (the `build_context` function defined in M1.4)
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\cli.py` (the `main` function defined in M1.5)
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_cli_context.py`

**Interfaces:**
- Consumes:
  - `retail.core.RuleContext(repo_root: Path, tracked_files: tuple[str, ...], commit_range: str | None = None, commit_message: str | None = None)` — the contract-v2 frozen DTO (from M1.1, already exists). The two v2 fields default to `None`.
  - **Assumption (pinned because M1.1–M1.5 are not in this plan file):** `build_context` lives in `src/retail/runner.py` (M1.4) and `main` lives in `src/retail/cli.py` (M1.5), per the plan header (runner builds the context, line 99; CLI owns `main`). M1.4's `build_context` already returns a `RuleContext`; this task widens its signature and threads the two new fields through.
- Produces:
  - `build_context(repo_root: Path, commit_range: str | None = None, commit_message: str | None = None) -> RuleContext` — populates `RuleContext.commit_range` and `RuleContext.commit_message` from its arguments (both default `None`, preserving existing callers).
  - `_build_parser() -> argparse.ArgumentParser` in `cli.py` — exposes the argument parser so flag→field mapping is unit-testable without executing the registry. **Retains** M1.5's `check` subcommand and its `--repo PATH` (default `"."`); **adds**, under that same `check` subparser, `--commit-range` (stored as `commit_range`, default `None`) and `--commit-msg-file` (stored as `commit_msg_file`, a path, default `None`). Because the flags live under `check`, parser tests must invoke `parse_args(["check", ...])`.
  - `main(argv: list[str] | None = None) -> int` parses args via `_build_parser()` (keeping M1.5's `try/except SystemExit` exit-2 path for a missing subcommand), reads the commit message from `--commit-msg-file` if given (`Path(...).read_text(encoding="utf-8")`, **trailing newline stripped** with `.rstrip("\n")` — git's `COMMIT_EDITMSG` ends in `\n`), builds the context from `--repo`, and passes `commit_range` + `commit_message` to `build_context`, then returns `run(all_rules(), ctx)`.

- [ ] **Step 1: Write the failing tests**

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_cli_context.py`:

```python
"""M1.7: mode-aware build_context + the two new CLI flags."""

from pathlib import Path

import pytest

from retail.cli import _build_parser
from retail.runner import build_context

pytestmark = pytest.mark.unit


def test_build_context_defaults_both_none(tmp_path: Path) -> None:
    ctx = build_context(tmp_path)
    # Only the two v2 fields are asserted here — tracked_files behavior on a
    # tmp dir is out of scope for this test.
    assert ctx.commit_range is None
    assert ctx.commit_message is None


def test_build_context_populates_v2_fields(tmp_path: Path) -> None:
    ctx = build_context(
        tmp_path,
        commit_range="origin/main..HEAD",
        commit_message="feat: a thing",
    )
    assert ctx.commit_range == "origin/main..HEAD"
    assert ctx.commit_message == "feat: a thing"


def test_parser_default_flags_are_none() -> None:
    # The commit-aware flags live under the `check` subcommand.
    ns = _build_parser().parse_args(["check"])
    assert ns.commit_range is None
    assert ns.commit_msg_file is None
    assert ns.repo == "."  # M1.5's --repo is retained with its default


def test_parser_commit_range_flag() -> None:
    ns = _build_parser().parse_args(["check", "--commit-range", "origin/main..HEAD"])
    assert ns.commit_range == "origin/main..HEAD"


def test_parser_commit_msg_file_flag() -> None:
    ns = _build_parser().parse_args(["check", "--commit-msg-file", "/tmp/MSG"])
    assert ns.commit_msg_file == "/tmp/MSG"


def test_main_commit_msg_file_is_read_and_stripped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # git writes COMMIT_EDITMSG with a trailing newline; main must strip it.
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("feat: real message\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_build_context(repo_root, commit_range=None, commit_message=None):
        captured["commit_range"] = commit_range
        captured["commit_message"] = commit_message
        from retail.core import RuleContext

        return RuleContext(
            repo_root=repo_root,
            tracked_files=(),
            commit_range=commit_range,
            commit_message=commit_message,
        )

    # Patch where cli looks it up, and stub run so no rules execute.
    monkeypatch.setattr("retail.cli.build_context", fake_build_context)
    monkeypatch.setattr("retail.cli.run", lambda rules, ctx: 0)

    rc = main_under_test(["check", "--commit-msg-file", str(msg_file)])

    assert rc == 0
    assert captured["commit_message"] == "feat: real message"
    assert captured["commit_range"] is None


def test_main_commit_range_flag_threads_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_build_context(repo_root, commit_range=None, commit_message=None):
        captured["commit_range"] = commit_range
        captured["commit_message"] = commit_message
        from retail.core import RuleContext

        return RuleContext(repo_root=repo_root, tracked_files=())

    monkeypatch.setattr("retail.cli.build_context", fake_build_context)
    monkeypatch.setattr("retail.cli.run", lambda rules, ctx: 0)

    rc = main_under_test(["check", "--commit-range", "origin/main..HEAD"])

    assert rc == 0
    assert captured["commit_range"] == "origin/main..HEAD"
    assert captured["commit_message"] is None


# Imported at module scope after monkeypatch targets above are defined; aliased
# so the patch sites (retail.cli.build_context / retail.cli.run) are the ones
# main() actually calls.
from retail.cli import main as main_under_test  # noqa: E402
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli_context.py -v`
Expected: FAIL — `TypeError: build_context() got an unexpected keyword argument 'commit_range'` (M1.5's `build_context` does not yet accept the v2 keywords) and/or `ImportError: cannot import name '_build_parser' from 'retail.cli'` (the parser is not yet factored out).

- [ ] **Step 3: Make `build_context` mode-aware in `runner.py`**

In `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\runner.py`, replace the M1.4 `build_context` signature/body with the v2 version (keep the existing `tracked_files` discovery — shown here calling the `_git_ls_files` helper factored in M1.4 Step 3; if your M1.4 inlined that logic instead, keep it inlined and only add the two new parameters and pass them into `RuleContext`):

```python
def build_context(
    repo_root: Path,
    commit_range: str | None = None,
    commit_message: str | None = None,
) -> RuleContext:
    """Build the read-only context every rule receives.

    ``commit_range`` and ``commit_message`` are the contract-v2 invocation
    fields: populated by the CLI flags ``--commit-range`` / ``--commit-msg-file``
    and consumed by P2. Both default to ``None`` (no commit context), which is
    the local ``retail check`` mode.
    """
    return RuleContext(
        repo_root=repo_root,
        tracked_files=_git_ls_files(repo_root),
        commit_range=commit_range,
        commit_message=commit_message,
    )
```

- [ ] **Step 4: Replace M1.5 Step 3's `main()` with the unified `_build_parser` + `main` in `cli.py`**

This task **supersedes** the M1.5 Step 3 `cli.py` (it does not add a second `main`). The unified version **retains** M1.5's `check` subcommand and its `--repo PATH` (default `"."`), the `try/except SystemExit` exit-2 path (so `test_no_subcommand_returns_2` still passes), and the `run(all_rules(), ctx)` call — and **adds** `--commit-range` / `--commit-msg-file` **under the `check` subparser**. The parser is factored into `_build_parser()` so flag→field mapping is unit-testable without executing rules. The imports of `build_context` and `run` stay module-level so the tests' `monkeypatch.setattr("retail.cli.build_context", ...)` / `"retail.cli.run"` patch the names `main` resolves.

Replace the body of `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\cli.py` with:

```python
from __future__ import annotations

import argparse
from pathlib import Path

import retail.rules  # noqa: F401  (import for side effects: fires every @register)

from .registry import all_rules
from .runner import build_context, run


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Exposed (not inlined in ``main``) so flag→field mapping is unit-testable
    without executing any rules. The two commit-aware flags live UNDER the
    ``check`` subcommand alongside ``--repo``.
    """
    parser = argparse.ArgumentParser(
        prog="retail",
        description="Static governance checks for committed Power BI artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="run static governance checks")
    check.add_argument("--repo", default=".", help="repo root to check")
    check.add_argument(
        "--commit-range",
        dest="commit_range",
        default=None,
        metavar="ORIGIN..HEAD",
        help="CI mode: git commit range to scope commit-aware rules (P2).",
    )
    check.add_argument(
        "--commit-msg-file",
        dest="commit_msg_file",
        default=None,
        metavar="PATH",
        help="commit-msg-hook mode: file holding the incoming commit message (P2).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on bad/missing args (e.g. no subcommand); surface it
        # as a return code rather than letting it propagate.
        return int(exc.code or 0)

    if args.command == "check":
        commit_message: str | None = None
        if args.commit_msg_file is not None:
            # git's COMMIT_EDITMSG ends in a trailing newline — strip it so the
            # message passed to rules is the bare text.
            commit_message = Path(args.commit_msg_file).read_text(
                encoding="utf-8"
            ).rstrip("\n")

        ctx = build_context(
            Path(args.repo),
            commit_range=args.commit_range,
            commit_message=commit_message,
        )
        return run(all_rules(), ctx)

    return 0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli_context.py -v`
Expected: PASS — 7 passed.

- [ ] **Step 6: Run the full unit suite to confirm no regression in M1.5 callers**

Run: `python -m pytest -m unit -q`
Expected: all unit tests pass (the widened `build_context` signature is backward-compatible — both new parameters default to `None`, so existing `build_context(repo_root)` callers are unaffected).

- [ ] **Step 7: Lint and format**

Run: `ruff check src/retail/cli.py src/retail/runner.py tests/unit/test_cli_context.py && black --check src/retail/cli.py src/retail/runner.py tests/unit/test_cli_context.py`
Expected: `All checks passed!` and `All done!`. If black reformats, run `black src/retail/cli.py src/retail/runner.py tests/unit/test_cli_context.py` then re-run the check.

- [ ] **Step 8: Commit**

```bash
git add src/retail/runner.py src/retail/cli.py tests/unit/test_cli_context.py
git commit -m "feat: make build_context mode-aware with --commit-range and --commit-msg-file flags"
```

---

### Final Integration Gate (run after M5 — NOT part of M1.6)

> Placed here so the M1.6 implementer does not write a count assertion that cannot pass until every rule module is populated. **Run this only after M2–M5 are complete** (all rule functions exist and self-register). It is the single authoritative assertion that the full rule set is wired.

**Files:**
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\integration\test_rule_registry_complete.py`

**Interfaces:**
- Consumes: `retail.rules` (import side effect registers all rules), `retail.registry.all_rules()`.

- [ ] **Step 1: Write the integration gate test**

Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\integration\test_rule_registry_complete.py`:

```python
"""Final integration gate: the full rule set is registered exactly once.

SOURCE OF TRUTH is the enumerated id-set below. See the DISCREPANCY callout in
the plan: contract prose says "22" but enumerates 23 ids — the spec owner must
reconcile before this gate is treated as authoritative. The count assertion is
written as len(EXPECTED_RULE_IDS), never a hard-coded number, so it tracks the
set.
"""

import pytest

pytestmark = pytest.mark.integration

EXPECTED_RULE_IDS = frozenset(
    {
        "S1", "S2", "S3", "S4a", "S4b",
        "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8",
        "R1",
        "C1", "C2",
        "G1", "G2", "G3", "G4", "G5",
        "P1", "P2",
    }
)


def test_registry_has_exactly_the_expected_rule_set() -> None:
    import retail.rules  # noqa: F401  (import for registration side effect)
    from retail.registry import all_rules

    ids = [r.id for r in all_rules()]

    # No rule registered twice (one @register per id).
    assert len(ids) == len(set(ids)), f"duplicate rule ids: {ids}"

    id_set = set(ids)
    missing = EXPECTED_RULE_IDS - id_set
    extra = id_set - EXPECTED_RULE_IDS
    assert not missing, f"missing rule ids: {sorted(missing)}"
    assert not extra, f"unexpected rule ids: {sorted(extra)}"

    # Count tracks the set (NOT a hard-coded 22 — see DISCREPANCY callout).
    assert len(all_rules()) == len(EXPECTED_RULE_IDS)
```

- [ ] **Step 2: Run the gate**

Run: `python -m pytest tests/integration/test_rule_registry_complete.py -v`
Expected (after M5): PASS — 1 passed. Before M5 it FAILS with `missing rule ids: [...]`, which is correct: it is the gate proving the wiring is complete.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_rule_registry_complete.py
git commit -m "test: add final registry-completeness integration gate for the full rule set"
```

---

## Milestone 0 — Golden PBIP Fixture + Parser Decision (gates M4/M5)

### Task M0.1: TMDL parser stub + parser-decision docstring + decision doc

Establishes the hand-rolled TMDL parser module that M4 builds on, and records the
search-first parser decision (TMDL hand-rolled; PBIR stdlib `json` `utf-8-sig`). The
stub ships a real minimal slice (`top_level_blocks`) so the M0.2 smoke test has
something to call — not `NotImplementedError`. The docstring pins the observed TMDL
token literals as the regression anchor for M4/M5. Runs AFTER M1 (which created
`src/retail/`); GATES M4/M5.

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\tmdl.py`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\docs\decisions\0001-tmdl-pbir-parser.md`
- Test: (none — the parser smoke test is in M0.2; this task is stub + docs, verified by import + grep)

**Interfaces:**
- Consumes: nothing (stub uses stdlib only).
- Produces: `top_level_blocks(text: str) -> list[str]` — given TMDL source text, returns
  the stripped header line of each block at indentation level 0, in document order. M4
  extends this module with nested-block / key-value parsing; this name is stable and
  inherited by M4.

- [ ] **Step 1: Write the parser-decision docstring + minimal stub in `src/retail/tmdl.py`**

```python
"""Hand-rolled TMDL (Tabular Model Definition Language) parser.

PARSER DECISION (search-first; full rationale in docs/decisions/0001-tmdl-pbir-parser.md):
  - TMDL is parsed by THIS hand-rolled indentation/block tokenizer. No PyPI TMDL
    parser is mature enough to depend on (surveyed 2026-06); TOM and sempy read TMDL
    only via the Windows/.NET or Fabric live path, which defeats headless CI, so both
    are disqualified for the static checker.
  - PBIR / report JSON is parsed with the stdlib ``json`` module opened
    ``encoding="utf-8-sig"`` because Power BI writes UTF-8-with-BOM and ``json.load``
    chokes on a leading BOM.

REGRESSION ANCHOR (token literals observed in tests/fixtures/golden_pbip/; M4/M5 pin
their regexes to these. If a fixture edit drops one, tests/unit/test_tmdl.py fails):
  - measure block shape:        ``measure 'TotalSales' = SUM(Sales[Amount])``
                                (single-quoted name; ``measure <name> = <expr>``)
  - display folder:             ``displayFolder: Sales``
  - relationship cross-filter:  ``crossFilteringBehavior: bothDirections``
  - implicit aggregation:       ``summarizeBy: sum``
  - gold-only M source schema:  ``Schema="gold"``
  - parameterized M source:     ``PostgreSQL.Database(Server, Database)``  (identifiers)
  - date-table marker:          ``annotation PBI_DateTable = true``  (table-level)
    *** PROVISIONAL ***  This is the table-level annotation form that M4.1's
    ``DATE_TABLE_MARKER`` constant consumes, used here so M0 and M4 agree. The exact
    "Mark as Date Table" TMDL literal is NOT yet confirmed against a real Power BI
    capture (spec §5.2 D7 note / §13 flag it may differ). RE-VERIFY against the real
    PBIP captured in Task M0.3 before M4 builds D7. If the captured real fixture shows
    a different marker literal, update BOTH M0 and M4.1's DATE_TABLE_MARKER together.
"""

from __future__ import annotations


def top_level_blocks(text: str) -> list[str]:
    """Return the stripped header line of each indentation-level-0 block, in order.

    A "top-level block" is any non-blank line that starts at column 0 (no leading
    whitespace) and is not a continuation. This is the smallest honest slice of the
    hand-rolled parser; M4 extends it with nested-block descent.
    """
    headers: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        if raw_line[0] in (" ", "\t"):
            continue
        headers.append(raw_line.strip())
    return headers
```

- [ ] **Step 2: Verify the module imports and the pinned tokens are present in the docstring**

```bash
python -c "from retail.tmdl import top_level_blocks; print(top_level_blocks('table Sales\n    column Amount\ntable Date'))"
```
Expected stdout (exact): `['table Sales', 'table Date']`

```bash
grep -c "crossFilteringBehavior: bothDirections" src/retail/tmdl.py
```
Expected stdout (exact): `1`

- [ ] **Step 3: Write the decision doc `docs/decisions/0001-tmdl-pbir-parser.md`**

```markdown
# 0001 — TMDL / PBIR parser choice

- **Date:** 2026-06-23
- **Status:** Accepted
- **Context:** The static governance core (spec §9) must parse committed TMDL and
  PBIR text with **no Power BI Desktop, no .NET, no network** — it has to run headless
  in CI on any OS (spec §11).

## Decision

- **TMDL → hand-rolled indentation/block tokenizer** in `src/retail/tmdl.py`.
- **PBIR / report JSON → stdlib `json`**, opened `encoding="utf-8-sig"` (Power BI
  writes UTF-8-with-BOM; a plain `json.load` raises on the BOM).

## Alternatives rejected

- **PyPI TMDL parsers** — surveyed 2026-06; none mature/maintained enough to take as a
  runtime dependency for a gate that must never falsely pass.
- **TOM (Tabular Object Model) / `sempy`** — read TMDL only via the Windows/.NET live
  path or the Fabric service. Both require a live connection and a platform we cannot
  guarantee in CI, so they defeat the headless requirement. Disqualified.

## Consequence

The parser is ours to maintain, but it stays dependency-light and OS-independent. Its
token expectations are pinned as a regression anchor in the `tmdl.py` module docstring
and locked by `tests/fixtures/golden_pbip/` (Task M0.2).
```

- [ ] **Step 4: Run lint/format on the new module**

```bash
ruff format --check src/retail/tmdl.py && ruff check src/retail/tmdl.py
```
Expected: ruff reports `1 file already formatted` and `All checks passed!` (exit 0).

- [ ] **Step 5: Commit the stub + decision doc**

```bash
git add src/retail/tmdl.py docs/decisions/0001-tmdl-pbir-parser.md
git commit -m "feat: add TMDL parser stub and record TMDL/PBIR parser decision"
```

---

### Task M0.2: Hand-authored golden PBIP fallback fixture + parser smoke test

Captures a minimal PBIP as committed fixture files so M4/M5 unit tests are NOT blocked
on a local Power BI Desktop capture (which Task M0.3 instructs separately). The fixture
is a **token-shape anchor**, not a globally-clean pass fixture: it deliberately contains
a `bothDirections` relationship (a D6 *violation*) and a `summarizeBy: sum` (a D5
*warning trigger*) — those are intentional anchors. M4/M5 author their own clean/dirty
pass-fail fixtures; M0 only pins the literals. The fixture has two tables — `Sales`
(fact) and `Date` (dim) — because a relationship needs two endpoints and the date-table
marker needs a Date table.

All fixture files are written **UTF-8 without BOM** (project CLAUDE.md rule; G3 flags a
leading BOM and this anchor must be G3-clean). The smoke test reads the PBIR with
`encoding="utf-8-sig"` per the runner contract.

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\RetailGold.SemanticModel\definition\model.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\RetailGold.SemanticModel\definition\relationships.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\RetailGold.Report\definition.pbir`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\.platform`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\RetailGold.pbip`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\README.md`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_tmdl.py`

**Interfaces:**
- Consumes: `top_level_blocks` from `src/retail/tmdl.py` (Task M0.1); stdlib `json`.
- Produces: `GOLDEN_PBIP_ROOT` (module-level `Path` constant in `tests/unit/test_tmdl.py`,
  repo-relative `tests/fixtures/golden_pbip`) — M4/M5 import or re-derive this path to
  locate the fixture.

- [ ] **Step 1: Write the failing smoke test `tests/unit/test_tmdl.py`**

```python
import json
from pathlib import Path

import pytest

from retail.tmdl import top_level_blocks

GOLDEN_PBIP_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden_pbip"
_MODEL = GOLDEN_PBIP_ROOT / "RetailGold.SemanticModel" / "definition" / "model.tmdl"
_RELS = GOLDEN_PBIP_ROOT / "RetailGold.SemanticModel" / "definition" / "relationships.tmdl"
_PBIR = GOLDEN_PBIP_ROOT / "RetailGold.Report" / "definition.pbir"


@pytest.mark.unit
def test_parser_reads_model_top_level_blocks() -> None:
    text = _MODEL.read_text(encoding="utf-8")
    blocks = top_level_blocks(text)
    assert "table Sales" in blocks
    assert "table Date" in blocks


@pytest.mark.unit
def test_model_pins_measure_and_displayfolder_and_no_slash() -> None:
    text = _MODEL.read_text(encoding="utf-8")
    assert "measure 'TotalSales' = SUM(Sales[Amount])" in text
    assert "displayFolder: Sales" in text
    assert "summarizeBy: sum" in text  # D5 warning anchor
    # D4 anchor: the measure body uses SUM, not a "/" division operator.
    assert "/" not in "measure 'TotalSales' = SUM(Sales[Amount])"


@pytest.mark.unit
def test_model_pins_gold_schema_and_parameterized_source() -> None:
    text = _MODEL.read_text(encoding="utf-8")
    assert 'Schema="gold"' in text  # D8 anchor
    assert "PostgreSQL.Database(Server, Database)" in text  # C1 anchor (identifiers)


@pytest.mark.unit
def test_model_pins_provisional_date_table_marker() -> None:
    # PROVISIONAL marker (spec §5.2 D7 / §13). Re-verify against the real PBIP from
    # Task M0.3 before M4 builds D7; if the real literal differs, update fixture + assert.
    text = _MODEL.read_text(encoding="utf-8")
    assert "annotation PBI_DateTable = true" in text


@pytest.mark.unit
def test_relationships_pins_bothdirections() -> None:
    # Intentional D6 VIOLATION used as the crossFilteringBehavior anchor.
    text = _RELS.read_text(encoding="utf-8")
    assert "crossFilteringBehavior: bothDirections" in text


@pytest.mark.unit
def test_pbir_is_bom_tolerant_and_uses_relative_bypath() -> None:
    # Contract: PBIR opened encoding="utf-8-sig" (BOM-tolerant). R1 anchor: byPath relative.
    data = json.loads(_PBIR.read_text(encoding="utf-8-sig"))
    path = data["datasetReference"]["byPath"]["path"]
    assert path == "../RetailGold.SemanticModel"
    assert not path[:1].isalpha() or path[1:2] != ":"  # not absolute "C:\..."
```

- [ ] **Step 2: Run the test to fail (fixtures absent)**

```bash
pytest -m unit tests/unit/test_tmdl.py -v
```
Expected: collection succeeds (import of `top_level_blocks` works after M0.1) but every
test ERRORs with `FileNotFoundError: ... tests\fixtures\golden_pbip\RetailGold.SemanticModel\definition\model.tmdl` (the fixture files do not exist yet). Exit code non-zero.

- [ ] **Step 3: Write `RetailGold.SemanticModel/definition/model.tmdl`** (UTF-8, no BOM)

```
table Sales
	column Amount
		dataType: decimal
		summarizeBy: sum
		sourceColumn: amount

	partition Sales = m
		mode: import
		source =
				let
					Source = PostgreSQL.Database(Server, Database),
					gold_sales = Source{[Schema="gold", Item="fct_sales"]}[Data]
				in
					gold_sales

	measure 'TotalSales' = SUM(Sales[Amount])
		displayFolder: Sales
		formatString: #,0

table Date
	annotation PBI_DateTable = true

	column Date
		dataType: dateTime
		dataCategory: Time
		summarizeBy: none
		sourceColumn: date

	partition Date = m
		mode: import
		source =
				let
					Source = PostgreSQL.Database(Server, Database),
					gold_dim_date = Source{[Schema="gold", Item="dim_date"]}[Data]
				in
					gold_dim_date
```

- [ ] **Step 4: Write `RetailGold.SemanticModel/definition/relationships.tmdl`** (UTF-8, no BOM)

```
relationship cc11aa22-bb33-4cc4-dd55-ee66ff770088
	fromColumn: Sales.Date
	toColumn: Date.Date
	crossFilteringBehavior: bothDirections
```

- [ ] **Step 5: Write `RetailGold.Report/definition.pbir`** (UTF-8, no BOM)

```json
{
  "version": "4.0",
  "datasetReference": {
    "byPath": {
      "path": "../RetailGold.SemanticModel"
    }
  }
}
```

- [ ] **Step 6: Write `.platform`, `RetailGold.pbip`, and the fixture `README.md`** (UTF-8, no BOM)

`.platform`:
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "Report",
    "displayName": "RetailGold"
  },
  "config": {
    "version": "2.0",
    "logicalId": "00000000-0000-0000-0000-000000000000"
  }
}
```

`RetailGold.pbip`:
```json
{
  "version": "1.0",
  "artifacts": [
    {
      "report": {
        "path": "RetailGold.Report"
      }
    }
  ],
  "settings": {
    "enableAutoRecovery": true
  }
}
```

`README.md`:
```markdown
# Golden PBIP fixture

Hand-authored minimal PBIP used as the **token-shape regression anchor** for the
TMDL/PBIR rules (M4/M5). It is intentionally NOT globally clean: the `bothDirections`
relationship (a D6 violation) and `summarizeBy: sum` (a D5 warning) are deliberate
anchors. Per-rule pass/fail fixtures live with the rules, not here.

The pinned literals are listed in `src/retail/tmdl.py`'s module docstring. If you edit
this fixture and a pinned token disappears, `tests/unit/test_tmdl.py` fails — that is
the anchor doing its job. The date-table marker (`annotation PBI_DateTable = true`) is
**PROVISIONAL** until replaced by a real Power BI capture (see Task M0.3).
```

- [ ] **Step 7: Run the smoke test to pass**

```bash
pytest -m unit tests/unit/test_tmdl.py -v
```
Expected: `6 passed` (all six tests green), exit 0.

- [ ] **Step 8: Assert no fixture file carries a UTF-8 BOM (G3-clean anchor)**

```bash
python -c "import pathlib,sys; bad=[str(p) for p in pathlib.Path('tests/fixtures/golden_pbip').rglob('*') if p.is_file() and p.read_bytes()[:3]==b'\xef\xbb\xbf']; print('BOM_FILES:', bad); sys.exit(1 if bad else 0)"
```
Expected stdout (exact): `BOM_FILES: []` and exit 0.

- [ ] **Step 9: Commit the fixture + smoke test**

```bash
git add tests/fixtures/golden_pbip tests/unit/test_tmdl.py
git commit -m "test: add hand-authored golden PBIP fixture and TMDL parser smoke test"
```

---

### Task M0.3: Local-capture instructions for the real golden PBIP

The hand-authored fixture (M0.2) unblocks M4/M5, but its token literals are the
implementer's best guess — most critically the **PROVISIONAL** date-table marker. This
task records the exact steps to capture ONE real minimal PBIP locally and reconcile the
pinned literals against it. It **requires Power BI Desktop or `pbi-cli` and is NOT run in
CI or by this agent** — so it has no pytest PASS line. Its durable deliverable is a
committed real PBIP that replaces (or confirms) the hand-authored anchor; the verification
is a `git ls-files` check, not a test.

**Files:**
- Modify (after capture): `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\tmdl.py` (reconcile the PROVISIONAL date-table marker + any literal that differs from the real capture)
- Create (after capture, real artifact paths): `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\` real PBIP under a `RetailGold.SemanticModel/`, `RetailGold.Report/` skeleton (or a parallel `golden_pbip_real/` if the implementer wants to keep both — choose one and update `GOLDEN_PBIP_ROOT`)
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\golden_pbip\CAPTURE.md` (the instructions below, committed so they outlive this plan)

**Interfaces:**
- Consumes: nothing programmatic.
- Produces: a verified real PBIP and a reconciled set of pinned literals in `tmdl.py`.

- [ ] **Step 1: Write the capture instructions to `tests/fixtures/golden_pbip/CAPTURE.md`**

```markdown
# Capturing the real golden PBIP (MANUAL, LOCAL — requires Power BI Desktop or pbi-cli)

> NOT run in CI or by the coding agent. Do this once on a Windows machine with Power BI
> Desktop (PBIP preview enabled) or `pbi-cli` installed, then commit the result.

## Option A — pbi-cli (preferred, scriptable)

From the repo root:

    pbi report create --name RetailGold --output tests/fixtures/golden_pbip

Then add one `Sales` table, one `Date` table, one `TotalSales` measure, and one
relationship, and **Mark the Date table as a date table** in Desktop (the whole point
of this capture is the real "Mark as Date Table" TMDL literal — D7's anchor).

## Option B — Power BI Desktop Save As

1. Enable PBIP: File > Options > Preview features > "Power BI Project (.pbip) save option".
2. Build the minimal model: `Sales` (with `Amount`), `Date` (with `Date`), measure
   `TotalSales = SUM(Sales[Amount])`, a `Sales.Date -> Date.Date` relationship.
3. Mark `Date` as a date table (Table tools > Mark as date table).
4. File > Save as > Power BI Project (.pbip), target `tests/fixtures/golden_pbip`.

## After capture — reconcile and verify

1. Open the real `*.SemanticModel/definition/*.tmdl` and compare each pinned literal in
   `src/retail/tmdl.py`'s docstring against the real text. The likely mismatch is the
   date-table marker (table-level annotation vs `dataCategory: Time`). Update the
   docstring literal, the fixture, AND the `test_model_pins_provisional_date_table_marker`
   assertion in `tests/unit/test_tmdl.py`. Remove the `*** PROVISIONAL ***` banner once
   confirmed.
2. Verify the real definition files are tracked and the local-only files are ignored:

       git add tests/fixtures/golden_pbip
       git ls-files tests/fixtures/golden_pbip | grep "definition/"
       git check-ignore "tests/fixtures/golden_pbip/RetailGold.SemanticModel/.pbi/cache.abf"

   The first must list the `definition/` TMDL/PBIR files; the second must print the
   `cache.abf` path (ignored). If `definition/` files are missing from `git ls-files`,
   the model is being dropped from git — fix `.gitignore` before committing.
3. Re-run `pytest -m unit tests/unit/test_tmdl.py -v` — it must stay green against the
   real fixture.
```

- [ ] **Step 2: Verify the instructions doc is the only thing this task commits now**

```bash
git status --short tests/fixtures/golden_pbip/CAPTURE.md
```
Expected stdout (exact): `?? tests/fixtures/golden_pbip/CAPTURE.md`

- [ ] **Step 3: Commit the capture instructions**

```bash
git add tests/fixtures/golden_pbip/CAPTURE.md
git commit -m "docs: add manual local-capture instructions for the real golden PBIP"
```

> **Note for the executor:** Steps after this point (running `pbi report create` /
> Save-as-PBIP, reconciling the PROVISIONAL date-table marker, re-committing the real
> fixture) are the manual local follow-up described in `CAPTURE.md`. They are NOT
> executed by the agent or in CI and have no PASS line — the committed hand-authored
> fixture (M0.2) is what keeps M4/M5 unblocked in the meantime.


---

## Milestone 2 — Git-Metadata Rules

## Milestone M2 — Git-metadata rules (6 rules live today)

These six rules (C2, G1, G2, G5, P1, P2) operate on `git ls-files` / `git check-ignore` / `git log` and on a handful of repo-relative paths — they have real artifacts to check on the current repo. All rules live in `src/retail/rules/git_meta.py`; tests in `tests/unit/test_git_meta.py`. A shared subprocess helper (`src/retail/gitutil.py`) and a test fixture helper (`tests/unit/_gitfix.py`) are introduced here because the runner contract does not provide them.

> Contract names consumed verbatim (from `src/retail/core.py` / `src/retail/registry.py`): `Severity`, `Finding`, `RuleContext`, `register`. `RuleContext(repo_root: Path, tracked_files: tuple[str, ...])`.

---

### Task M2.1: Git subprocess helper (`gitutil`)

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\gitutil.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`
- Test (fixture helper): `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\_gitfix.py`

**Interfaces:**
- Produces `git_output(repo_root: Path, *args: str) -> str` — runs `git -C <repo_root> <args>` and returns stdout (UTF-8), raising on non-zero.
- Produces `git_check_ignore(repo_root: Path, path: str) -> bool` — `True` iff `git check-ignore` reports the path ignored (exit 0); `False` on exit 1 (not ignored); raises on exit 128.
- Produces `git_log_subjects(repo_root: Path, base_ref: str) -> list[str]` — `git log --no-merges <base_ref>..HEAD --format=%s` split into subject lines (merge commits excluded by `--no-merges`).
- Produces test helpers `make_git_repo(tmp_path) -> Path` and `context_for(repo_root: Path) -> RuleContext` in `_gitfix.py`.

- [ ] **Step 1: Write the fixture helper `_gitfix.py` (used by every later test).**
  Create `tests/unit/_gitfix.py`:
  ```python
  from __future__ import annotations

  import subprocess
  from pathlib import Path

  from retail.core import RuleContext


  def make_git_repo(tmp_path: Path) -> Path:
      """Init a deterministic git repo at tmp_path/repo with an identity and main branch."""
      repo = tmp_path / "repo"
      repo.mkdir()
      subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True,
                     capture_output=True)
      subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo,
                     check=True, capture_output=True)
      subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True,
                     capture_output=True)
      return repo


  def commit_all(repo: Path, message: str) -> None:
      subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
      subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True,
                     capture_output=True)


  def context_for(repo: Path) -> RuleContext:
      out = subprocess.run(["git", "ls-files"], cwd=repo, check=True,
                           capture_output=True, text=True).stdout
      tracked = tuple(line for line in out.splitlines() if line)
      return RuleContext(repo_root=repo, tracked_files=tracked)
  ```

- [ ] **Step 2: Write the failing test for `git_check_ignore`.**
  Add to `tests/unit/test_git_meta.py`:
  ```python
  from __future__ import annotations

  import pytest

  from retail import gitutil
  from tests.unit._gitfix import commit_all, context_for, make_git_repo


  @pytest.mark.unit
  def test_git_check_ignore_respects_gitignore(tmp_path):
      repo = make_git_repo(tmp_path)
      (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
      (repo / ".env").write_text("SECRET=x\n", encoding="utf-8")
      (repo / "keep.txt").write_text("ok\n", encoding="utf-8")
      assert gitutil.git_check_ignore(repo, ".env") is True
      assert gitutil.git_check_ignore(repo, "keep.txt") is False
  ```

- [ ] **Step 3: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ModuleNotFoundError: No module named 'retail.gitutil'` (or `ImportError`).

- [ ] **Step 4: Implement `gitutil.py` minimally.**
  Create `src/retail/gitutil.py`:
  ```python
  from __future__ import annotations

  import subprocess
  from pathlib import Path


  def git_output(repo_root: Path, *args: str) -> str:
      result = subprocess.run(
          ["git", "-C", str(repo_root), *args],
          capture_output=True,
          text=True,
          encoding="utf-8",
      )
      if result.returncode != 0:
          raise RuntimeError(
              f"git {' '.join(args)} failed ({result.returncode}): {result.stderr}"
          )
      return result.stdout


  def git_check_ignore(repo_root: Path, path: str) -> bool:
      result = subprocess.run(
          ["git", "-C", str(repo_root), "check-ignore", "-q", path],
          capture_output=True,
          text=True,
      )
      if result.returncode == 0:
          return True
      if result.returncode == 1:
          return False
      raise RuntimeError(
          f"git check-ignore error ({result.returncode}): {result.stderr}"
      )


  def git_log_subjects(repo_root: Path, base_ref: str) -> list[str]:
      out = git_output(
          repo_root, "log", "--no-merges", f"{base_ref}..HEAD", "--format=%s"
      )
      return [line for line in out.splitlines() if line]
  ```

- [ ] **Step 5: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: `test_git_check_ignore_respects_gitignore PASSED` (1 passed).

- [ ] **Step 6: Commit.**
  Command: `git add src/retail/gitutil.py tests/unit/_gitfix.py tests/unit/test_git_meta.py && git commit -m "feat: add git subprocess helper for git-metadata rules"`

---

### Task M2.2: G5 — repo-relative path length > 200 fails

**Files:**
- Create/Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`

**Interfaces:**
- Produces `rule_g5_path_length(ctx: RuleContext) -> list[Finding]` registered as `register("G5", "Windows MAX_PATH discipline")`.
- Consumes `ctx.tracked_files` only (no subprocess). One `Finding(rule_id="G5", severity=Severity.ERROR, message=..., locator=<path>)` per path with `len(path) > 200`.

- [ ] **Step 1: Write failing test (synthetic path — no real file created).**
  G5 reads only `tracked_files` strings, so build a `RuleContext` directly with a 201-char path. Do NOT create a real >200-char file (Windows MAX_PATH would fail the create, not the rule). Add to `tests/unit/test_git_meta.py`:
  ```python
  from pathlib import Path

  from retail.core import RuleContext, Severity
  from retail.rules.git_meta import rule_g5_path_length


  @pytest.mark.unit
  def test_g5_flags_long_path():
      long_path = "warehouse/migrations/" + ("x" * 201) + ".sql"
      assert len(long_path) > 200
      ctx = RuleContext(repo_root=Path("."), tracked_files=(long_path, "ok.sql"))
      findings = list(rule_g5_path_length(ctx))
      assert len(findings) == 1
      f = findings[0]
      assert f.rule_id == "G5"
      assert f.severity is Severity.ERROR
      assert f.locator == long_path


  @pytest.mark.unit
  def test_g5_passes_short_paths():
      ctx = RuleContext(repo_root=Path("."), tracked_files=("warehouse/x.sql",))
      assert list(rule_g5_path_length(ctx)) == []
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ModuleNotFoundError: No module named 'retail.rules.git_meta'`.

- [ ] **Step 3: Implement G5 (create the group module).**
  Create `src/retail/rules/git_meta.py`:
  ```python
  from __future__ import annotations

  from collections.abc import Iterable

  from ..core import Finding, RuleContext, Severity
  from ..registry import register

  MAX_REL_PATH = 200


  @register("G5", "Windows MAX_PATH discipline")
  def rule_g5_path_length(ctx: RuleContext) -> Iterable[Finding]:
      findings: list[Finding] = []
      for path in ctx.tracked_files:
          if len(path) > MAX_REL_PATH:
              findings.append(
                  Finding(
                      rule_id="G5",
                      severity=Severity.ERROR,
                      message=(
                          f"repo-relative path is {len(path)} chars "
                          f"(> {MAX_REL_PATH}); risks Windows MAX_PATH overflow"
                      ),
                      locator=path,
                  )
              )
      return findings
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: `test_g5_flags_long_path PASSED`, `test_g5_passes_short_paths PASSED` (3 passed total).

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add G5 path-length rule"`

---

### Task M2.3: P1 — Approach-A repo layout

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`

**Interfaces:**
- Produces `rule_p1_layout(ctx: RuleContext) -> list[Finding]` registered as `register("P1", "Approach-A layout")`.
- Consumes `ctx.tracked_files`. ERROR `Finding`s for: a missing required dir/README; any PBIP signature (`*.pbip`, `*.SemanticModel/`, `*.Report/`, `definition.pbir`) not under `powerbi/`; any `*.sql` not under `warehouse/`. Locator = the offending path, or the required path for a missing-dir finding.

- [ ] **Step 1: Write failing tests (passing layout + two violations).**
  Add to `tests/unit/test_git_meta.py`:
  ```python
  from retail.rules.git_meta import rule_p1_layout

  GOOD_LAYOUT = (
      "README.md",
      "warehouse/README.md",
      "powerbi/README.md",
      "warehouse/migrations/0001_init.sql",
      "powerbi/Sales.pbip",
  )


  @pytest.mark.unit
  def test_p1_accepts_good_layout():
      ctx = RuleContext(repo_root=Path("."), tracked_files=GOOD_LAYOUT)
      assert list(rule_p1_layout(ctx)) == []


  @pytest.mark.unit
  def test_p1_flags_misplaced_sql_and_pbip():
      tracked = GOOD_LAYOUT + ("scripts/adhoc.sql", "reports/Sales.pbip")
      ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
      ids = {f.locator for f in rule_p1_layout(ctx)}
      assert "scripts/adhoc.sql" in ids
      assert "reports/Sales.pbip" in ids


  @pytest.mark.unit
  def test_p1_flags_missing_required_dir():
      tracked = ("README.md", "warehouse/README.md")  # no powerbi/README.md
      ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
      findings = list(rule_p1_layout(ctx))
      assert any(f.locator == "powerbi/README.md" for f in findings)
      assert all(f.severity is Severity.ERROR for f in findings)
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ImportError: cannot import name 'rule_p1_layout' from 'retail.rules.git_meta'`.

- [ ] **Step 3: Implement P1.**
  Append to `src/retail/rules/git_meta.py`:
  ```python
  REQUIRED_PATHS = ("README.md", "warehouse/README.md", "powerbi/README.md")
  PBIP_SIGNATURES = (".pbip", "definition.pbir")
  PBIP_DIR_MARKERS = (".SemanticModel/", ".Report/")


  def _is_pbip_signature(path: str) -> bool:
      if path.endswith(PBIP_SIGNATURES):
          return True
      return any(marker in path for marker in PBIP_DIR_MARKERS)


  @register("P1", "Approach-A layout")
  def rule_p1_layout(ctx: RuleContext) -> Iterable[Finding]:
      tracked = set(ctx.tracked_files)
      findings: list[Finding] = []
      for required in REQUIRED_PATHS:
          if required not in tracked:
              findings.append(
                  Finding(
                      rule_id="P1",
                      severity=Severity.ERROR,
                      message=f"required layout path is missing: {required}",
                      locator=required,
                  )
              )
      for path in ctx.tracked_files:
          if _is_pbip_signature(path) and not path.startswith("powerbi/"):
              findings.append(
                  Finding(
                      rule_id="P1",
                      severity=Severity.ERROR,
                      message="PBIP artifact must live under powerbi/",
                      locator=path,
                  )
              )
          if path.endswith(".sql") and not path.startswith("warehouse/"):
              findings.append(
                  Finding(
                      rule_id="P1",
                      severity=Severity.ERROR,
                      message="*.sql must live under warehouse/",
                      locator=path,
                  )
              )
      return findings
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: `test_p1_accepts_good_layout`, `test_p1_flags_misplaced_sql_and_pbip`, `test_p1_flags_missing_required_dir` all PASSED (6 passed total).

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add P1 Approach-A layout rule"`

---

### Task M2.4: G1 — `.gitignore` correctness (must-contain subset + must-not-ignore predicate)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`

**Interfaces:**
- Produces `rule_g1_gitignore_correctness(ctx: RuleContext) -> list[Finding]` registered as `register("G1", ".gitignore correctness")`.
- Consumes `ctx.repo_root` (reads `.gitignore`) and `gitutil.git_check_ignore`. ERROR if any of `{**/.pbi/localSettings.json, **/.pbi/cache.abf, .env}` is absent (locator `.gitignore`). ERROR if any synthesized `definition/` path is reported ignored by `git check-ignore` (locator = the synthesized path). Extra ignore entries are permitted (subset check).

- [ ] **Step 1: Write failing tests (good repo, missing entry, over-broad ignore).**
  Add to `tests/unit/test_git_meta.py`:
  ```python
  from retail.rules.git_meta import rule_g1_gitignore_correctness

  GOOD_GITIGNORE = (
      "**/.pbi/localSettings.json\n"
      "**/.pbi/cache.abf\n"
      ".env\n"
      "__pycache__/\n"  # extra entry — permitted
  )


  @pytest.mark.unit
  def test_g1_accepts_correct_gitignore(tmp_path):
      repo = make_git_repo(tmp_path)
      (repo / ".gitignore").write_text(GOOD_GITIGNORE, encoding="utf-8")
      commit_all(repo, "chore: add gitignore")
      assert list(rule_g1_gitignore_correctness(context_for(repo))) == []


  @pytest.mark.unit
  def test_g1_flags_missing_required_entry(tmp_path):
      repo = make_git_repo(tmp_path)
      (repo / ".gitignore").write_text("**/.pbi/cache.abf\n.env\n", encoding="utf-8")
      commit_all(repo, "chore: add gitignore")
      findings = list(rule_g1_gitignore_correctness(context_for(repo)))
      assert any("localSettings.json" in f.message for f in findings)
      assert all(f.severity is Severity.ERROR for f in findings)


  @pytest.mark.unit
  def test_g1_flags_ignored_definition_path(tmp_path):
      repo = make_git_repo(tmp_path)
      (repo / ".gitignore").write_text(
          GOOD_GITIGNORE + "definition/\n", encoding="utf-8"
      )
      commit_all(repo, "chore: add gitignore")
      findings = list(rule_g1_gitignore_correctness(context_for(repo)))
      assert any("definition" in f.locator for f in findings)
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ImportError: cannot import name 'rule_g1_gitignore_correctness' from 'retail.rules.git_meta'`.

- [ ] **Step 3: Implement G1.**
  Append to `src/retail/rules/git_meta.py` (add `from .. import gitutil` to the imports at the top — combine with existing import edits in one save):
  ```python
  REQUIRED_IGNORES = (
      "**/.pbi/localSettings.json",
      "**/.pbi/cache.abf",
      ".env",
  )
  # synthesized PBIP definition paths that must NOT be ignored
  DEFINITION_PROBE_PATHS = (
      "powerbi/Sales.SemanticModel/definition/model.tmdl",
      "powerbi/Sales.Report/definition/report.json",
  )


  @register("G1", ".gitignore correctness")
  def rule_g1_gitignore_correctness(ctx: RuleContext) -> Iterable[Finding]:
      findings: list[Finding] = []
      gitignore = ctx.repo_root / ".gitignore"
      lines = (
          {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
          if gitignore.exists()
          else set()
      )
      for required in REQUIRED_IGNORES:
          if required not in lines:
              findings.append(
                  Finding(
                      rule_id="G1",
                      severity=Severity.ERROR,
                      message=f".gitignore must contain '{required}'",
                      locator=".gitignore",
                  )
              )
      for probe in DEFINITION_PROBE_PATHS:
          if gitutil.git_check_ignore(ctx.repo_root, probe):
              findings.append(
                  Finding(
                      rule_id="G1",
                      severity=Severity.ERROR,
                      message=(
                          "a .gitignore pattern ignores a PBIP definition/ path "
                          "(the model must never be ignored)"
                      ),
                      locator=probe,
                  )
              )
      return findings
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: `test_g1_accepts_correct_gitignore`, `test_g1_flags_missing_required_entry`, `test_g1_flags_ignored_definition_path` PASSED (9 passed total).

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add G1 gitignore-correctness rule"`

---

### Task M2.5: G2 — PBIP definition artifacts committed (with INFO empty-case)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`

**Interfaces:**
- Produces `rule_g2_definition_committed(ctx: RuleContext) -> list[Finding]` registered as `register("G2", "definition artifacts committed")`.
- Consumes `ctx.tracked_files` and `gitutil.git_check_ignore`. If no PBIP signature is tracked → emit exactly one INFO `Finding(rule_id="G2", severity=Severity.INFO, message="no PBIP project present", locator=".")` (NOT a silent empty list). If PBIP present: ERROR for any tracked `.pbi/localSettings.json` or `.pbi/cache.abf`; ERROR if any tracked PBIP signature path is reported ignored by `git check-ignore`.

- [ ] **Step 1: Write failing tests (empty-case INFO, tracked cache.abf error).**
  Add to `tests/unit/test_git_meta.py`:
  ```python
  from retail.rules.git_meta import rule_g2_definition_committed


  @pytest.mark.unit
  def test_g2_emits_info_when_no_pbip(tmp_path):
      repo = make_git_repo(tmp_path)
      (repo / "README.md").write_text("hi\n", encoding="utf-8")
      commit_all(repo, "docs: readme")
      findings = list(rule_g2_definition_committed(context_for(repo)))
      assert len(findings) == 1
      assert findings[0].severity is Severity.INFO
      assert findings[0].message == "no PBIP project present"


  @pytest.mark.unit
  def test_g2_flags_tracked_cache_abf(tmp_path):
      repo = make_git_repo(tmp_path)
      pbip_dir = repo / "powerbi" / "Sales.SemanticModel" / "definition"
      pbip_dir.mkdir(parents=True)
      (pbip_dir / "model.tmdl").write_text("model\n", encoding="utf-8")
      (repo / "powerbi" / "Sales.pbip").write_text("{}\n", encoding="utf-8")
      pbi_dir = repo / "powerbi" / "Sales.SemanticModel" / ".pbi"
      pbi_dir.mkdir(parents=True)
      (pbi_dir / "cache.abf").write_text("x\n", encoding="utf-8")
      commit_all(repo, "feat: add pbip with stray cache")
      findings = list(rule_g2_definition_committed(context_for(repo)))
      assert any("cache.abf" in f.locator and f.severity is Severity.ERROR
                 for f in findings)
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ImportError: cannot import name 'rule_g2_definition_committed' from 'retail.rules.git_meta'`.

- [ ] **Step 3: Implement G2.**
  Append to `src/retail/rules/git_meta.py`:
  ```python
  FORBIDDEN_TRACKED = (".pbi/localSettings.json", ".pbi/cache.abf")


  @register("G2", "definition artifacts committed")
  def rule_g2_definition_committed(ctx: RuleContext) -> Iterable[Finding]:
      pbip_paths = [p for p in ctx.tracked_files if _is_pbip_signature(p)]
      if not pbip_paths:
          return [
              Finding(
                  rule_id="G2",
                  severity=Severity.INFO,
                  message="no PBIP project present",
                  locator=".",
              )
          ]
      findings: list[Finding] = []
      for path in ctx.tracked_files:
          if path.endswith(FORBIDDEN_TRACKED):
              findings.append(
                  Finding(
                      rule_id="G2",
                      severity=Severity.ERROR,
                      message="Desktop-local PBIP file must not be tracked",
                      locator=path,
                  )
              )
      for path in pbip_paths:
          if gitutil.git_check_ignore(ctx.repo_root, path):
              findings.append(
                  Finding(
                      rule_id="G2",
                      severity=Severity.ERROR,
                      message="tracked PBIP artifact is also gitignored",
                      locator=path,
                  )
              )
      return findings
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: `test_g2_emits_info_when_no_pbip`, `test_g2_flags_tracked_cache_abf` PASSED (11 passed total).

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add G2 definition-committed rule with INFO empty-case"`

---

### Task M2.6: P2 — commit-subject convention over BASE..HEAD (merge-exempt)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`

**Interfaces:**
- Produces `rule_p2_commit_subjects(ctx: RuleContext) -> list[Finding]` registered as `register("P2", "commit-message convention")`.
- Consumes the contract-v2 invocation fields on `RuleContext` (no `os.environ`):
  - if `ctx.commit_message is not None` → **commit-msg-hook mode**: validate that single incoming subject (first line of the message);
  - elif `ctx.commit_range is not None` → **CI mode**: scan that range via `gitutil.git_log_subjects(ctx.repo_root, ctx.commit_range)`;
  - else → **local fallback**: scan the default range `HEAD~20` (`DEFAULT_BASE_REF`).
  Each subject must match `^(feat|fix|refactor|docs|chore): .+`; merge commits are already excluded by `--no-merges`. ERROR `Finding` per non-conforming subject, locator = the subject text.

- [ ] **Step 1: Write failing tests (good + bad subjects, merge exempt).**
  Add to `tests/unit/test_git_meta.py`:
  ```python
  import subprocess

  from retail.rules.git_meta import rule_p2_commit_subjects


  def _build_p2_history(repo):
      subprocess.run(["git", "commit", "--allow-empty", "-m", "feat: base"],
                     cwd=repo, check=True, capture_output=True)
      base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                            capture_output=True, text=True).stdout.strip()
      subprocess.run(["git", "commit", "--allow-empty", "-m", "fix: ok change"],
                     cwd=repo, check=True, capture_output=True)
      subprocess.run(["git", "commit", "--allow-empty", "-m", "bad subject here"],
                     cwd=repo, check=True, capture_output=True)
      return base


  @pytest.mark.unit
  def test_p2_flags_bad_subject(tmp_path):
      import dataclasses

      repo = make_git_repo(tmp_path)
      base = _build_p2_history(repo)
      # CI mode: scope P2 to a commit range via the contract field (no env var).
      ctx = dataclasses.replace(context_for(repo), commit_range=base)
      findings = list(rule_p2_commit_subjects(ctx))
      assert len(findings) == 1
      assert findings[0].rule_id == "P2"
      assert findings[0].locator == "bad subject here"
      assert findings[0].severity is Severity.ERROR


  @pytest.mark.unit
  def test_p2_validates_single_commit_message(tmp_path):
      import dataclasses

      repo = make_git_repo(tmp_path)
      # commit-msg-hook mode: a single incoming subject via ctx.commit_message.
      ctx = dataclasses.replace(context_for(repo), commit_message="bad subject here")
      findings = list(rule_p2_commit_subjects(ctx))
      assert len(findings) == 1
      assert findings[0].locator == "bad subject here"
      # A conforming message yields no findings.
      ok = dataclasses.replace(context_for(repo), commit_message="feat: a thing")
      assert list(rule_p2_commit_subjects(ok)) == []


  @pytest.mark.unit
  def test_p2_exempts_merge_commits(tmp_path):
      repo = make_git_repo(tmp_path)
      subprocess.run(["git", "commit", "--allow-empty", "-m", "feat: base"],
                     cwd=repo, check=True, capture_output=True)
      base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                            capture_output=True, text=True).stdout.strip()
      subprocess.run(["git", "checkout", "-b", "side"], cwd=repo, check=True,
                     capture_output=True)
      subprocess.run(["git", "commit", "--allow-empty", "-m", "feat: side work"],
                     cwd=repo, check=True, capture_output=True)
      subprocess.run(["git", "checkout", "main"], cwd=repo, check=True,
                     capture_output=True)
      subprocess.run(["git", "merge", "--no-ff", "side", "-m",
                      "Merge branch 'side'"], cwd=repo, check=True,
                     capture_output=True)
      import dataclasses

      ctx = dataclasses.replace(context_for(repo), commit_range=base)
      assert list(rule_p2_commit_subjects(ctx)) == []
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ImportError: cannot import name 'rule_p2_commit_subjects' from 'retail.rules.git_meta'`.

- [ ] **Step 3: Implement P2.**
  Append to `src/retail/rules/git_meta.py` (add `import re` to the top imports in the same save — no `import os`; the base ref now comes from `RuleContext`, never the environment):
  ```python
  SUBJECT_RE = re.compile(r"^(feat|fix|refactor|docs|chore): .+")
  DEFAULT_BASE_REF = "HEAD~20"


  @register("P2", "commit-message convention")
  def rule_p2_commit_subjects(ctx: RuleContext) -> Iterable[Finding]:
      # Source the subjects to validate from the contract-v2 invocation fields:
      #   commit-msg-hook mode -> the single incoming message;
      #   CI mode             -> every subject in the supplied commit range;
      #   local fallback      -> the last DEFAULT_BASE_REF..HEAD commits.
      if ctx.commit_message is not None:
          subjects = [ctx.commit_message.splitlines()[0] if ctx.commit_message else ""]
      else:
          base_ref = ctx.commit_range if ctx.commit_range is not None else DEFAULT_BASE_REF
          subjects = gitutil.git_log_subjects(ctx.repo_root, base_ref)
      findings: list[Finding] = []
      for subject in subjects:
          if not SUBJECT_RE.match(subject):
              findings.append(
                  Finding(
                      rule_id="P2",
                      severity=Severity.ERROR,
                      message=(
                          "commit subject must match "
                          "'<type>: <desc>' (feat|fix|refactor|docs|chore)"
                      ),
                      locator=subject,
                  )
              )
      return findings
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: `test_p2_flags_bad_subject`, `test_p2_validates_single_commit_message`, `test_p2_exempts_merge_commits` PASSED (14 passed total).

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add P2 commit-subject convention rule"`

---

### Task M2.7: C2 — no committed secrets (gitignore + .env.example keys + content scan)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`

**Interfaces:**
- Produces `rule_c2_no_committed_secrets(ctx: RuleContext) -> list[Finding]` registered as `register("C2", "no committed secrets")`.
- Consumes `ctx.repo_root`, `ctx.tracked_files`, `gitutil.git_check_ignore`. Three checks: (a) `.env` must be untracked AND gitignored; (b) `.env.example` must contain the six `ANALYTICS_DB_*` keys with HOST/NAME/USER/PASSWORD empty (PORT/SSLMODE may carry defaults); (c) content-scan tracked files (EXCLUDING `docs/` and `*.example`) for `postgres(ql)?://[^@]+@` and a real `<label>.db.ondigitalocean.com` (excluding angle-bracket placeholders). Locator = `path:line` for content hits, else the file path.

- [ ] **Step 1: Write failing tests — covering ALL FOUR endpoint cases.**
  The verified false-positive `<your-db-host>.db.ondigitalocean.com` must be placed in a ROOT-level scanned file (not `docs/`, not `*.example`) so the regex exclusion — not the path exclusion — is what keeps it clean. Add to `tests/unit/test_git_meta.py`:
  ```python
  from retail.rules.git_meta import rule_c2_no_committed_secrets

  GOOD_ENV_EXAMPLE = (
      "ANALYTICS_DB_HOST=\n"
      "ANALYTICS_DB_PORT=25060\n"
      "ANALYTICS_DB_NAME=\n"
      "ANALYTICS_DB_USER=\n"
      "ANALYTICS_DB_PASSWORD=\n"
      "ANALYTICS_DB_SSLMODE=require\n"
  )


  def _seed_c2_repo(repo):
      (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
      (repo / ".env.example").write_text(GOOD_ENV_EXAMPLE, encoding="utf-8")


  @pytest.mark.unit
  def test_c2_clean_repo_passes(tmp_path):
      repo = make_git_repo(tmp_path)
      _seed_c2_repo(repo)
      commit_all(repo, "chore: seed env example")
      assert list(rule_c2_no_committed_secrets(context_for(repo))) == []


  @pytest.mark.unit
  def test_c2_flags_real_endpoint_in_scanned_file(tmp_path):
      repo = make_git_repo(tmp_path)
      _seed_c2_repo(repo)
      (repo / "config.txt").write_text(
          "host = db-prod-01.db.ondigitalocean.com\n", encoding="utf-8"
      )
      commit_all(repo, "chore: add config")
      findings = list(rule_c2_no_committed_secrets(context_for(repo)))
      assert any(f.locator.startswith("config.txt:") for f in findings)


  @pytest.mark.unit
  def test_c2_ignores_angle_bracket_placeholder_in_scanned_file(tmp_path):
      repo = make_git_repo(tmp_path)
      _seed_c2_repo(repo)
      # ROOT-level scanned file (not docs/, not *.example) — exercises the REGEX
      # exclusion, not the path exclusion.
      (repo / "config.txt").write_text(
          "host = <your-db-host>.db.ondigitalocean.com\n", encoding="utf-8"
      )
      commit_all(repo, "chore: add placeholder config")
      assert list(rule_c2_no_committed_secrets(context_for(repo))) == []


  @pytest.mark.unit
  def test_c2_skips_docs_and_example_files(tmp_path):
      repo = make_git_repo(tmp_path)
      _seed_c2_repo(repo)
      docs = repo / "docs"
      docs.mkdir()
      (docs / "conn.md").write_text(
          "postgresql://user:pw@real-host.db.ondigitalocean.com:25060/db\n",
          encoding="utf-8",
      )
      (repo / "settings.example").write_text(
          "postgresql://user:pw@real-host.db.ondigitalocean.com/db\n",
          encoding="utf-8",
      )
      commit_all(repo, "docs: add connection placeholders")
      assert list(rule_c2_no_committed_secrets(context_for(repo))) == []


  @pytest.mark.unit
  def test_c2_flags_tracked_env(tmp_path):
      repo = make_git_repo(tmp_path)
      _seed_c2_repo(repo)
      (repo / ".env").write_text("ANALYTICS_DB_PASSWORD=hunter2\n", encoding="utf-8")
      subprocess.run(["git", "add", "-f", ".env"], cwd=repo, check=True,
                     capture_output=True)
      commit_all(repo, "chore: oops env")
      findings = list(rule_c2_no_committed_secrets(context_for(repo)))
      assert any(f.locator == ".env" for f in findings)


  @pytest.mark.unit
  def test_c2_flags_env_example_with_filled_secret(tmp_path):
      repo = make_git_repo(tmp_path)
      (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
      bad = GOOD_ENV_EXAMPLE.replace(
          "ANALYTICS_DB_PASSWORD=\n", "ANALYTICS_DB_PASSWORD=secret\n"
      )
      (repo / ".env.example").write_text(bad, encoding="utf-8")
      commit_all(repo, "chore: bad example")
      findings = list(rule_c2_no_committed_secrets(context_for(repo)))
      assert any("ANALYTICS_DB_PASSWORD" in f.message for f in findings)
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected fail: `ImportError: cannot import name 'rule_c2_no_committed_secrets' from 'retail.rules.git_meta'`.

- [ ] **Step 3: Implement C2.**
  Append to `src/retail/rules/git_meta.py`:
  ```python
  # A real DigitalOcean endpoint: a concrete subdomain label (alnum start, then
  # alnum/hyphen) directly before `.db.ondigitalocean.com`. `>` from an
  # angle-bracket placeholder cannot sit in the label class, so
  # `<your-db-host>.db.ondigitalocean.com` does NOT match.
  DO_ENDPOINT_RE = re.compile(
      r"[A-Za-z0-9][A-Za-z0-9-]*\.db\.ondigitalocean\.com"
  )
  CONN_URI_RE = re.compile(r"postgres(?:ql)?://[^@\s]+@")
  REQUIRED_ENV_KEYS = (
      "ANALYTICS_DB_HOST",
      "ANALYTICS_DB_PORT",
      "ANALYTICS_DB_NAME",
      "ANALYTICS_DB_USER",
      "ANALYTICS_DB_PASSWORD",
      "ANALYTICS_DB_SSLMODE",
  )
  MUST_BE_EMPTY = (
      "ANALYTICS_DB_HOST",
      "ANALYTICS_DB_NAME",
      "ANALYTICS_DB_USER",
      "ANALYTICS_DB_PASSWORD",
  )


  def _scan_excluded(path: str) -> bool:
      return path.startswith("docs/") or path.endswith(".example")


  def _check_env_file(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      if ".env" in ctx.tracked_files:
          findings.append(
              Finding(
                  rule_id="C2",
                  severity=Severity.ERROR,
                  message=".env must never be tracked",
                  locator=".env",
              )
          )
      elif not gitutil.git_check_ignore(ctx.repo_root, ".env"):
          findings.append(
              Finding(
                  rule_id="C2",
                  severity=Severity.ERROR,
                  message=".env must be gitignored",
                  locator=".gitignore",
              )
          )
      return findings


  def _check_env_example(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      example = ctx.repo_root / ".env.example"
      if not example.exists():
          return [
              Finding(
                  rule_id="C2",
                  severity=Severity.ERROR,
                  message=".env.example is missing",
                  locator=".env.example",
              )
          ]
      pairs: dict[str, str] = {}
      for line in example.read_text(encoding="utf-8").splitlines():
          stripped = line.strip()
          if stripped.startswith("#") or "=" not in stripped:
              continue
          key, _, value = stripped.partition("=")
          pairs[key.strip()] = value.strip()
      for key in REQUIRED_ENV_KEYS:
          if key not in pairs:
              findings.append(
                  Finding(
                      rule_id="C2",
                      severity=Severity.ERROR,
                      message=f".env.example missing key {key}",
                      locator=".env.example",
                  )
              )
      for key in MUST_BE_EMPTY:
          if pairs.get(key):
              findings.append(
                  Finding(
                      rule_id="C2",
                      severity=Severity.ERROR,
                      message=f".env.example {key} must be empty (no committed value)",
                      locator=".env.example",
                  )
              )
      return findings


  def _scan_contents(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      for path in ctx.tracked_files:
          if _scan_excluded(path):
              continue
          full = ctx.repo_root / path
          try:
              text = full.read_text(encoding="utf-8")
          except (OSError, UnicodeDecodeError):
              continue
          for lineno, line in enumerate(text.splitlines(), start=1):
              if CONN_URI_RE.search(line) or DO_ENDPOINT_RE.search(line):
                  findings.append(
                      Finding(
                          rule_id="C2",
                          severity=Severity.ERROR,
                          message="possible committed connection string / secret",
                          locator=f"{path}:{lineno}",
                      )
                  )
      return findings


  @register("C2", "no committed secrets")
  def rule_c2_no_committed_secrets(ctx: RuleContext) -> Iterable[Finding]:
      return [
          *_check_env_file(ctx),
          *_check_env_example(ctx),
          *_scan_contents(ctx),
      ]
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: all six C2 tests PASSED — `test_c2_clean_repo_passes`, `test_c2_flags_real_endpoint_in_scanned_file`, `test_c2_ignores_angle_bracket_placeholder_in_scanned_file`, `test_c2_skips_docs_and_example_files`, `test_c2_flags_tracked_env`, `test_c2_flags_env_example_with_filled_secret` (20 passed total — includes the extra P2 commit-message test).

- [ ] **Step 5: Run full quality gate for the group.**
  Command: `ruff check src/retail/rules/git_meta.py src/retail/gitutil.py tests/unit/test_git_meta.py tests/unit/_gitfix.py && black --check src/retail tests && pytest -m unit tests/unit/test_git_meta.py -v`
  Expected: ruff `All checks passed!`, black `would reformat 0 files` / `4 files would be left unchanged`, pytest `20 passed`.

- [ ] **Step 6: Commit.**
  Command: `git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add C2 no-committed-secrets rule with placeholder-safe endpoint scan"`


---

### Task M2.G3: G3 — UTF-8 without BOM

**Milestone:** M2 (git-hygiene). G3 lives in the existing `git_meta.py` group alongside G1/G2; the module and its `__init__.py` import are already in place from those tasks. This task **adds** one rule function plus a private byte-reading helper — it does not re-scaffold the module or re-register the group. Note: G3 reads raw **file bytes** (`open("rb")`), not git plumbing.

**Files:**

- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py` — add `_read_leading_bytes` helper and `g3_no_bom` rule.
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py` — add the G3 test cases (file already exists from G1/G2).

> Do **not** create `src/retail/core.py`, `src/retail/registry.py`, or `src/retail/rules/__init__.py` — they exist from M1 + earlier M2 tasks. Do **not** redefine `Finding`, `Severity`, `RuleContext`, or `register` — import them (contract v2).

**Interfaces:**

- Consumes (contract v2, import-only — exact signatures):
  - `from retail.core import Finding, Severity, RuleContext` — `Finding(rule_id: str, severity: Severity, message: str, locator: str)`; `RuleContext(repo_root: Path, tracked_files: tuple[str, ...], commit_range: str | None = None, commit_message: str | None = None)`; `Severity.ERROR`.
  - `from retail.registry import register` — `register(rule_id: str, title: str) -> Callable[[Rule], Rule]`.
- Produces:
  - `_read_leading_bytes(path: Path, count: int = 3) -> bytes` — module-private byte helper (opens `"rb"`, returns up to `count` bytes; **never** decodes — a text decode with `utf-8-sig` would swallow the very BOM this rule detects).
  - `g3_no_bom(ctx: RuleContext) -> Iterable[Finding]` — registered via `@register("G3", "UTF-8 without BOM")`; yields one `Finding(rule_id="G3", severity=Severity.ERROR, ...)` per committed `*.tmdl`/`*.pbir`/`*.json`/`*.pbism` file whose first 3 bytes are `EF BB BF`. `locator` is the **repo-relative POSIX path string taken from `ctx.tracked_files`** (spec §11 "most specific available" = a path), not the absolute joined path. The rule joins `ctx.repo_root / relpath` only to read bytes.

**Steps:**

- [ ] **Step 1: Write the failing test (RED).** Append the following to `tests/unit/test_git_meta.py`. It imports `g3_no_bom` directly (registry-independent unit test), builds real fixtures via `tmp_path`, and asserts behavior. The `.sql`-with-BOM fixture makes the extension filter load-bearing (a "flag any BOM file" bug would wrongly flag it).

  ```python
  from pathlib import Path

  import pytest

  from retail.core import RuleContext, Severity
  from retail.rules.git_meta import _read_leading_bytes, g3_no_bom

  BOM = b"\xef\xbb\xbf"


  def _write(path: Path, prefix: bytes, text: str) -> None:
      path.write_bytes(prefix + text.encode("utf-8"))


  @pytest.mark.unit
  def test_read_leading_bytes_returns_first_three_bytes(tmp_path: Path) -> None:
      f = tmp_path / "x.tmdl"
      f.write_bytes(BOM + b"table Sales")
      assert _read_leading_bytes(f) == BOM


  @pytest.mark.unit
  def test_read_leading_bytes_short_file_returns_fewer(tmp_path: Path) -> None:
      f = tmp_path / "x.tmdl"
      f.write_bytes(b"ab")
      assert _read_leading_bytes(f) == b"ab"


  @pytest.mark.unit
  def test_g3_flags_tmdl_with_bom(tmp_path: Path) -> None:
      _write(tmp_path / "withbom.tmdl", BOM, "table Sales")
      ctx = RuleContext(repo_root=tmp_path, tracked_files=("withbom.tmdl",))
      findings = list(g3_no_bom(ctx))
      assert len(findings) == 1
      f = findings[0]
      assert f.rule_id == "G3"
      assert f.severity is Severity.ERROR
      assert f.locator == "withbom.tmdl"


  @pytest.mark.unit
  def test_g3_passes_tmdl_without_bom(tmp_path: Path) -> None:
      _write(tmp_path / "clean.tmdl", b"", "table Sales")
      ctx = RuleContext(repo_root=tmp_path, tracked_files=("clean.tmdl",))
      assert list(g3_no_bom(ctx)) == []


  @pytest.mark.unit
  def test_g3_ignores_non_target_extension_with_bom(tmp_path: Path) -> None:
      # A .sql file WITH a BOM must NOT be flagged: G3 only covers
      # *.tmdl/*.pbir/*.json/*.pbism. This keeps the extension filter load-bearing.
      _write(tmp_path / "ddl.sql", BOM, "select 1")
      ctx = RuleContext(repo_root=tmp_path, tracked_files=("ddl.sql",))
      assert list(g3_no_bom(ctx)) == []
  ```

- [ ] **Step 2: Run to fail.** Exact command:

  ```
  pytest tests/unit/test_git_meta.py -q
  ```

  Expected: collection/run fails with `ImportError: cannot import name 'g3_no_bom' from 'retail.rules.git_meta'` (and `_read_leading_bytes` likewise) — the new symbols do not exist yet, so the five new tests error at import.

- [ ] **Step 3: Write minimal implementation (GREEN).** Add to `src/retail/rules/git_meta.py`. Reuse the existing module imports if `Finding`/`Severity`/`RuleContext`/`register`/`Path`/`Iterable` are already imported by G1/G2; otherwise add only the missing ones. Do not duplicate existing import lines.

  ```python
  # --- add near the other imports if not already present ---
  from collections.abc import Iterable
  from pathlib import Path

  from retail.core import Finding, RuleContext, Severity
  from retail.registry import register

  # --- G3 implementation ---
  _UTF8_BOM = b"\xef\xbb\xbf"
  _G3_SUFFIXES = (".tmdl", ".pbir", ".json", ".pbism")


  def _read_leading_bytes(path: Path, count: int = 3) -> bytes:
      """Return up to ``count`` leading bytes of ``path``.

      Reads in binary mode on purpose: a text open with ``encoding="utf-8-sig"``
      would strip the BOM that G3 exists to detect. A file shorter than ``count``
      simply yields fewer bytes (no error, comparison is False).
      """
      with path.open("rb") as fh:
          return fh.read(count)


  @register("G3", "UTF-8 without BOM")
  def g3_no_bom(ctx: RuleContext) -> Iterable[Finding]:
      """Flag any committed TMDL/PBIR/JSON/PBISM file beginning with a UTF-8 BOM."""
      for rel in ctx.tracked_files:
          if not rel.lower().endswith(_G3_SUFFIXES):
              continue
          if _read_leading_bytes(ctx.repo_root / rel) == _UTF8_BOM:
              yield Finding(
                  rule_id="G3",
                  severity=Severity.ERROR,
                  message=f"File starts with a UTF-8 BOM; save as UTF-8 without BOM: {rel}",
                  locator=rel,
              )
  ```

- [ ] **Step 4: Run to pass (GREEN).** Exact command:

  ```
  pytest tests/unit/test_git_meta.py -q
  ```

  Expected: all G1/G2/G3 tests PASS, including the five new ones (`test_read_leading_bytes_returns_first_three_bytes`, `test_read_leading_bytes_short_file_returns_fewer`, `test_g3_flags_tmdl_with_bom`, `test_g3_passes_tmdl_without_bom`, `test_g3_ignores_non_target_extension_with_bom`). Output ends with e.g. `N passed` and exit code 0.

- [ ] **Step 5: Lint + format.** Exact commands (must pass clean before commit):

  ```
  ruff check src/retail/rules/git_meta.py tests/unit/test_git_meta.py
  black --check src/retail/rules/git_meta.py tests/unit/test_git_meta.py
  ```

  Expected: `All checks passed!` from ruff and `2 files would be left unchanged.` from black. If black reports reformatting, run `black src/retail/rules/git_meta.py tests/unit/test_git_meta.py` and re-run Step 4.

- [ ] **Step 6: Commit.** Exact command (conventional message, type ∈ {feat,fix,refactor,docs,chore}):

  ```
  git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py && git commit -m "feat: add G3 UTF-8 no-BOM rule"
  ```

  Expected: one commit recorded touching exactly those two files.

---

### Task M2.G4: G4 — `.gitattributes` EOL policy (MUST-CONTAIN subset)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py` (append rule `check_gitattributes_eol`; group module already exists and is already imported by `src/retail/rules/__init__.py` from the G1–G3 tasks, so the `@register` decorator fires without any `__init__.py` change)
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py` (append G4 tests; file already exists from prior G-rule tasks)

**Interfaces:**
- Consumes (from `src/retail/core.py`, contract v2 — verbatim):
  - `Severity` (`str`, `Enum`): `ERROR` / `WARNING` / `INFO`.
  - `@dataclass(frozen=True) Finding(rule_id: str, severity: Severity, message: str, locator: str)`.
  - `@dataclass(frozen=True) RuleContext(repo_root: Path, tracked_files: tuple[str, ...], commit_range: str | None = None, commit_message: str | None = None)`.
  - `Rule = Callable[[RuleContext], Iterable[Finding]]`.
- Consumes (from `src/retail/registry.py`): `register(rule_id: str, title: str)` decorator.
- Consumes (assumption): `src/retail/rules/git_meta.py` exists with `from __future__ import annotations`, and `src/retail/rules/__init__.py` already contains `from . import git_meta` (added by the G1/G2/G3 tasks earlier in M2). This task is purely additive — it appends one function; it does **not** create the module or edit `__init__.py`.
- Produces (later tasks / the registry rely on this exact name):
  - `check_gitattributes_eol(ctx: RuleContext) -> Iterable[Finding]` — registered as rule id `"G4"`, title `".gitattributes EOL policy"`, severity `Severity.ERROR`.

**Behavior contract (subset semantics):** Parse `<repo_root>/.gitattributes`. For each REQUIRED glob, the line whose **first whitespace-delimited token equals that glob exactly** must carry the required attribute token:

| Required glob | Required attribute token |
|---|---|
| `*.tmdl` `*.pbir` `*.pbism` `*.json` | `eol=crlf` |
| `*.sql` `*.md` `*.py` | `eol=lf` |
| `*.pbix` `*.abf` `*.png` | `binary` |

Matching is by **exact first-token equality**, never glob expansion (so the catch-all `*` line and benign extras like `*.svg text eol=lf`, `*.toml`, `*.yml` are ignored, not flagged — subset, not exact). A REQUIRED glob that is **absent** OR present but **missing/contradicting** its required token yields one `Finding` (`severity=Severity.ERROR`). Locator is most-specific-available: `.gitattributes:<line>` when the glob's line exists but lacks the token; `.gitattributes` (no line) when the glob is absent or the file does not exist. No `exists()` early-return guard — a missing/empty `.gitattributes` means every required glob is absent and produces 11 findings (no silent pass). The spec's `git ls-files --eol` cross-check is **out of scope** for this rule (subset check against the declared attributes file only).

---

- [ ] **Step 1: Write the failing tests**

Append to `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_git_meta.py`:

```python
import pytest

from retail.core import RuleContext, Severity
from retail.rules.git_meta import check_gitattributes_eol


def _ctx(tmp_path):
    return RuleContext(repo_root=tmp_path, tracked_files=(".gitattributes",))


_PASSING_GITATTRIBUTES = """\
# Normalize line endings; Power BI Desktop writes CRLF for PBIP text files.
* text=auto

*.tmdl   text eol=crlf
*.pbir   text eol=crlf
*.pbism  text eol=crlf
*.json   text eol=crlf
*.sql    text eol=lf
*.md     text eol=lf
*.py     text eol=lf

*.pbix   binary
*.abf    binary
*.png    binary
*.svg    text eol=lf
*.toml   text eol=lf
*.yml    text eol=lf
"""


@pytest.mark.unit
def test_g4_passes_when_all_required_mappings_present(tmp_path):
    (tmp_path / ".gitattributes").write_text(_PASSING_GITATTRIBUTES, encoding="utf-8")
    findings = list(check_gitattributes_eol(_ctx(tmp_path)))
    assert findings == []


@pytest.mark.unit
def test_g4_flags_missing_tmdl_crlf(tmp_path):
    # Drop the *.tmdl line entirely -> required glob absent.
    content = _PASSING_GITATTRIBUTES.replace("*.tmdl   text eol=crlf\n", "")
    (tmp_path / ".gitattributes").write_text(content, encoding="utf-8")
    findings = list(check_gitattributes_eol(_ctx(tmp_path)))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "G4"
    assert f.severity is Severity.ERROR
    assert "*.tmdl" in f.message
    assert "eol=crlf" in f.message
    # Glob absent -> locator is the bare file, no line number.
    assert f.locator == ".gitattributes"


@pytest.mark.unit
def test_g4_flags_contradicting_token_with_line_locator(tmp_path):
    # *.sql present but declared eol=crlf instead of required eol=lf.
    content = _PASSING_GITATTRIBUTES.replace(
        "*.sql    text eol=lf", "*.sql    text eol=crlf"
    )
    (tmp_path / ".gitattributes").write_text(content, encoding="utf-8")
    findings = list(check_gitattributes_eol(_ctx(tmp_path)))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "G4"
    assert f.severity is Severity.ERROR
    assert "*.sql" in f.message
    # Line exists -> most-specific locator carries the line number.
    assert f.locator.startswith(".gitattributes:")


@pytest.mark.unit
def test_g4_flags_all_when_file_absent(tmp_path):
    # No .gitattributes at all -> every required glob missing, no silent pass.
    findings = list(check_gitattributes_eol(_ctx(tmp_path)))
    assert len(findings) == 11
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(f.locator == ".gitattributes" for f in findings)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd C:\Users\user\Documents\GitHub\Retail_Tower_analytics
python -m pytest tests/unit/test_git_meta.py -k g4 -v
```
Expected: FAIL during collection — `ImportError: cannot import name 'check_gitattributes_eol' from 'retail.rules.git_meta'` (the function does not exist yet).

- [ ] **Step 3: Write the minimal implementation**

Append to `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\git_meta.py` (the module already has `from __future__ import annotations` and imports `Finding`, `RuleContext`, `Severity`, `Iterable`, and `register` from the G1–G3 tasks; add any of these imports only if absent):

```python
from typing import Iterable  # noqa: F811 — present already if added by G1–G3

from ..core import Finding, RuleContext, Severity  # noqa: F811
from ..registry import register  # noqa: F811

# Required (glob -> required attribute token). Exact first-token match, subset semantics.
_G4_REQUIRED: tuple[tuple[str, str], ...] = (
    ("*.tmdl", "eol=crlf"),
    ("*.pbir", "eol=crlf"),
    ("*.pbism", "eol=crlf"),
    ("*.json", "eol=crlf"),
    ("*.sql", "eol=lf"),
    ("*.md", "eol=lf"),
    ("*.py", "eol=lf"),
    ("*.pbix", "binary"),
    ("*.abf", "binary"),
    ("*.png", "binary"),
)


@register("G4", ".gitattributes EOL policy")
def check_gitattributes_eol(ctx: RuleContext) -> Iterable[Finding]:
    """G4: each REQUIRED glob in .gitattributes must carry its eol/binary token.

    Subset (MUST-CONTAIN) check: extra benign entries are permitted. Matching is
    by exact first-token equality, never glob expansion, so the `* text=auto`
    catch-all does not satisfy any required glob.
    """
    path = ctx.repo_root / ".gitattributes"
    # Index: glob token -> (1-based line number, set of remaining tokens on that line).
    declared: dict[str, tuple[int, set[str]]] = {}
    if path.exists():
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            glob = tokens[0]
            declared[glob] = (lineno, set(tokens[1:]))

    findings: list[Finding] = []
    for glob, required_token in _G4_REQUIRED:
        entry = declared.get(glob)
        if entry is None:
            findings.append(
                Finding(
                    rule_id="G4",
                    severity=Severity.ERROR,
                    message=f"{glob} missing required attribute {required_token} in .gitattributes",
                    locator=".gitattributes",
                )
            )
            continue
        lineno, attr_tokens = entry
        if required_token not in attr_tokens:
            findings.append(
                Finding(
                    rule_id="G4",
                    severity=Severity.ERROR,
                    message=f"{glob} must declare {required_token} in .gitattributes",
                    locator=f".gitattributes:{lineno}",
                )
            )
    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd C:\Users\user\Documents\GitHub\Retail_Tower_analytics
python -m pytest tests/unit/test_git_meta.py -k g4 -v
```
Expected: PASS — `test_g4_passes_when_all_required_mappings_present`, `test_g4_flags_missing_tmdl_crlf`, `test_g4_flags_contradicting_token_with_line_locator`, `test_g4_flags_all_when_file_absent` all green (4 passed).

- [ ] **Step 5: Lint and format**

Run:
```bash
cd C:\Users\user\Documents\GitHub\Retail_Tower_analytics
ruff check src/retail/rules/git_meta.py tests/unit/test_git_meta.py
black --check src/retail/rules/git_meta.py tests/unit/test_git_meta.py
```
Expected: ruff reports `All checks passed!`; black reports the files are already formatted (`2 files would be left unchanged`). If black reports it would reformat, run `black src/retail/rules/git_meta.py tests/unit/test_git_meta.py` and re-run the tests from Step 4.

- [ ] **Step 6: Commit**

```bash
cd C:\Users\user\Documents\GitHub\Retail_Tower_analytics
git add src/retail/rules/git_meta.py tests/unit/test_git_meta.py
git commit -m "feat: add G4 .gitattributes EOL policy subset rule"
```

---

## Milestone 3 — SQL Rules

### Task M3.1: SQL lexer + file iterator (`src/retail/sql.py`)

The shared substrate every SQL rule consumes. A line-tracking tokenizer that strips comments and string literals (so `S2`/`S3`/`S4b` never match inside a comment or a quoted string), a `.sql` file iterator scoped to `warehouse/**`, and the **schema-position matcher** that `S2` uses now and `D8` (M4) reuses verbatim.

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\sql.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_sql_lexer.py` (lexer/helpers; rule tests live in `tests/unit/test_sql.py`, Task M3.2+)

**Interfaces:**
- Consumes: `RuleContext` (from `src/retail/core.py` — `repo_root: Path`, `tracked_files: tuple[str, ...]`).
- Produces:
  - `@dataclass(frozen=True) class SqlToken: text: str; line: int` — one significant token with its 1-based source line.
  - `def tokenize_sql(text: str) -> list[SqlToken]` — strips `--` line comments and `/* */` block comments and the *contents* of `'...'`/`"..."` literals (the literal collapses to an empty `SqlToken` placeholder so positions are preserved but no inner word leaks); identifiers, schema-qualified names split on `.`, punctuation, and keywords each become a token carrying their line.
  - `def iter_sql_files(ctx: RuleContext) -> list[str]` — repo-relative POSIX paths from `ctx.tracked_files` matching `warehouse/**/*.sql` (used by every rule; rules then read `ctx.repo_root / path`).
  - `def stale_schema_tokens(text: str) -> list[tuple[str, int]]` — `(schema_token, line)` for any `raw|marts|bronze|silver` appearing **only** in a schema-qualifying position: after `CREATE SCHEMA`, as the schema half of `schema.object`, or after `FROM`/`JOIN`. Never matches the substring inside `raw_amount`. Reused by D8.

- [ ] **Step 1: Write failing test for the lexer + schema matcher.**
  Create `tests/unit/test_sql_lexer.py`:
  ```python
  import pytest

  from retail.sql import SqlToken, stale_schema_tokens, tokenize_sql

  pytestmark = pytest.mark.unit


  def test_tokenize_tracks_line_numbers() -> None:
      toks = tokenize_sql("CREATE SCHEMA gold;\nSELECT 1;")
      texts = [(t.text, t.line) for t in toks if t.text]
      assert ("CREATE", 1) in texts
      assert ("gold", 1) in texts
      assert ("SELECT", 2) in texts


  def test_tokenize_strips_line_comment() -> None:
      toks = tokenize_sql("SELECT 1; -- CREATE SCHEMA raw\n")
      assert all(t.text != "raw" for t in toks)


  def test_tokenize_strips_string_literal_contents() -> None:
      toks = tokenize_sql("SELECT 'CREATE SCHEMA raw' AS note;")
      assert all(t.text != "raw" for t in toks)


  def test_stale_schema_passes_snake_case_column() -> None:
      # "raw_amount" is a single identifier; \braw\b does NOT match it.
      assert stale_schema_tokens("SELECT raw_amount FROM gold.sales;") == []


  def test_stale_schema_flags_create_schema_raw() -> None:
      hits = stale_schema_tokens("CREATE SCHEMA raw;")
      assert hits == [("raw", 1)]


  def test_stale_schema_flags_qualifier_and_from() -> None:
      hits = stale_schema_tokens("SELECT * FROM marts.orders;")
      assert ("marts", 1) in hits
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_sql_lexer.py -v`
  Expected: collection/import error — `ModuleNotFoundError: No module named 'retail.sql'` (the module does not exist yet).

- [ ] **Step 3: Implement the lexer + helpers.**
  Create `src/retail/sql.py`:
  ```python
  from __future__ import annotations

  import re
  from dataclasses import dataclass

  from .core import RuleContext

  _SCHEMA_TOKENS = ("raw", "marts", "bronze", "silver")


  @dataclass(frozen=True)
  class SqlToken:
      text: str
      line: int


  def tokenize_sql(text: str) -> list[SqlToken]:
      """Tokenize SQL, dropping comments and string-literal contents.

      Each token keeps its 1-based source line so rules can emit path:line.
      String literals collapse to an empty-text placeholder token so no inner
      word leaks into rule matching while position is preserved.
      """
      tokens: list[SqlToken] = []
      i, line, n = 0, 1, len(text)
      word = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[().,;*]")
      while i < n:
          ch = text[i]
          if ch == "\n":
              line += 1
              i += 1
              continue
          if ch.isspace():
              i += 1
              continue
          if text.startswith("--", i):
              j = text.find("\n", i)
              i = n if j == -1 else j
              continue
          if text.startswith("/*", i):
              j = text.find("*/", i)
              line += text.count("\n", i, n if j == -1 else j)
              i = n if j == -1 else j + 2
              continue
          if ch in ("'", '"'):
              j = text.find(ch, i + 1)
              end = n if j == -1 else j
              line += text.count("\n", i, end)
              tokens.append(SqlToken("", line))
              i = n if j == -1 else j + 1
              continue
          m = word.match(text, i)
          if m:
              tokens.append(SqlToken(m.group(0), line))
              i = m.end()
              continue
          i += 1
      return tokens


  def iter_sql_files(ctx: RuleContext) -> list[str]:
      """Repo-relative POSIX paths of tracked warehouse SQL files."""
      return sorted(
          p
          for p in ctx.tracked_files
          if p.startswith("warehouse/") and p.endswith(".sql")
      )


  def stale_schema_tokens(text: str) -> list[tuple[str, int]]:
      """Find raw/marts/bronze/silver in schema-qualifying positions only."""
      toks = [t for t in tokenize_sql(text) if t.text]
      hits: list[tuple[str, int]] = []
      for idx, tok in enumerate(toks):
          low = tok.text.lower()
          if low not in _SCHEMA_TOKENS:
              continue
          prev = toks[idx - 1].text.upper() if idx else ""
          prev2 = toks[idx - 2].text.upper() if idx >= 2 else ""
          nxt = toks[idx + 1].text if idx + 1 < len(toks) else ""
          after_create_schema = prev == "SCHEMA" and prev2 == "CREATE"
          after_from_join = prev in ("FROM", "JOIN")
          schema_qualifier = nxt == "."
          if after_create_schema or after_from_join or schema_qualifier:
              hits.append((low, tok.line))
      return hits
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_sql_lexer.py -v`
  Expected: `6 passed`.

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/sql.py tests/unit/test_sql_lexer.py && git commit -m "feat: add SQL lexer and schema-position matcher for retail check"`

---

### Task M3.2: S1 snake_case + S2 medallion schema rules (`src/retail/rules/sql.py`)

S1 flags declaration-position identifiers that are not `snake_case` (quoted/bracketed identifiers with uppercase or spaces). S2 reuses `stale_schema_tokens` to flag stale `raw`/`marts` schema tokens, exempting `warehouse/README.md` (which is `.md`, already outside the glob — the exemption is an explicit belt-and-braces guard).

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\sql.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_sql.py`
- Test fixtures: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\pass_s1_s2.sql`, `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\fail_s1_quoted_caps.sql`, `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\fail_s2_create_schema_raw.sql`

**Interfaces:**
- Consumes: `RuleContext`; `iter_sql_files`, `tokenize_sql`, `stale_schema_tokens` (from `retail.sql`); `Finding`, `Severity` (from `retail.core`); `register` (from `retail.registry`).
- Produces:
  - `@register("S1", "snake_case SQL identifiers") def s1_snake_case_identifiers(ctx: RuleContext) -> list[Finding]`
  - `@register("S2", "medallion schema names") def s2_medallion_schemas(ctx: RuleContext) -> list[Finding]`
- Test-harness convention (used by every rule test in this milestone): build `RuleContext` explicitly against a fixture dir; never shell to git in a unit test.
  ```python
  ctx = RuleContext(repo_root=FIXTURES, tracked_files=("warehouse/schema/x.sql",))
  ```

- [ ] **Step 1: Create the fixtures.**
  `tests/fixtures/sql/pass_s1_s2.sql`:
  ```sql
  CREATE SCHEMA gold;
  CREATE TABLE gold.fct_sales (
      sale_id BIGINT,
      raw_amount NUMERIC
  );
  SELECT raw_amount FROM gold.fct_sales;
  ```
  `tests/fixtures/sql/fail_s1_quoted_caps.sql`:
  ```sql
  CREATE TABLE gold."Sale Items" (
      "Item Id" BIGINT
  );
  ```
  `tests/fixtures/sql/fail_s2_create_schema_raw.sql`:
  ```sql
  CREATE SCHEMA raw;
  SELECT * FROM marts.orders;
  ```

- [ ] **Step 2: Write failing tests.**
  Create `tests/unit/test_sql.py`:
  ```python
  from pathlib import Path

  import pytest

  from retail.core import RuleContext, Severity
  from retail.rules.sql import s1_snake_case_identifiers, s2_medallion_schemas

  pytestmark = pytest.mark.unit

  FIXTURES = Path(__file__).parent.parent / "fixtures" / "sql"


  def _ctx(*rel: str) -> RuleContext:
      return RuleContext(repo_root=FIXTURES, tracked_files=tuple(rel))


  def test_s1_passes_snake_case() -> None:
      ctx = _ctx("warehouse/pass_s1_s2.sql")
      # fixture lives flat; map the warehouse-relative name to the file
      (FIXTURES / "warehouse").mkdir(exist_ok=True)
      (FIXTURES / "warehouse" / "pass_s1_s2.sql").write_text(
          (FIXTURES / "pass_s1_s2.sql").read_text(encoding="utf-8"),
          encoding="utf-8",
      )
      assert list(s1_snake_case_identifiers(ctx)) == []


  def test_s1_flags_quoted_caps() -> None:
      (FIXTURES / "warehouse").mkdir(exist_ok=True)
      (FIXTURES / "warehouse" / "fail_s1_quoted_caps.sql").write_text(
          (FIXTURES / "fail_s1_quoted_caps.sql").read_text(encoding="utf-8"),
          encoding="utf-8",
      )
      ctx = _ctx("warehouse/fail_s1_quoted_caps.sql")
      findings = list(s1_snake_case_identifiers(ctx))
      assert findings
      assert all(f.rule_id == "S1" for f in findings)
      assert all(f.severity is Severity.ERROR for f in findings)


  def test_s2_passes_raw_amount_column() -> None:
      ctx = _ctx("warehouse/pass_s1_s2.sql")
      assert list(s2_medallion_schemas(ctx)) == []


  def test_s2_flags_create_schema_raw() -> None:
      (FIXTURES / "warehouse").mkdir(exist_ok=True)
      (FIXTURES / "warehouse" / "fail_s2_create_schema_raw.sql").write_text(
          (FIXTURES / "fail_s2_create_schema_raw.sql").read_text(encoding="utf-8"),
          encoding="utf-8",
      )
      ctx = _ctx("warehouse/fail_s2_create_schema_raw.sql")
      findings = list(s2_medallion_schemas(ctx))
      assert len(findings) >= 1
      assert any("raw" in f.message for f in findings)
      assert all(f.rule_id == "S2" for f in findings)
      assert all(f.severity is Severity.ERROR for f in findings)


  def test_s2_exempts_warehouse_readme() -> None:
      ctx = _ctx("warehouse/README.md")  # not a .sql -> never scanned
      assert list(s2_medallion_schemas(ctx)) == []
  ```

- [ ] **Step 3: Run to fail.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `ModuleNotFoundError: No module named 'retail.rules.sql'`.

- [ ] **Step 4: Implement S1 + S2.**
  Create `src/retail/rules/sql.py`:
  ```python
  from __future__ import annotations

  import re

  from ..core import Finding, RuleContext, Severity
  from ..registry import register
  from ..sql import iter_sql_files, stale_schema_tokens, tokenize_sql

  _SNAKE = re.compile(r"^[a-z_][a-z0-9_]*$")
  # quoted/bracketed identifier in a declaration position
  _QUOTED = re.compile(r'"([^"]*)"|\[([^\]]*)\]')
  EXEMPT_S2 = frozenset({"warehouse/README.md"})


  def _read(ctx: RuleContext, rel: str) -> str:
      return (ctx.repo_root / rel).read_text(encoding="utf-8")


  @register("S1", "snake_case SQL identifiers")
  def s1_snake_case_identifiers(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      for rel in iter_sql_files(ctx):
          text = _read(ctx, rel)
          for lineno, line in enumerate(text.splitlines(), start=1):
              for m in _QUOTED.finditer(line):
                  ident = m.group(1) if m.group(1) is not None else m.group(2)
                  if not _SNAKE.match(ident):
                      findings.append(
                          Finding(
                              rule_id="S1",
                              severity=Severity.ERROR,
                              message=f"non-snake_case identifier {ident!r}",
                              locator=f"{rel}:{lineno}",
                          )
                      )
      return findings


  @register("S2", "medallion schema names")
  def s2_medallion_schemas(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      for rel in iter_sql_files(ctx):
          if rel in EXEMPT_S2:
              continue
          text = _read(ctx, rel)
          for token, line in stale_schema_tokens(text):
              if token in ("raw", "marts"):
                  findings.append(
                      Finding(
                          rule_id="S2",
                          severity=Severity.ERROR,
                          message=f"stale schema {token!r}; use bronze/silver/gold",
                          locator=f"{rel}:{line}",
                      )
                  )
      return findings
  ```
  (S2 flags only the legacy `raw`/`marts`; `bronze`/`silver` are valid schemas — `stale_schema_tokens` surfaces all four so D8 can also flag non-`gold`, but S2 narrows to the two stale ones per spec §5.1.)

- [ ] **Step 5: Run to pass.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `5 passed`.

- [ ] **Step 6: Commit.**
  Command: `git add src/retail/rules/sql.py tests/unit/test_sql.py tests/fixtures/sql && git commit -m "feat: add S1 snake_case and S2 medallion-schema SQL rules"`

---

### Task M3.3: S3 vw_ view-prefix rule

`CREATE VIEW` (and `CREATE OR REPLACE VIEW`) names must carry the `vw_` prefix; the schema qualifier is stripped before the check, so `CREATE VIEW gold.sales` flags `sales` and `gold.vw_sales` passes.

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\sql.py`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_sql.py`
- Test fixtures: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\pass_s3_vw.sql`, `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\fail_s3_no_prefix.sql`

**Interfaces:**
- Consumes: `tokenize_sql`, `iter_sql_files` (from `retail.sql`); `RuleContext`, `Finding`, `Severity`; `register`.
- Produces: `@register("S3", "vw_ prefix on views") def s3_vw_prefix(ctx: RuleContext) -> list[Finding]`.

- [ ] **Step 1: Create the fixtures.**
  `tests/fixtures/sql/pass_s3_vw.sql`:
  ```sql
  CREATE VIEW gold.vw_daily_sales AS SELECT 1;
  CREATE OR REPLACE VIEW gold.vw_returns AS SELECT 2;
  ```
  `tests/fixtures/sql/fail_s3_no_prefix.sql`:
  ```sql
  CREATE VIEW gold.daily_sales AS SELECT 1;
  ```
  Mirror both into the `warehouse/`-prefixed location the harness reads, in the test (Step 2).

- [ ] **Step 2: Write failing tests.** Append to `tests/unit/test_sql.py`:
  ```python
  from retail.rules.sql import s3_vw_prefix


  def _stage(name: str) -> str:
      (FIXTURES / "warehouse").mkdir(exist_ok=True)
      (FIXTURES / "warehouse" / name).write_text(
          (FIXTURES / name).read_text(encoding="utf-8"), encoding="utf-8"
      )
      return f"warehouse/{name}"


  def test_s3_passes_prefixed_views() -> None:
      ctx = _ctx(_stage("pass_s3_vw.sql"))
      assert list(s3_vw_prefix(ctx)) == []


  def test_s3_flags_unprefixed_view() -> None:
      ctx = _ctx(_stage("fail_s3_no_prefix.sql"))
      findings = list(s3_vw_prefix(ctx))
      assert len(findings) == 1
      assert findings[0].rule_id == "S3"
      assert findings[0].severity is Severity.ERROR
      assert findings[0].locator == "warehouse/fail_s3_no_prefix.sql:1"
  ```

- [ ] **Step 3: Run to fail.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `ImportError: cannot import name 's3_vw_prefix' from 'retail.rules.sql'`.

- [ ] **Step 4: Implement S3.** Append to `src/retail/rules/sql.py`:
  ```python
  @register("S3", "vw_ prefix on views")
  def s3_vw_prefix(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      for rel in iter_sql_files(ctx):
          toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
          for idx, tok in enumerate(toks):
              if tok.text.upper() != "VIEW":
                  continue
              # the view name is the next identifier; skip a schema qualifier
              nxt = toks[idx + 1] if idx + 1 < len(toks) else None
              if nxt is None:
                  continue
              # gold.vw_x -> name token is two ahead (skip "gold" and ".")
              if idx + 3 < len(toks) and toks[idx + 2].text == ".":
                  name_tok = toks[idx + 3]
              else:
                  name_tok = nxt
              if not name_tok.text.lower().startswith("vw_"):
                  findings.append(
                      Finding(
                          rule_id="S3",
                          severity=Severity.ERROR,
                          message=f"view {name_tok.text!r} missing vw_ prefix",
                          locator=f"{rel}:{name_tok.line}",
                      )
                  )
      return findings
  ```

- [ ] **Step 5: Run to pass.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `7 passed`.

- [ ] **Step 6: Commit.**
  Command: `git add src/retail/rules/sql.py tests/unit/test_sql.py tests/fixtures/sql && git commit -m "feat: add S3 vw_ view-prefix SQL rule"`

---

### Task M3.4: S4a migration filename + numbering rule

Migration filenames under `warehouse/migrations/` must match `^\d{4}_.+\.sql$`; the four-digit numbers must be unique and contiguous (no gaps, no duplicates). Operates on filenames only — fixtures are empty files. Locator is the migration path (no line — never invent one).

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\sql.py`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_sql.py`

**Interfaces:**
- Consumes: `iter_sql_files`; `RuleContext`, `Finding`, `Severity`; `register`.
- Produces: `@register("S4a", "migration filename + numbering") def s4a_migration_numbering(ctx: RuleContext) -> list[Finding]`.

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_sql.py`:
  ```python
  from retail.rules.sql import s4a_migration_numbering


  def test_s4a_passes_contiguous_unique() -> None:
      ctx = _ctx(
          "warehouse/migrations/0001_init.sql",
          "warehouse/migrations/0002_add_sales.sql",
      )
      assert list(s4a_migration_numbering(ctx)) == []


  def test_s4a_flags_bad_name() -> None:
      ctx = _ctx("warehouse/migrations/1_init.sql")
      findings = list(s4a_migration_numbering(ctx))
      assert any(f.rule_id == "S4a" for f in findings)
      assert all(f.severity is Severity.ERROR for f in findings)
      assert all(":" not in f.locator.rsplit(".sql", 1)[-1] for f in findings)


  def test_s4a_flags_gap() -> None:
      ctx = _ctx(
          "warehouse/migrations/0001_init.sql",
          "warehouse/migrations/0003_skip.sql",
      )
      findings = list(s4a_migration_numbering(ctx))
      assert any("gap" in f.message or "contiguous" in f.message for f in findings)


  def test_s4a_flags_duplicate() -> None:
      ctx = _ctx(
          "warehouse/migrations/0001_init.sql",
          "warehouse/migrations/0001_again.sql",
      )
      findings = list(s4a_migration_numbering(ctx))
      assert any("duplicate" in f.message for f in findings)
  ```

- [ ] **Step 2: Run to fail.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `ImportError: cannot import name 's4a_migration_numbering' from 'retail.rules.sql'`.

- [ ] **Step 3: Implement S4a.** Append to `src/retail/rules/sql.py` (add `from pathlib import PurePosixPath` to the imports at the top of the file):
  ```python
  _MIGRATION_NAME = re.compile(r"^\d{4}_.+\.sql$")


  @register("S4a", "migration filename + numbering")
  def s4a_migration_numbering(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      migrations = [
          rel
          for rel in iter_sql_files(ctx)
          if rel.startswith("warehouse/migrations/")
      ]
      numbers: dict[int, str] = {}
      for rel in migrations:
          name = PurePosixPath(rel).name
          if not _MIGRATION_NAME.match(name):
              findings.append(
                  Finding(
                      rule_id="S4a",
                      severity=Severity.ERROR,
                      message=f"migration filename {name!r} must match ^\\d{{4}}_.+\\.sql$",
                      locator=rel,
                  )
              )
              continue
          num = int(name[:4])
          if num in numbers:
              findings.append(
                  Finding(
                      rule_id="S4a",
                      severity=Severity.ERROR,
                      message=f"duplicate migration number {num:04d}",
                      locator=rel,
                  )
              )
          else:
              numbers[num] = rel
      if numbers:
          ordered = sorted(numbers)
          for prev, cur in zip(ordered, ordered[1:]):
              if cur != prev + 1:
                  findings.append(
                      Finding(
                          rule_id="S4a",
                          severity=Severity.ERROR,
                          message=(
                              f"non-contiguous migration numbering: gap between "
                              f"{prev:04d} and {cur:04d}"
                          ),
                          locator=numbers[cur],
                      )
                  )
      return findings
  ```

- [ ] **Step 4: Run to pass.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `11 passed`.

- [ ] **Step 5: Commit.**
  Command: `git add src/retail/rules/sql.py tests/unit/test_sql.py && git commit -m "feat: add S4a migration filename and numbering SQL rule"`

---

### Task M3.5: S4b migration guard-form rule (WARNING)

Bare `CREATE`/`ALTER` outside the accepted guarded forms (`CREATE TABLE … IF NOT EXISTS`, `CREATE OR REPLACE VIEW`, `ALTER TABLE … IF [NOT] EXISTS`, `DROP … IF EXISTS`) emit a `Severity.WARNING` (does NOT fail the build).

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\sql.py`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_sql.py`
- Test fixtures: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\pass_s4b_guarded.sql`, `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\sql\fail_s4b_bare.sql`

**Interfaces:**
- Consumes: `tokenize_sql`, `iter_sql_files`; `RuleContext`, `Finding`, `Severity`; `register`.
- Produces: `@register("S4b", "migration guard form") def s4b_guard_form(ctx: RuleContext) -> list[Finding]`.

- [ ] **Step 1: Create the fixtures.**
  `tests/fixtures/sql/pass_s4b_guarded.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS gold.fct_sales (sale_id BIGINT);
  CREATE OR REPLACE VIEW gold.vw_returns AS SELECT 1;
  ALTER TABLE IF EXISTS gold.fct_sales ADD COLUMN qty INT;
  DROP TABLE IF EXISTS gold.tmp_load;
  ```
  `tests/fixtures/sql/fail_s4b_bare.sql`:
  ```sql
  CREATE TABLE gold.fct_sales (sale_id BIGINT);
  ALTER TABLE gold.fct_sales ADD COLUMN qty INT;
  ```

- [ ] **Step 2: Write failing tests.** Append to `tests/unit/test_sql.py`:
  ```python
  from retail.rules.sql import s4b_guard_form


  def test_s4b_passes_guarded_forms() -> None:
      ctx = _ctx(_stage("pass_s4b_guarded.sql"))
      assert list(s4b_guard_form(ctx)) == []


  def test_s4b_warns_on_bare_create_and_alter() -> None:
      ctx = _ctx(_stage("fail_s4b_bare.sql"))
      findings = list(s4b_guard_form(ctx))
      assert len(findings) == 2
      assert all(f.rule_id == "S4b" for f in findings)
      assert all(f.severity is Severity.WARNING for f in findings)
      assert {f.locator for f in findings} == {
          "warehouse/fail_s4b_bare.sql:1",
          "warehouse/fail_s4b_bare.sql:2",
      }
  ```

- [ ] **Step 3: Run to fail.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `ImportError: cannot import name 's4b_guard_form' from 'retail.rules.sql'`.

- [ ] **Step 4: Implement S4b.** Append to `src/retail/rules/sql.py`:
  ```python
  def _is_guarded(toks: list, idx: int) -> bool:
      """True if the CREATE/ALTER/DROP at toks[idx] is an accepted guarded form."""
      verb = toks[idx].text.upper()
      # window of the next few keyword tokens, upper-cased
      tail = [t.text.upper() for t in toks[idx : idx + 8]]
      joined = " ".join(tail)
      if verb == "CREATE":
          return "OR REPLACE VIEW" in joined or "IF NOT EXISTS" in joined
      if verb == "ALTER":
          return "IF EXISTS" in joined or "IF NOT EXISTS" in joined
      if verb == "DROP":
          return "IF EXISTS" in joined
      return False


  @register("S4b", "migration guard form")
  def s4b_guard_form(ctx: RuleContext) -> list[Finding]:
      findings: list[Finding] = []
      for rel in iter_sql_files(ctx):
          toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
          for idx, tok in enumerate(toks):
              if tok.text.upper() not in ("CREATE", "ALTER"):
                  continue
              if _is_guarded(toks, idx):
                  continue
              findings.append(
                  Finding(
                      rule_id="S4b",
                      severity=Severity.WARNING,
                      message=(
                          f"bare {tok.text.upper()} is not an accepted guarded "
                          "form (use IF [NOT] EXISTS / OR REPLACE VIEW)"
                      ),
                      locator=f"{rel}:{tok.line}",
                  )
              )
      return findings
  ```

- [ ] **Step 5: Run to pass.**
  Command: `pytest -m unit tests/unit/test_sql.py -v`
  Expected: `13 passed`.

- [ ] **Step 6: Verify the whole SQL surface together and commit.**
  Command: `ruff check src tests && black --check src tests && pytest -m unit tests/unit/test_sql.py tests/unit/test_sql_lexer.py -v`
  Expected: ruff/black clean; `19 passed` (6 lexer + 13 rule tests).
  Command: `git add src/retail/rules/sql.py tests/unit/test_sql.py tests/fixtures/sql && git commit -m "feat: add S4b migration guard-form SQL warning rule"`


---

## Milestone 4 — TMDL + M Rules

### Task M4.1: Hand-rolled TMDL parser (`src/retail/tmdl.py`)

The indentation/block parser every D-rule consumes. It exposes BOTH the raw expression text (D4 must lex and strip comments/strings from un-normalized source) AND structured fields (name, displayFolder, dataType, summarizeBy — D1/D2/D5). D3 gets normalization via `normalize_measure_body`. D8 needs partition `source` M bodies; this parser captures them as raw text on the table.

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\tmdl.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_tmdl.py`

**Interfaces:**
- Consumes: nothing from the contract (pure stdlib). Reads `.tmdl` text via `Path.read_text(encoding="utf-8-sig")` (TMDL may carry a BOM; strip it like PBIR).
- Produces:
  - `@dataclass(frozen=True) TmdlMeasure(name: str, expression: str, display_folder: str | None, line: int)` — `expression` is the RAW body text (comments + strings intact) for D4; `line` is the 1-based line of the `measure` header.
  - `@dataclass(frozen=True) TmdlColumn(name: str, data_type: str | None, summarize_by: str | None, line: int)`
  - `@dataclass(frozen=True) TmdlRelationship(name: str, cross_filtering_behavior: str | None, line: int)`
  - `@dataclass(frozen=True) TmdlTable(name: str, measures: tuple[TmdlMeasure, ...], columns: tuple[TmdlColumn, ...], partition_sources: tuple[str, ...], annotations: tuple[str, ...], line: int)` — `partition_sources` are RAW M source bodies (D8); `annotations` are raw `annotation <name> = <value>` lines (D7 marker).
  - `@dataclass(frozen=True) TmdlModel(tables: tuple[TmdlTable, ...], relationships: tuple[TmdlRelationship, ...])`
  - `parse_tmdl(text: str) -> TmdlTable | None` — parse a single `table` `.tmdl` file's text; returns `None` if the file is not a table file (e.g. `relationships.tmdl`).
  - `parse_relationships(text: str) -> tuple[TmdlRelationship, ...]` — parse `relationships.tmdl`.
  - `iter_model_files(ctx: RuleContext, suffix: str) -> Iterable[tuple[str, str]]` — yields `(repo_relative_path, text)` for every tracked file under `*.SemanticModel/definition/**` whose POSIX path ends with `suffix` (e.g. `.tmdl`), reading from `ctx.repo_root`.
  - `normalize_measure_body(expression: str) -> str` — strip `//`/`/* */` comments, collapse runs of whitespace to one space, lowercase, trim; used by D3 hashing.

- [ ] **Step 1: Write failing test for object-header + indented-property parsing.**
  In `tests/unit/test_tmdl.py`:
```python
import pytest

from retail.tmdl import parse_tmdl


pytestmark = pytest.mark.unit

SALES_TMDL = """table Sales
\tmeasure Revenue = SUM(Sales[Amount])
\t\tdisplayFolder: KPIs

\tmeasure Margin = DIVIDE([Revenue], [Cost])
\t\tdisplayFolder: KPIs

\tcolumn Amount
\t\tdataType: decimal
\t\tsummarizeBy: sum

\tcolumn ProductKey
\t\tdataType: int64
\t\tsummarizeBy: none
"""


def test_parse_tmdl_reads_table_name_and_measures() -> None:
    table = parse_tmdl(SALES_TMDL)
    assert table is not None
    assert table.name == "Sales"
    names = [m.name for m in table.measures]
    assert names == ["Revenue", "Margin"]
    revenue = table.measures[0]
    assert revenue.expression == "SUM(Sales[Amount])"
    assert revenue.display_folder == "KPIs"
    assert revenue.line == 2


def test_parse_tmdl_reads_columns() -> None:
    table = parse_tmdl(SALES_TMDL)
    assert table is not None
    amount = next(c for c in table.columns if c.name == "Amount")
    assert amount.data_type == "decimal"
    assert amount.summarize_by == "sum"
    pk = next(c for c in table.columns if c.name == "ProductKey")
    assert pk.summarize_by == "none"
```
- [ ] **Step 2: Run to fail.** `pytest -m unit tests/unit/test_tmdl.py -v` → `ModuleNotFoundError: No module named 'retail.tmdl'`.
- [ ] **Step 3: Minimal impl — dataclasses + block parser.**
  Create `src/retail/tmdl.py`:
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .core import RuleContext

DATE_TABLE_MARKER = "annotation PBI_DateTable = true"
# Pinned to the table-level marker literal M0 captured from a real
# "Mark as Date Table" PBIP. M4 consumes this single constant; if M0's
# observed literal differs, only this line changes (single source of truth,
# per spec §9.0 / §13). Column-level `dataCategory: Time` alone is NOT the
# marker (spec line 135).

TI_TRIGGER_FUNCTIONS = frozenset(
    {
        "TOTALYTD", "TOTALQTD", "TOTALMTD", "DATESYTD", "DATESQTD", "DATESMTD",
        "SAMEPERIODLASTYEAR", "DATEADD", "DATESINPERIOD", "DATESBETWEEN",
        "PARALLELPERIOD", "PREVIOUSYEAR", "PREVIOUSQUARTER", "PREVIOUSMONTH",
        "PREVIOUSDAY", "NEXTYEAR", "NEXTQUARTER", "NEXTMONTH", "NEXTDAY",
        "OPENINGBALANCEMONTH", "OPENINGBALANCEQUARTER", "OPENINGBALANCEYEAR",
        "CLOSINGBALANCEMONTH", "CLOSINGBALANCEQUARTER", "CLOSINGBALANCEYEAR",
        "STARTOFYEAR", "STARTOFQUARTER", "STARTOFMONTH",
        "ENDOFYEAR", "ENDOFQUARTER", "ENDOFMONTH", "FIRSTDATE", "LASTDATE",
    }
)


@dataclass(frozen=True)
class TmdlMeasure:
    name: str
    expression: str
    display_folder: str | None
    line: int


@dataclass(frozen=True)
class TmdlColumn:
    name: str
    data_type: str | None
    summarize_by: str | None
    line: int


@dataclass(frozen=True)
class TmdlRelationship:
    name: str
    cross_filtering_behavior: str | None
    line: int


@dataclass(frozen=True)
class TmdlTable:
    name: str
    measures: tuple[TmdlMeasure, ...]
    columns: tuple[TmdlColumn, ...]
    partition_sources: tuple[str, ...]
    annotations: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class TmdlModel:
    tables: tuple[TmdlTable, ...]
    relationships: tuple[TmdlRelationship, ...]


def _indent(line: str) -> int:
    n = 0
    for ch in line:
        if ch == "\t":
            n += 1
        else:
            break
    return n


def _strip_bom(text: str) -> str:
    return text.lstrip("﻿")


def parse_tmdl(text: str) -> TmdlTable | None:
    lines = _strip_bom(text).splitlines()
    table_name: str | None = None
    table_line = 0
    for i, raw in enumerate(lines, start=1):
        m = re.match(r"table\s+('?)(?P<name>[^'\n]+?)\1\s*$", raw.strip())
        if raw and _indent(raw) == 0 and m:
            table_name = m.group("name")
            table_line = i
            break
    if table_name is None:
        return None

    measures: list[TmdlMeasure] = []
    columns: list[TmdlColumn] = []
    sources: list[str] = []
    annotations: list[str] = []

    n = len(lines)
    i = 0
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        ind = _indent(raw)
        mm = re.match(r"measure\s+('?)(?P<name>[^'=]+?)\1\s*=\s*(?P<expr>.*)$", stripped)
        cm = re.match(r"column\s+('?)(?P<name>[^'\n]+?)\1\s*$", stripped)
        am = re.match(r"annotation\s+.+", stripped)
        if mm and ind == 1:
            name = mm.group("name").strip()
            expr_parts = [mm.group("expr").rstrip()]
            df: str | None = None
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                child = lines[j].strip()
                dfm = re.match(r"displayFolder:\s*(?P<v>.+)$", child)
                if dfm:
                    df = dfm.group("v").strip()
                elif child and not re.match(r"\w+:\s", child):
                    expr_parts.append(child)
                j += 1
            measures.append(
                TmdlMeasure(name=name, expression=" ".join(expr_parts).strip(),
                            display_folder=df, line=i + 1)
            )
            i = j
            continue
        if cm and ind == 1:
            name = cm.group("name").strip()
            dt: str | None = None
            sb: str | None = None
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                child = lines[j].strip()
                d = re.match(r"dataType:\s*(?P<v>.+)$", child)
                s = re.match(r"summarizeBy:\s*(?P<v>.+)$", child)
                if d:
                    dt = d.group("v").strip()
                if s:
                    sb = s.group("v").strip()
                j += 1
            columns.append(TmdlColumn(name=name, data_type=dt, summarize_by=sb, line=i + 1))
            i = j
            continue
        if re.match(r"(source|partition)\b", stripped) and "=" in stripped:
            body = [stripped.split("=", 1)[1].strip()]
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                if lines[j].strip():
                    body.append(lines[j].strip())
                j += 1
            sources.append(" ".join(p for p in body if p).strip())
            i = j
            continue
        if am and ind <= 1:
            annotations.append(stripped)
        i += 1

    return TmdlTable(
        name=table_name,
        measures=tuple(measures),
        columns=tuple(columns),
        partition_sources=tuple(sources),
        annotations=tuple(annotations),
        line=table_line,
    )


def parse_relationships(text: str) -> tuple[TmdlRelationship, ...]:
    lines = _strip_bom(text).splitlines()
    rels: list[TmdlRelationship] = []
    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        rm = re.match(r"relationship\s+('?)(?P<name>[^'\n]+?)\1\s*$", stripped)
        if rm and _indent(lines[i]) == 0:
            name = rm.group("name").strip()
            cfb: str | None = None
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > 0):
                c = re.match(r"crossFilteringBehavior:\s*(?P<v>.+)$", lines[j].strip())
                if c:
                    cfb = c.group("v").strip()
                j += 1
            rels.append(TmdlRelationship(name=name, cross_filtering_behavior=cfb, line=i + 1))
            i = j
            continue
        i += 1
    return tuple(rels)


def iter_model_files(ctx: RuleContext, suffix: str) -> Iterable[tuple[str, str]]:
    for rel in ctx.tracked_files:
        if ".SemanticModel/definition/" in rel and rel.endswith(suffix):
            text = (ctx.repo_root / Path(rel)).read_text(encoding="utf-8-sig")
            yield rel, text


def normalize_measure_body(expression: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", " ", expression, flags=re.DOTALL)
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    return re.sub(r"\s+", " ", no_line).strip().lower()
```
- [ ] **Step 4: Run to pass.** `pytest -m unit tests/unit/test_tmdl.py -v` → both tests PASS.
- [ ] **Step 5: Add failing tests for relationships, sources, annotations, and `normalize_measure_body`.**
  Append to `tests/unit/test_tmdl.py`:
```python
from retail.tmdl import (
    normalize_measure_body,
    parse_relationships,
)

REL_TMDL = """relationship Sales_Date
\tfromColumn: Sales.DateKey
\ttoColumn: Date.DateKey
\tcrossFilteringBehavior: bothDirections

relationship Sales_Product
\tfromColumn: Sales.ProductKey
\ttoColumn: Product.ProductKey
"""

PARTITION_TMDL = """table Sales
\tpartition Sales = m
\t\tsource =
\t\t\tlet
\t\t\t\tSrc = PostgreSQL.Database(Server, DB),
\t\t\t\tData = Value.NativeQuery(Src, "SELECT * FROM gold.fct_sales")
\t\t\tin
\t\t\t\tData
\tannotation PBI_DateTable = true
"""


def test_parse_relationships_captures_crossfilter() -> None:
    rels = parse_relationships(REL_TMDL)
    assert [r.name for r in rels] == ["Sales_Date", "Sales_Product"]
    assert rels[0].cross_filtering_behavior == "bothDirections"
    assert rels[1].cross_filtering_behavior is None


def test_parse_tmdl_captures_partition_source_and_annotation() -> None:
    table = parse_tmdl(PARTITION_TMDL)
    assert table is not None
    assert len(table.partition_sources) == 1
    assert "gold.fct_sales" in table.partition_sources[0]
    assert "annotation PBI_DateTable = true" in table.annotations


def test_normalize_measure_body_strips_comments_and_case() -> None:
    body = "SUM ( Sales[Amount] ) // total\n/* note */"
    assert normalize_measure_body(body) == "sum ( sales[amount] )"
```
- [ ] **Step 6: Run to pass.** `pytest -m unit tests/unit/test_tmdl.py -v` → all 5 tests PASS (impl already covers these; if `parse_relationships` import or source-capture fails, fix `tmdl.py` until green).
- [ ] **Step 7: Format + lint + commit.**
  `black src/retail/tmdl.py tests/unit/test_tmdl.py && ruff check src/retail/tmdl.py tests/unit/test_tmdl.py && pytest -m unit tests/unit/test_tmdl.py -v`
  then `git add src/retail/tmdl.py tests/unit/test_tmdl.py && git commit -m "feat: hand-rolled TMDL block parser for model rules"`

---

### Task M4.2: TMDL fixtures (passing + failing) under `tests/fixtures/tmdl/`

Shared fixtures for D1-D8. Each rule references the relevant file. Failing files each contain exactly one violation class so a rule's failing test is unambiguous.

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\clean_sales.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\clean_date.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\clean_relationships.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_names.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_divide.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_duplicate.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_summarize.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_relationships.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_ti_no_marker.tmdl`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\tmdl\bad_source_bronze.tmdl`

**Interfaces:**
- Consumes: nothing (data files).
- Produces: fixture files read by the D-rule tests via `Path(__file__).parent.parent / "fixtures" / "tmdl" / "<name>"`.

- [ ] **Step 1: Write the passing fixtures.**
  `tests/fixtures/tmdl/clean_sales.tmdl`:
```
table Sales
	measure Revenue = SUM(Sales[Amount])
		displayFolder: KPIs

	measure Margin = DIVIDE([Revenue], [Cost])
		displayFolder: KPIs

	column Amount
		dataType: decimal
		summarizeBy: none

	column ProductKey
		dataType: int64
		summarizeBy: none

	partition Sales = m
		source =
			let
				Src = PostgreSQL.Database(ServerParam, DbParam),
				Data = Value.NativeQuery(Src, "SELECT * FROM gold.fct_sales")
			in
				Data
```
  `tests/fixtures/tmdl/clean_date.tmdl`:
```
table Date
	measure YTD = TOTALYTD([Revenue], Date[Date])
		displayFolder: Time

	column Date
		dataType: dateTime
		summarizeBy: none

	annotation PBI_DateTable = true
```
  `tests/fixtures/tmdl/clean_relationships.tmdl`:
```
relationship Sales_Date
	fromColumn: Sales.DateKey
	toColumn: Date.DateKey

relationship Sales_Product
	fromColumn: Sales.ProductKey
	toColumn: Product.ProductKey
```
- [ ] **Step 2: Write the failing fixtures (one violation class each).**
  `tests/fixtures/tmdl/bad_names.tmdl` (D1: `total_revenue` not PascalCase; D2-safe — has folder):
```
table Sales
	measure total_revenue = SUM(Sales[Amount])
		displayFolder: KPIs
```
  `tests/fixtures/tmdl/bad_divide.tmdl` (D4: bare `/`):
```
table Sales
	measure Ratio = [Revenue] / [Cost]
		displayFolder: KPIs
```
  `tests/fixtures/tmdl/bad_duplicate.tmdl` (D3: two measures, identical normalized body):
```
table Sales
	measure Revenue = SUM(Sales[Amount])
		displayFolder: KPIs

	measure TotalSales = SUM( Sales[Amount] )
		displayFolder: KPIs
```
  `tests/fixtures/tmdl/bad_summarize.tmdl` (D5: numeric column summarizeBy != none):
```
table Sales
	column Amount
		dataType: decimal
		summarizeBy: sum
```
  `tests/fixtures/tmdl/bad_relationships.tmdl` (D6: bothDirections):
```
relationship Sales_Date
	fromColumn: Sales.DateKey
	toColumn: Date.DateKey
	crossFilteringBehavior: bothDirections
```
  `tests/fixtures/tmdl/bad_ti_no_marker.tmdl` (D7: TI function, no date marker):
```
table Sales
	measure YTD = TOTALYTD([Revenue], Sales[Date])
		displayFolder: Time
```
  `tests/fixtures/tmdl/bad_source_bronze.tmdl` (D8: native SQL FROM bronze):
```
table Sales
	measure Revenue = SUM(Sales[Amount])
		displayFolder: KPIs

	partition Sales = m
		source =
			let
				Src = PostgreSQL.Database(ServerParam, DbParam),
				Data = Value.NativeQuery(Src, "SELECT * FROM bronze.stg_sales")
			in
				Data
```
- [ ] **Step 3: Sanity-check the fixtures parse.** Run a one-off:
  `python -c "from pathlib import Path; import sys; sys.path.insert(0,'src'); from retail.tmdl import parse_tmdl; t=parse_tmdl(Path('tests/fixtures/tmdl/clean_sales.tmdl').read_text(encoding='utf-8-sig')); print(t.name, [m.name for m in t.measures], len(t.partition_sources))"`
  → expected output: `Sales ['Revenue', 'Margin'] 1`
- [ ] **Step 4: Commit fixtures.**
  `git add tests/fixtures/tmdl/ && git commit -m "test: add passing+failing TMDL fixtures for D-rules"`

---

### Task M4.3: D1 (PascalCase measures) + D2 (displayFolder required)

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`

**Interfaces:**
- Consumes: `RuleContext`, `Finding`, `Severity` from `retail.core`; `register` from `retail.registry`; `parse_tmdl`, `iter_model_files` from `retail.tmdl`.
- Produces: rules `d1_pascalcase_measures`, `d2_display_folder` (registered as `D1`, `D2`).

- [ ] **Step 1: Write failing tests.** In `tests/unit/test_dax.py`:
```python
from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.dax import d1_pascalcase_measures, d2_display_folder

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "tmdl"


def _ctx(tmp_path: Path, fixture: str) -> RuleContext:
    rel = "Model.SemanticModel/definition/tables/T.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / fixture).read_text(encoding="utf-8-sig"), encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def test_d1_flags_non_pascalcase(tmp_path: Path) -> None:
    findings = list(d1_pascalcase_measures(_ctx(tmp_path, "bad_names.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D1"
    assert findings[0].severity is Severity.ERROR
    assert "total_revenue" in findings[0].message


def test_d1_passes_clean(tmp_path: Path) -> None:
    assert list(d1_pascalcase_measures(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d2_flags_missing_display_folder(tmp_path: Path) -> None:
    findings = list(d2_display_folder(_ctx(tmp_path, "bad_ti_no_marker.tmdl")))
    # bad_ti_no_marker has displayFolder, so D2 is clean there; use a folderless fixture
    assert findings == []


def test_d2_passes_clean(tmp_path: Path) -> None:
    assert list(d2_display_folder(_ctx(tmp_path, "clean_sales.tmdl"))) == []
```
- [ ] **Step 2: Add a folderless fixture for D2's failing case.**
  Create `tests/fixtures/tmdl/bad_no_folder.tmdl`:
```
table Sales
	measure Revenue = SUM(Sales[Amount])
```
  and append the D2 failing test to `tests/unit/test_dax.py`:
```python
def test_d2_flags_missing_folder(tmp_path: Path) -> None:
    findings = list(d2_display_folder(_ctx(tmp_path, "bad_no_folder.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D2"
    assert "Revenue" in findings[0].message
```
- [ ] **Step 3: Run to fail.** `pytest -m unit tests/unit/test_dax.py -v` → `ModuleNotFoundError: No module named 'retail.rules.dax'`.
- [ ] **Step 4: Minimal impl.** Create `src/retail/rules/dax.py`:
```python
from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity
from ..registry import register
from ..tmdl import iter_model_files, parse_tmdl

_PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@register("D1", "Measure names must be PascalCase")
def d1_pascalcase_measures(ctx: RuleContext) -> Iterable[Finding]:
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            if not _PASCAL.match(m.name):
                yield Finding(
                    rule_id="D1",
                    severity=Severity.ERROR,
                    message=f"Measure '{m.name}' is not PascalCase (^[A-Z][A-Za-z0-9]*$)",
                    locator=f"{rel}:{m.line}",
                )


@register("D2", "Each measure must have a displayFolder")
def d2_display_folder(ctx: RuleContext) -> Iterable[Finding]:
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            if not m.display_folder:
                yield Finding(
                    rule_id="D2",
                    severity=Severity.ERROR,
                    message=f"Measure '{m.name}' has no displayFolder",
                    locator=f"{rel}:{m.line}",
                )
```
  `src/retail/rules/__init__.py` already exists from M1.6 with `from . import dax, git_meta, pbir, sql` — do NOT recreate or empty it; the @register side-effect imports must stay. This task only ADDS rule functions to dax.py.
- [ ] **Step 5: Run to pass.** `pytest -m unit tests/unit/test_dax.py -v` → all D1/D2 tests PASS.
- [ ] **Step 6: Commit.** `black src/retail/rules/dax.py tests/unit/test_dax.py && ruff check src/retail/rules/dax.py tests/unit/test_dax.py && pytest -m unit tests/unit/test_dax.py -v` then `git add src/retail/rules/dax.py tests/unit/test_dax.py tests/fixtures/tmdl/bad_no_folder.tmdl && git commit -m "feat: add D1 PascalCase and D2 displayFolder measure rules"`

---

### Task M4.4: D3 (no duplicated measure logic) + D4 (DIVIDE not /)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`

**Interfaces:**
- Consumes: `normalize_measure_body` from `retail.tmdl` (D3); raw `TmdlMeasure.expression` (D4).
- Produces: rules `d3_no_duplicate_logic`, `d4_divide_not_slash` (registered `D3`, `D4`).

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_dax.py`:
```python
from retail.rules.dax import d3_no_duplicate_logic, d4_divide_not_slash


def test_d3_flags_identical_bodies(tmp_path: Path) -> None:
    findings = list(d3_no_duplicate_logic(_ctx(tmp_path, "bad_duplicate.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D3"
    assert "Revenue" in findings[0].message and "TotalSales" in findings[0].message


def test_d3_passes_clean(tmp_path: Path) -> None:
    assert list(d3_no_duplicate_logic(_ctx(tmp_path, "clean_sales.tmdl"))) == []


def test_d4_flags_bare_slash(tmp_path: Path) -> None:
    findings = list(d4_divide_not_slash(_ctx(tmp_path, "bad_divide.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D4"
    assert findings[0].locator.endswith(":2")


def test_d4_passes_clean(tmp_path: Path) -> None:
    # clean_sales uses DIVIDE(...) and SUM(...) — no bare slash
    assert list(d4_divide_not_slash(_ctx(tmp_path, "clean_sales.tmdl"))) == []
```
- [ ] **Step 2: Run to fail.** `pytest -m unit tests/unit/test_dax.py -v` → `ImportError: cannot import name 'd3_no_duplicate_logic'`.
- [ ] **Step 3: Minimal impl.** Append to `src/retail/rules/dax.py`:
```python
from ..tmdl import normalize_measure_body


def _strip_dax_comments_and_strings(expr: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", " ", expr, flags=re.DOTALL)
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    return re.sub(r'"(?:[^"]|"")*"', " ", no_line)


@register("D3", "No duplicated measure logic")
def d3_no_duplicate_logic(ctx: RuleContext) -> Iterable[Finding]:
    seen: dict[str, tuple[str, str, int]] = {}
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            norm = normalize_measure_body(m.expression)
            if not norm:
                continue
            if norm in seen:
                prev_rel, prev_name, prev_line = seen[norm]
                yield Finding(
                    rule_id="D3",
                    severity=Severity.ERROR,
                    message=(
                        f"Measure '{m.name}' duplicates logic of "
                        f"'{prev_name}' (identical normalized body)"
                    ),
                    locator=f"{rel}:{m.line}",
                )
            else:
                seen[norm] = (rel, m.name, m.line)


@register("D4", "Use DIVIDE() not the / operator")
def d4_divide_not_slash(ctx: RuleContext) -> Iterable[Finding]:
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            cleaned = _strip_dax_comments_and_strings(m.expression)
            if "/" in cleaned:
                yield Finding(
                    rule_id="D4",
                    severity=Severity.ERROR,
                    message=f"Measure '{m.name}' uses '/'; use DIVIDE() instead",
                    locator=f"{rel}:{m.line}",
                )
```
- [ ] **Step 4: Run to pass.** `pytest -m unit tests/unit/test_dax.py -v` → all D3/D4 tests PASS.
- [ ] **Step 5: Commit.** `black src/retail/rules/dax.py tests/unit/test_dax.py && ruff check src/retail/rules/dax.py tests/unit/test_dax.py && pytest -m unit tests/unit/test_dax.py -v` then `git add src/retail/rules/dax.py tests/unit/test_dax.py && git commit -m "feat: add D3 duplicate-logic and D4 DIVIDE rules"`

---

### Task M4.5: D5 (WARNING: numeric column summarizeBy != none)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`

**Interfaces:**
- Consumes: `TmdlColumn.data_type`, `TmdlColumn.summarize_by`.
- Produces: rule `d5_explicit_aggregation` (registered `D5`, severity WARNING).

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_dax.py`:
```python
from retail.rules.dax import d5_explicit_aggregation


def test_d5_warns_on_implicit_aggregation(tmp_path: Path) -> None:
    findings = list(d5_explicit_aggregation(_ctx(tmp_path, "bad_summarize.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D5"
    assert findings[0].severity is Severity.WARNING
    assert "Amount" in findings[0].message


def test_d5_passes_when_summarize_none(tmp_path: Path) -> None:
    # clean_sales: Amount and ProductKey both summarizeBy none
    assert list(d5_explicit_aggregation(_ctx(tmp_path, "clean_sales.tmdl"))) == []
```
- [ ] **Step 2: Run to fail.** `pytest -m unit tests/unit/test_dax.py -v` → `ImportError: cannot import name 'd5_explicit_aggregation'`.
- [ ] **Step 3: Minimal impl.** Append to `src/retail/rules/dax.py`:
```python
_NUMERIC_TYPES = frozenset({"int64", "decimal", "double", "int", "currency"})


@register("D5", "Prefer explicit measures over implicit aggregation")
def d5_explicit_aggregation(ctx: RuleContext) -> Iterable[Finding]:
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for c in table.columns:
            dt = (c.data_type or "").lower()
            sb = (c.summarize_by or "none").lower()
            if dt in _NUMERIC_TYPES and sb != "none":
                yield Finding(
                    rule_id="D5",
                    severity=Severity.WARNING,
                    message=(
                        f"Numeric column '{c.name}' has summarizeBy='{c.summarize_by}'; "
                        "prefer explicit measures (summarizeBy: none)"
                    ),
                    locator=f"{rel}:{c.line}",
                )
```
- [ ] **Step 4: Run to pass.** `pytest -m unit tests/unit/test_dax.py -v` → D5 tests PASS.
- [ ] **Step 5: Commit.** `black src/retail/rules/dax.py tests/unit/test_dax.py && ruff check src/retail/rules/dax.py tests/unit/test_dax.py && pytest -m unit tests/unit/test_dax.py -v` then `git add src/retail/rules/dax.py tests/unit/test_dax.py && git commit -m "feat: add D5 implicit-aggregation warning rule"`

---

### Task M4.6: D6 (single-direction relationships)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`

**Interfaces:**
- Consumes: `parse_relationships` from `retail.tmdl`; matches tracked files ending `relationships.tmdl`.
- Produces: rule `d6_single_direction` (registered `D6`).

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_dax.py`:
```python
from retail.rules.dax import d6_single_direction


def _rel_ctx(tmp_path: Path, fixture: str) -> RuleContext:
    rel = "Model.SemanticModel/definition/relationships.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / fixture).read_text(encoding="utf-8-sig"), encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def test_d6_flags_bidirectional(tmp_path: Path) -> None:
    findings = list(d6_single_direction(_rel_ctx(tmp_path, "bad_relationships.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D6"
    assert "Sales_Date" in findings[0].message


def test_d6_passes_clean(tmp_path: Path) -> None:
    assert list(d6_single_direction(_rel_ctx(tmp_path, "clean_relationships.tmdl"))) == []
```
- [ ] **Step 2: Run to fail.** `pytest -m unit tests/unit/test_dax.py -v` → `ImportError: cannot import name 'd6_single_direction'`.
- [ ] **Step 3: Minimal impl.** Append to `src/retail/rules/dax.py`:
```python
from ..tmdl import parse_relationships


@register("D6", "Relationships must be single-direction")
def d6_single_direction(ctx: RuleContext) -> Iterable[Finding]:
    for rel, text in iter_model_files(ctx, "relationships.tmdl"):
        for r in parse_relationships(text):
            if (r.cross_filtering_behavior or "").lower() == "bothdirections":
                yield Finding(
                    rule_id="D6",
                    severity=Severity.ERROR,
                    message=(
                        f"Relationship '{r.name}' is bothDirections; "
                        "use single-direction (justify many-to-many in review)"
                    ),
                    locator=f"{rel}:{r.line}",
                )
```
- [ ] **Step 4: Run to pass.** `pytest -m unit tests/unit/test_dax.py -v` → D6 tests PASS.
- [ ] **Step 5: Commit.** `black src/retail/rules/dax.py tests/unit/test_dax.py && ruff check src/retail/rules/dax.py tests/unit/test_dax.py && pytest -m unit tests/unit/test_dax.py -v` then `git add src/retail/rules/dax.py tests/unit/test_dax.py && git commit -m "feat: add D6 single-direction relationship rule"`

---

### Task M4.7: D7 (time-intelligence date marker — static half)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`

**Interfaces:**
- Consumes: `TI_TRIGGER_FUNCTIONS`, `DATE_TABLE_MARKER` from `retail.tmdl`; raw measure expressions + table annotations across all `.tmdl` files (model-wide check). `DATE_TABLE_MARKER` is the single source of truth pinned by M0; if M0's observed literal differs, only that constant changes.
- Produces: rule `d7_time_intelligence_marker` (registered `D7`). Locator is the file path (model-wide condition — never invent a line number).

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_dax.py`:
```python
from retail.rules.dax import d7_time_intelligence_marker


def _multi_ctx(tmp_path: Path, *fixtures: str) -> RuleContext:
    rels: list[str] = []
    for idx, fx in enumerate(fixtures):
        rel = f"Model.SemanticModel/definition/tables/T{idx}.tmdl"
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((FIXTURES / fx).read_text(encoding="utf-8-sig"), encoding="utf-8")
        rels.append(rel)
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rels))


def test_d7_flags_ti_without_marker(tmp_path: Path) -> None:
    findings = list(d7_time_intelligence_marker(_multi_ctx(tmp_path, "bad_ti_no_marker.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D7"
    assert "TOTALYTD" in findings[0].message


def test_d7_passes_when_marker_present(tmp_path: Path) -> None:
    # clean_date.tmdl uses TOTALYTD AND carries the date-table marker annotation
    assert list(d7_time_intelligence_marker(_multi_ctx(tmp_path, "clean_date.tmdl"))) == []


def test_d7_passes_when_no_ti_used(tmp_path: Path) -> None:
    # clean_sales.tmdl uses no TI function → no marker required
    assert list(d7_time_intelligence_marker(_multi_ctx(tmp_path, "clean_sales.tmdl"))) == []
```
- [ ] **Step 2: Run to fail.** `pytest -m unit tests/unit/test_dax.py -v` → `ImportError: cannot import name 'd7_time_intelligence_marker'`.
- [ ] **Step 3: Minimal impl.** Append to `src/retail/rules/dax.py`:
```python
from ..tmdl import DATE_TABLE_MARKER, TI_TRIGGER_FUNCTIONS

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@register("D7", "Time-intelligence requires a marked date table")
def d7_time_intelligence_marker(ctx: RuleContext) -> Iterable[Finding]:
    used_ti: set[str] = set()
    ti_locator: str | None = None
    marker_present = False
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        if any(a.strip() == DATE_TABLE_MARKER for a in table.annotations):
            marker_present = True
        for m in table.measures:
            cleaned = _strip_dax_comments_and_strings(m.expression)
            for tok in _WORD.findall(cleaned):
                if tok.upper() in TI_TRIGGER_FUNCTIONS:
                    used_ti.add(tok.upper())
                    if ti_locator is None:
                        ti_locator = rel
    if used_ti and not marker_present:
        funcs = ", ".join(sorted(used_ti))
        yield Finding(
            rule_id="D7",
            severity=Severity.ERROR,
            message=(
                f"Time-intelligence functions used ({funcs}) but no date-table "
                f"marker found ({DATE_TABLE_MARKER!r})"
            ),
            locator=ti_locator or ".",
        )
```
- [ ] **Step 4: Run to pass.** `pytest -m unit tests/unit/test_dax.py -v` → D7 tests PASS.
- [ ] **Step 5: Commit.** `black src/retail/rules/dax.py tests/unit/test_dax.py && ruff check src/retail/rules/dax.py tests/unit/test_dax.py && pytest -m unit tests/unit/test_dax.py -v` then `git add src/retail/rules/dax.py tests/unit/test_dax.py && git commit -m "feat: add D7 time-intelligence date-marker rule"`

---

### Task M4.8: D8 (gold-only sourcing — M + native SQL)

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`

**Interfaces:**
- Consumes: `TmdlTable.partition_sources` (raw M bodies). Reuses the S2 schema-position matcher `stale_schema_tokens(text: str) -> list[tuple[str, int]]` from `retail.sql` (produced by M3.1) — yields `(schema_token, line)` for tokens in schema-qualifying positions only (M `Schema="…"` and native-SQL `FROM <schema>.<obj>`), never the English word "raw". Does NOT re-derive the matcher.
- Produces: rule `d8_gold_only_source` (registered `D8`); and the shared M-source iterator `iter_m_sources` (with `MSource`) consumed by D8 itself and reused by M4.C1.

- [ ] **Step 1: Write failing tests.** Append to `tests/unit/test_dax.py`:
```python
from retail.rules.dax import d8_gold_only_source


def test_d8_flags_non_gold_schema(tmp_path: Path) -> None:
    findings = list(d8_gold_only_source(_ctx(tmp_path, "bad_source_bronze.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D8"
    assert "bronze" in findings[0].message


def test_d8_passes_gold_source(tmp_path: Path) -> None:
    # clean_sales.tmdl sources FROM gold.fct_sales
    assert list(d8_gold_only_source(_ctx(tmp_path, "clean_sales.tmdl"))) == []
```
- [ ] **Step 2: Run to fail.** `pytest -m unit tests/unit/test_dax.py -v` → `ImportError: cannot import name 'd8_gold_only_source'`.
- [ ] **Step 3: Minimal impl.** Append to `src/retail/rules/dax.py`.

  **Produces (consumed by D8 itself and reused verbatim by M4.C1):** the shared
  M-source iterator. It walks every `*.SemanticModel/definition/**` TMDL file and
  yields one `MSource` per partition `source = …` M block **and** per shared
  `expression … = …` block (a TMDL parameter is a shared `expression` block, so
  this single helper already reaches parameter defaults), each with a
  `"path:line"` locator pointing at the block's first line.

  ```python
  from dataclasses import dataclass
  from pathlib import Path

  from ..sql import stale_schema_tokens

  # `re`, `Iterable`, `RuleContext`, `Finding`, `Severity`, `register`, and
  # `iter_model_files` are already imported at the top of dax.py (from D1).


  @dataclass(frozen=True)
  class MSource:
      text: str        # the raw M expression text of the source/expression block
      locator: str     # "path:line" pointing at the block's first line


  # Headers that open an M block whose body is the value we must scan.
  _M_BLOCK_RE = re.compile(r"^(?P<indent>\s*)(?:partition\s+\S+\s*=\s*m\b|source\s*=|expression\s+\S+\s*=)")


  def iter_m_sources(
      repo_root: Path, tracked_files: tuple[str, ...]
  ) -> Iterable[MSource]:
      """Yield every partition `source` M block and shared `expression` block.

      Walks each tracked `*.SemanticModel/definition/**` TMDL file. A block runs
      from its header line until the indentation returns to (or below) the
      header's own indent. Locator is "<repo-relative-posix-path>:<1-based line>".
      """
      ctx = RuleContext(repo_root=repo_root, tracked_files=tracked_files)
      for rel, text in iter_model_files(ctx, ".tmdl"):
          lines = text.splitlines()
          i = 0
          while i < len(lines):
              m = _M_BLOCK_RE.match(lines[i])
              if not m:
                  i += 1
                  continue
              header_indent = len(m.group("indent"))
              start = i
              body: list[str] = [lines[i]]
              i += 1
              while i < len(lines):
                  nxt = lines[i]
                  if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= header_indent:
                      break
                  body.append(nxt)
                  i += 1
              yield MSource(text="\n".join(body), locator=f"{rel}:{start + 1}")


  @register("D8", "Power BI must source the gold schema only")
  def d8_gold_only_source(ctx: RuleContext) -> Iterable[Finding]:
      for src in iter_m_sources(ctx.repo_root, ctx.tracked_files):
          for token, line in stale_schema_tokens(src.text):
              if token.lower() != "gold":
                  yield Finding(
                      rule_id="D8",
                      severity=Severity.ERROR,
                      message=(
                          f"partition sources schema '{token}'; "
                          "Power BI must read 'gold' only"
                      ),
                      locator=src.locator,
                  )
  ```
- [ ] **Step 4: Run to pass.** `pytest -m unit tests/unit/test_dax.py -v` → D8 tests PASS. (Depends on M3.1's `stale_schema_tokens` already existing; if M3 is not yet merged, this task is blocked on it.)
- [ ] **Step 5: Full M4 gate + commit.** Run the whole DAX suite + parser suite together:
  `black src/retail tests/unit && ruff check src/retail tests/unit && pytest -m unit tests/unit/test_tmdl.py tests/unit/test_dax.py -v`
  → all tests PASS, no ruff errors. Then `git add src/retail/rules/dax.py tests/unit/test_dax.py && git commit -m "feat: add D8 gold-only sourcing rule"`


---

### Task M4.C1: C1 parameterized-connection rule

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py` (append the C1 rule; module already exists from D1–D8 and is already imported by `src/retail/rules/__init__.py`)
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py` (append C1 tests to the existing `dax` group test module)

**Interfaces:**

- Consumes (contract-v2, from `src/retail/core.py`):
  - `Severity` (`str`, `Enum`): `ERROR` / `WARNING` / `INFO`
  - `Finding(rule_id: str, severity: Severity, message: str, locator: str)` — `@dataclass(frozen=True)`
  - `RuleContext(repo_root: Path, tracked_files: tuple[str, ...], commit_range: str | None = None, commit_message: str | None = None)` — `@dataclass(frozen=True)`
  - `Rule = Callable[[RuleContext], Iterable[Finding]]`
- Consumes (from `src/retail/registry.py`):
  - `register(rule_id: str, title: str) -> Callable[[Rule], Rule]`
- Consumes (from **Task M4.8 (D8)**, produced and consumed there, defined in `src/retail/rules/dax.py`): the shared M-source iterator `MSource` / `iter_m_sources` that D8 uses to walk **both** partition `source` M blocks and shared `expression` blocks (a TMDL parameter is a shared `expression` block, so this single helper already reaches parameter defaults). C1 imports nothing new — both symbols already live in `dax.py` from M4.8:

  ```python
  # Defined in M4.8 (D8) — reused verbatim by C1, NOT re-derived here.
  @dataclass(frozen=True)
  class MSource:
      text: str        # the raw M expression text of the source/expression block
      locator: str     # "path:line" pointing at the block's first line

  def iter_m_sources(
      repo_root: Path, tracked_files: tuple[str, ...]
  ) -> Iterable[MSource]: ...
  ```

  > These are produced by Task M4.8 (D8) with exactly this signature; C1 calls `iter_m_sources(ctx.repo_root, ctx.tracked_files)`. Do **not** write a second TMDL scanner.

- Produces (consumed by no later task; C1 is one of the fixed 23 rules, asserted by the Final Integration Gate's `EXPECTED_RULE_IDS` set-equality check):
  - `_M_CONNECTORS: tuple[str, ...]` — the three connector call prefixes C1 inspects.
  - `_split_top_level_args(arg_text: str) -> list[str]` — splits a connector call's argument list on **top-level** commas (depth-aware over `()`, `[]`, `{}`, and `"…"` string literals), returning each argument's trimmed source text.
  - `check_parameterized_connection(ctx: RuleContext) -> Iterable[Finding]` — the C1 rule, decorated `@register("C1", "Parameterized connection (no literal server/database)")`.

**Rule behavior (exact):** For each `MSource` from `iter_m_sources`:
1. **Positional check** — find every `PostgreSQL.Database(`, `Sql.Database(`, `Odbc.DataSource(` call. Split its top-level args; emit one `Severity.ERROR` `Finding` for **each** of argument positions **0 (server) and 1 (database)** that is a string literal (starts with `"`). A parameter identifier in those positions (e.g. `ServerParam`) is fine. Literals elsewhere — `Source{[Schema="gold"]}`, an `sslmode` options-record literal (position ≥ 2) — are excluded **by construction** (not in positions 0–1).
2. **Connection-string check** — independently, flag any string literal in the block containing `Host=`, `Server=`, `Database=`, `User Id=`, or `Password=` (case-insensitive). Token `Database=` carries a trailing `=`, so it never false-matches the `Sql.Database(` call name.

Cardinality: **one `Finding` per offending argument** (positional check) plus **one `Finding` per offending connection-string literal** (string check). Locator = the `MSource.locator`.

---

- [ ] **Step 1: Write the failing tests**

Append to `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dax.py`:

```python
import textwrap
from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.dax import (
    _split_top_level_args,
    check_parameterized_connection,
)


def _write_tmdl(tmp_path: Path, body: str) -> RuleContext:
    """Write a TMDL file containing `body` and return a RuleContext for it."""
    model_dir = tmp_path / "Sales.SemanticModel" / "definition" / "tables"
    model_dir.mkdir(parents=True)
    rel = "Sales.SemanticModel/definition/tables/Orders.tmdl"
    (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel).write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


@pytest.mark.unit
def test_split_top_level_args_ignores_nested_commas() -> None:
    text = 'ServerParam, DbParam, [Schema="gold", CommandTimeout=#duration(0,0,30,0)]'
    assert _split_top_level_args(text) == [
        "ServerParam",
        "DbParam",
        '[Schema="gold", CommandTimeout=#duration(0,0,30,0)]',
    ]


@pytest.mark.unit
def test_c1_pass_parameterized_server_and_database(tmp_path: Path) -> None:
    body = textwrap.dedent(
        '''\
        table Orders
        \tpartition Orders = m
        \t\tmode: import
        \t\tsource =
        \t\t\tlet
        \t\t\t\tSource = PostgreSQL.Database(ServerParam, DbParam),
        \t\t\t\tData = Source{[Schema="gold"]}[Data]
        \t\t\tin
        \t\t\t\tData
        '''
    )
    ctx = _write_tmdl(tmp_path, body)
    assert list(check_parameterized_connection(ctx)) == []


@pytest.mark.unit
def test_c1_pass_negative_control_schema_and_sslmode_literals(tmp_path: Path) -> None:
    # Parameterized server/db, but literals present in NON server/db positions
    # (Schema="gold", and an sslmode options-record literal). Must be ZERO findings.
    body = textwrap.dedent(
        '''\
        table Orders
        \tpartition Orders = m
        \t\tsource =
        \t\t\tlet
        \t\t\t\tSource = PostgreSQL.Database(ServerParam, DbParam, [sslmode="require"]),
        \t\t\t\tData = Source{[Schema="gold"]}[Data]
        \t\t\tin
        \t\t\t\tData
        '''
    )
    ctx = _write_tmdl(tmp_path, body)
    assert list(check_parameterized_connection(ctx)) == []


@pytest.mark.unit
def test_c1_fail_literal_server_and_database(tmp_path: Path) -> None:
    body = textwrap.dedent(
        '''\
        table Orders
        \tpartition Orders = m
        \t\tsource =
        \t\t\tlet
        \t\t\t\tSource = PostgreSQL.Database("realhost.db.ondigitalocean.com","analytics"),
        \t\t\t\tData = Source{[Schema="gold"]}[Data]
        \t\t\tin
        \t\t\t\tData
        '''
    )
    ctx = _write_tmdl(tmp_path, body)
    findings = list(check_parameterized_connection(ctx))
    # One per literal in positions 0 and 1 = two positional findings.
    assert len(findings) == 2
    assert all(f.rule_id == "C1" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all("Orders.tmdl" in f.locator for f in findings)


@pytest.mark.unit
def test_c1_fail_connection_string_literal_in_odbc(tmp_path: Path) -> None:
    body = textwrap.dedent(
        '''\
        table Orders
        \tpartition Orders = m
        \t\tsource =
        \t\t\tlet
        \t\t\t\tSource = Odbc.DataSource("Host=x;Database=y;User Id=z;Password=p")
        \t\t\tin
        \t\t\t\tSource
        '''
    )
    ctx = _write_tmdl(tmp_path, body)
    findings = list(check_parameterized_connection(ctx))
    # Position 0 is a string literal (1 positional finding) AND it is a
    # connection-string literal (1 string-scan finding) = 2 findings.
    assert len(findings) == 2
    assert all(f.severity is Severity.ERROR for f in findings)
    assert any("connection string" in f.message.lower() for f in findings)


@pytest.mark.unit
def test_c1_fail_parameter_default_connection_string(tmp_path: Path) -> None:
    # A shared `expression` block (a TMDL parameter) whose default is a full
    # connection string. Proves iter_m_sources reaches parameter expressions.
    body = textwrap.dedent(
        '''\
        expression ServerParam =
        \t\t"Host=realhost.db.ondigitalocean.com;Database=analytics;User Id=u;Password=p"
        \t\tmeta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
        '''
    )
    ctx = _write_tmdl(tmp_path, body)
    findings = list(check_parameterized_connection(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "C1"
    assert findings[0].severity is Severity.ERROR
    assert "connection string" in findings[0].message.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
C:/Users/user/miniforge3/python.exe -m pytest tests/unit/test_dax.py -k "c1 or split_top_level" -v
```
Expected: FAIL — collection/import error `ImportError: cannot import name '_split_top_level_args' from 'retail.rules.dax'` (and `check_parameterized_connection` once that import resolves). The six C1 tests do not run.

- [ ] **Step 3: Write the minimal implementation**

Append to `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\dax.py` (keep `from __future__ import annotations` and the existing `re` import at the top of the module; add `re` only if D8 did not already import it):

```python
_M_CONNECTORS: tuple[str, ...] = (
    "PostgreSQL.Database",
    "Sql.Database",
    "Odbc.DataSource",
)

# Connection-string tokens that must never appear inside a string literal.
_CONN_STRING_TOKENS: tuple[str, ...] = (
    "Host=",
    "Server=",
    "Database=",
    "User Id=",
    "Password=",
)

# A double-quoted M string literal (no escape handling needed: M escapes a
# quote by doubling it, which leaves a benign empty adjacency for our checks).
_M_STRING_RE = re.compile(r'"[^"]*"')


def _split_top_level_args(arg_text: str) -> list[str]:
    """Split a connector call's argument list on top-level commas.

    Depth-aware over (), [], {} and quoted "" strings, so commas nested in a
    record/list/string literal do not split. Returns each argument trimmed.
    """
    args: list[str] = []
    depth = 0
    in_str = False
    start = 0
    for i, ch in enumerate(arg_text):
        if in_str:
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(arg_text[start:i].strip())
            start = i + 1
    tail = arg_text[start:].strip()
    if tail:
        args.append(tail)
    return args


def _connector_arg_lists(text: str) -> list[str]:
    """Return the raw argument-list text of each connector call in `text`."""
    out: list[str] = []
    for connector in _M_CONNECTORS:
        idx = 0
        token = connector + "("
        while True:
            hit = text.find(token, idx)
            if hit == -1:
                break
            open_paren = hit + len(token) - 1
            depth = 0
            in_str = False
            j = open_paren
            while j < len(text):
                ch = text[j]
                if in_str:
                    if ch == '"':
                        in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            out.append(text[open_paren + 1 : j])
            idx = j + 1
    return out


@register("C1", "Parameterized connection (no literal server/database)")
def check_parameterized_connection(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for src in iter_m_sources(ctx.repo_root, ctx.tracked_files):
        # (1) Positional check: literal server (pos 0) / database (pos 1).
        for arg_text in _connector_arg_lists(src.text):
            args = _split_top_level_args(arg_text)
            for pos in (0, 1):
                if pos < len(args) and args[pos].startswith('"'):
                    label = "server" if pos == 0 else "database"
                    findings.append(
                        Finding(
                            rule_id="C1",
                            severity=Severity.ERROR,
                            message=(
                                f"connection {label} argument is a string "
                                f"literal {args[pos]}; use a parameter identifier"
                            ),
                            locator=src.locator,
                        )
                    )
        # (2) Connection-string-literal check (any literal in the block).
        for literal in _M_STRING_RE.findall(src.text):
            if any(
                tok.lower() in literal.lower() for tok in _CONN_STRING_TOKENS
            ):
                findings.append(
                    Finding(
                        rule_id="C1",
                        severity=Severity.ERROR,
                        message=(
                            "embedded connection string literal "
                            f"{literal}; use connection parameters"
                        ),
                        locator=src.locator,
                    )
                )
    return findings
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
C:/Users/user/miniforge3/python.exe -m pytest tests/unit/test_dax.py -k "c1 or split_top_level" -v
```
Expected: PASS — all 7 selected tests green (`test_split_top_level_args_ignores_nested_commas`, `test_c1_pass_parameterized_server_and_database`, `test_c1_pass_negative_control_schema_and_sslmode_literals`, `test_c1_fail_literal_server_and_database`, `test_c1_fail_connection_string_literal_in_odbc`, `test_c1_fail_parameter_default_connection_string`, plus any existing D-rule tests not deselected).

- [ ] **Step 5: Run the full dax group plus lint/format to confirm no regression**

Run:
```bash
C:/Users/user/miniforge3/python.exe -m pytest tests/unit/test_dax.py -q
C:/Users/user/miniforge3/python.exe -m ruff check src/retail/rules/dax.py tests/unit/test_dax.py
C:/Users/user/miniforge3/python.exe -m black --check src/retail/rules/dax.py tests/unit/test_dax.py
```
Expected: pytest reports all dax-group tests passing (D1–D8 plus the 6 new C1 tests + the splitter test); `ruff check` prints `All checks passed!`; `black --check` reports the two files `would be left unchanged`. (If black reports it would reformat, run `C:/Users/user/miniforge3/python.exe -m black src/retail/rules/dax.py tests/unit/test_dax.py` and re-run the checks.)

- [ ] **Step 6: Commit**

```bash
git add src/retail/rules/dax.py tests/unit/test_dax.py
git commit -m "feat: add C1 parameterized-connection rule"
```

---

## Milestone 5 — PBIR Rule

### Task M5.1: PBIR rule R1 — relative model reference (`src/retail/rules/pbir.py`)

Implements spec §5.3 R1: in every `*.Report/definition.pbir`, `datasetReference.byPath.path` must be a relative path. Flag an absolute path (`^[A-Za-z]:`, `^\\`, `^/`) or an unexpected `byConnection`. PBIR files are stdlib `json` opened `encoding="utf-8-sig"` (Power BI writes a BOM). Locator is `"definition.pbir"` plus a JSON pointer to the offending node.

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\pbir.py` (the package stub created in M1.6 — replace its body so the `@register("R1")` decorator fires when `retail.rules` is imported and `from . import pbir` runs)
- Create (fixtures, real `.pbir` JSON):
  - `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\pbir\relative.Report\definition.pbir` (relative → pass)
  - `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\pbir\absolute.Report\definition.pbir` (absolute path → fail)
  - `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\pbir\byconn.Report\definition.pbir` (unexpected `byConnection` → fail)
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_pbir.py`

**Interfaces:**
- Consumes (from `src/retail/core.py`, verbatim): `Finding`, `Severity`, `RuleContext`. From `src/retail/registry.py`: `register`.
- Produces:
  - `@register("R1", "PBIR model reference must be relative")` `def check_pbir_relative_reference(ctx: RuleContext) -> Iterable[Finding]: ...`
  - helper `def _iter_pbir_files(ctx: RuleContext) -> list[str]:` — returns repo-relative POSIX paths in `ctx.tracked_files` ending `.Report/definition.pbir`.

The fixtures live under `tests/fixtures/` and are read directly by the unit test (not via `git ls-files`); the rule reads `ctx.repo_root / <tracked path>`.

- [ ] **Step M5.1.1: Create the passing fixture (relative path).**
  Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\pbir\relative.Report\definition.pbir` with this exact content (a real minimal PBIR `definition.pbir`, byPath relative):
  ```json
  {
    "version": "4.0",
    "datasetReference": {
      "byPath": {
        "path": "../relative.SemanticModel"
      }
    }
  }
  ```

- [ ] **Step M5.1.2: Create the failing fixture (absolute path).**
  Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\pbir\absolute.Report\definition.pbir`:
  ```json
  {
    "version": "4.0",
    "datasetReference": {
      "byPath": {
        "path": "C:\\Users\\user\\models\\sales.SemanticModel"
      }
    }
  }
  ```

- [ ] **Step M5.1.3: Create the failing fixture (unexpected byConnection).**
  Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\fixtures\pbir\byconn.Report\definition.pbir`:
  ```json
  {
    "version": "4.0",
    "datasetReference": {
      "byConnection": {
        "connectionString": "Data Source=powerbi://api.powerbi.com",
        "pbiServiceModelId": null
      }
    }
  }
  ```

- [ ] **Step M5.1.4: Write the failing test.**
  Create `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_pbir.py` with real pytest code. The fixtures are not tracked by the real repo git, so each test builds a `RuleContext` whose `repo_root` is the fixtures dir and `tracked_files` lists the one fixture under test (repo-relative POSIX):
  ```python
  from __future__ import annotations

  from pathlib import Path

  import pytest

  from retail.core import RuleContext, Severity
  from retail.rules.pbir import check_pbir_relative_reference

  FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"


  def _ctx(report_dir: str) -> RuleContext:
      return RuleContext(
          repo_root=FIXTURES,
          tracked_files=(f"{report_dir}/definition.pbir",),
      )


  @pytest.mark.unit
  def test_relative_path_passes() -> None:
      findings = list(check_pbir_relative_reference(_ctx("relative.Report")))
      assert findings == []


  @pytest.mark.unit
  def test_absolute_path_fails() -> None:
      findings = list(check_pbir_relative_reference(_ctx("absolute.Report")))
      assert len(findings) == 1
      f = findings[0]
      assert f.rule_id == "R1"
      assert f.severity is Severity.ERROR
      assert f.locator == "absolute.Report/definition.pbir#/datasetReference/byPath/path"
      assert "absolute" in f.message.lower()


  @pytest.mark.unit
  def test_byconnection_fails() -> None:
      findings = list(check_pbir_relative_reference(_ctx("byconn.Report")))
      assert len(findings) == 1
      f = findings[0]
      assert f.rule_id == "R1"
      assert f.severity is Severity.ERROR
      assert f.locator == "byconn.Report/definition.pbir#/datasetReference/byConnection"
      assert "byconnection" in f.message.lower()


  @pytest.mark.unit
  def test_no_pbir_files_is_silent() -> None:
      ctx = RuleContext(repo_root=FIXTURES, tracked_files=("warehouse/x.sql",))
      assert list(check_pbir_relative_reference(ctx)) == []
  ```

- [ ] **Step M5.1.5: Run the test to confirm it fails (module missing).**
  Command (from repo root):
  ```
  pytest -m unit tests/unit/test_pbir.py -v
  ```
  Expected: collection error / failure with `ImportError: cannot import name 'check_pbir_relative_reference' from 'retail.rules.pbir'` (the M1.6 stub module exists but does not yet define the rule).

- [ ] **Step M5.1.6: Write the minimal implementation.**
  Replace the M1.6 stub body of `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\src\retail\rules\pbir.py` with real code (it is a submodule of the `retail.rules` package, so the contract imports are `..core` / `..registry`). Absolute-path detection covers Windows drive (`C:\`), UNC/backslash root (`\\` and `\`), and POSIX root (`/`):
  ```python
  """PBIR/JSON rule R1 (relative model reference). Replaces the M1.6 stub."""

  from __future__ import annotations

  import json
  import re
  from typing import Any, Iterable

  from ..core import Finding, RuleContext, Severity
  from ..registry import register

  _ABSOLUTE = re.compile(r"^(?:[A-Za-z]:|\\|/)")


  def _iter_pbir_files(ctx: RuleContext) -> list[str]:
      return [p for p in ctx.tracked_files if p.endswith(".Report/definition.pbir")]


  @register("R1", "PBIR model reference must be relative")
  def check_pbir_relative_reference(ctx: RuleContext) -> Iterable[Finding]:
      findings: list[Finding] = []
      for rel in _iter_pbir_files(ctx):
          path = ctx.repo_root / rel
          with path.open(encoding="utf-8-sig") as fh:
              doc: Any = json.load(fh)
          ref = doc.get("datasetReference", {}) if isinstance(doc, dict) else {}
          if "byConnection" in ref:
              findings.append(
                  Finding(
                      rule_id="R1",
                      severity=Severity.ERROR,
                      message=(
                          "PBIR uses byConnection; a committed report must "
                          "reference its model byPath (relative)"
                      ),
                      locator=f"{rel}#/datasetReference/byConnection",
                  )
              )
              continue
          by_path = ref.get("byPath", {}) if isinstance(ref, dict) else {}
          model_path = by_path.get("path") if isinstance(by_path, dict) else None
          if isinstance(model_path, str) and _ABSOLUTE.match(model_path):
              findings.append(
                  Finding(
                      rule_id="R1",
                      severity=Severity.ERROR,
                      message=(
                          f"datasetReference.byPath.path is absolute "
                          f"({model_path!r}); must be relative"
                      ),
                      locator=f"{rel}#/datasetReference/byPath/path",
                  )
              )
      return findings
  ```

- [ ] **Step M5.1.7: Run the test to confirm it passes.**
  Command (from repo root):
  ```
  pytest -m unit tests/unit/test_pbir.py -v
  ```
  Expected: `4 passed` — `test_relative_path_passes`, `test_absolute_path_fails`, `test_byconnection_fails`, `test_no_pbir_files_is_silent` all PASS.

- [ ] **Step M5.1.8: Lint and format the new module and test.**
  Commands (from repo root):
  ```
  ruff format --check src/retail/rules/pbir.py tests/unit/test_pbir.py
  ruff check src/retail/rules/pbir.py tests/unit/test_pbir.py
  ```
  Expected: `ruff format` prints `1 file already formatted` style output with no diff; `ruff check` prints `All checks passed!`. If format reports a would-reformat, run `ruff format src/retail/rules/pbir.py tests/unit/test_pbir.py` and re-run the checks.

- [ ] **Step M5.1.9: Commit.**
  Command (from repo root):
  ```
  git add src/retail/rules/pbir.py tests/unit/test_pbir.py tests/fixtures/pbir/
  git commit -m "feat: add PBIR rule R1 (relative model reference) with fixtures"
  ```
  Expected: commit succeeds; `git show --stat HEAD` lists `src/retail/rules/pbir.py`, `tests/unit/test_pbir.py`, and the three `tests/fixtures/pbir/*.Report/definition.pbir` files.


---

## Milestone 6 — C-Seam (pre-commit + CI)

## Milestone 6 — C-seam (pre-commit + CI)

This milestone wires the `retail check` checker (the `retail` console script produced by M1, which exposes the `check` subcommand and exits non-zero iff any `Finding.severity is Severity.ERROR`) into two unattended runners: a local pre-commit hook and a GitHub Actions workflow. Both invoke the **exact** command `retail check`. A single smoke test asserts the CI workflow YAML parses and references `retail check`.

> Per repo `CLAUDE.md` YAGNI: this is the spec's milestone 6 (§9 step 6, "C-seam — pre-commit hook + CI workflow stub that run `retail check`"), so it is explicitly in scope and built here. Task (b) enumerates exactly five CI steps; nothing beyond them is added.

---

### Task M6.1: Add `pyyaml` to the `[dev]` extras

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\pyproject.toml`

**Interfaces:**
- Consumes: the `[project.optional-dependencies] dev = [...]` block authored in M1 (the package skeleton). This task appends one entry to it.
- Produces: `pyyaml>=6` importable as `import yaml` in the test/dev environment. Required because there is no stdlib YAML parser and Task M6.4's smoke test must assert the workflow YAML *parses*.

- [ ] **Step 1: Confirm the smoke test is absent (baseline).**
  Run:
  ```
  pytest -m unit tests/unit/test_cseam.py -v
  ```
  Expected fail (the test file does not exist yet):
  ```
  ERROR: file or directory not found: tests/unit/test_cseam.py
  ```
  This confirms a clean start. Now open `pyproject.toml` and locate the M1-authored block, which reads:
  ```toml
  [project.optional-dependencies]
  dev = [
      "pytest>=8",
      "pytest-cov>=5",
      "ruff>=0.6",
      "black>=24",
  ]
  ```

- [ ] **Step 2: Append `pyyaml>=6` to the `dev` extras.**
  Edit `pyproject.toml`, changing the block to:
  ```toml
  [project.optional-dependencies]
  dev = [
      "pytest>=8",
      "pytest-cov>=5",
      "ruff>=0.6",
      "black>=24",
      "pyyaml>=6",
  ]
  ```

- [ ] **Step 3: Reinstall dev extras and confirm `yaml` imports.**
  Run:
  ```
  pip install -e ".[dev]"
  python -c "import yaml; print('yaml', yaml.__version__)"
  ```
  Expected (version may differ; presence is what matters):
  ```
  yaml 6.0.2
  ```

- [ ] **Step 4: Commit the dependency.**
  ```
  git add pyproject.toml
  git commit -m "chore: add pyyaml to dev extras for CI-YAML smoke test"
  ```

---

### Task M6.2: Pre-commit local hook running `retail check`

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\.pre-commit-config.yaml`

**Interfaces:**
- Consumes: the `retail` console script (M1) — invoked as `retail check`. The hook passes no filenames (`pass_filenames: false`) because `retail check` builds its own `RuleContext` from `git ls-files` at the repo root.
- Produces: `.pre-commit-config.yaml` defining one `repo: local` hook with id `retail-check` that blocks the commit when `retail check` exits non-zero.

- [ ] **Step 1: Write the pre-commit config verbatim.**
  Create `.pre-commit-config.yaml` with exactly this content:
  ```yaml
  # Pre-commit gate for Retail Tower Power BI governance.
  # The single hook runs the in-repo `retail check` static checker; a non-zero
  # exit (any ERROR-severity Finding) blocks the commit.
  repos:
    - repo: local
      hooks:
        - id: retail-check
          name: retail check (Power BI governance)
          entry: retail check
          language: system
          pass_filenames: false
          always_run: true
  ```
  Notes (do not add to the file): `language: system` runs the already-installed `retail` console script — pre-commit does not manage the env, matching this repo's plain-Python tooling. `pass_filenames: false` + `always_run: true` make the hook run once per commit over the whole tracked tree, never per-file.

- [ ] **Step 2: Verify the config is valid YAML and references `retail check`.**
  Run:
  ```
  python -c "import yaml; d = yaml.safe_load(open('.pre-commit-config.yaml', encoding='utf-8')); print(d['repos'][0]['hooks'][0]['entry'])"
  ```
  Expected output:
  ```
  retail check
  ```

- [ ] **Step 3: Commit the hook config.**
  ```
  git add .pre-commit-config.yaml
  git commit -m "feat: add pre-commit hook running retail check"
  ```

---

### Task M6.3: GitHub Actions CI workflow running `retail check`

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\.github\workflows\ci.yml`

**Interfaces:**
- Consumes: the `retail` console script (M1) and the `[dev]` extras (now including `pyyaml` from Task M6.1). Runs the five steps mandated by task (b): `pip install -e ".[dev]"`, `ruff format --check src tests`, `ruff check src tests`, `pytest -m unit`, `retail check`.
- Produces: `.github/workflows/ci.yml` triggered on `push` and `pull_request`.

- [ ] **Step 1: Create the workflows directory.**
  Run:
  ```
  mkdir -p .github/workflows
  ```
  Expected: no output (directory created or already present).

- [ ] **Step 2: Write the CI workflow verbatim.**
  Create `.github/workflows/ci.yml` with exactly this content:
  ```yaml
  name: ci

  on:
    push:
    pull_request:

  jobs:
    check:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
          with:
            # Full history: `retail check` runs git-metadata rules (P2 scans the
            # commit-message BASE..HEAD range; C2/G1/G2 read git ls-files /
            # check-ignore). A shallow clone would make those mis-scan or error.
            fetch-depth: 0

        - uses: actions/setup-python@v5
          with:
            python-version: "3.13"

        - name: Install package
          run: pip install -e ".[dev]"

        - name: Ruff format check
          run: ruff format --check src tests

        - name: Ruff lint
          run: ruff check src tests

        - name: Unit tests
          run: pytest -m unit

        - name: Retail governance check
          run: retail check
  ```
  Notes (do not add to the file): the editable install target is quoted (`".[dev]"`) so the shell does not glob-expand `.[dev]`. The five `run:` steps are exactly task (b)'s enumerated commands, in order; no `pre-commit` step is added.

- [ ] **Step 3: Verify the workflow parses and references `retail check`.**
  Run:
  ```
  python -c "import yaml; t = open('.github/workflows/ci.yml', encoding='utf-8').read(); yaml.safe_load(t); print('parsed ok'); print('retail check' in t)"
  ```
  Expected output:
  ```
  parsed ok
  True
  ```

- [ ] **Step 4: Commit the workflow.**
  ```
  git add .github/workflows/ci.yml
  git commit -m "ci: add GitHub Actions workflow running ruff, pytest, and retail check"
  ```

---

### Task M6.4: Smoke test for the C-seam YAML

**Files:**
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_cseam.py`

**Interfaces:**
- Consumes: `pyyaml` (`import yaml`, Task M6.1); the committed `.github/workflows/ci.yml` (Task M6.3) and `.pre-commit-config.yaml` (Task M6.2), resolved relative to the repo root via `Path(__file__).parents[2]`.
- Produces: two `@pytest.mark.unit` tests asserting each YAML file parses and references `retail check`.

- [ ] **Step 1: Write the failing smoke test (REAL code).**
  Create `tests/unit/test_cseam.py` with exactly this content:
  ```python
  from __future__ import annotations

  from pathlib import Path

  import pytest
  import yaml

  # tests/unit/test_cseam.py -> parents[2] is the repo root.
  REPO_ROOT = Path(__file__).resolve().parents[2]
  CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
  PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"


  @pytest.mark.unit
  def test_ci_workflow_parses_and_references_retail_check() -> None:
      text = CI_WORKFLOW.read_text(encoding="utf-8")
      parsed = yaml.safe_load(text)  # raises if the YAML is invalid
      assert parsed is not None
      assert "retail check" in text


  @pytest.mark.unit
  def test_pre_commit_config_parses_and_references_retail_check() -> None:
      text = PRE_COMMIT.read_text(encoding="utf-8")
      parsed = yaml.safe_load(text)  # raises if the YAML is invalid
      assert parsed is not None
      assert "retail check" in text
  ```

- [ ] **Step 2: Run to fail (before the YAML files exist, if running this task first) / confirm pass once M6.2–M6.3 are committed.**
  If Tasks M6.2 and M6.3 are not yet done, run:
  ```
  pytest -m unit tests/unit/test_cseam.py -v
  ```
  Expected fail (files missing):
  ```
  FAILED tests/unit/test_cseam.py::test_ci_workflow_parses_and_references_retail_check - FileNotFoundError: ...ci.yml
  ```
  This proves the test actually checks for the files. (If M6.2/M6.3 are already committed, this step passes immediately — proceed to Step 3.)

- [ ] **Step 3: Run to pass.**
  With `.github/workflows/ci.yml` and `.pre-commit-config.yaml` present, run:
  ```
  pytest -m unit tests/unit/test_cseam.py -v
  ```
  Expected output (PASS):
  ```
  tests/unit/test_cseam.py::test_ci_workflow_parses_and_references_retail_check PASSED
  tests/unit/test_cseam.py::test_pre_commit_config_parses_and_references_retail_check PASSED
  ```

- [ ] **Step 4: Commit the smoke test.**
  ```
  git add tests/unit/test_cseam.py
  git commit -m "test: smoke-test C-seam YAML parses and references retail check"
  ```


---

## Milestone 7 — D-Seam (agent + retail-govern skill)

## Milestone 7 — D-seam (agent + skill, invoke-only)

> Documentation milestone. No `retail` package code is written here. The deliverables are (a) the rewritten `powerbi-analyst` agent prompt pointing at the checker + rule-id catalog instead of restating rules in marts-only prose, and (b) a new bounded `retail-govern` skill that teaches Claude to run `retail check`, read its findings, and map rule ids to fixes — reference/invoke only, no orchestration or self-heal. The "tests" are a single stdlib-only pytest that asserts both artifacts reference the `retail check` command and that the new skill's YAML frontmatter is well-formed. No PyYAML (not in the stack) — frontmatter is validated by hand-parsing the `---` block.

### Task M7.1: Reconcile the `powerbi-analyst` agent prompt to the checker + rule ids

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\.claude\agents\powerbi-analyst.md`
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dseam.py`
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dseam.py`

**Interfaces:**
- Consumes: the `retail check` CLI command name (produced by Milestone 1 runner / Milestone 6 C-seam); the static rule-id catalog in spec §5 (`docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`); the gold-only decision (spec §2 row 3, rule D8).
- Produces: a rewritten `powerbi-analyst.md` whose frontmatter and body reference `retail check` + the rule-id catalog, carry **no** marts-only claim, and route enforcement to the checker rather than prose. No Python symbols are produced.

Rationale: spec §13 routes "reconcile the `powerbi-analyst` agent prompt … point them at the rule ids" into this §9-step-7 D-seam. The current file (`powerbi-analyst.md:3,17,25,45`) preaches "read `marts` only (never `raw`)", which contradicts the gold-only checker (D8 flags `marts`/`raw`/`silver`/`bronze`). The edit must **replace** the marts-only prose, not append beside it.

- [ ] **Step 1: Write the failing test for the agent artifact.** Create `tests/unit/test_dseam.py` with a test asserting the agent file references the checker, names at least two rule ids, and no longer carries a marts-only claim. Use the repo root resolved from the test file location (the package is `src/retail/`, tests at `tests/unit/`, so repo root is `parents[2]`).

```python
# tests/unit/test_dseam.py
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT = REPO_ROOT / ".claude" / "agents" / "powerbi-analyst.md"


def _read(path: Path) -> str:
    # Power BI / editor files may carry a UTF-8 BOM; utf-8-sig strips it.
    return path.read_text(encoding="utf-8-sig")


@pytest.mark.unit
def test_agent_references_retail_check() -> None:
    text = _read(AGENT)
    assert "retail check" in text


@pytest.mark.unit
def test_agent_names_rule_ids() -> None:
    text = _read(AGENT)
    # The agent must point at concrete rule ids, not restate rules in prose.
    assert "D8" in text
    assert "C1" in text


@pytest.mark.unit
def test_agent_drops_marts_only_claim() -> None:
    text = _read(AGENT)
    lowered = text.lower()
    # Gold-only supersedes marts-only everywhere (spec §2 row 3, D8).
    assert "gold" in lowered
    assert "marts" not in lowered
```

- [ ] **Step 2: Run the agent tests to confirm they fail.** The unedited file still says "marts" and lacks `retail check`.

```
pytest -m unit tests/unit/test_dseam.py -v
```

Expected: `test_agent_references_retail_check` and `test_agent_drops_marts_only_claim` FAIL with `AssertionError` (`assert 'retail check' in text` and `assert 'marts' not in lowered`), `test_agent_names_rule_ids` FAILS with `AssertionError` (`assert 'D8' in text`). 3 failed.

- [ ] **Step 3: Rewrite `powerbi-analyst.md` to reference the checker and rule ids.** Replace the whole file. The frontmatter `description` drops "marts-based data models"; the body swaps the prose "Key principles / DAX guidance / Checklist" sections for a gold-only summary plus a rule-id table that points at `retail check` and spec §5 as the source of truth.

```markdown
---
name: powerbi-analyst
description: Power BI + DAX for the Retail Tower Analytics repo — PBIP semantic models, measures, gold-only data models, performance. Use for any DAX/PBIP work here.
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
model: opus
---

# Power BI Analyst Agent (Retail Tower Analytics)

Power BI specialist for THIS repo: PBIP semantic models, DAX measures, and reports
that read the DigitalOcean Postgres analytics DB. Tuned to the repo's conventions —
which are now **enforced by a checker**, not just described here.

## Repo context

```
Source:   DigitalOcean PostgreSQL — read the `gold` schema ONLY (never bronze/silver/raw/marts).
Format:   PBIP (plain-text TMDL/PBIR). PBIP is a PREVIEW feature in PB Desktop.
Connect:  via PARAMETERS (ANALYTICS_DB_* from .env) — never a baked-in connection string.
Layout:   powerbi/ is the only tool-specific folder. SQL lives in warehouse/.
```

## The rules are enforced — do not restate them, satisfy them

This repo ships a static governance checker. Before treating any DAX/PBIP/SQL work
as done, run it from the repo root:

```
retail check
```

`retail check` parses the committed TMDL/PBIR/SQL/git text and exits non-zero on any
`error`-severity violation (warnings are reported but do not fail). The authoritative
rule catalog — ids, what each parses, and the violation signal — is spec §5 in
`docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`. **Do not duplicate
the rules in prose here; point at the id and fix the violation the checker reports.**

The rule ids most relevant to this agent's work:

| Rule | What it enforces |
|------|------------------|
| D1   | Measure names are `PascalCase`. |
| D2   | Every measure block carries a `displayFolder`. |
| D3   | No duplicated measure logic (normalized-body hash collision). |
| D4   | `DIVIDE()` not `/` in measure expressions. |
| D5   | Explicit over implicit aggregation (`summarizeBy` — WARNING). |
| D6   | Single-direction relationships (no `bothDirections`). |
| D7   | Time-intelligence functions require a date-table marker. |
| D8   | Gold-only sourcing — model reads `gold`, never bronze/silver/raw/marts. |
| R1   | Report references its model by a relative path. |
| C1   | Connection args are parameters, not connection-string literals. |
| C2   | No committed secrets; `.env` gitignored. |

For the SQL ids (S1–S4b) and git-hygiene ids (G1–G5, P1, P2), see spec §5 and the
`retail-govern` skill, which maps each id to its fix.

## Human-judgment items the checker deliberately does NOT gate

These are real conventions with no parse signal — the checker stays silent so the gate
stays trustworthy (spec §7). Honor them yourself:

- **YAGNI / scope discipline** — no ETL/provisioning unless requested. `pipelines/load_bronze.py`
  is sanctioned ETL; do not add more without an explicit ask.
- **Don't hand-edit Desktop-owned files**; save through Desktop, then commit the text.
- **PBIP preview toggle** lives in Desktop app settings, not a committed file.

## Workflow

1. Make the DAX/PBIP/SQL change.
2. Run `retail check` from the repo root.
3. For each finding, read its rule id, open the `retail-govern` skill for the id→fix
   mapping, fix the violation, and re-run until clean.
```

- [ ] **Step 4: Run the agent tests to confirm they pass.**

```
pytest -m unit tests/unit/test_dseam.py -v
```

Expected: `test_agent_references_retail_check`, `test_agent_names_rule_ids`, `test_agent_drops_marts_only_claim` all PASS. 3 passed.

- [ ] **Step 5: Lint and commit.**

```
ruff check tests/unit/test_dseam.py && black --check tests/unit/test_dseam.py
git add .claude/agents/powerbi-analyst.md tests/unit/test_dseam.py
git commit -m "docs: point powerbi-analyst agent at retail check + rule ids (gold-only)"
```

Expected: `ruff` prints `All checks passed!`, `black` prints `1 file would be left unchanged.`, commit succeeds.

### Task M7.2: Author the bounded `retail-govern` skill

**Files:**
- Create: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\.claude\skills\retail-govern\SKILL.md`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dseam.py` (add skill assertions)
- Test: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\tests\unit\test_dseam.py`

**Interfaces:**
- Consumes: the `retail check` CLI command name (M1/M6); the rule-id catalog (spec §5); the `Finding` shape (`rule_id`, `severity`, `message`, `locator` — `src/retail/core.py`) so the skill can teach Claude how to read a finding line.
- Produces: a new `SKILL.md` with valid YAML frontmatter (`name: retail-govern`, a `description:`) and a body that maps rule id → meaning → fix location, explicitly **bounded to invoke-and-interpret** (no orchestration, no auto-fix). No Python symbols.

Bound (restated from the task and spec §9-step-7): the skill references/invokes the checker and its rule ids **only**. It must NOT orchestrate a build, run `pbi-cli`, or self-heal — those are deferred D work. The boundary is asserted in the body and is part of the deliverable's coherence.

- [ ] **Step 6: Add the failing skill tests.** Append to `tests/unit/test_dseam.py`. Frontmatter is validated stdlib-only (no PyYAML — not in the stack): open `utf-8-sig`, require a leading `---`, slice the block between the first two `---` fences, and assert the required keys appear in it.

```python
# --- appended to tests/unit/test_dseam.py ---

SKILL = REPO_ROOT / ".claude" / "skills" / "retail-govern" / "SKILL.md"


def _frontmatter(text: str) -> str:
    # Hand-parse the leading `---` fenced YAML block (stdlib-only; no PyYAML).
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "missing opening frontmatter fence"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    raise AssertionError("missing closing frontmatter fence")


@pytest.mark.unit
def test_skill_frontmatter_valid() -> None:
    fm = _frontmatter(_read(SKILL))
    assert "name: retail-govern" in fm
    assert "description:" in fm


@pytest.mark.unit
def test_skill_references_retail_check() -> None:
    text = _read(SKILL)
    assert "retail check" in text


@pytest.mark.unit
def test_skill_maps_rule_ids_to_fixes() -> None:
    text = _read(SKILL)
    # The skill's job is id -> fix mapping, so concrete ids must appear.
    assert "D8" in text
    assert "C2" in text


@pytest.mark.unit
def test_skill_is_bounded_invoke_only() -> None:
    lowered = _read(SKILL).lower()
    # Bounded scope must be stated in the deliverable, not just honored.
    assert "does not" in lowered
    assert "orchestrat" in lowered  # matches "orchestrate" / "orchestration"
```

- [ ] **Step 7: Run the skill tests to confirm they fail.** The skill file does not exist yet.

```
pytest -m unit tests/unit/test_dseam.py -v
```

Expected: the four new tests ERROR/FAIL — `_read(SKILL)` raises `FileNotFoundError` (no `.claude/skills/retail-govern/SKILL.md`). The three M7.1 tests still PASS.

- [ ] **Step 8: Author `SKILL.md`.** Create `.claude/skills/retail-govern/SKILL.md` with valid frontmatter and a bounded body.

```markdown
---
name: retail-govern
description: >-
  Run the Retail Tower governance checker and interpret its findings. Use when
  someone asks to check, validate, or gate Power BI / DAX / TMDL / PBIR / SQL
  work in the Retail_Tower_analytics repo, when `retail check` reports a rule
  violation, or when you need to know what a rule id (D8, C2, S2, G1, …) means
  and where to fix it. Invoke-and-interpret only: this skill does NOT build
  models, run pbi-cli, or auto-fix — it runs the checker and maps ids to fixes.
---

# retail-govern

Retail Tower's conventions are enforced by a static checker, `retail check`. This
skill teaches you to **run it, read its findings, and map each rule id to the file
and fix it points at**. The authoritative catalog is spec §5 in
`docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`.

## Scope boundary (read this first)

This skill is **invoke-and-interpret only**. It does **not** orchestrate a Power BI
build, does **not** call `pbi-cli` or Power BI Desktop, and does **not** auto-fix or
self-heal violations. Those are deferred D-layer work (spec §9). Here you run the
checker, explain a finding, and tell the user (or the `powerbi-analyst` agent) the
single place to change — then stop.

## Run the checker

From the repo root:

```
retail check
```

It parses the committed TMDL / PBIR / SQL / git text — **no Power BI Desktop, no
`pbi-cli`, no network** — and exits non-zero if any `error`-severity finding exists.
`warning` and `info` findings are printed but do not fail the build (`S4b` and `D5`
are warnings; `G2` emits an `info` "no PBIP project present" when the repo has no
model yet).

## Read a finding

Each finding carries four fields: `rule_id`, `severity` (`error` / `warning` /
`info`), a one-line `message`, and a `locator`. The locator is the **most specific**
pointer available — `path:line` for an in-file violation, otherwise a file path, git
ref, or commit SHA (the git-metadata rules have no natural line number). Start at the
locator; the rule id tells you which fix below applies.

## Rule id → meaning → where to fix

| Rule | Means | Fix at |
|------|-------|--------|
| S1   | Non-snake_case SQL identifier. | Rename the identifier in `warehouse/**/*.sql`. |
| S2   | Stale `raw`/`marts` schema token (only in schema position). | Rename the schema to `bronze`/`silver`/`gold` in the SQL. |
| S3   | View missing `vw_` prefix. | Rename the `CREATE VIEW` object. |
| S4a  | Migration filename / numbering broken. | Rename to `^\d{4}_.+\.sql$`; make numbering contiguous + unique. |
| S4b  | Bare `CREATE`/`ALTER` (WARNING). | Use a guarded form (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`). |
| D1   | Measure not `PascalCase`. | Rename the measure in its `.tmdl`. |
| D2   | Measure missing `displayFolder`. | Add a `displayFolder` to the measure block. |
| D3   | Duplicated measure logic. | Replace the inlined body with a `[Name]` reference. |
| D4   | `/` in a measure. | Replace with `DIVIDE(num, den)`. |
| D5   | Implicit aggregation (WARNING). | Set `summarizeBy: none` or annotate the intentional exception. |
| D6   | Bidirectional relationship. | Set `crossFilteringBehavior: singleDirection` in `relationships.tmdl`, or justify the many-to-many. |
| D7   | Time-intelligence used without a date-table marker. | Mark a date table in the model. |
| D8   | Model sources a non-`gold` schema. | Repoint the partition/expression `Schema=`/`FROM` to `gold`. |
| R1   | Report model reference is absolute / `byConnection`. | Make `datasetReference.byPath.path` relative in `definition.pbir`. |
| C1   | Connection-string literal in a source. | Replace the server/database arg with a parameter identifier. |
| C2   | Committed secret / `.env` not ignored. | Remove the secret, gitignore `.env`, rotate the credential. |
| G1   | `.gitignore` missing a required entry. | Add `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`, `.env`; never ignore `definition/`. |
| G2   | A `definition/` artifact is untracked, or a cache file is tracked. | `git add` the definition; stop tracking `.pbi/localSettings.json` / `cache.abf`. |
| G3   | UTF-8 BOM in a committed text file. | Re-save the `.tmdl`/`.pbir`/`.json`/`.pbism` as UTF-8 without BOM. |
| G4   | `.gitattributes` EOL entry missing. | Add the required glob→eol mapping (TMDL/PBIR/JSON=CRLF; SQL/MD/PY=LF). |
| G5   | Repo-relative path > 200 chars. | Shorten the PBIP project/table name. |
| P1   | PBIP outside `powerbi/`, or SQL outside `warehouse/`. | Move the file to the right folder. |
| P2   | Commit subject off-convention. | Reword to `^(feat|fix|refactor|docs|chore): .+`. |

## What to do after interpreting

Report the failing ids, their locators, and the one fix each needs. Hand DAX/PBIP
fixes to the `powerbi-analyst` agent; SQL fixes belong in `warehouse/`. Then **stop** —
re-running `retail check` to confirm green is the user's (or agent's) next call, not an
automated loop this skill performs.
```

- [ ] **Step 9: Run the full D-seam test file to confirm everything passes.**

```
pytest -m unit tests/unit/test_dseam.py -v
```

Expected: all seven tests PASS (`test_agent_references_retail_check`, `test_agent_names_rule_ids`, `test_agent_drops_marts_only_claim`, `test_skill_frontmatter_valid`, `test_skill_references_retail_check`, `test_skill_maps_rule_ids_to_fixes`, `test_skill_is_bounded_invoke_only`). 7 passed.

- [ ] **Step 10: Lint and commit.**

```
ruff check tests/unit/test_dseam.py && black --check tests/unit/test_dseam.py
git add .claude/skills/retail-govern/SKILL.md tests/unit/test_dseam.py
git commit -m "docs: add bounded retail-govern skill mapping rule ids to fixes"
```

Expected: `ruff` prints `All checks passed!`, `black` prints `1 file would be left unchanged.`, commit succeeds.


---

## Milestone 8 — Doc Reconciliation (marts→gold)

### Task M8.1: Reconcile stale `marts`/`raw` schema references in docs to `gold`/`bronze`

This milestone applies the verified `marts → gold` (and `raw → bronze`) edits from spec §12 so the repo's own committed docs stop tripping the schema-token rules (S2 medallion schemas, D8 gold-only sourcing) when `retail check` runs against the repo. There is no new Python in this milestone — the deliverable is the doc reconciliation plus a green `retail check`. Each edit is an exact-string replacement already verified against the working tree; the `warehouse/README.md:15-17` legacy note is deliberately left untouched (it is the S2-whitelisted authoritative historical quote).

**Files:**
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\docs\conventions.md`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\docs\powerbi-connection.md`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\docs\data-dictionary.md`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\powerbi\README.md`
- Modify: `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\warehouse\README.md` — edit line ~22 only (the `marts/` folder bullet → `gold/`); KEEP lines 15-17 (legacy `raw`/`marts` note — S2-exempt historical quote) untouched
- Modify (rename): `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\warehouse\marts\.gitkeep` → `C:\Users\user\Documents\GitHub\Retail_Tower_analytics\warehouse\gold\.gitkeep`

**Interfaces:**
- Consumes: the `retail` CLI entrypoint from the runner milestone — invoked as `retail check` (alias for `python -m retail check`); exits non-zero iff any `Finding.severity is Severity.ERROR`. Specifically consumes the S2, D8, and C2 rules already registered via `registry.register(rule_id, title)`.
- Produces: no new code symbols. Produces a repository state where `retail check` emits zero S2, zero D8, and zero C2 `Finding`s.

- [ ] **Step 1: Snapshot the stale-reference baseline (run-to-confirm-stale)**
  Confirm the exact stale strings still exist before editing, so each `Edit` below matches uniquely. From repo root:
  ```
  git grep -n "marts" -- docs/conventions.md docs/powerbi-connection.md docs/data-dictionary.md powerbi/README.md
  ```
  Expected output (10 stale hits to fix; `warehouse/README.md` is intentionally excluded from this grep):
  ```
  docs/conventions.md:16:- Connect via parameters; read from `marts` only.
  docs/data-dictionary.md:13:## marts schema
  docs/powerbi-connection.md:21:| 3 | **DigitalOcean PostgreSQL** | The remote analytics database itself (`raw` → `marts`). The actual data source. | — it *is* the source. |
  docs/powerbi-connection.md:36:        └─ reads the  marts  schema only (never raw)
  docs/powerbi-connection.md:68:| `AnalyticsDbSchema`| Schema to read | `marts` |
  docs/powerbi-connection.md:81:2. Point the data source at PostgreSQL, selecting the **`marts`** schema. Apply
  powerbi/README.md:26:- Read from the `marts` schema, not `raw`.
  ```
  (Note: `data-dictionary.md:5 "## raw schema"` and the `powerbi-connection.md` "never raw" / "never bronze" lines are reached in the `raw` grep below — this grep covers the `marts` substring set.)

- [ ] **Step 2: Edit `docs/conventions.md:16` (`marts` → `gold`)**
  Apply the exact-string replacement:
  - old: `- Connect via parameters; read from \`marts\` only.`
  - new: `- Connect via parameters; read from \`gold\` only.`

- [ ] **Step 3: Edit `docs/powerbi-connection.md` table row :21 (`raw` → `marts` becomes `bronze` → `gold`)**
  Apply the exact-string replacement (note the literal `→` arrow and `—` em dash already in the line):
  - old: `| 3 | **DigitalOcean PostgreSQL** | The remote analytics database itself (\`raw\` → \`marts\`). The actual data source. | — it *is* the source. |`
  - new: `| 3 | **DigitalOcean PostgreSQL** | The remote analytics database itself (\`bronze\` → \`gold\`). The actual data source. | — it *is* the source. |`

- [ ] **Step 4: Edit `docs/powerbi-connection.md` ascii diagram :36 (`marts`/`raw` → `gold`/`bronze`)**
  Apply the exact-string replacement (the line begins with the box-drawing `└─` glyph; preserve the surrounding whitespace exactly):
  - old: `        └─ reads the  marts  schema only (never raw)`
  - new: `        └─ reads the  gold  schema only (never bronze)`

- [ ] **Step 5: Edit `docs/powerbi-connection.md` parameter table :68 (`marts` → `gold`)**
  Apply the exact-string replacement:
  - old: `| \`AnalyticsDbSchema\`| Schema to read | \`marts\` |`
  - new: `| \`AnalyticsDbSchema\`| Schema to read | \`gold\` |`

- [ ] **Step 6: Edit `docs/powerbi-connection.md` flow step :81 (`marts` → `gold`)**
  Apply the exact-string replacement (preserve the trailing `Apply`):
  - old: `2. Point the data source at PostgreSQL, selecting the **\`marts\`** schema. Apply`
  - new: `2. Point the data source at PostgreSQL, selecting the **\`gold\`** schema. Apply`

- [ ] **Step 7: Edit `docs/powerbi-connection.md` rules recap :134 (`marts`/`raw` → `gold`/`bronze`)**
  Apply the exact-string replacement:
  - old: `- Read \`marts\`, never \`raw\`.`
  - new: `- Read \`gold\`, never \`bronze\`.`

- [ ] **Step 8: Edit `docs/data-dictionary.md:5` section header (`raw` → `bronze`)**
  Apply the exact-string replacement:
  - old: `## raw schema`
  - new: `## bronze schema`

- [ ] **Step 9: Edit `docs/data-dictionary.md:13` section header (`marts` → `gold`)**
  Apply the exact-string replacement:
  - old: `## marts schema`
  - new: `## gold schema`

- [ ] **Step 9a: Edit `docs/data-dictionary.md:3` intro line (`marts` → `gold marts`)**
  Apply the exact-string replacement (preserve the trailing sentence):
  - old: `Catalog of analytics tables, columns, and marts. Grows as the warehouse fills in.`
  - new: `Catalog of analytics tables, columns, and gold marts. Grows as the warehouse fills in.`

- [ ] **Step 9b: Edit `docs/data-dictionary.md:15` empty-state line (`marts` → `gold marts`)**
  Apply the exact-string replacement (this is the placeholder under the `## gold schema` header from Step 9):
  - old: `_No marts yet._`
  - new: `_No gold marts yet._`

- [ ] **Step 9c: Edit `docs/powerbi-connection.md:82` transformations note (`warehouse/marts/` → `warehouse/gold/`)**
  Apply the exact-string replacement (the line continues the numbered step from :81; preserve the leading indentation and trailing `, not in Power Query.`):
  - old: `   transformations in \`warehouse/marts/\`, not in Power Query.`
  - new: `   transformations in \`warehouse/gold/\`, not in Power Query.`

- [ ] **Step 9d: Edit `warehouse/README.md:22` folder bullet (`marts/` → `gold/`) — KEEP lines 15-17 untouched**
  Apply the exact-string replacement to the `## Folders` bullet only. Do NOT touch the legacy note at lines 15-17.
  - old: `- \`marts/\` — reporting view/mart definitions for the \`gold\` schema (read by Power BI).`
  - new: `- \`gold/\` — reporting view/mart definitions for the \`gold\` schema (read by Power BI).`

- [ ] **Step 10: Edit `powerbi/README.md:26` rule (`marts`/`raw` → `gold`/`bronze`)**
  Apply the exact-string replacement:
  - old: `- Read from the \`marts\` schema, not \`raw\`.`
  - new: `- Read from the \`gold\` schema, not \`bronze\`.`

- [ ] **Step 11: Rename the `warehouse/marts/` placeholder directory to `warehouse/gold/` (git mv)**
  The gold-only model implies a `gold/` folder; `warehouse/marts/.gitkeep` is the only tracked file under `warehouse/marts/`. Use `git mv` so the rename is staged atomically. From repo root:
  ```
  git mv warehouse/marts/.gitkeep warehouse/gold/.gitkeep
  ```
  Then confirm the rename is staged:
  ```
  git status --porcelain warehouse/
  ```
  Expected output (a single rename plus the `README.md` folder-bullet edit from Step 9d):
  ```
   M warehouse/README.md
  R  warehouse/marts/.gitkeep -> warehouse/gold/.gitkeep
  ```

- [ ] **Step 12: Confirm the legacy note in `warehouse/README.md` is preserved (run-to-confirm-exempt)**
  `warehouse/README.md` is edited at line ~22 (Step 9d) but the S2-whitelisted historical quote at lines 15-17 must remain unchanged. Confirm the only change is the folder bullet and the legacy note is intact:
  ```
  git diff -U0 -- warehouse/README.md
  ```
  Expected: the diff shows ONLY the `- \`marts/\` …` → `- \`gold/\` …` folder-bullet line changing; no hunk touches lines 15-17.
  And reconfirm the exempt note text is still intact (unchanged):
  ```
  git grep -n "Earlier drafts of this repo used" -- warehouse/README.md
  ```
  Expected output:
  ```
  warehouse/README.md:15:> Earlier drafts of this repo used `raw`/`marts` (a 2-layer model). The deployed
  ```

- [ ] **Step 13: Confirm no stale schema references remain in the reconciled docs (run-to-verify)**
  Re-run the grep from Step 1 plus a `raw`-as-schema sweep over the same four files. From repo root:
  ```
  git grep -n -E "(^| )marts( |$|\`|/)" -- docs/conventions.md docs/powerbi-connection.md docs/data-dictionary.md powerbi/README.md
  ```
  Expected output (empty — every stale `marts` reference in these four files is now `gold`):
  ```
  ```

- [ ] **Step 14: Run `retail check` and assert green on S2/D8/C2 (run-to-pass)**
  Run the full governance gate against the repo. From repo root:
  ```
  retail check
  ```
  Expected: exit code 0 with no `S2`, `D8`, or `C2` findings printed. Confirm the exit code and that those three rule ids are absent:
  ```
  retail check; echo "exit=$?"
  ```
  Expected output ends with:
  ```
  exit=0
  ```
  And explicitly confirm none of the three rule ids appear in the output:
  ```
  retail check 2>&1 | grep -E "^(S2|D8|C2)\b"; echo "matches=$?"
  ```
  Expected output (grep finds nothing, so it exits 1):
  ```
  matches=1
  ```

- [ ] **Step 15: Commit the reconciliation**
  Stage the four edited docs and the directory rename, then commit. From repo root:
  ```
  git add docs/conventions.md docs/powerbi-connection.md docs/data-dictionary.md powerbi/README.md warehouse/README.md warehouse/gold/.gitkeep warehouse/marts/.gitkeep
  git commit -m "docs: reconcile marts/raw references to gold/bronze for S2/D8"
  ```
  Expected: commit succeeds; `git show --stat HEAD` lists the four edited `docs/` + `powerbi/README.md` docs, the `warehouse/README.md` folder-bullet edit, and the `warehouse/marts/.gitkeep -> warehouse/gold/.gitkeep` rename.


---

