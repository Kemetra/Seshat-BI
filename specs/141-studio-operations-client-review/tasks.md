# Tasks: Studio Operations and Client Review

**Feature**: `specs/141-studio-operations-client-review/` | **Plan**: [plan.md](./plan.md) |
**Spec**: [spec.md](./spec.md) | **Contract**:
[contracts/export-boundary.md](./contracts/export-boundary.md)

**Spec status**: `draft`. Phases 0 and 1 (research, design) are complete. **Every task
below is BLOCKED** until a named human ratifies this package and the sole active Spec Kit
fence points at this plan (FR-141-020). Specs 139 and 140 are accepted, so the first of
the three conditions is met.

**Progress**: 0 of 15 tasks. Nothing started.

TDD order: the failing test comes before the code. A task is done only when its test was
seen RED, then GREEN. Nothing is marked done that was not observed.

**Verified against the shipped tree** -- do not substitute guesses:

- `doctor.collect_findings(ctx) -> list[Finding]`; `Finding` is `rule_id`, `severity`,
  `message`, `locator` (`seshat/core.py:44`). `Severity` is only `error`/`warning`/`info`
  -- there is **no** six-state component vocabulary in the tree, so the mapping in Task A1
  is new code.
- `doctor.repair_hint(rule_id) -> str` and `doctor.group_by_rule(findings)` exist and
  should be reused.
- `studio/redaction.py` exposes `scrub_payload`, `redact_credentials`, `redact_paths`,
  `redact_for_boundary`.
- `studio/review_scope.review_for(scope=..., decisions=...)` refuses an absent scope.
- `decision_write.decisions_at_head(committed, rel_path)` reads HEAD.
- Test helpers to reuse, not reinvent: `tests/unit/_workbench_fixtures.py`
  (`studio_client`, `unauthenticated_client`, `git_workspace`, `store_file`) and
  `tests/unit/_studio_workspace_fixtures.py`.
- Web-touching test modules need `pytest.importorskip("fastapi")` before the import; CI's
  `unit` job installs no app extras.

Phase order is mandatory: **Phase A must be fully green before Phases B-D**, because every
later phase discloses through its primitives.

---

## Phase A -- Disclosure primitives (no UI)

### Task A1: Map a Finding to a component state

**Files:**
- Create: `src/seshat/studio/operations.py`
- Test: `tests/unit/test_studio_operations.py`

**Interfaces:**
- Consumes: `seshat.core.Finding`, `seshat.doctor.repair_hint`
- Produces: `COMPONENT_STATES: tuple[str, ...]`, `state_for(findings: list[Finding]) -> str`

- [ ] **Step 1: Write the failing test**

```python
from seshat.core import Finding, Severity
from seshat.studio import operations


def test_component_states_are_a_closed_set():
    assert operations.COMPONENT_STATES == (
        "missing",
        "misconfigured",
        "incompatible",
        "deferred",
        "failed",
        "healthy",
    )


def test_no_findings_means_healthy():
    assert operations.state_for([]) == "healthy"


def test_an_error_finding_means_failed():
    finding = Finding(
        rule_id="X1", severity=Severity.ERROR, message="broken", locator="a.py"
    )
    assert operations.state_for([finding]) == "failed"


def test_an_unrecognized_severity_fails_closed_to_failed():
    """FR-141-006: absence of evidence must never read as healthy."""

    class _Odd:
        value = "surprise"

    finding = Finding(
        rule_id="X1", severity=_Odd(), message="?", locator="a.py"
    )
    assert operations.state_for([finding]) == "failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.studio.operations'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Operations: component diagnostics and run history (spec 141).

Presentation over existing truth. `doctor.py` does the probing; this module maps its
findings into the component vocabulary spec 141 introduces. FR-141-004 forbids a second
probe SET, not a mapping layer -- and the mapping is new because `Finding.severity` is
only error/warning/info.
"""

from __future__ import annotations

from seshat.core import Finding, Severity

#: Closed vocabulary (FR-141-003). `deferred` is NOT a failure: it means a boundary
#: legitimately unavailable (no DSN, optional extra absent), and rendering it red would
#: train technicians to ignore red.
COMPONENT_STATES: tuple[str, ...] = (
    "missing",
    "misconfigured",
    "incompatible",
    "deferred",
    "failed",
    "healthy",
)


def state_for(findings: list[Finding]) -> str:
    """The component state implied by its findings.

    Fails CLOSED: an unrecognized severity yields `failed`, never `healthy`
    (FR-141-006). Absence of evidence is not evidence of health -- but an empty finding
    list is a genuine "nothing wrong", which is different from "could not read".
    """
    if not findings:
        return "healthy"
    severities = {getattr(f.severity, "value", f.severity) for f in findings}
    if severities - {Severity.WARNING.value, Severity.INFO.value}:
        return "failed"
    return "misconfigured"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations.py src/seshat/studio/operations.py
git commit -m "feat: map doctor findings to component states"
```

---

### Task A2: A deferred boundary is deferred, not failed

**Files:**
- Modify: `src/seshat/studio/operations.py`
- Test: `tests/unit/test_studio_operations.py`

- [ ] **Step 1: Write the failing test**

```python
def test_a_pending_live_finding_is_deferred_not_failed():
    """A missing DSN is a deferred boundary, not a defect."""
    finding = Finding(
        rule_id="LIVE1",
        severity=Severity.WARNING,
        message="[PENDING LIVE PROFILE] no DSN configured",
        locator="mappings/sales/readiness-status.yaml",
    )
    assert operations.state_for([finding]) == "deferred"


def test_a_real_warning_is_not_reported_as_deferred():
    """The inverse. Without it, `deferred` could swallow every warning and the test
    above would still pass."""
    finding = Finding(
        rule_id="W1",
        severity=Severity.WARNING,
        message="audit metadata is stale",
        locator="mappings/sales/readiness-status.yaml",
    )
    assert operations.state_for([finding]) == "misconfigured"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations.py -k deferred -v`
Expected: FAIL — the pending-live finding returns `misconfigured`

- [ ] **Step 3: Write minimal implementation**

```python
#: The marker the rest of Seshat already uses for "not verified against a live source".
PENDING_LIVE_MARKER = "[PENDING LIVE PROFILE]"


def _is_deferred(findings: list[Finding]) -> bool:
    return all(PENDING_LIVE_MARKER in f.message for f in findings)
```

and insert this fragment into the existing `state_for`, after the fail-closed branch and
before the final `return` (it is a fragment, not a standalone block -- the indentation is
the function body's):

```text
    if _is_deferred(findings):
        return "deferred"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations.py src/seshat/studio/operations.py
git commit -m "feat: treat a pending-live boundary as deferred, not failed"
```

---

### Task A3: The diagnostic carries traceable evidence and no score

**Files:**
- Modify: `src/seshat/studio/operations.py`
- Test: `tests/unit/test_studio_operations.py`

**Interfaces:**
- Produces: `ComponentDiagnostic` (frozen dataclass), `diagnose(component, findings) -> ComponentDiagnostic`

- [ ] **Step 1: Write the failing test**

```python
def test_a_diagnostic_traces_back_to_the_rules_that_produced_it():
    findings = [
        Finding(rule_id="A1", severity=Severity.ERROR, message="x", locator="a.py"),
        Finding(rule_id="B2", severity=Severity.ERROR, message="y", locator="b.py"),
    ]

    diagnostic = operations.diagnose("static_gate", findings)

    assert diagnostic.state == "failed"
    assert diagnostic.source_rule_ids == ("A1", "B2")
    assert diagnostic.evidence
    assert diagnostic.recovery_action


def test_a_diagnostic_has_no_aggregate_score_field():
    """FR-141-002 as a type constraint: the model cannot express a roll-up."""
    fields = {f.name for f in dataclasses.fields(operations.ComponentDiagnostic)}

    assert not fields & {"score", "health_index", "percent", "overall", "grade"}


def test_no_numeric_rollup_appears_in_the_payload():
    """Searches for a numeric roll-up rather than a field NAME -- an absence-assertion
    on a name goes green when the value ships under a different key."""
    findings = [Finding(rule_id="A1", severity=Severity.ERROR, message="x", locator="a")]

    payload = operations.diagnose("static_gate", findings).as_dict()

    numeric = [v for v in payload.values() if isinstance(v, (int, float))]
    assert numeric == [], f"unexpected numeric value in diagnostic payload: {numeric}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations.py -k diagnostic -v`
Expected: FAIL — `AttributeError: module has no attribute 'ComponentDiagnostic'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass

from seshat import doctor


@dataclass(frozen=True, slots=True)
class ComponentDiagnostic:
    """One component's state, with the findings that justify it.

    `source_rule_ids` exists so a displayed diagnosis is traceable to the rule that
    produced it. Without it, Operations could show a state no rule supports and nobody
    could tell. There is deliberately NO aggregate field (FR-141-002).
    """

    component: str
    state: str
    evidence: tuple[str, ...] = ()
    blocker: str | None = None
    recovery_action: str | None = None
    source_rule_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "component": self.component,
            "state": self.state,
            "evidence": list(self.evidence),
            "blocker": self.blocker,
            "recovery_action": self.recovery_action,
            "source_rule_ids": list(self.source_rule_ids),
        }


def diagnose(component: str, findings: list[Finding]) -> ComponentDiagnostic:
    """Map findings to a diagnostic, reusing doctor's own repair hints."""
    state = state_for(findings)
    return ComponentDiagnostic(
        component=component,
        state=state,
        evidence=tuple(f"{f.message} ({f.locator})" for f in findings),
        blocker=findings[0].message if findings else None,
        recovery_action=doctor.repair_hint(findings[0].rule_id) if findings else None,
        source_rule_ids=tuple(f.rule_id for f in findings),
    )
```

Add `import dataclasses` to the test module.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations.py src/seshat/studio/operations.py
git commit -m "feat: build traceable component diagnostics with no aggregate score"
```

---

### Task A4: The export scrubber takes an allowlist and has no bypass

**Files:**
- Create: `src/seshat/studio/exports.py`
- Test: `tests/unit/test_studio_exports.py`

**Interfaces:**
- Produces: `scrub_for_export(payload: dict, *, allowed: tuple[str, ...], workspace_root: Path) -> dict`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from seshat.studio import exports

#: Assembled from parts on purpose. A literal DSN in a committed file trips the repo's
#: own C2 secret scanner (`CONN_URI_RE`), and rightly so -- a scanner that recognised
#: "obviously fake" credentials would be one heuristic away from passing a real one.
#: `git_meta.py:547` builds its scheme the same way for the same reason.
_SCHEME = "postgres" + "ql://"
FAKE_DSN = _SCHEME + "u:p@h/db"


def test_only_allowlisted_fields_survive(tmp_path: Path):
    payload = {"metric": "net_sales", "dsn": FAKE_DSN, "note": "ok"}

    result = exports.scrub_for_export(
        payload, allowed=("metric", "note"), workspace_root=tmp_path
    )

    assert result == {"metric": "net_sales", "note": "ok"}


def test_a_field_added_upstream_is_absent_without_changing_export_code(tmp_path: Path):
    """O2: an allowlist fails CLOSED. A denylist would disclose this new field."""
    payload = {"metric": "net_sales", "secret_added_later": "sk-live-abcd1234"}

    result = exports.scrub_for_export(
        payload, allowed=("metric",), workspace_root=tmp_path
    )

    assert "secret_added_later" not in result


def test_an_allowlisted_value_is_still_scrubbed(tmp_path: Path):
    """Allowlisting a FIELD does not bless its CONTENT: both redaction layers run."""
    payload = {"note": f"connect via {FAKE_DSN} to check"}

    result = exports.scrub_for_export(
        payload, allowed=("note",), workspace_root=tmp_path
    )

    assert "postgresql://" not in result["note"]
    assert "u:p@h" not in result["note"]


def test_there_is_no_scrub_everything_except_entry_point():
    """The module must not offer a denylist-shaped convenience function."""
    names = [n for n in dir(exports) if not n.startswith("_")]

    assert not [n for n in names if "denylist" in n.lower() or "exclude" in n.lower()]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.studio.exports'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Export assembly and scrubbing (spec 141).

The disclosure boundary. Every artifact leaving Studio passes through here, which is why
this module stays small: the whole disclosure path should be auditable in one read.

`allowed` is a REQUIRED parameter with no default. There is deliberately no
"scrub everything except" entry point -- a denylist fails open on the field nobody
enumerated (FR-141-012).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from seshat.studio import redaction


def scrub_for_export(
    payload: dict[str, Any], *, allowed: tuple[str, ...], workspace_root: Path
) -> dict[str, Any]:
    """Keep only allowlisted fields, then scrub what remains.

    Two steps, both required. Allowlisting a FIELD does not bless its CONTENT: a note
    the analyst wrote may still contain a DSN, so the surviving values go through the
    shipped redaction layers (FR-141-008).
    """
    narrowed = {key: value for key, value in payload.items() if key in allowed}
    return redaction.scrub_payload(narrowed, workspace_root=workspace_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_exports.py src/seshat/studio/exports.py
git commit -m "feat: add the allowlist export scrubber"
```

**Phase A gate**: `pytest tests/unit/test_studio_operations.py tests/unit/test_studio_exports.py -v`
all green, plus `ruff format --check`, `ruff check`, `seshat check`. Phases B-D MUST NOT
start before this.

---

## Phase B -- Operations view (US1)

### Task B1: Report the seven components

**Files:**
- Modify: `src/seshat/studio/operations.py`
- Test: `tests/unit/test_studio_operations.py`

**Interfaces:**
- Produces: `COMPONENTS: tuple[str, ...]`, `report(repo_root: Path) -> tuple[ComponentDiagnostic, ...]`

- [ ] **Step 1: Write the failing test**

```python
def test_the_report_covers_every_named_component(tmp_path: Path):
    report = operations.report(tmp_path)

    assert {d.component for d in report} == set(operations.COMPONENTS)
    assert len(operations.COMPONENTS) == 7


def test_every_state_in_the_report_is_from_the_closed_set(tmp_path: Path):
    report = operations.report(tmp_path)

    for diagnostic in report:
        assert diagnostic.state in operations.COMPONENT_STATES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations.py -k report -v`
Expected: FAIL — `AttributeError: module has no attribute 'COMPONENTS'`

- [ ] **Step 3: Write minimal implementation**

```python
#: The seven surfaces US1 names. One diagnostic each, never a roll-up.
COMPONENTS: tuple[str, ...] = (
    "studio_process",
    "package_extras",
    "codex_adapter",
    "bundle_capability",
    "static_gate",
    "live_boundary",
    "frontend_assets",
)
```

with a `report()` that calls `diagnose()` per component, sourcing each component's
findings from `doctor.collect_findings` grouped by `doctor.group_by_rule`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations.py src/seshat/studio/operations.py
git commit -m "feat: report all seven Operations components"
```

---

### Task B2: A recovery action cannot execute without approval

**Files:**
- Create: `src/seshat/studio/operations_routes.py`
- Test: `tests/unit/test_studio_operations_routes.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _workbench_fixtures as fixtures  # noqa: E402

API = "/api/v1"


def test_a_recovery_action_is_refused_without_technical_approval(tmp_path: Path):
    """FR-141-005: a support surface that can fix things is a mutation surface."""
    client = fixtures.studio_client(tmp_path)

    response = client.post(f"{API}/operations/recover", json={"component": "static_gate"})

    assert response.status_code == 422, response.text
    assert "approval" in response.text.lower()


def test_the_operations_report_route_requires_a_session(tmp_path: Path):
    client = fixtures.unauthenticated_client(tmp_path)

    assert client.get(f"{API}/operations").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations_routes.py -v`
Expected: FAIL — 404, routes not registered

- [ ] **Step 3: Write minimal implementation**

Create `operations_routes.py` following `workbench_routes.py`: module-level async handlers
taking a frozen `Deps(app, problem, redact, snapshot, api_prefix)`, and a branch-free
`register(deps)`. The recover route returns `_problem(422, ...)` unconditionally until an
approved path exists — refusal is the default, not an afterthought.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations_routes.py src/seshat/studio/operations_routes.py src/seshat/studio/app.py
git commit -m "feat: expose Operations and refuse unapproved recovery"
```

---

### Task B3: The Operations payload is redacted and score-free

- [ ] **Step 1: Write the failing test**

```python
def test_the_operations_payload_is_redacted_and_has_no_rollup(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/operations")
    body = response.json()

    assert response.status_code == 200, response.text
    assert "postgresql://" not in response.text
    assert body["components"], "a positive assertion, so an empty payload cannot pass"
    assert "score" not in body and "health_index" not in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations_routes.py -k redacted -v`
Expected: FAIL until the route returns `_redact(...)` over the report

- [ ] **Step 3: Write minimal implementation**

Return `_redact({"components": [d.as_dict() for d in operations.report(root)]})`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations_routes.py src/seshat/studio/operations_routes.py
git commit -m "feat: redact the Operations payload and keep it score-free"
```

---

## Phase C -- Run history (US2)

### Task C1: A durable claim must cite committed state

**Files:**
- Modify: `src/seshat/studio/operations.py`
- Test: `tests/unit/test_studio_operations.py`

**Interfaces:**
- Produces: `GovernedRunSummary`, `summarize_run(...) -> GovernedRunSummary`

- [ ] **Step 1: Write the failing test**

```python
def test_a_run_without_a_committed_source_is_ephemeral():
    summary = operations.summarize_run(
        run_id="r1", requested="net of returns", committed_source=None
    )

    assert summary.durability == "ephemeral"


def test_a_run_with_a_committed_source_is_durable():
    """The paired positive case. Without it, `durability` could be hardcoded."""
    summary = operations.summarize_run(
        run_id="r1", requested="net of returns", committed_source="421c8f4d"
    )

    assert summary.durability == "durable"
    assert summary.committed_source == "421c8f4d"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations.py -k durab -v`
Expected: FAIL — `AttributeError: summarize_run`

- [ ] **Step 3: Write minimal implementation**

`GovernedRunSummary` per data-model.md, with `durability` derived from
`committed_source is not None` — derived, never passed in, so the two cannot disagree.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations.py src/seshat/studio/operations.py
git commit -m "feat: derive run durability from a committed citation"
```

---

### Task C2: A pending-commit decision reads as pending

- [ ] **Step 1: Write the failing test**

```python
def test_a_pending_commit_decision_is_not_reported_as_settled():
    """FR-141-021: spec 140's guard is on the WRITE side; this is the render side."""
    summary = operations.summarize_run(
        run_id="r1",
        requested="net of returns",
        committed_source=None,
        decision_state="pending_commit",
    )

    assert summary.decision_state == "pending_commit"
    assert summary.outcome != "approved"


def test_an_authoritative_decision_is_reported_as_such():
    summary = operations.summarize_run(
        run_id="r1",
        requested="net of returns",
        committed_source="421c8f4d",
        decision_state="authoritative",
    )

    assert summary.decision_state == "authoritative"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations.py -k pending_commit -v`
Expected: FAIL — `summarize_run` takes no `decision_state`

- [ ] **Step 3: Write minimal implementation**

Add `decision_state: str = "pending_commit"` to the summary and thread it through. Default
to the *unsettled* state so a caller that forgets cannot accidentally claim authority.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations.py src/seshat/studio/operations.py
git commit -m "feat: carry the pending-commit state into run history"
```

---

### Task C3: Ephemeral history does not survive a restart

- [ ] **Step 1: Write the failing test**

```python
def test_ephemeral_history_is_gone_after_a_restart(tmp_path: Path):
    first = fixtures.studio_client(tmp_path)
    first.post(f"{API}/proposals", json={"intent": "x", "target_artifact": "y"})
    before = first.get(f"{API}/operations/history").json()["runs"]
    assert before, "the fixture must produce at least one ephemeral run"

    second = fixtures.studio_client(tmp_path)  # a fresh app = a restart

    after = second.get(f"{API}/operations/history").json()["runs"]
    assert [r for r in after if r["durability"] == "ephemeral"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_operations_routes.py -k restart -v`
Expected: FAIL — 404 until the history route exists

- [ ] **Step 3: Write minimal implementation**

Serve history from the in-process `ThreadStore` for ephemeral runs and
`decisions_at_head` for durable ones. Ephemeral records live only in process state, so a
new app has none by construction rather than by cleanup.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_operations_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_operations_routes.py src/seshat/studio/operations_routes.py
git commit -m "feat: serve run history with ephemeral records held only in process"
```

---

## Phase D -- Client review, responses, support bundle

### Task D1: Only approved committed evidence enters the client view

- [ ] **Step 1: Write the failing test**

```python
def test_an_uncommitted_decision_does_not_enter_the_client_view(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = client.post(
        f"{API}/proposals",
        json={"intent": "net of returns", "target_artifact": ".seshat/semantic-decisions.yaml"},
    ).json()
    client.post(
        f"{API}/decisions/record",
        json={
            "signer": "Ahmed Shaaban (owner)",
            "declared_authority": "owner",
            "answer": proposal["allowed_answers"][0],
            "proposal_hash": proposal["proposal_hash"],
            "workspace_revision": proposal["workspace_revision"],
        },
    )

    draft = client.get(f"{API}/client-review?scope=.seshat/semantic-decisions.yaml").json()

    assert draft["decisions"] == [], "an uncommitted decision is not approved evidence"
    assert draft["pending_items"], "it must appear as PENDING, not vanish"


def test_a_committed_decision_does_enter_the_client_view(tmp_path: Path):
    """The paired positive case: without it, an always-empty view would pass."""
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = client.post(
        f"{API}/proposals",
        json={"intent": "net of returns", "target_artifact": ".seshat/semantic-decisions.yaml"},
    ).json()
    client.post(
        f"{API}/decisions/record",
        json={
            "signer": "Ahmed Shaaban (owner)",
            "declared_authority": "owner",
            "answer": proposal["allowed_answers"][0],
            "proposal_hash": proposal["proposal_hash"],
            "workspace_revision": proposal["workspace_revision"],
        },
    )
    workspace.commit_all("decision: recorded")

    draft = client.get(f"{API}/client-review?scope=.seshat/semantic-decisions.yaml").json()

    assert len(draft["decisions"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_exports.py -k client_view -v`
Expected: FAIL — 404 until the route exists

- [ ] **Step 3: Write minimal implementation**

Read eligible decisions via `decision_write.decisions_at_head`; surface working-tree-only
entries in `pending_items`. `pending_items` is its own field so a renderer cannot omit it
while rendering the happy path.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_exports.py src/seshat/studio/exports.py src/seshat/studio/operations_routes.py
git commit -m "feat: admit only committed approved evidence to the client view"
```

---

### Task D2: The narrative may not add a claim

- [ ] **Step 1: Write the failing test**

```python
def test_the_narrative_contains_no_fact_outside_the_selection(tmp_path: Path):
    """FR-141-022: a generated narrative must not invent a claim."""
    draft = exports.build_narrative(
        selected_facts=("net sales is reported net of returns",),
        pending_items=("margin definition awaiting sign-off",),
    )

    assert "net of returns" in draft
    assert "margin definition" in draft, "pending items must be VISIBLE, not dropped"
    assert "approved" not in draft.lower(), "a pending item must not read as approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_exports.py -k narrative -v`
Expected: FAIL — `AttributeError: build_narrative`

- [ ] **Step 3: Write minimal implementation**

Compose the narrative by templating over the supplied tuples only, with pending items in
their own labelled section. No sentence is generated from anything not passed in.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_exports.py src/seshat/studio/exports.py
git commit -m "feat: bound the client narrative to its selected facts"
```

---

### Task D3: Acknowledgement cannot carry a ruling

- [ ] **Step 1: Write the failing test**

```python
def test_acknowledgement_has_no_answer_field():
    """FR-141-011 as a type constraint: the two cannot collapse."""
    fields = {f.name for f in dataclasses.fields(exports.ClientAcknowledgment)}

    assert not fields & {"answer", "approval", "decision", "signer"}


def test_posting_an_acknowledgement_writes_no_decision(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    before = store.read_text(encoding="utf-8")

    response = client.post(
        f"{API}/client-review/acknowledge",
        json={"scope": ".seshat/semantic-decisions.yaml", "acknowledged_by": "Client"},
    )

    assert response.status_code == 201, response.text
    assert store.read_text(encoding="utf-8") == before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_exports.py -k acknowledge -v`
Expected: FAIL — `AttributeError: ClientAcknowledgment`

- [ ] **Step 3: Write minimal implementation**

`ClientAcknowledgment(scope, acknowledged_by, acknowledged_at, run_id)` — no answer field
exists, so the collapse is unrepresentable. The route records it without touching the
decision store.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_exports.py src/seshat/studio/exports.py src/seshat/studio/operations_routes.py
git commit -m "feat: keep acknowledgement structurally distinct from approval"
```

---

### Task D4: The support bundle excludes secrets structurally

- [ ] **Step 1: Write the failing test**

```python
def test_the_bundle_contains_no_env_dsn_or_absolute_path(tmp_path: Path):
    (tmp_path / ".env").write_text("PGPASSWORD=hunter2\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(
        f"dsn {FAKE_DSN} at {tmp_path}\n", encoding="utf-8"
    )

    bundle = exports.build_support_bundle(tmp_path, destination=tmp_path / "b.zip")

    text = bundle.read_bytes().decode("utf-8", errors="ignore")
    assert "hunter2" not in text
    assert "postgresql://" not in text
    assert str(tmp_path) not in text


def test_the_bundle_still_contains_its_allowlisted_content(tmp_path: Path):
    """The paired positive case: an empty archive would pass the test above."""
    bundle = exports.build_support_bundle(tmp_path, destination=tmp_path / "b.zip")

    assert bundle.stat().st_size > 0
    assert exports.read_manifest(bundle)["allowlisted_fields"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_exports.py -k bundle -v`
Expected: FAIL — `AttributeError: build_support_bundle`

- [ ] **Step 3: Write minimal implementation**

Stage allowlisted files only, scrub each through `scrub_for_export`, write the manifest
with hashes, then move into place. `.env` is never a candidate because it is not on the
allowlist — exclusion is structural, not a filter step.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_exports.py src/seshat/studio/exports.py
git commit -m "feat: build support bundles from an allowlist"
```

---

### Task D5: A failed scan aborts the bundle

- [ ] **Step 1: Write the failing test**

```python
def test_a_scan_failure_leaves_no_artifact(tmp_path: Path, monkeypatch):
    """O5: a partially scrubbed archive is worse than none."""

    def _fail(*args, **kwargs):
        raise exports.ScanFailed("residual secret detected")

    monkeypatch.setattr(exports, "_scan_staged", _fail)
    destination = tmp_path / "b.zip"

    with pytest.raises(exports.ScanFailed):
        exports.build_support_bundle(tmp_path, destination=destination)

    assert not destination.exists()
    assert [p for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_exports.py -k scan_failure -v`
Expected: FAIL — `AttributeError: ScanFailed`

- [ ] **Step 3: Write minimal implementation**

Add `class ScanFailed(Exception)`, call `_scan_staged` before the atomic move, and clean
up the staging path in a `finally`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_exports.py src/seshat/studio/exports.py
git commit -m "feat: abort a support bundle when its redaction scan fails"
```

**Phase D gate**: full `pytest -m unit`, `seshat check`, `seshat kit-lint`,
`ruff format --check`, `ruff check`. This phase carries the disclosure risk — request a
Codex review and a CodeScene delta before merging.

---

## Traceability

| Requirement | Task |
| --- | --- |
| FR-141-001 | B1 |
| FR-141-002 | A3, B3 |
| FR-141-003 | A1, A2 |
| FR-141-004 | A1, A3, B1 |
| FR-141-005 | B2 |
| FR-141-006 | A1 |
| FR-141-007 | C3 |
| FR-141-008 | A4, B3 |
| FR-141-009 | C3 |
| FR-141-010 | C1 |
| FR-141-011 | D3 |
| FR-141-012 | A4, D4 |
| FR-141-013 | D4 |
| FR-141-014 | D5 |
| FR-141-017 | B2 |
| FR-141-018 | B2 |
| FR-141-021 | C2, D1 |
| FR-141-022 | D2 |
| SC-141-001 | A3 |
| SC-141-002 | A2 |
| SC-141-003 | D4 |
| SC-141-004 | D1 |
| SC-141-005 | B2 |
| SC-141-006 | C3 |

FR-141-015 (WCAG 2.2 AA), FR-141-016 (responsive), FR-141-019 (backward compatibility)
and FR-141-020 (the fence) are constraints on how the above are built rather than
separately testable units. They are enforced by the phase gates, by Foundation's existing
accessibility suite, and by review of the contract.
