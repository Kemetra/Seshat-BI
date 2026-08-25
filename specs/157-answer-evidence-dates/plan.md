# Answer Evidence Dates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disclose the evidence dates behind an answerability claim and their
calendar-day separation without turning age into a judgment or score.

**Architecture:** Add an explicit reporting-date coverage contract to source
profiles, then reference that fact plus two existing readiness fields from the
optional answerability summary. Documentation-contract tests preserve the exact
sources, GAP behavior, genericity, and no-judgment boundary.

**Tech Stack:** Markdown templates and filled profiles, pytest documentation
contracts, Python 3.13 test runner.

**Spec:** `specs/157-answer-evidence-dates/spec.md`

## Global Constraints

- Spec 156 must be accepted and its active fence closed before spec 157 is ratified.
- Named-owner ratification and one active fence are required before Task 1.
- Use committed evidence only; run no database query or live profile.
- `GAP` is a valid result and never changes a readiness status.
- Emit dates and arithmetic only: no age threshold, evaluation, badge, verdict,
  traffic light, aggregate number, or confidence/health score.
- Do not infer a coverage end from `Profiled on` or arbitrary evidence prose.
- The answerability summary remains optional and grants no approval.
- Every template behavior change follows RED -> verify RED -> GREEN -> regression.

## File Structure

```text
tests/unit/test_source_profile_evidence_dates.py
tests/unit/test_answer_evidence_dates.py
templates/source-profile.md
templates/handoff/answerability-summary.md
mappings/demo_sample_orders/source-profile.md
mappings/finance_gl_actuals/source-profile.md
mappings/finance_gl_budget/source-profile.md
mappings/retail_store_sales/source-profile.md
docs/readiness/publish-ready.md
specs/157-answer-evidence-dates/evidence/validation.md
docs/roadmap/{idea-backlog.md,shipped-ideas.yaml}
```

### Task 0: Ratify After Spec 156 and Move the Fence

**Files:**
- Modify: `specs/157-answer-evidence-dates/spec.md`
- Modify: `specs/157-answer-evidence-dates/tasks.md`
- Create: `specs/157-answer-evidence-dates/ratify-ledger.md`
- Modify: `.specify/feature.json`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Test: `tests/contract/test_dbt_documentation.py`

**Interfaces:**
- Active feature directory: `specs/157-answer-evidence-dates`
- Ratification record: named human, authority `owner`, date, and exact FR scope

- [ ] **Step 1: Prove the prerequisite**

Read spec 156's acceptance record and confirm feature JSON is null. Do not treat
unchecked task boxes or an implementation-only commit as acceptance.

- [ ] **Step 2: Record ratification and move one pointer**

Set feature JSON to:

```json
{"feature_directory": "specs/157-answer-evidence-dates"}
```

Record the named ratifier and replace both `SPECKIT` bodies with one reference to
`specs/157-answer-evidence-dates/plan.md`. Preserve spec 141 as paused.

- [ ] **Step 3: Verify the lifecycle contract**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\contract\test_dbt_documentation.py::test_active_spec_kit_markers_agree_and_resolve -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add .specify/feature.json AGENTS.md CLAUDE.md specs/157-answer-evidence-dates
git -c commit.gpgsign=false commit -m "docs: ratify answer evidence dates"
```

### Task 1: Make Source Coverage an Explicit Profile Fact

**Files:**
- Create: `tests/unit/test_source_profile_evidence_dates.py`
- Modify: `templates/source-profile.md`
- Modify: `mappings/demo_sample_orders/source-profile.md`
- Modify: `mappings/finance_gl_actuals/source-profile.md`
- Modify: `mappings/finance_gl_budget/source-profile.md`
- Modify: `mappings/retail_store_sales/source-profile.md`

**Interfaces:**
- Required labels: `Primary reporting-date column`, `Observed coverage start`,
  `Observed coverage end`, `Coverage evidence`.
- Each value is an ISO date, a column/citation, or an explicit `GAP` explanation.

- [ ] **Step 1: Write RED generic-template tests**

```python
def test_source_profile_template_declares_reporting_date_coverage() -> None:
    text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    for label in (
        "Primary reporting-date column",
        "Observed coverage start",
        "Observed coverage end",
        "Coverage evidence",
    ):
        assert f"| {label} |" in text
    assert "GAP --" in text
    assert "Profiled on" in text
    assert "must not substitute" in text
```

- [ ] **Step 2: Write RED filled-profile tests**

Assert these committed facts exactly:

```python
EXPECTED = {
    "demo_sample_orders": ("order_date", "2026-01-02", "2026-01-13"),
    "finance_gl_actuals": ("posting_date", "2024-01-01", "2025-12-31"),
    "retail_store_sales": ("transaction_date", "2022-01-01", "2025-01-18"),
}
```

For `finance_gl_budget`, require `GAP` for the primary date and both observed
dates, with evidence explaining that the committed source is fiscal-quarter grain
and has no calendar date column.

- [ ] **Step 3: Run RED**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_source_profile_evidence_dates.py -q
```

Expected: FAIL because none of the five profiles has the four-row block.

- [ ] **Step 4: Add the minimal profile blocks**

Add this generic shape near the profile metadata:

```markdown
## Reporting-date coverage

| Fact | Value |
|---|---|
| Primary reporting-date column | `<column | GAP -- source is non-temporal or not established>` |
| Observed coverage start | `<YYYY-MM-DD | GAP -- not established>` |
| Observed coverage end | `<YYYY-MM-DD | GAP -- not established>` |
| Coverage evidence | `<committed profile query/result citation | GAP -- not established>` |
```

Populate the three temporal profiles with the exact EXPECTED values. Cite the
committed demo CSV, the finance actuals Shape table, and the retail column profile.
Populate the budget profile with GAP only.

- [ ] **Step 5: Run GREEN and packaging regression**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_source_profile_evidence_dates.py tests\unit\test_stage1_scaffold.py tests\contract\test_release_artifact_contents.py -q
```

Expected: PASS; the packaged source-profile template remains present.

- [ ] **Step 6: Commit**

```powershell
git add templates/source-profile.md mappings/demo_sample_orders/source-profile.md mappings/finance_gl_actuals/source-profile.md mappings/finance_gl_budget/source-profile.md mappings/retail_store_sales/source-profile.md tests/unit/test_source_profile_evidence_dates.py
git -c commit.gpgsign=false commit -m "docs: record source coverage evidence dates"
```

### Task 2: Add the Three-Date Answerability Disclosure

**Files:**
- Create: `tests/unit/test_answer_evidence_dates.py`
- Modify: `templates/handoff/answerability-summary.md`

**Interfaces:**
- Exactly three facts: coverage end, readiness last checked, publish approval.
- Exact upstream keys: source profile `Observed coverage end`, readiness
  `last_checked_at`, latest shape-valid `approvals[stage=publish_ready].at`.
- GAP suppresses dependent arithmetic.

- [ ] **Step 1: Write RED structure and provenance tests**

Extract only the `## Evidence dates` section and assert its three rows and sources:

```python
def test_answerability_summary_names_three_authoritative_dates() -> None:
    section = _section("Evidence dates")
    assert section.count("| **") == 3
    assert "Observed coverage end" in section
    assert "last_checked_at" in section
    assert "stage: publish_ready" in section
    assert "GAP --" in section
    assert "calendar days" in section
```

- [ ] **Step 2: Write RED no-judgment tests**

```python
@pytest.mark.parametrize(
    "token",
    ("fresh", "stale", "current", "outdated", "acceptable", "unacceptable", "confidence", "health score"),
)
def test_evidence_dates_section_has_no_age_judgment(token: str) -> None:
    assert token not in _section("Evidence dates").lower()
```

Also reject C086, concrete schema names, and concrete ISO dates in the section.

- [ ] **Step 3: Run RED**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_answer_evidence_dates.py -q
```

Expected: FAIL because the section is absent.

- [ ] **Step 4: Add the minimal disclosure**

Insert after the optional-companion notice:

```markdown
## Evidence dates

| Evidence fact | Measured date | Committed source |
|---|---|---|
| **Data coverage ends** | `<YYYY-MM-DD | GAP -- observed coverage end not established>` | `<mappings/<table>/source-profile.md>` -> `Observed coverage end` |
| **Readiness last checked** | `<YYYY-MM-DD | GAP -- last_checked_at absent or malformed>` | `<mappings/<table>/readiness-status.yaml>` -> `last_checked_at` |
| **Publish approval recorded** | `<YYYY-MM-DD | GAP -- no shape-valid publish_ready approval>` | `<mappings/<table>/readiness-status.yaml>` -> latest `approvals[]` entry with `stage: publish_ready` |

**Elapsed calendar time:** The readiness check is `<N>` calendar days after the
observed data coverage end; the publish approval is `<M>` calendar days after
that readiness check.

When a required date is a GAP, omit its dependent arithmetic and write:
`GAP -- cannot calculate <named difference> because <named date> is absent or malformed.`
```

Keep interpretive prohibitions outside the extracted section so the section
itself cannot accidentally emit one of the prohibited labels.

- [ ] **Step 5: Run GREEN**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_answer_evidence_dates.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add templates/handoff/answerability-summary.md tests/unit/test_answer_evidence_dates.py
git -c commit.gpgsign=false commit -m "docs: disclose answer evidence dates"
```

### Task 3: Route the Optional Disclosure from Publish Ready Guidance

**Files:**
- Modify: `tests/unit/test_answer_evidence_dates.py`
- Modify: `docs/readiness/publish-ready.md`

**Interfaces:**
- Guidance distinguishes data coverage, readiness audit, and publish approval.
- Guidance repeats that the companion is optional and non-gating.

- [ ] **Step 1: Add the RED route test**

```python
def test_publish_ready_routes_each_evidence_date_to_its_authority() -> None:
    text = PUBLISH_READY.read_text(encoding="utf-8")
    assert "Observed coverage end" in text
    assert "last_checked_at" in text
    assert "publish_ready" in text
    assert "optional" in text.lower()
    assert "does not change" in text.lower()
```

- [ ] **Step 2: Run RED**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_answer_evidence_dates.py::test_publish_ready_routes_each_evidence_date_to_its_authority -q
```

Expected: FAIL because the current guidance links the companion but does not define its sources.

- [ ] **Step 3: Add the smallest guidance section**

Document the three authorities, ISO-or-GAP rule, conditional arithmetic, and the
non-gating/no-judgment boundary beside the existing optional companion link.

- [ ] **Step 4: Run GREEN and focused regression**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_answer_evidence_dates.py tests\unit\test_source_profile_evidence_dates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add docs/readiness/publish-ready.md tests/unit/test_answer_evidence_dates.py
git -c commit.gpgsign=false commit -m "docs: route answer evidence authorities"
```

### Task 4: Acceptance, Tracker Reconciliation, and Fence Closure

**Files:**
- Create: `specs/157-answer-evidence-dates/evidence/validation.md`
- Modify: `specs/157-answer-evidence-dates/ratify-ledger.md`
- Modify: `specs/157-answer-evidence-dates/tasks.md`
- Modify: `docs/roadmap/idea-backlog.md`
- Modify: `docs/roadmap/shipped-ideas.yaml`
- Modify: `.specify/feature.json`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run focused and repository gates**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\unit\test_source_profile_evidence_dates.py tests\unit\test_answer_evidence_dates.py tests\unit\test_stage1_scaffold.py tests\contract\test_release_artifact_contents.py tests\contract\test_dbt_documentation.py -q
C:\Users\user\miniforge3\python.exe -m pytest -m unit -q
C:\Users\user\miniforge3\python.exe -m seshat.cli check
git -c safe.directory=C:/Users/user/Documents/GitHub/Seshat-BI diff --check
```

Record commands, exit codes, pass counts, and environmental limitations in evidence.

- [ ] **Step 2: Reconcile the c35 state**

Add c35 to `shipped-ideas.yaml` with its implementation commit SHA. Update only
the backlog's current-status note so all eight ADOPT candidates are settled;
preserve the historical panel body.

- [ ] **Step 3: Close the active spec**

Mark T001-T005 complete after evidence exists. Set feature JSON to null and both
`SPECKIT` bodies to `No active Spec Kit implementation plan.` Leave spec 141
paused unless the owner separately directs resumption.

- [ ] **Step 4: Verify closure and commit**

```powershell
C:\Users\user\miniforge3\python.exe -m pytest tests\contract\test_dbt_documentation.py::test_active_spec_kit_markers_agree_and_resolve -q
git add specs/157-answer-evidence-dates docs/roadmap/shipped-ideas.yaml docs/roadmap/idea-backlog.md .specify/feature.json AGENTS.md CLAUDE.md
git -c commit.gpgsign=false commit -m "docs: accept answer evidence dates"
```
