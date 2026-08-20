# Target-Scoped Post-Write Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make post-write validation blame only the write that caused a finding, run the binding and value validators FR-013 requires, and record every validator that did not run together with the reason it did not.

**Architecture:** Split validator *selection* (pure, no I/O) from *judgment* (runs the validators). Gap 3 is solved by diffing `semantic-check` findings against a baseline captured before the mutation, so pre-existing findings are reported but never blocking. Gap 1 pairs reports to the mutated model by reading `definition.pbir`. Gap 2 runs `value-check` only when a contract pins a value and a DSN resolves, degrading loudly otherwise.

**Tech Stack:** Python 3.13, pytest (`-m unit`), ruff, stdlib `subprocess`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-20-target-scoped-validation-design.md`

## Global Constraints

- **Branch stacking:** this work sits on `661-target-scoped-validation`, which is rebased onto `663-git-read-and-ignored-scope` (PR #672). **#672 must merge first.** Do not rebase onto `main` while #672 is open.
- **Authority:** nothing in this slice may grant an approval, move a readiness stage to `pass`, or write `approvals[]`. Evidence stays derived-only.
- **The closed vocabulary:** the five-value outcome set (`materialized`, `blocked`, `deferred`, `failed`, `not_started`) MUST NOT grow. A degraded check is a `checks_skipped` entry, never a new outcome token.
- **`_target_was_examined` is untouched.** No task may change its logic. It is the proof that the authorized artifact was really examined.
- **Redaction is two layers, always in this order:** `redact()` (DSN/URI components), then `scrub_secret_shaped()`. `redact()` alone leaks a bare tenant GUID.
- **No secret in output:** no DSN, tenant GUID, or user path may reach evidence, stdout, or a blocker string.
- **Vacuous-pass guards stay:** `ValidationOutcome.passed` requires non-empty `artifacts_examined`; a `failed` outcome requires non-empty `rollback_guidance`.
- **Commits:** `git -c commit.gpgsign=false commit --no-gpg-sign` (1Password signing wall). Verify `git rev-parse --abbrev-ref HEAD` before **every** commit — a stash/worktree round-trip silently returns HEAD to `main`.
- **Test command:** `PYTHONPATH=src python -m pytest <path> -q -p no:cacheprovider --no-cov`.

## File Structure

| File | Responsibility |
|------|----------------|
| `src/seshat/pbi_mcp_adapter/validation_plan.py` | **new** — pure validator selection: report pairing, value-pinning detection, skip reasons. No subprocess, no git. |
| `src/seshat/pbi_mcp_adapter/validation.py` | modified — `checks_skipped` field, `PBIMCP-VAL-04`, baseline capture/diff, binding + value legs |
| `src/seshat/pbi_mcp_adapter/orchestrate.py` | modified — capture the semantic baseline next to the existing `before = _snapshot(root)`; carry `checks_skipped` into the report |
| `src/seshat/pbi_mcp_adapter/evidence.py` | modified — carry `checks_skipped` into the record |
| `specs/149-pbi-mcp-write-adapter/spec.md` | modified — FR-013 correction + FR-013a/b/c |
| `docs/integrations/pbi-mcp-adapter.md` | modified — document the validator set and degraded reporting |
| `tests/unit/test_pbi_mcp_validation_plan.py` | **new** — selection tests (pure, fast, no subprocess) |
| `tests/unit/test_pbi_mcp_validation.py` | modified — baseline diff, blockers, skips |

`validation_plan.py` is a new file rather than more code in `validation.py` because selection is pure and must be testable without spawning a validator; `validation.py` is already 346 lines and CodeScene scores it at the ceiling — keeping it there would push it toward the ~800-line gate.

---

### Task 1: Record a skipped check with its reason

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/validation.py:59-108` (`ValidationOutcome`)
- Test: `tests/unit/test_pbi_mcp_validation.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `ValidationOutcome.checks_skipped: tuple[tuple[str, str], ...]` — pairs of `(check_name, reason)`, default `()`. `ValidationOutcome.passed` and `.blocking` semantics unchanged: a skip is neither a failure nor a blocker.

- [ ] **Step 1: Write the failing test**

```python
def test_a_skipped_check_is_recorded_with_its_reason() -> None:
    """Absence is never a pass: a check that did not run says so, and why."""
    outcome = validation.ValidationOutcome(
        checks_run=("seshat semantic-check --require-inputs",),
        artifacts_examined=("Target.SemanticModel/definition/sales.tmdl",),
        failed=(),
        rollback_guidance=(),
        blockers=(),
        checks_skipped=(("value-check", "[PENDING LIVE PROFILE] no DSN resolved"),),
    )

    assert outcome.passed is True, "a recorded skip is not a failure"
    assert outcome.blocking is False, "a recorded skip does not block"
    assert outcome.checks_skipped == (
        ("value-check", "[PENDING LIVE PROFILE] no DSN resolved"),
    )


def test_a_skip_must_carry_a_reason() -> None:
    """A skip with no reason is indistinguishable from a check nobody ran."""
    with pytest.raises(validation.ValidationInvalid):
        validation.ValidationOutcome(
            checks_run=("seshat semantic-check --require-inputs",),
            artifacts_examined=("x.tmdl",),
            failed=(),
            rollback_guidance=(),
            blockers=(),
            checks_skipped=(("value-check", ""),),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py -q -p no:cacheprovider --no-cov -k "skipped_check_is_recorded or skip_must_carry"`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'checks_skipped'`

- [ ] **Step 3: Write minimal implementation**

In `validation.py`, add the field to `ValidationOutcome` (after `blockers`, so existing positional callers are unaffected) and one guard:

```python
    checks_skipped: tuple[tuple[str, str], ...] = ()

    @property
    def _skip_without_a_reason(self) -> bool:
        """A skip nobody explained reads exactly like a check nobody ran."""
        return any(not reason for _check, reason in self.checks_skipped)
```

Then in `__post_init__`, after the existing two guards:

```python
        if self._skip_without_a_reason:
            raise ValidationInvalid(
                "a skipped check must name why it was skipped; an unexplained "
                "skip is indistinguishable from a check that never ran"
            )
```

Leave `passed` and `blocking` untouched — a skip is deliberately neither.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py -q -p no:cacheprovider --no-cov`
Expected: PASS, and every pre-existing test in the file still passes (the new field is defaulted).

- [ ] **Step 5: Commit**

```bash
git rev-parse --abbrev-ref HEAD   # must be 661-target-scoped-validation
git add src/seshat/pbi_mcp_adapter/validation.py tests/unit/test_pbi_mcp_validation.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "feat: record a skipped validator with its reason (#661)"
```

---

### Task 2: Parse semantic-check findings into a comparable set

**Files:**
- Create: `src/seshat/pbi_mcp_adapter/validation_plan.py`
- Test: `tests/unit/test_pbi_mcp_validation_plan.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `finding_lines(stdout: str) -> frozenset[str]` — every rendered finding line in `stdout`, stripped, as a set. Non-finding chatter (the "no drift" summary, blank lines) is excluded.

Findings render as `[severity] rule_id message (locator)` via `runner._format`. Only lines beginning with `[` count.

- [ ] **Step 1: Write the failing test**

```python
"""Pure validator selection for the Power BI MCP write adapter (#661, #663)."""

from __future__ import annotations

import pytest

from seshat.pbi_mcp_adapter import validation_plan

pytestmark = pytest.mark.unit


def test_finding_lines_keeps_only_rendered_findings() -> None:
    """`[severity] rule message (locator)` is the shape; chatter is not a finding."""
    stdout = (
        "[error] L3 measure 'Unapproved': no approved metric contract "
        "(Other.SemanticModel/definition/other.tmdl:2)\n"
        "\n"
        "seshat semantic-check: no drift (0 findings).\n"
    )

    lines = validation_plan.finding_lines(stdout)

    assert lines == frozenset(
        {
            "[error] L3 measure 'Unapproved': no approved metric contract "
            "(Other.SemanticModel/definition/other.tmdl:2)"
        }
    )


def test_finding_lines_of_a_clean_run_is_empty() -> None:
    """No findings must be an empty set, never a set holding the summary line."""
    assert validation_plan.finding_lines("seshat semantic-check: no drift (0 findings).\n") == frozenset()


def test_finding_lines_tolerates_no_output() -> None:
    """A validator that printed nothing yields no findings, not a crash."""
    assert validation_plan.finding_lines("") == frozenset()
    assert validation_plan.finding_lines(None) == frozenset()  # type: ignore[arg-type]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation_plan.py -q -p no:cacheprovider --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.pbi_mcp_adapter.validation_plan'`

- [ ] **Step 3: Write minimal implementation**

Create `src/seshat/pbi_mcp_adapter/validation_plan.py`:

```python
"""Spec 149 -- which validators a write target implies, and why others did not run.

Pure selection: no subprocess, no git, no database. Kept separate from
``validation`` so the selection rules can be tested exhaustively without
spawning a validator, and so ``validation`` does not grow past the file-size
gate.
"""

from __future__ import annotations


def finding_lines(stdout: str | None) -> frozenset[str]:
    """Every rendered finding in ``stdout``, as a comparable set.

    ``runner._format`` renders a finding as ``[severity] rule_id message
    (locator)``, so a leading ``[`` is what distinguishes a finding from the
    command's own summary chatter. The whole line is the identity key: it
    carries severity, rule and locator, so two runs can be diffed without
    parsing any of them.
    """
    if not stdout:
        return frozenset()
    return frozenset(
        stripped
        for line in stdout.splitlines()
        if (stripped := line.strip()).startswith("[")
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation_plan.py -q -p no:cacheprovider --no-cov`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/validation_plan.py tests/unit/test_pbi_mcp_validation_plan.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "feat: parse semantic-check findings into a comparable set (#663)"
```

---

### Task 3: Block only on findings this write introduced

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/validation.py:34-52` (blocker ids), `:238-274` (`_outcome_for`), `:277-346` (`validate_semantic_model`)
- Test: `tests/unit/test_pbi_mcp_validation.py`

**Interfaces:**
- Consumes: `validation_plan.finding_lines` (Task 2); `ValidationOutcome.checks_skipped` (Task 1).
- Produces:
  - `BLOCKER_BASELINE_UNAVAILABLE = "PBIMCP-VAL-04"`
  - `semantic_baseline(repo_root: Path, *, runner: object = None) -> frozenset[str] | None` — the pre-mutation finding set, or `None` when the baseline could not be obtained.
  - `validate_semantic_model(...)` gains a keyword-only `baseline: frozenset[str] | None = None`. Passing `None` means "no baseline was captured" and is a blocker, NOT an empty baseline.

- [ ] **Step 1: Write the failing test**

```python
_PRE_EXISTING = (
    "[error] L3 measure 'Unapproved': no approved metric contract "
    "(Other.SemanticModel/definition/other.tmdl:2)"
)
_NEW = (
    "[error] L3 measure 'Broken': no approved metric contract "
    "(Target.SemanticModel/definition/sales.tmdl:4)"
)


def _runner_printing(text: str, returncode: int):
    def invoke(_root, _args):
        return subprocess.CompletedProcess(args=["x"], returncode=returncode, stdout=text, stderr="")

    return invoke


def test_a_pre_existing_finding_does_not_block_the_write(tmp_path: Path) -> None:
    """The #663 gap-3 defect: an error in an UNTOUCHED model blocked a good write
    and offered rollback guidance that could not fix it."""
    target = tmp_path / "Target.SemanticModel" / "definition"
    target.mkdir(parents=True)
    (target / "sales.tmdl").write_text("table Sales\n", encoding="utf-8")

    outcome = validation.validate_semantic_model(
        tmp_path,
        target_path="Target.SemanticModel/definition/sales.tmdl",
        baseline=frozenset({_PRE_EXISTING}),
        runner=_runner_printing(_PRE_EXISTING + "\n", 1),
        examined=lambda _root, _artifact: True,
    )

    assert outcome.blocking is False, f"a pre-existing finding blocked: {outcome.failed}"
    assert outcome.rollback_guidance == (), "offered rollback for someone else's error"


def test_a_finding_this_write_introduced_does_block(tmp_path: Path) -> None:
    """The check must still work: a NEW finding blocks and carries rollback."""
    target = tmp_path / "Target.SemanticModel" / "definition"
    target.mkdir(parents=True)
    (target / "sales.tmdl").write_text("table Sales\n", encoding="utf-8")

    outcome = validation.validate_semantic_model(
        tmp_path,
        target_path="Target.SemanticModel/definition/sales.tmdl",
        baseline=frozenset({_PRE_EXISTING}),
        runner=_runner_printing(f"{_PRE_EXISTING}\n{_NEW}\n", 1),
        examined=lambda _root, _artifact: True,
    )

    assert outcome.blocking is True
    assert any(_NEW in item for item in outcome.failed)
    assert not any(_PRE_EXISTING in item for item in outcome.failed), (
        "a pre-existing finding was reported as this write's failure"
    )
    assert outcome.rollback_guidance, "a failure must carry rollback guidance"


def test_an_unobtainable_baseline_blocks(tmp_path: Path) -> None:
    """Fails CLOSED. An empty baseline would make every finding look new (noisy
    but safe); a silently-complete baseline would make every finding look
    pre-existing, hiding the exact regression this check exists to catch."""
    target = tmp_path / "Target.SemanticModel" / "definition"
    target.mkdir(parents=True)
    (target / "sales.tmdl").write_text("table Sales\n", encoding="utf-8")

    outcome = validation.validate_semantic_model(
        tmp_path,
        target_path="Target.SemanticModel/definition/sales.tmdl",
        baseline=None,
        runner=_runner_printing("", 0),
        examined=lambda _root, _artifact: True,
    )

    assert outcome.blocking is True
    assert validation.BLOCKER_BASELINE_UNAVAILABLE in outcome.blockers
    assert outcome.rollback_guidance, "a blocking outcome must carry rollback guidance"
```

Add `import subprocess` and `from pathlib import Path` to the test file if absent.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py -q -p no:cacheprovider --no-cov -k "pre_existing or introduced or unobtainable"`
Expected: FAIL — `TypeError: validate_semantic_model() got an unexpected keyword argument 'baseline'`

- [ ] **Step 3: Write minimal implementation**

In `validation.py`, add the blocker id beside the existing three:

```python
BLOCKER_BASELINE_UNAVAILABLE = "PBIMCP-VAL-04"
```

and its detail line in `BLOCKER_DETAIL`:

```python
    BLOCKER_BASELINE_UNAVAILABLE: (
        "the pre-write finding baseline could not be captured, so a finding "
        "cannot be attributed to this write; refusing rather than guessing"
    ),
```

Add the baseline capture helper:

```python
def semantic_baseline(
    repo_root: Path, *, runner: object = None
) -> frozenset[str] | None:
    """The finding set BEFORE the mutation, or None if it could not be taken.

    None is not an empty set. An empty baseline would make every finding look
    new; a baseline that silently captured everything would make every finding
    look pre-existing, hiding the regression this check exists to catch. So the
    two are kept distinguishable and None is treated as a blocker upstream.
    """
    from seshat.pbi_mcp_adapter.validation_plan import finding_lines

    root = Path(repo_root).resolve()
    invoke = runner if runner is not None else _run_validator
    try:
        completed = invoke(root, _semantic_argv(root))  # type: ignore[operator]
    except (subprocess.TimeoutExpired, OSError):
        return None
    return finding_lines(completed.stdout)
```

Extract the argv so both legs share one definition (replacing the inline tuple in `validate_semantic_model`):

```python
def _semantic_argv(root: Path) -> tuple[str, ...]:
    """The validator command. `sys.executable`, never a bare `python`: on the
    documented pipx install a bare `python` is absent or lacks Seshat."""
    return (
        sys.executable,
        "-m",
        "seshat.cli",
        "semantic-check",
        "--repo",
        str(root),
        "--require-inputs",
    )
```

Give `_ValidationRun` two more fields:

```python
    baseline: frozenset[str] | None = None
    stdout: str = ""
```

Rewrite `_outcome_for` so the returncode is judged against the baseline:

```python
def _outcome_for(returncode: int, run: _ValidationRun) -> ValidationOutcome:
    """Turn one finished validator run into a verdict.

    A non-zero exit is no longer sufficient to blame this write: the corpus is
    repo-wide, so an error in a model this write never touched exits non-zero
    too. Only findings absent from the baseline are attributable (#663 gap 3).
    """
    from seshat.pbi_mcp_adapter.validation_plan import finding_lines

    target_path, backup_ref = run.target_path, run.backup_ref
    checks_run, artifact = run.checks_run, run.artifact

    if run.baseline is None:
        return ValidationOutcome(
            checks_run=checks_run,
            artifacts_examined=(target_path,),
            failed=("the pre-write finding baseline was not captured",),
            rollback_guidance=rollback_guidance_for(target_path, backup_ref),
            blockers=(BLOCKER_BASELINE_UNAVAILABLE,),
        )

    regressions = tuple(sorted(finding_lines(run.stdout) - run.baseline))
    if regressions:
        return ValidationOutcome(
            checks_run=checks_run,
            artifacts_examined=(target_path,),
            failed=regressions,
            rollback_guidance=rollback_guidance_for(target_path, backup_ref),
            blockers=(BLOCKER_VALIDATION_FAILED,),
        )

    # A non-zero exit with no NEW finding is a pre-existing error elsewhere in
    # the corpus. Reported as a skip-with-reason rather than silently dropped,
    # and non-blocking: rolling this write back cannot fix it.
    pre_existing: tuple[tuple[str, str], ...] = ()
    if returncode != 0:
        pre_existing = (
            (
                "semantic-check",
                f"exit {returncode} from findings that predate this write; "
                "not attributable to it",
            ),
        )

    if not _target_was_examined(run.repo_root, artifact):
        return ValidationOutcome(
            checks_run=checks_run,
            artifacts_examined=(),
            failed=(
                "the validator did not examine the target: it is not a "
                "parseable semantic-model artifact after the write",
            ),
            rollback_guidance=rollback_guidance_for(target_path, backup_ref),
            blockers=(BLOCKER_READ_NOTHING,),
            checks_skipped=pre_existing,
        )
    return ValidationOutcome(
        checks_run=checks_run,
        artifacts_examined=(target_path,),
        failed=(),
        rollback_guidance=(),
        blockers=(),
        checks_skipped=pre_existing,
    )
```

In `validate_semantic_model`, add the two keyword-only parameters and thread them through. `examined` exists so a test can drive the baseline branches without building a discoverable TMDL corpus; it defaults to the real function, so production behaviour is unchanged:

```python
def validate_semantic_model(
    repo_root: Path,
    *,
    target_path: str,
    backup_ref: str | None = None,
    runner: object = None,
    baseline: frozenset[str] | None = None,
    examined: object = None,
) -> ValidationOutcome:
```

Replace the inline `args = (...)` with `args = _semantic_argv(root)`, and build the run with the new fields:

```python
    return _outcome_for(
        completed.returncode,
        _ValidationRun(
            root,
            artifact,
            target_path,
            backup_ref,
            checks_run,
            baseline,
            completed.stdout or "",
        ),
    )
```

To honour `examined`, change the single call inside `_outcome_for` to go through the run:

```python
    if not run.examined(run.repo_root, artifact):
```

adding `examined` to `_ValidationRun` with a default of `_target_was_examined`, and passing `examined or _target_was_examined` from `validate_semantic_model`. **Do not change `_target_was_examined` itself** — it stays the real proof; only its injection point moves.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py tests/unit/test_pbi_mcp_validation_plan.py -q -p no:cacheprovider --no-cov`
Expected: PASS. Some pre-existing tests in this file call `validate_semantic_model` without `baseline` and will now hit the `PBIMCP-VAL-04` branch — that is correct new behaviour, so update each to pass `baseline=frozenset()` where the test's intent is "a clean baseline", and add one test asserting the no-baseline default blocks.

- [ ] **Step 5: Prove the fail-open is closed**

Weaken only the `run.baseline is None` guard (make it `if False:`), run the three tests from Step 1, and confirm `test_an_unobtainable_baseline_blocks` goes RED. Restore and confirm GREEN. Use a `try/finally` with a `shutil.copy2` backup outside the repo — a previous slice's harness crashed mid-run and left a fix reverted under its own new docstring.

- [ ] **Step 6: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/validation.py tests/unit/test_pbi_mcp_validation.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "fix: blame only findings this write introduced (#663)"
```

---

### Task 4: Capture the baseline before the mutation

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/orchestrate.py:314` (beside `before = _snapshot(root)`), `:360-390` (the validation call and report)
- Test: `tests/unit/test_pbi_mcp_orchestrate.py`

**Interfaces:**
- Consumes: `validation.semantic_baseline` and the `baseline=` parameter (Task 3).
- Produces: no new public name. `WriteReport` gains `checks_skipped: tuple[tuple[str, str], ...] = ()`, mirroring its existing `checks_run`.

- [ ] **Step 1: Write the failing test**

```python
def test_a_pre_existing_finding_elsewhere_does_not_block_an_apply(
    ready_repo: Path,
) -> None:
    """End to end: the corpus is repo-wide, so an error in a model this apply
    never touched must not fail the apply nor recommend rolling it back."""
    other = ready_repo / "Other.SemanticModel" / "definition"
    other.mkdir(parents=True, exist_ok=True)
    (other / "other.tmdl").write_text(
        "table Other\n\tmeasure Unapproved = SUM(Other[X])\n", encoding="utf-8"
    )

    report = _apply(ready_repo)

    assert report.outcome == "materialized", f"blocked by: {report.blockers}"
    assert report.rollback_guidance == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_orchestrate.py -q -p no:cacheprovider --no-cov -k pre_existing_finding_elsewhere`
Expected: FAIL — the apply is `blocked`, because no baseline is passed so Task 3's `PBIMCP-VAL-04` branch fires.

- [ ] **Step 3: Write minimal implementation**

At the existing pre-mutation hook (`orchestrate.py:314`), capture the baseline next to the file snapshot:

```python
    before = _snapshot(root)
    # The finding baseline must be taken BEFORE the mutation: afterwards there
    # is no way to tell a finding this write introduced from one that was
    # already there (#663 gap 3).
    semantic_before = validation.semantic_baseline(root)
```

Pass it into the validation call:

```python
    outcome = validation.validate_semantic_model(
        root,
        target_path=authorized_path,
        backup_ref=request.backup_ref,
        baseline=semantic_before,
    )
```

Add `checks_skipped` to `WriteReport` (beside `checks_run`) and to both construction sites at `:374` and `:384`:

```python
        checks_skipped=outcome.checks_skipped,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_orchestrate.py -q -p no:cacheprovider --no-cov`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/orchestrate.py tests/unit/test_pbi_mcp_orchestrate.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "fix: capture the finding baseline before the mutation (#663)"
```

---

### Task 5: Pair reports to the mutated model

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/validation_plan.py`
- Test: `tests/unit/test_pbi_mcp_validation_plan.py`

**Interfaces:**
- Consumes: `finding_lines` (Task 2) — same module, no dependency.
- Produces: `paired_reports(repo_root: Path, model_dir: Path) -> tuple[tuple[Path, ...], tuple[tuple[str, str], ...]]` — `(paired, skipped)`. `paired` is report dirs whose `definition.pbir` names `model_dir`; `skipped` is `(check, reason)` pairs for reports whose pairing could not be read.

- [ ] **Step 1: Write the failing test**

```python
def test_a_report_naming_the_model_is_paired(tmp_path) -> None:
    """The link is READ from definition.pbir, never guessed from directory names."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    report = tmp_path / "Sales.Report"
    report.mkdir()
    (report / "definition.pbir").write_text(
        '{"datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}}',
        encoding="utf-8",
    )

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == (report,)
    assert skipped == ()


def test_a_report_naming_a_different_model_is_not_paired(tmp_path) -> None:
    """Scoping is the point: an unrelated report must not be validated."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    other = tmp_path / "Other.Report"
    other.mkdir()
    (other / "definition.pbir").write_text(
        '{"datasetReference": {"byPath": {"path": "../Other.SemanticModel"}}}',
        encoding="utf-8",
    )

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert skipped == ()


def test_an_unreadable_pbir_is_a_recorded_skip_not_a_pairing(tmp_path) -> None:
    """D3: unknown pairing is recorded with a reason, and does not block."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    broken = tmp_path / "Broken.Report"
    broken.mkdir()
    (broken / "definition.pbir").write_text("{not json", encoding="utf-8")

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert len(skipped) == 1
    check, reason = skipped[0]
    assert check == "pbir-validate-bindings"
    assert "Broken.Report" in reason
    assert "definition.pbir" in reason


def test_a_report_with_no_pbir_at_all_is_a_recorded_skip(tmp_path) -> None:
    """Absence is reported, never silently treated as 'not paired'."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    (tmp_path / "Bare.Report").mkdir()

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert len(skipped) == 1
    assert "Bare.Report" in skipped[0][1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation_plan.py -q -p no:cacheprovider --no-cov -k paired or pbir`
Expected: FAIL — `AttributeError: module 'seshat.pbi_mcp_adapter.validation_plan' has no attribute 'paired_reports'`

- [ ] **Step 3: Write minimal implementation**

Append to `validation_plan.py`:

```python
import json
from pathlib import Path

#: The binding validator's name, as it appears in ``checks_run`` / ``checks_skipped``.
BINDING_CHECK = "pbir-validate-bindings"


def _referenced_model(report_dir: Path) -> Path | None:
    """The model a report's ``definition.pbir`` points at, or None if unreadable.

    Read from the artifact rather than inferred from directory names: a report
    and its model need not share a stem, and guessing would either miss a real
    pairing or invent one.
    """
    pbir = report_dir / "definition.pbir"
    try:
        document = json.loads(pbir.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    reference = document.get("datasetReference")
    by_path = reference.get("byPath") if isinstance(reference, dict) else None
    path = by_path.get("path") if isinstance(by_path, dict) else None
    if not isinstance(path, str) or not path:
        return None
    return (report_dir / path).resolve()


def paired_reports(
    repo_root: Path, model_dir: Path
) -> tuple[tuple[Path, ...], tuple[tuple[str, str], ...]]:
    """Reports in scope for a write to ``model_dir``, plus reports we cannot place.

    A report is IN SCOPE when its ``definition.pbir`` names this model. A report
    whose pbir is missing or unreadable is neither paired nor ignored: it is
    returned as a recorded skip, because silently treating unknown pairing as
    "not paired" would hide a binding this write may have orphaned.
    """
    target = Path(model_dir).resolve()
    paired: list[Path] = []
    skipped: list[tuple[str, str]] = []
    for report_dir in sorted(Path(repo_root).glob("*.Report")):
        if not report_dir.is_dir():
            continue
        referenced = _referenced_model(report_dir)
        if referenced is None:
            skipped.append(
                (
                    BINDING_CHECK,
                    f"{report_dir.name}: definition.pbir is missing or unreadable, "
                    "so its model pairing is unknown",
                )
            )
            continue
        if referenced == target:
            paired.append(report_dir)
    return tuple(paired), tuple(skipped)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation_plan.py -q -p no:cacheprovider --no-cov`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/validation_plan.py tests/unit/test_pbi_mcp_validation_plan.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "feat: pair reports to the mutated model via definition.pbir (#661)"
```

---

### Task 6: Run binding validation on the paired reports

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/validation.py`
- Test: `tests/unit/test_pbi_mcp_validation.py`

**Interfaces:**
- Consumes: `validation_plan.paired_reports`, `validation_plan.BINDING_CHECK` (Task 5); `ValidationOutcome.checks_skipped` (Task 1).
- Produces: `validate_bindings_for(repo_root: Path, model_dir: Path, *, validator: object = None) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, str], ...]]` — `(checks_run, failures, skipped)`.

`pbir_validate_bindings.validate_bindings(report_dir=, model_dir=)` returns a `BindingValidationResult` NamedTuple with `status` in `{"pass", "warning", "blocked"}` and `unresolved` / `kind_mismatches` finding tuples. Only `status == "blocked"` is a failure; `"warning"` is recorded, not blocking.

- [ ] **Step 1: Write the failing test**

```python
class _FakeBindingResult:
    def __init__(self, status: str) -> None:
        self.status = status
        self.unresolved = (("Sales", "Amount"),) if status == "blocked" else ()
        self.kind_mismatches = ()


def test_a_blocked_binding_on_a_paired_report_is_a_failure(tmp_path: Path) -> None:
    """A measure rename can orphan a visual's binding; that must fail the write."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    report = tmp_path / "Sales.Report"
    report.mkdir()
    (report / "definition.pbir").write_text(
        '{"datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}}',
        encoding="utf-8",
    )

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=lambda **_kw: _FakeBindingResult("blocked")
    )

    assert checks_run == ("pbir-validate-bindings Sales.Report",)
    assert failures, "a blocked binding was not reported as a failure"
    assert skipped == ()


def test_a_passing_binding_is_run_and_reports_no_failure(tmp_path: Path) -> None:
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    report = tmp_path / "Sales.Report"
    report.mkdir()
    (report / "definition.pbir").write_text(
        '{"datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}}',
        encoding="utf-8",
    )

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=lambda **_kw: _FakeBindingResult("pass")
    )

    assert checks_run == ("pbir-validate-bindings Sales.Report",)
    assert failures == ()
    assert skipped == ()


def test_no_report_in_the_repo_is_a_recorded_skip(tmp_path: Path) -> None:
    """A model with no report is normal -- but 'no binding check ran' must be
    visible, not inferred from an empty checks_run."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=lambda **_kw: _FakeBindingResult("pass")
    )

    assert checks_run == ()
    assert failures == ()
    assert len(skipped) == 1
    assert skipped[0][0] == "pbir-validate-bindings"
    assert "no report" in skipped[0][1].lower()


def test_a_validator_that_raises_is_a_recorded_skip_not_a_pass(tmp_path: Path) -> None:
    """Fails CLOSED into a visible skip: a crashed validator never reads clean."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)
    report = tmp_path / "Sales.Report"
    report.mkdir()
    (report / "definition.pbir").write_text(
        '{"datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}}',
        encoding="utf-8",
    )

    def boom(**_kw):
        raise RuntimeError("validator exploded")

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=boom
    )

    assert checks_run == ()
    assert failures == ()
    assert len(skipped) == 1
    assert "Sales.Report" in skipped[0][1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py -q -p no:cacheprovider --no-cov -k binding`
Expected: FAIL — `AttributeError: module 'seshat.pbi_mcp_adapter.validation' has no attribute 'validate_bindings_for'`

- [ ] **Step 3: Write minimal implementation**

Append to `validation.py`:

```python
def validate_bindings_for(
    repo_root: Path,
    model_dir: Path,
    *,
    validator: object = None,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Validate every report bound to ``model_dir``. Returns (run, failures, skipped).

    Only ``status == "blocked"`` is a failure: a kind mismatch is the shipped
    validator's warning class, so promoting it here would block writes the
    report layer itself does not consider broken.

    A validator that raises becomes a recorded SKIP, never an implicit pass --
    a crashed check that reads clean is the fail-open this whole module exists
    to prevent.
    """
    from seshat.pbi_mcp_adapter.validation_plan import BINDING_CHECK, paired_reports

    paired, skipped_pairs = paired_reports(repo_root, model_dir)
    skipped = list(skipped_pairs)
    if not paired:
        skipped.append(
            (
                BINDING_CHECK,
                "no report in this repository is bound to the mutated model, so "
                "no binding check ran",
            )
        )
        return (), (), tuple(skipped)

    invoke = validator if validator is not None else _real_binding_validator()
    checks_run: list[str] = []
    failures: list[str] = []
    for report_dir in paired:
        try:
            result = invoke(report_dir=report_dir, model_dir=model_dir)  # type: ignore[operator]
        except Exception as exc:  # noqa: BLE001 - any validator error is a skip
            skipped.append(
                (BINDING_CHECK, f"{report_dir.name}: validator did not complete ({exc})")
            )
            continue
        checks_run.append(f"{BINDING_CHECK} {report_dir.name}")
        if getattr(result, "status", "") == "blocked":
            failures.append(
                f"{BINDING_CHECK} {report_dir.name}: "
                f"{len(result.unresolved)} unresolved binding(s)"
            )
    return tuple(checks_run), tuple(failures), tuple(skipped)


def _real_binding_validator() -> object:
    """The shipped validator, imported lazily so the stdlib-only chain stays clean."""
    from seshat.pbir_validate_bindings import validate_bindings

    return validate_bindings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py -q -p no:cacheprovider --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/validation.py tests/unit/test_pbi_mcp_validation.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "feat: validate bindings on reports bound to the mutated model (#661)"
```

---

### Task 7: Run value-check when a value is pinned and a DSN resolves

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/validation_plan.py`, `src/seshat/pbi_mcp_adapter/validation.py`
- Test: `tests/unit/test_pbi_mcp_validation_plan.py`, `tests/unit/test_pbi_mcp_validation.py`

**Interfaces:**
- Consumes: `BINDING_CHECK` pattern from Task 5.
- Produces:
  - `validation_plan.VALUE_CHECK = "value-check"`
  - `validation_plan.dsn_is_available(env: Mapping[str, str]) -> bool`
  - `validation.validate_value_for(repo_root: Path, *, env: Mapping[str, str], runner: object = None) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, str], ...]]` — same `(checks_run, failures, skipped)` shape as Task 6.

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_pbi_mcp_validation_plan.py`:

```python
def test_a_dsn_is_available_from_either_documented_variable() -> None:
    """Both documented forms count: DATABASE_URL and the ANALYTICS_DB_* set."""
    assert validation_plan.dsn_is_available({"DATABASE_URL": "postgresql://h/db"}) is True
    assert validation_plan.dsn_is_available({"ANALYTICS_DB_HOST": "h"}) is True
    assert validation_plan.dsn_is_available({}) is False
    assert validation_plan.dsn_is_available({"DATABASE_URL": ""}) is False
```

In `tests/unit/test_pbi_mcp_validation.py`:

```python
def test_no_dsn_is_a_loud_skip_never_a_pass(tmp_path: Path) -> None:
    """D2: 'no data leg' must never read as 'validated'."""
    checks_run, failures, skipped = validation.validate_value_for(tmp_path, env={})

    assert checks_run == ()
    assert failures == ()
    assert len(skipped) == 1
    check, reason = skipped[0]
    assert check == "value-check"
    assert "[PENDING LIVE PROFILE]" in reason


def test_a_resolvable_dsn_runs_value_check(tmp_path: Path) -> None:
    """With a data leg the check runs, and a non-zero exit is a real failure."""
    def runner(_root, _args):
        return subprocess.CompletedProcess(args=["x"], returncode=1, stdout="", stderr="")

    checks_run, failures, skipped = validation.validate_value_for(
        tmp_path, env={"DATABASE_URL": "postgresql://h/db"}, runner=runner
    )

    assert checks_run == ("seshat value-check",)
    assert failures, "a non-zero value-check exit was not reported"
    assert skipped == ()


def test_the_dsn_never_appears_in_a_skip_reason_or_failure(tmp_path: Path) -> None:
    """A reason string is an output surface: it carries no credential."""
    secret = "postgresql://user:hunter2@db.example.com:5432/prod"

    def runner(_root, _args):
        return subprocess.CompletedProcess(args=["x"], returncode=1, stdout="", stderr="")

    _run, failures, skipped = validation.validate_value_for(
        tmp_path, env={"DATABASE_URL": secret}, runner=runner
    )

    rendered = " ".join(list(failures) + [reason for _c, reason in skipped])
    assert "hunter2" not in rendered
    assert "db.example.com" not in rendered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation_plan.py tests/unit/test_pbi_mcp_validation.py -q -p no:cacheprovider --no-cov -k "dsn or value_check"`
Expected: FAIL — `AttributeError: ... has no attribute 'dsn_is_available'`

- [ ] **Step 3: Write minimal implementation**

In `validation_plan.py`:

```python
from collections.abc import Mapping

#: The value validator's name in ``checks_run`` / ``checks_skipped``.
VALUE_CHECK = "value-check"

#: The documented ways a data leg is configured (`docs/install`).
_DSN_KEYS = ("DATABASE_URL", "ANALYTICS_DB_HOST")


def dsn_is_available(env: Mapping[str, str]) -> bool:
    """Whether a data leg is configured. Never reads or returns the value itself."""
    return any(env.get(key) for key in _DSN_KEYS)
```

In `validation.py`:

```python
def validate_value_for(
    repo_root: Path,
    *,
    env: Mapping[str, str],
    runner: object = None,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, str], ...]]:
    """Recompute approved values live, or record loudly that we could not.

    No DSN is a SKIP WITH A REASON, never silence and never a pass (D2): the
    shipped `retail validate` posture is `[PENDING LIVE PROFILE]`, and "no data
    leg" must not read as "validated".

    No DSN value is ever interpolated into a reason or a failure -- those are
    output surfaces, and a reason string reaches evidence and stdout.
    """
    from seshat.pbi_mcp_adapter.validation_plan import VALUE_CHECK, dsn_is_available

    if not dsn_is_available(env):
        return (
            (),
            (),
            (
                (
                    VALUE_CHECK,
                    "[PENDING LIVE PROFILE] no data leg is configured, so approved "
                    "values were not recomputed after this write",
                ),
            ),
        )

    root = Path(repo_root).resolve()
    argv = (sys.executable, "-m", "seshat.cli", "value-check", "--repo", str(root))
    invoke = runner if runner is not None else _run_validator
    try:
        completed = invoke(root, argv)  # type: ignore[operator]
    except (subprocess.TimeoutExpired, OSError):
        return (
            (),
            (),
            ((VALUE_CHECK, "the value validator did not complete"),),
        )
    if completed.returncode != 0:
        return (
            (f"seshat {VALUE_CHECK}",),
            (f"seshat {VALUE_CHECK} exit {completed.returncode}",),
            (),
        )
    return ((f"seshat {VALUE_CHECK}",), (), ())
```

Add `from collections.abc import Mapping` to `validation.py`'s imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_validation.py tests/unit/test_pbi_mcp_validation_plan.py -q -p no:cacheprovider --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/validation.py src/seshat/pbi_mcp_adapter/validation_plan.py tests/unit/test_pbi_mcp_validation.py tests/unit/test_pbi_mcp_validation_plan.py
git -c commit.gpgsign=false commit --no-gpg-sign -m "feat: run value-check when a data leg resolves, degrade loudly otherwise (#661)"
```

---

### Task 8: Wire binding + value legs into the apply path and evidence

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/validation.py` (`validate_semantic_model` merges the three legs), `src/seshat/pbi_mcp_adapter/evidence.py`, `src/seshat/cli/commands/pbi_mcp.py`
- Test: `tests/unit/test_pbi_mcp_orchestrate.py`, `tests/unit/test_pbi_mcp_evidence.py`

**Interfaces:**
- Consumes: `validate_bindings_for` (Task 6), `validate_value_for` (Task 7), `ValidationOutcome.checks_skipped` (Task 1).
- Produces: `RunEvidence.checks_skipped: tuple[tuple[str, str], ...] = ()`, serialized in `to_payload()` as a list of `{"check": ..., "reason": ...}` objects.

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_pbi_mcp_evidence.py`:

```python
def test_a_skipped_check_reaches_the_record_with_its_reason(tmp_path: Path) -> None:
    """Evidence must show what was NOT verified, or a reader over-trusts it."""
    record = _record(
        checks_skipped=(("value-check", "[PENDING LIVE PROFILE] no data leg"),),
    )
    payload = json.loads(evidence.finalize(tmp_path, record).read_text("utf-8"))

    assert payload["checks_skipped"] == [
        {"check": "value-check", "reason": "[PENDING LIVE PROFILE] no data leg"}
    ]


def test_a_skip_reason_is_redacted_like_every_other_string(tmp_path: Path) -> None:
    """A reason is an output surface: both redaction layers apply."""
    record = _record(
        mutation_attempted=True,
        checks_skipped=(
            ("value-check", "host=db.example.com password=hunter2 unreachable"),
        ),
    )
    text = evidence.finalize(tmp_path, record).read_text("utf-8")

    assert "hunter2" not in text
    assert "db.example.com" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_evidence.py -q -p no:cacheprovider --no-cov -k skip`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'checks_skipped'`

- [ ] **Step 3: Write minimal implementation**

In `evidence.py`, add the field to `RunEvidence` (after `rollback_guidance`):

```python
    checks_skipped: tuple[tuple[str, str], ...] = field(default_factory=tuple)
```

and in `to_payload()`, after `rollback_guidance`:

```python
            "checks_skipped": [
                {"check": redact(check), "reason": redact(reason)}
                for check, reason in self.checks_skipped
            ],
```

`_payload_strings` walks only top-level strings and lists of strings, so nested dicts would escape the pre-JSON scan. Extend it to descend one level into dicts inside a list:

```python
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str):
                    found.append((f"{key}[{index}]", item))
                elif isinstance(item, dict):
                    found.extend(
                        (f"{key}[{index}].{sub_key}", sub_value)
                        for sub_key, sub_value in item.items()
                        if isinstance(sub_value, str)
                    )
```

`_redact_payload`'s inner `scrub` already recurses into lists; add a `dict` branch so the post-mutation path scrubs these too:

```python
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
```

In `validation.py`, merge the three legs at the end of `validate_semantic_model`, replacing the bare `return _outcome_for(...)`:

```python
    semantic = _outcome_for(
        completed.returncode,
        _ValidationRun(
            root, artifact, target_path, backup_ref, checks_run,
            baseline, completed.stdout or "", examined or _target_was_examined,
        ),
    )
    if semantic.blocking:
        # A blocking semantic result is terminal: running further validators
        # against an artifact already known bad adds noise, not information.
        return semantic

    model_dir = _model_dir_for(artifact)
    bind_run, bind_failed, bind_skipped = validate_bindings_for(root, model_dir)
    value_run, value_failed, value_skipped = validate_value_for(root, env=os.environ)

    failed = (*semantic.failed, *bind_failed, *value_failed)
    return ValidationOutcome(
        checks_run=(*semantic.checks_run, *bind_run, *value_run),
        artifacts_examined=semantic.artifacts_examined,
        failed=failed,
        rollback_guidance=(
            rollback_guidance_for(target_path, backup_ref) if failed else ()
        ),
        blockers=(BLOCKER_VALIDATION_FAILED,) if failed else (),
        checks_skipped=(*semantic.checks_skipped, *bind_skipped, *value_skipped),
    )


def _model_dir_for(artifact: Path) -> Path:
    """The ``*.SemanticModel`` directory containing ``artifact``.

    The target may be the model folder itself or a file inside it, so walk up
    to the ``.SemanticModel`` ancestor; fall back to the artifact's own
    directory when there is none, which simply pairs no reports.
    """
    for candidate in (artifact, *artifact.parents):
        if candidate.name.endswith(".SemanticModel"):
            return candidate
    return artifact if artifact.is_dir() else artifact.parent
```

Add `import os` to `validation.py`.

In `orchestrate.py`, pass `checks_skipped` into the evidence record where the terminal record is built, and in `cli/commands/pbi_mcp.py` add to `_write_leg_payload`:

```python
        "checks_skipped": [
            {"check": clean(check), "reason": clean(reason)}
            for check, reason in getattr(report, "checks_skipped", ())
        ],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_evidence.py tests/unit/test_pbi_mcp_validation.py tests/unit/test_pbi_mcp_orchestrate.py tests/unit/test_pbi_mcp_cli_contract.py -q -p no:cacheprovider --no-cov`
Expected: PASS

- [ ] **Step 5: Prove the nested redaction is real**

Run `test_a_skip_reason_is_redacted_like_every_other_string`, then revert only the `_payload_strings` dict branch and confirm it goes RED. Restore, confirm GREEN. `try/finally` with a durable backup.

- [ ] **Step 6: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add src/seshat/pbi_mcp_adapter/ src/seshat/cli/commands/pbi_mcp.py tests/unit/
git -c commit.gpgsign=false commit --no-gpg-sign -m "feat: carry binding, value and skip results into evidence (#661)"
```

---

### Task 9: Correct FR-013 and document the validator set

**Files:**
- Modify: `specs/149-pbi-mcp-write-adapter/spec.md` (the FR-013 entry), `docs/integrations/pbi-mcp-adapter.md`
- Test: none (documentation); `seshat check` and `seshat semantic-check` are the gates.

**Interfaces:**
- Consumes: the blocker id and behaviour from Tasks 3, 6, 7.
- Produces: nothing consumed by code.

- [ ] **Step 1: Correct FR-013 in `specs/149-pbi-mcp-write-adapter/spec.md`**

Replace the FR-013 entry with:

```markdown
- **FR-013**: After a mutation the adapter MUST validate the touched artifact with
  `seshat semantic-check --require-inputs` (the semantic-model family — NOT the
  `seshat check` R-family, which is report-layer only and would examine zero bytes
  of a TMDL write); with binding validation for every report whose
  `definition.pbir` names the mutated model; and with `seshat value-check` where a
  metric contract pins an expected value and a data leg resolves.
- **FR-013a**: Post-write semantic validation MUST block only on findings this
  write introduced, measured against a baseline captured before the mutation.
  Pre-existing findings are reported and are NOT blocking: rolling this write back
  cannot fix an error in a model it never touched.
- **FR-013b**: A baseline that could not be captured MUST be a blocker
  (`PBIMCP-VAL-04`), never an empty baseline. An empty baseline makes every finding
  look new; a silently-complete one makes every finding look pre-existing, hiding
  the regression the check exists to catch.
- **FR-013c**: Every validator that did not run MUST be recorded with the reason it
  did not run. Absence of a check is never a pass.
```

- [ ] **Step 2: Document the behaviour in `docs/integrations/pbi-mcp-adapter.md`**

Add, after the existing evidence paragraph:

```markdown
### What post-write validation checks

| Validator | Runs when | On failure |
|-----------|-----------|------------|
| `semantic-check --require-inputs` | always | blocks, with rollback guidance — but only for findings this write introduced |
| `pbir-validate-bindings` | a report's `definition.pbir` names the mutated model | blocks when a binding is unresolved |
| `value-check` | a contract pins an expected value **and** a data leg resolves | blocks on a value outside tolerance |

Findings that already existed before the write are reported as
`checks_skipped` with the reason, and do not block: rolling the write back cannot
fix an error in a model it never touched. A validator that could not run — no data
leg, an unreadable `definition.pbir`, a crashed validator — is likewise recorded
with its reason. **An empty `checks_skipped` means nothing was skipped, not that
nothing was checked.**
```

- [ ] **Step 3: Run the governance gates**

Run: `PYTHONPATH=src python -m seshat.cli check` then `PYTHONPATH=src python -m seshat.cli semantic-check`
Expected: no NEW findings versus the pre-task run (the pre-existing RS1 `last_checked_at` warning on `mappings/retail_store_sales/readiness-status.yaml` is unrelated and stays).

- [ ] **Step 4: Commit**

```bash
git rev-parse --abbrev-ref HEAD
git add specs/149-pbi-mcp-write-adapter/spec.md docs/integrations/pbi-mcp-adapter.md
git -c commit.gpgsign=false commit --no-gpg-sign -m "docs: correct FR-013 and document the validator set (#661)"
```

---

### Task 10: Full gate set and PR

**Files:** none modified — verification only.

**Interfaces:** none.

- [ ] **Step 1: Format and lint**

Run: `ruff format --check src/ tests/` then `ruff check src/ tests/`
Expected: both clean. If format fails, run `ruff format src/ tests/` and re-commit.

- [ ] **Step 2: Full unit suite**

Run: `PYTHONPATH=src python -m pytest -m unit -q -p no:cacheprovider --no-cov`
Expected: all pass. Baseline before this plan: 6117 passed, 31 skipped.

- [ ] **Step 3: Confirm no SyntaxWarning was introduced**

Run: `PYTHONPATH=src python -W error::SyntaxWarning -c "import py_compile, pathlib; [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('src/seshat/pbi_mcp_adapter').glob('*.py')]"`
Expected: no output, exit 0. (A previous slice shipped a stray `\`` in a docstring.)

- [ ] **Step 4: CodeScene the changed files**

Run: `"$LOCALAPPDATA/codescene-cli/cs.exe" review src/seshat/pbi_mcp_adapter/validation.py` and the same for `validation_plan.py`, `orchestrate.py`, `evidence.py`.
Expected: no file scores below its value on the base branch. Compare by extracting the base version first:
`git show 663-git-read-and-ignored-scope:src/seshat/pbi_mcp_adapter/validation.py > /tmp/base.py && cs review /tmp/base.py`
Use `cs review`, not `cs delta` — `delta` needs a license token on this build and crashes in its telemetry parser without one.

- [ ] **Step 5: Confirm any remaining failures are pre-existing**

For any contract/integration failure, stash and re-run on the clean base branch to prove it is not from this work:
`git stash push -u -m verify && pytest <the failing tests> ; git stash pop`
**Then immediately re-check `git rev-parse --abbrev-ref HEAD`** — a stash round-trip has silently returned HEAD to `main` in this repo before, and two commits landed on the wrong branch as a result.

Known pre-existing failures on this base (do not attempt to fix): `test_statistical_package_contract.py::test_statistics_extras_are_exact_and_base_stays_pyyaml_only`, `test_python_release_artifacts.py::test_real_wheel_sdist_and_isolated_rebuild`, `test_studio_codex_real.py::test_a_real_turn_reaches_a_terminal_event`.

- [ ] **Step 6: Push and open the PR**

```bash
git push -u origin 661-target-scoped-validation
gh pr create --base main --head 661-target-scoped-validation \
  --title "fix: scope post-write validation to the write that caused a finding (#661, #663)" \
  --body-file <(cat <<'EOF'
Closes #661. Closes the remaining gap 3 of #663.

Implements `docs/superpowers/specs/2026-08-20-target-scoped-validation-design.md`.

**Stacked on #672** — do not merge before it.
EOF
)
```

The PR body must state the three decisions (baseline diff, degraded value-check, recorded skip on unreadable pbir), which of them were owner-chosen versus delegated, and the fail-open `PBIMCP-VAL-04` closes.

- [ ] **Step 7: Report to the owner**

Do NOT merge. Branch protection requires one human approving review, and an `--admin` bypass is blocked by the harness classifier. Report: check status, unresolved threads, and that #672 must merge first.

---

## Self-Review

**1. Spec coverage**

| Spec section | Task |
|---|---|
| D1 baseline diff | 2, 3, 4 |
| D2 degraded value-check | 7 |
| D3 recorded skip on unreadable pbir | 5 |
| `plan_validators` / selection split | 2, 5, 7 (`validation_plan.py`) |
| `checks_skipped` field + reason guard | 1 |
| `PBIMCP-VAL-04` fail-closed baseline | 3 |
| Gap 1 binding validation | 5, 6 |
| Gap 2 value-check | 7 |
| `_target_was_examined` untouched | 3 (injection point only), asserted in Task 3 Step 3 |
| Closed outcome vocabulary | no task adds a token; Task 1 keeps skips out of `passed`/`blocking` |
| FR-013 + a/b/c | 9 |
| Both redaction layers on new strings | 8 (Steps 3, 5) |
| Proof-by-weakening | 3 Step 5, 8 Step 5 |

The spec's `plan_validators` / `run_plan` pair is realized as `validation_plan`'s selection functions plus the merge block in Task 8 rather than as two literal functions — same separation, fewer indirection layers, and each piece is independently testable. No spec requirement is unimplemented.

**2. Placeholder scan** — no TBD/TODO; every code step carries real code; no "similar to Task N".

**3. Type consistency** — `checks_skipped` is `tuple[tuple[str, str], ...]` in `ValidationOutcome` (1), `RunEvidence` (8) and `WriteReport` (4). Both validator legs return the same `(checks_run, failures, skipped)` triple (6, 7). `finding_lines` returns `frozenset[str]`, matching the `baseline` parameter type (2, 3). `BINDING_CHECK` / `VALUE_CHECK` are defined once in `validation_plan` and imported (5, 7).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-20-target-scoped-validation.md`.
