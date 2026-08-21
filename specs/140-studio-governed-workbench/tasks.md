# Tasks: Studio Governed Analyst Workbench

**Feature**: `specs/140-studio-governed-workbench/` | **Plan**: [plan.md](./plan.md) |
**Spec**: [spec.md](./spec.md) | **Boundary contract**:
[contracts/decision-write-boundary.md](./contracts/decision-write-boundary.md)

**Spec status**: `draft`. Phases 0 and 1 (research, design) are complete. **Every task
below is BLOCKED until a named human ratifies this package and the sole active Spec Kit
fence points at this plan** (FR-140-020).

**Progress**: 0 of 19 implementation tasks. Nothing started.

TDD order: the failing test comes before the code. A task is done only when its test
was seen RED, then GREEN. Nothing is marked done that was not observed.

**Vocabulary and helpers verified against the shipped tree** (do not substitute
guesses; an unrecognized status is malformed and fails closed at every consumer):

- `status` must come from `decision_store.STATUS_VALUES`: `proposed`, `approved`,
  `rejected`, `pending`, `needs_user_input`, `needs_sample`, `blocked`, `deferred`,
  `superseded`. **There is no `decided`** -- a recorded human answer is `approved`.
- A **non-critical** `decision_type` is any recognized type outside
  `CRITICAL_DECISION_TYPES` (which contains `kpi_definition`, `pii_handling`,
  `table_grain`, `primary_key`, `relationship_cardinality`, `missing_value_rule`,
  `data_exclusion`, `policy_ruling`, `dashboard_blueprint_approval`,
  `report_intent_approval`, `publish_export`). Only a non-critical decision can be
  written with `authority=None`.
- YAML: the repo is deliberately **`pyyaml`-only** (`pyproject.toml` pins `pyyaml>=6`
  and comments that the static core stays dependency-light). Task 1.3 therefore
  hand-appends text rather than adding a round-trip library. Do not introduce
  `ruamel.yaml`; the repo has a dependency-freshness gate.
- Test helpers that already exist and MUST be reused rather than reinvented:
  `tests/unit/_studio_workspace_fixtures.py` provides `write_ready_table`,
  `write_blocked_table`, `write_warning_table`, `write_empty_workspace`,
  `write_pending_live_table`, `write_malformed_table`, `write_missing_stage_table`.
  The house client pattern is `create_app(tmp_path, port=9999)` wrapped in a
  `fastapi.testclient.TestClient` with a browser Origin header, then
  `POST {API}/bootstrap?token=...` expecting 204 -- see
  `tests/unit/test_studio_approval_reachability.py::_client`.
- Projection field names (verified): `WorkspaceSnapshot.input_defects` (not
  `defects`); `InputDefect` has **no** `table_id` (`code`, `message`, `source_ref`,
  `recovery_action`); `StageState` has **no** `pending_live` (`stage`, `status`,
  `evidence`, `blocking_reasons`, `required_authority`); pending-live state lives on
  `EvidenceRef.live_state`.

Phase order is mandatory: **Phase A must be fully green before Phase C begins**, because
C's routes depend on A's invariants.

---

## Phase A -- Decision Store write path (no UI)

### Task 1.0: Build the shared test fixtures the later phases consume

Phases B-D reference `studio_client`, `git_workspace`, `prepared_proposal`,
`store_file`, `committed_decision`, and `two_scoped_decisions`. **None of these exist
today** -- `grep -rn 'def studio_client' tests/` returns nothing. Build them once here
so no later task starts by inventing one.

**Files:**
- Create: `tests/unit/_workbench_fixtures.py`
- Test: `tests/unit/test_workbench_fixtures.py`

**Interfaces:**
- Reuses: `tests/unit/_studio_workspace_fixtures.py` (`write_ready_table`,
  `write_pending_live_table`, `write_malformed_table`, ...) and the house client
  pattern in `tests/unit/test_studio_approval_reachability.py::_client`
- Produces: `studio_client(tmp_path)`, `git_workspace(tmp_path)`,
  `store_file(tmp_path)`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from tests.unit import _workbench_fixtures as fixtures


def test_the_client_fixture_is_authenticated_and_the_workspace_is_a_git_repo(
    tmp_path: Path,
):
    """The fixtures must produce a REAL authenticated client over a REAL git repo.

    A fake would make every Phase C/D test vacuous: the readiness-reads-HEAD proof
    (Task 3.5) is meaningless without a workspace that can actually commit.
    """
    client = fixtures.studio_client(tmp_path)
    assert client.get("/api/v1/workspace").status_code == 200

    workspace = fixtures.git_workspace(tmp_path)
    workspace.commit_all("test: initial")
    assert workspace.head_sha()

    store = fixtures.store_file(tmp_path)
    assert store.exists() and store.name.endswith(".yaml")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_workbench_fixtures.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests.unit._workbench_fixtures'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Shared fixtures for the spec-140 workbench tests.

Deliberately builds on `_studio_workspace_fixtures` rather than hand-rolling readiness
documents: a fixture only these tests can read would make the whole suite green while
proving nothing about the shipped readers.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from tests.unit import _studio_workspace_fixtures as workspace_fixtures

API = "/api/v1"
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}


def studio_client(root: Path, *, table: str = "ready_sales") -> TestClient:
    """An authenticated TestClient over a workspace with one ready table."""
    from seshat.studio.app import create_app

    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    workspace_fixtures.write_ready_table(root, table=table)
    app, token = create_app(root, port=9999)
    client = TestClient(app, base_url="http://127.0.0.1:9999", headers=_BROWSER_ORIGIN)
    assert client.post(f"{API}/bootstrap", params={"token": token}).status_code == 204
    return client


@dataclass(frozen=True)
class GitWorkspace:
    root: Path

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def commit_all(self, message: str) -> None:
        self._git("add", "-A")
        self._git("-c", "commit.gpgsign=false", "commit", "--no-gpg-sign", "-m", message)

    def head_sha(self) -> str:
        return self._git("rev-parse", "HEAD")


def git_workspace(root: Path) -> GitWorkspace:
    """Initialise `root` as a real git repo with an identity set."""
    workspace = GitWorkspace(root)
    workspace._git("init", "-q")
    workspace._git("config", "user.email", "test@example.invalid")
    workspace._git("config", "user.name", "Test Runner")
    return workspace


def store_file(root: Path) -> Path:
    """The semantic-decisions store file, created empty if absent."""
    path = root / ".seshat" / "semantic-decisions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("decisions: []\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_workbench_fixtures.py -v`
Expected: PASS

Cross-platform note: use `Path` and the helpers above rather than hardcoded `/` or
`.exe` paths. The CI `unit` job runs `ubuntu-latest` only, so a POSIX-locked fixture
stays green in CI forever and fails only on Windows (issue #691).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/_workbench_fixtures.py tests/unit/test_workbench_fixtures.py
git commit -m "test: add shared workbench fixtures for spec 140"
```

`prepared_proposal`, `committed_decision`, and `two_scoped_decisions` depend on code
that does not exist until Phase C; add each to this module in the first task that needs
it, following the same rule -- build on shipped readers, never on a bespoke fake.

---

### Task 1.1: Build a decision entry from a named-human answer

**Files:**
- Create: `src/seshat/decision_write.py`
- Test: `tests/unit/test_decision_write.py`

**Interfaces:**
- Consumes: `decision_store.APPROVAL_REQUIRED_FIELDS`, `owner_shape_ok`
- Produces: `build_entry(*, decision_id: str, decision_type: str, scope: dict, signer: str, answer: str, proposal_hash: str, workspace_revision: str, recorded_at: str, reviewed_scope: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
from seshat import decision_store, decision_write


def test_build_entry_populates_every_required_approval_field():
    entry = decision_write.build_entry(
        decision_id="d-001",
        decision_type="kpi_definition",
        scope={"table": "sales"},
        signer="Ahmed Shaaban (owner)",
        answer="net_of_returns",
        proposal_hash="h" * 16,
        workspace_revision="r" * 16,
        recorded_at="2026-08-21T10:00:00Z",
        reviewed_scope=".seshat/kpi-contracts.yaml",
    )
    approval = entry["approval"]
    missing = [k for k in decision_store.APPROVAL_REQUIRED_FIELDS if not approval.get(k)]
    assert missing == []
    assert approval["approved_by"] == "Ahmed Shaaban (owner)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_decision_write.py::test_build_entry_populates_every_required_approval_field -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.decision_write'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Append-only writes into the Decision Store.

Separate from `decision_store` by design: that module is the READ side the static
gate depends on. Keeping mutation out of it means the gate's module stays read-only
by construction and the whole mutation surface is auditable in one file.
"""

from __future__ import annotations

from typing import Any


def build_entry(
    *,
    decision_id: str,
    decision_type: str,
    scope: dict[str, Any],
    signer: str,
    answer: str,
    proposal_hash: str,
    workspace_revision: str,
    recorded_at: str,
    reviewed_scope: str,
) -> dict[str, Any]:
    """Assemble one decision entry. Validation is the caller's next step, not here."""
    return {
        "id": decision_id,
        "decision_type": decision_type,
        "status": "approved",
        "scope": scope,
        "answer": answer,
        "approval": {
            "approved_by": signer,
            "approved_at": recorded_at,
            "source": "seshat-studio",
            "evidence": f"proposal:{proposal_hash}",
            "evidence_identity": f"workspace_revision:{workspace_revision}",
            "reviewed_scope": reviewed_scope,
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_decision_write.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_decision_write.py src/seshat/decision_write.py
git commit -m "feat: build a decision entry from a named-human answer"
```

---

### Task 1.2: Refuse an entry the shipped validators reject, writing nothing

**Files:**
- Modify: `src/seshat/decision_write.py`
- Test: `tests/unit/test_decision_write.py`

**Interfaces:**
- Produces: `append_decision(repo_root: Path, rel_path: str, entry: dict, authority: dict[str, frozenset[str]] | None) -> DecisionWriteReceipt`, and `class WriteRefused(Exception)`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from seshat import decision_write


def test_a_malformed_signer_is_refused_and_the_file_is_untouched(tmp_path):
    store = tmp_path / ".seshat"
    store.mkdir()
    target = store / "semantic-decisions.yaml"
    original = "decisions:\n  - id: existing\n"
    target.write_text(original, encoding="utf-8")

    entry = decision_write.build_entry(
        decision_id="d-002",
        decision_type="kpi_definition",
        scope={"table": "sales"},
        signer="owner (owner)",  # name is a role token -> owner_shape_ok rejects
        answer="net_of_returns",
        proposal_hash="h" * 16,
        workspace_revision="r" * 16,
        recorded_at="2026-08-21T10:00:00Z",
        reviewed_scope=".seshat/semantic-decisions.yaml",
    )

    with pytest.raises(decision_write.WriteRefused):
        decision_write.append_decision(
            tmp_path, ".seshat/semantic-decisions.yaml", entry, authority=None
        )

    assert target.read_text(encoding="utf-8") == original
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_decision_write.py::test_a_malformed_signer_is_refused_and_the_file_is_untouched -v`
Expected: FAIL — `AttributeError: module 'seshat.decision_write' has no attribute 'WriteRefused'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path

from seshat import decision_store


class WriteRefused(Exception):
    """The entry did not pass the shipped validators. Nothing was written."""


@dataclass(frozen=True)
class DecisionWriteReceipt:
    written_path: str
    decision_id: str
    state: str = "pending_commit"
    gate_authority: str = (
        "the static gate reads committed decisions at HEAD; this write is not authority"
    )


def append_decision(
    repo_root: Path,
    rel_path: str,
    entry: dict[str, Any],
    authority: dict[str, frozenset[str]] | None,
) -> DecisionWriteReceipt:
    """Validate through the shipped predicate, then append atomically."""
    valid, reason = decision_store.approval_is_valid(entry, authority)
    if not valid:
        raise WriteRefused(reason or "approval invalid")
    _atomic_append(Path(repo_root) / rel_path, entry)
    return DecisionWriteReceipt(written_path=rel_path, decision_id=str(entry["id"]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_decision_write.py -v`
Expected: PASS (implement `_atomic_append` in Task 1.3; stub it to raise
`NotImplementedError` for now — this test never reaches it)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_decision_write.py src/seshat/decision_write.py
git commit -m "feat: refuse an invalid decision entry before any write"
```

---

### Task 1.3: Append atomically, preserving existing entries and comments

**Files:**
- Modify: `src/seshat/decision_write.py`
- Test: `tests/unit/test_decision_write.py`

- [ ] **Step 1: Write the failing test**

```python
def test_append_preserves_existing_entries_and_comments(tmp_path):
    store = tmp_path / ".seshat"
    store.mkdir()
    target = store / "semantic-decisions.yaml"
    target.write_text(
        "# provenance: hand-authored, do not reorder\n"
        "decisions:\n"
        "  - id: first\n"
        "  - id: second\n",
        encoding="utf-8",
    )

    entry = decision_write.build_entry(
        decision_id="d-003",
        decision_type="assumption_note",
        scope={"table": "sales"},
        signer="Ahmed Shaaban (owner)",
        answer="yes",
        proposal_hash="h" * 16,
        workspace_revision="r" * 16,
        recorded_at="2026-08-21T10:00:00Z",
        reviewed_scope=".seshat/semantic-decisions.yaml",
    )
    decision_write.append_decision(
        tmp_path, ".seshat/semantic-decisions.yaml", entry, authority=None
    )

    text = target.read_text(encoding="utf-8")
    assert "# provenance: hand-authored, do not reorder" in text
    assert text.index("id: first") < text.index("id: second") < text.index("id: d-003")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_decision_write.py::test_append_preserves_existing_entries_and_comments -v`
Expected: FAIL — `NotImplementedError` from the `_atomic_append` stub

- [ ] **Step 3: Write minimal implementation**

```python
import os
import tempfile

def _atomic_append(path: Path, entry: dict[str, Any]) -> None:
    """Append one decision, then replace the file in a single atomic rename."""
import os
import tempfile

import yaml


def _atomic_append(path: Path, entry: dict[str, Any]) -> None:
    """Append one decision by TEXT append, then replace the file atomically.

    Deliberately not a parse-mutate-dump round trip. `yaml.safe_load` +
    `yaml.safe_dump` would drop every comment and reflow the whole document, which
    Task 1.3's test forbids -- and the repo is pyyaml-only by design
    (`pyproject.toml` keeps the static core dependency-light), so a round-trip
    loader is not available. Appending text leaves existing bytes untouched by
    construction, which is a stronger guarantee than reformatting carefully.
    """
    existing = path.read_text(encoding="utf-8")

    # Validate our own fragment parses, and that the merged document is still valid
    # YAML with the new entry last. A fragment that breaks the file must never land.
    fragment = yaml.safe_dump(
        [entry], sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    indented = "".join(
        f"  {line}\n" if line.strip() else "\n" for line in fragment.splitlines()
    )
    if "decisions:" not in existing:
        merged = existing.rstrip("\n") + "\ndecisions:\n" + indented
    else:
        merged = existing.rstrip("\n") + "\n" + indented

    parsed = yaml.safe_load(merged)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("decisions"), list):
        raise WriteRefused("append would produce a malformed decision store")
    if parsed["decisions"][-1].get("id") != entry["id"]:
        raise WriteRefused("append did not land the new entry last")

    directory = path.parent
    handle_fd, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as staged:
            staged.write(merged)
        os.replace(temporary, path)      # atomic on POSIX and Windows
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
```

Note for the implementer: the merged-document re-parse is the safety net that makes a
text append safe. Without it, a malformed fragment could corrupt the store and the
corruption would only surface later, in the gate.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_decision_write.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_decision_write.py src/seshat/decision_write.py
git commit -m "feat: append decisions atomically preserving comments and order"
```

---

### Task 1.4: Prove the write reaches the shipped predicate (no second trust path)

**Files:**
- Test: `tests/unit/test_decision_write.py`

- [ ] **Step 1: Write the failing test**

```python
def test_the_write_path_calls_the_shipped_predicate(tmp_path, monkeypatch):
    """Monkeypatch the ONE shared predicate to reject; the write must refuse.

    This fails if a second validity path is ever introduced, because the write would
    then succeed while the shipped predicate says no.
    """
    store = tmp_path / ".seshat"
    store.mkdir()
    target = store / "semantic-decisions.yaml"
    target.write_text("decisions: []\n", encoding="utf-8")

    monkeypatch.setattr(
        decision_store, "approval_is_valid", lambda entry, authority: (False, "stubbed")
    )

    entry = decision_write.build_entry(
        decision_id="d-004",
        decision_type="assumption_note",
        scope={"table": "sales"},
        signer="Ahmed Shaaban (owner)",
        answer="yes",
        proposal_hash="h" * 16,
        workspace_revision="r" * 16,
        recorded_at="2026-08-21T10:00:00Z",
        reviewed_scope=".seshat/semantic-decisions.yaml",
    )
    with pytest.raises(decision_write.WriteRefused):
        decision_write.append_decision(
            tmp_path, ".seshat/semantic-decisions.yaml", entry, authority=None
        )
    assert target.read_text(encoding="utf-8") == "decisions: []\n"
```

- [ ] **Step 2: Run test to verify it fails**

Temporarily change `append_decision` to validate with a local copy of the logic instead
of calling `decision_store.approval_is_valid`.
Run: `pytest tests/unit/test_decision_write.py::test_the_write_path_calls_the_shipped_predicate -v`
Expected: FAIL — the write succeeds despite the stub, proving the test detects a second
trust path. Revert the temporary change.

- [ ] **Step 3: No implementation needed**

Task 1.2 already calls the shipped predicate. This task adds the proof.

- [ ] **Step 4: Run the full module**

Run: `pytest tests/unit/test_decision_write.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_decision_write.py
git commit -m "test: prove the decision write reaches the shipped validity predicate"
```

---

### Task 1.5: Prove the write path performs no git operation

**Files:**
- Test: `tests/unit/test_decision_write.py`

- [ ] **Step 1: Write the failing test**

```python
def test_the_write_succeeds_with_the_git_runner_disabled(tmp_path, monkeypatch):
    """A decision write must not depend on -- or perform -- any git call.

    Making the git runner raise proves the write path never touches it. A grep-only
    assertion would pass even if a git call arrived through an alias or helper.
    """
    from seshat import gitutil

    def _explode(*args, **kwargs):
        raise AssertionError("the decision write path must not invoke git")

    monkeypatch.setattr(gitutil, "run_subprocess", _explode)

    store = tmp_path / ".seshat"
    store.mkdir()
    (store / "semantic-decisions.yaml").write_text("decisions: []\n", encoding="utf-8")

    entry = decision_write.build_entry(
        decision_id="d-005",
        decision_type="assumption_note",
        scope={"table": "sales"},
        signer="Ahmed Shaaban (owner)",
        answer="yes",
        proposal_hash="h" * 16,
        workspace_revision="r" * 16,
        recorded_at="2026-08-21T10:00:00Z",
        reviewed_scope=".seshat/semantic-decisions.yaml",
    )
    receipt = decision_write.append_decision(
        tmp_path, ".seshat/semantic-decisions.yaml", entry, authority=None
    )
    assert receipt.state == "pending_commit"
```

- [ ] **Step 2: Run test to verify it fails**

Temporarily add a `gitutil.run_subprocess(["git", "add", "-A"])` call to
`append_decision`.
Run: `pytest tests/unit/test_decision_write.py::test_the_write_succeeds_with_the_git_runner_disabled -v`
Expected: FAIL — `AssertionError: the decision write path must not invoke git`. Remove
the temporary call.

- [ ] **Step 3: No implementation needed**

- [ ] **Step 4: Run the full module**

Run: `pytest tests/unit/test_decision_write.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_decision_write.py
git commit -m "test: prove the decision write performs no git operation"
```

**Phase A gate**: `pytest tests/unit/test_decision_write.py -v` all green, plus
`ruff format --check`, `ruff check`, `seshat check`. Phase C MUST NOT start before this.

---

## Phase B -- Investigation journey (US1)

### Task 2.1: Assemble an `EvidenceBundle` for one table

**Files:**
- Create: `src/seshat/studio/evidence.py`
- Test: `tests/unit/test_studio_evidence.py`

**Interfaces:**
- Consumes: `projection.WorkspaceSnapshot`, `TableJourney`, `EvidenceRef`, `InputDefect`
- Produces: `bundle_for(snapshot, table_id: str) -> EvidenceBundle`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from seshat.studio import evidence, projection
from tests.unit import _studio_workspace_fixtures as workspace_fixtures


def test_a_table_with_malformed_evidence_reports_a_defect_not_a_pass(tmp_path: Path):
    """Malformed evidence must surface as a defect. An empty success state here would
    present missing information as a clean bill of health.

    Uses the SHIPPED fixture writer, so the bundle is built from a real committed
    readiness document rather than a hand-made snapshot only this test can read.
    """
    workspace_fixtures.write_malformed_table(tmp_path, table="malformed_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "malformed_sales")

    assert bundle.defects, "malformed evidence must produce at least one defect"
    assert all(stage.status != "pass" for stage in bundle.stages)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.studio.evidence'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass

from seshat.studio import projection

#: The `EvidenceRef.live_state` values that mean "no live evidence yet". Confirm the
#: exact vocabulary in projection.py before relying on it; an unrecognized value must
#: be treated as pending rather than as satisfied.
_PENDING_LIVE_STATES = frozenset({"pending", "pending_live"})


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    table_id: str
    stages: tuple[projection.StageState, ...]
    evidence: tuple[projection.EvidenceRef, ...]
    defects: tuple[projection.InputDefect, ...]
    pending_live: tuple[str, ...]


def bundle_for(
    snapshot: projection.WorkspaceSnapshot, table_id: str
) -> EvidenceBundle:
    journey = next(t for t in snapshot.tables if t.table_id == table_id)
    return EvidenceBundle(
        table_id=table_id,
        stages=journey.stages,
        evidence=tuple(ref for stage in journey.stages for ref in stage.evidence),
        # `WorkspaceSnapshot.input_defects` -- NOT `.defects`. `InputDefect` carries no
        # `table_id`, so defects cannot be filtered by table identity; correlate via
        # `source_ref` if per-table narrowing is needed, and otherwise carry them all
        # rather than silently dropping a defect that belongs to this view.
        defects=snapshot.input_defects,
        # `StageState` has NO `pending_live` field. Pending-live state lives on
        # `EvidenceRef.live_state`, so it is DERIVED here.
        pending_live=tuple(
            stage.stage
            for stage in journey.stages
            if any(ref.live_state in _PENDING_LIVE_STATES for ref in stage.evidence)
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_evidence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_evidence.py src/seshat/studio/evidence.py
git commit -m "feat: assemble a table evidence bundle for the workbench"
```

---

### Task 2.2: Every displayed claim carries a source reference

- [ ] **Step 1: Write the failing test**

```python
def test_a_pending_live_stage_is_reported_pending_not_unsourced(tmp_path: Path):
    """A stage awaiting a live profile is NOT the same as a stage with no source.

    Uses the shipped `write_pending_live_table` fixture so the live_state values come
    from a real readiness document.
    """
    workspace_fixtures.write_pending_live_table(tmp_path, table="pending_live_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "pending_live_sales")

    assert bundle.pending_live, "a pending-live stage must be reported as pending"
    for stage in bundle.stages:
        assert stage.evidence or stage.stage in bundle.pending_live, (
            f"stage {stage.stage} displays a claim with no source reference"
        )


def test_a_stage_with_no_evidence_is_not_reported_as_pending_live(tmp_path: Path):
    """The inverse, and the reason this pair exists: an empty evidence list means
    "no evidence" (a defect), never "awaiting a live profile". Collapsing the two
    would launder missing data into an expected-pending state."""
    workspace_fixtures.write_malformed_table(tmp_path, table="malformed_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "malformed_sales")

    for stage in bundle.stages:
        if not stage.evidence:
            assert stage.stage not in bundle.pending_live
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_evidence.py -k pending_live -v`
Expected: FAIL — the second test fails if `pending_live` is derived from "empty
evidence" instead of from `EvidenceRef.live_state`.

- [ ] **Step 3: Write minimal implementation**

Task 2.1 already derives `pending_live` from `EvidenceRef.live_state`. If the first
test fails, the `_PENDING_LIVE_STATES` vocabulary is wrong — read the real values out of
`projection.py` and correct the set. Do **not** switch to inferring from an empty
evidence list; the second test exists to forbid exactly that.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_evidence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_evidence.py src/seshat/studio/evidence.py
git commit -m "feat: require a source reference or pending-live marker per claim"
```

---

### Task 2.3: Expose the bundle on `GET /tables/{table_id}/evidence`

- [ ] **Step 1: Write the failing test**

```python
def test_the_evidence_route_is_redacted_and_session_guarded(studio_client):
    unauthenticated = studio_client.get("/api/v1/tables/sales/evidence")
    assert unauthenticated.status_code == 401

    response = studio_client.authenticated().get("/api/v1/tables/sales/evidence")
    assert response.status_code == 200
    assert "postgresql://" not in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_evidence.py::test_the_evidence_route_is_redacted_and_session_guarded -v`
Expected: FAIL — 404, route not registered.

- [ ] **Step 3: Write minimal implementation**

Register the route in `app.py::_register_routes`, returning `_redact(bundle)` through
the existing redaction helper. Reuse `_requires_session`; do not add a new auth path.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_evidence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_evidence.py src/seshat/studio/evidence.py src/seshat/studio/app.py
git commit -m "feat: expose the table evidence bundle route"
```

---

## Phase C -- Proposals and decision recording (US2, US3)

### Task 3.1: Build a hashed, revision-bound proposal

**Files:**
- Create: `src/seshat/studio/proposals.py`
- Test: `tests/unit/test_studio_proposals.py`

**Interfaces:**
- Produces: `build_proposal(...) -> ChangeProposal`, `is_stale(proposal, snapshot) -> bool`

- [ ] **Step 1: Write the failing test**

```python
from seshat.studio import proposals


def test_a_proposal_binds_its_hash_to_its_content():
    first = proposals.build_proposal(
        target_artifact=".seshat/kpi-contracts.yaml",
        diff="- net_sales\n+ net_sales_of_returns\n",
        fields=(),
        workspace_revision="r" * 16,
    )
    second = proposals.build_proposal(
        target_artifact=".seshat/kpi-contracts.yaml",
        diff="- net_sales\n+ gross_sales\n",
        fields=(),
        workspace_revision="r" * 16,
    )
    assert first.proposal_hash != second.proposal_hash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_proposals.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
import hashlib
import json
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChangeProposal:
    proposal_id: str
    proposal_hash: str
    workspace_revision: str
    target_artifact: str
    diff: str
    fields: tuple = ()
    stale: bool = False


def _canonical_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_proposal(
    *, target_artifact: str, diff: str, fields: tuple, workspace_revision: str
) -> ChangeProposal:
    digest = _canonical_hash(
        {"target": target_artifact, "diff": diff, "revision": workspace_revision}
    )
    return ChangeProposal(
        proposal_id=digest[:12],
        proposal_hash=digest,
        workspace_revision=workspace_revision,
        target_artifact=target_artifact,
        diff=diff,
        fields=fields,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_proposals.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_proposals.py src/seshat/studio/proposals.py
git commit -m "feat: build hashed revision-bound change proposals"
```

---

### Task 3.2: A moved workspace revision makes a proposal stale

- [ ] **Step 1: Write the failing test**

```python
def test_a_moved_revision_makes_the_proposal_stale():
    proposal = proposals.build_proposal(
        target_artifact=".seshat/kpi-contracts.yaml",
        diff="- a\n+ b\n",
        fields=(),
        workspace_revision="r" * 16,
    )
    assert proposals.is_stale(proposal, current_revision="r" * 16) is False
    assert proposals.is_stale(proposal, current_revision="z" * 16) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_proposals.py::test_a_moved_revision_makes_the_proposal_stale -v`
Expected: FAIL — `AttributeError: is_stale`

- [ ] **Step 3: Write minimal implementation**

```python
def is_stale(proposal: ChangeProposal, current_revision: str) -> bool:
    return proposal.workspace_revision != current_revision
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_proposals.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_proposals.py src/seshat/studio/proposals.py
git commit -m "feat: mark a proposal stale when the workspace revision moves"
```

---

### Task 3.3: The record route refuses a missing signer, authority, or answer

**Files:**
- Create: `src/seshat/studio/decision_routes.py`
- Test: `tests/unit/test_studio_decision_routes.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest


@pytest.mark.parametrize("omitted", ["signer", "declared_authority", "answer"])
def test_a_missing_human_supplied_field_is_refused(studio_client, omitted):
    """FR-140-009: the agent must not supply these. Absent means refuse, never infer."""
    payload = {
        "signer": "Ahmed Shaaban (owner)",
        "declared_authority": "owner",
        "answer": "net_of_returns",
        "proposal_hash": "h" * 64,
        "workspace_revision": "r" * 16,
    }
    del payload[omitted]

    response = studio_client.authenticated().post(
        "/api/v1/decisions/record", json=payload
    )
    assert response.status_code == 422
    assert omitted in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_decision_routes.py -v`
Expected: FAIL — 404, route not registered.

- [ ] **Step 3: Write minimal implementation**

Add the route with a Pydantic model in which `signer`, `declared_authority`, and
`answer` are **required with no default**. Do not add `None` defaults; a default is the
defect this test exists to prevent.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_decision_routes.py -v`
Expected: PASS (3 parametrized cases)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_decision_routes.py src/seshat/studio/decision_routes.py src/seshat/studio/app.py
git commit -m "feat: refuse a decision missing any human-supplied field"
```

---

### Task 3.4: The success receipt cannot claim approval

- [ ] **Step 1: Write the failing test**

```python
def test_the_receipt_state_cannot_express_approved():
    """FR-140-021 as a type constraint: the false claim must be unrepresentable."""
    from seshat.studio import decision_routes

    allowed = set(decision_routes.ReceiptState.__args__)   # Literal members
    assert allowed == {"pending_commit"}


def test_a_successful_record_reports_pending_commit(studio_client, prepared_proposal):
    response = studio_client.authenticated().post(
        "/api/v1/decisions/record",
        json={
            "signer": "Ahmed Shaaban (owner)",
            "declared_authority": "owner",
            "answer": "net_of_returns",
            "proposal_hash": prepared_proposal.proposal_hash,
            "workspace_revision": prepared_proposal.workspace_revision,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "pending_commit"
    assert "approved" not in body["state"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_decision_routes.py -v`
Expected: FAIL — `ReceiptState` not defined.

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Literal

ReceiptState = Literal["pending_commit"]
```

Adding an `"approved"` member later breaks the first test — which is the point.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_decision_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_decision_routes.py src/seshat/studio/decision_routes.py
git commit -m "feat: make an approved-state receipt unrepresentable"
```

---

### Task 3.5: An uncommitted decision moves no readiness stage — and a committed one does

**Files:**
- Test: `tests/unit/test_studio_decision_routes.py`

- [ ] **Step 1: Write the failing test**

```python
def test_an_uncommitted_decision_moves_nothing_but_a_committed_one_does(
    studio_client, git_workspace, prepared_proposal
):
    """Both halves are required. The first assertion alone passes vacuously if
    readiness is never recomputed at all; the second proves it IS recomputed."""
    before = studio_client.authenticated().get("/api/v1/workspace").json()

    studio_client.authenticated().post(
        "/api/v1/decisions/record",
        json={
            "signer": "Ahmed Shaaban (owner)",
            "declared_authority": "owner",
            "answer": "net_of_returns",
            "proposal_hash": prepared_proposal.proposal_hash,
            "workspace_revision": prepared_proposal.workspace_revision,
        },
    )

    uncommitted = studio_client.authenticated().get("/api/v1/workspace").json()
    assert uncommitted == before, "an uncommitted decision must move no stage"

    git_workspace.commit_all("decision: net of returns")

    committed = studio_client.authenticated().get("/api/v1/workspace").json()
    assert committed != before, "a committed decision must be read at HEAD"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_decision_routes.py::test_an_uncommitted_decision_moves_nothing_but_a_committed_one_does -v`
Expected: FAIL — the second assertion fails until readiness reads `HEAD`.

- [ ] **Step 3: Write minimal implementation**

Recompute readiness from committed state (the existing tracked-file read path), not from
the working tree. Do not add a working-tree fallback: that fallback is precisely the
fail-open this test guards.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_decision_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_decision_routes.py src/seshat/studio/decision_routes.py
git commit -m "feat: recompute readiness from committed state only"
```

---

### Task 3.6: A stale proposal hash is refused before any write

- [ ] **Step 1: Write the failing test**

```python
def test_a_stale_proposal_hash_is_refused_and_nothing_is_written(
    studio_client, prepared_proposal, store_file
):
    original = store_file.read_text(encoding="utf-8")
    response = studio_client.authenticated().post(
        "/api/v1/decisions/record",
        json={
            "signer": "Ahmed Shaaban (owner)",
            "declared_authority": "owner",
            "answer": "net_of_returns",
            "proposal_hash": "0" * 64,          # not the current proposal
            "workspace_revision": prepared_proposal.workspace_revision,
        },
    )
    assert response.status_code == 409
    assert store_file.read_text(encoding="utf-8") == original
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_decision_routes.py::test_a_stale_proposal_hash_is_refused_and_nothing_is_written -v`
Expected: FAIL — returns 201 until the staleness check is added.

- [ ] **Step 3: Write minimal implementation**

Compare the submitted `proposal_hash` and `workspace_revision` against the current
proposal **before** calling `append_decision`, returning 409 on mismatch.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_decision_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_decision_routes.py src/seshat/studio/decision_routes.py
git commit -m "feat: refuse a stale proposal before writing a decision"
```

**Phase C gate**: full `pytest -m unit`, `seshat check`, `seshat kit-lint`,
`ruff format --check`, `ruff check`. This phase carries the security weight — request a
Codex review and a CodeScene delta before merging.

---

## Phase D -- Apply and client review (US4, US5)

### Task 4.1: Apply refuses a decision that is only `pending commit`

- [ ] **Step 1: Write the failing test**

```python
def test_apply_refuses_an_uncommitted_decision(studio_client, prepared_proposal):
    studio_client.authenticated().post(
        "/api/v1/decisions/record",
        json={
            "signer": "Ahmed Shaaban (owner)",
            "declared_authority": "owner",
            "answer": "net_of_returns",
            "proposal_hash": prepared_proposal.proposal_hash,
            "workspace_revision": prepared_proposal.workspace_revision,
        },
    )
    response = studio_client.authenticated().post(
        f"/api/v1/proposals/{prepared_proposal.proposal_id}/apply"
    )
    assert response.status_code == 422
    assert "pending" in response.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_apply.py -v`
Expected: FAIL — 404, route not registered.

- [ ] **Step 3: Write minimal implementation**

Create `src/seshat/studio/apply.py`; gate on the decision being readable at `HEAD`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_apply.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_apply.py src/seshat/studio/apply.py src/seshat/studio/app.py
git commit -m "feat: refuse apply for an uncommitted decision"
```

---

### Task 4.2: Apply cannot exceed the reviewed scope

- [ ] **Step 1: Write the failing test**

```python
def test_apply_refuses_a_path_outside_the_reviewed_scope(
    studio_client, committed_decision, prepared_proposal
):
    widened = studio_client.authenticated().post(
        f"/api/v1/proposals/{prepared_proposal.proposal_id}/apply",
        json={"extra_paths": ["src/seshat/cli.py"]},
    )
    assert widened.status_code == 422
    assert "scope" in widened.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_apply.py::test_apply_refuses_a_path_outside_the_reviewed_scope -v`
Expected: FAIL — the extra path is accepted until scope binding is enforced.

- [ ] **Step 3: Write minimal implementation**

Intersect the requested paths with the proposal's `applied_paths` and with
`forbidden_scope_for`; refuse on any path outside the reviewed set. The caller must not
be able to supply the scope — derive it from the stored proposal.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_apply.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_apply.py src/seshat/studio/apply.py
git commit -m "feat: bind apply to the reviewed proposal scope"
```

---

### Task 4.3: Static success is not presented as live correctness

- [ ] **Step 1: Write the failing test**

```python
def test_a_missing_dsn_yields_pending_live_not_a_pass(
    studio_client, committed_decision, prepared_proposal, monkeypatch
):
    monkeypatch.delenv("SESHAT_DSN", raising=False)
    response = studio_client.authenticated().post(
        f"/api/v1/proposals/{prepared_proposal.proposal_id}/apply"
    )
    verification = response.json()["verification"]
    assert "PENDING LIVE PROFILE" in verification.get("live", "")
    assert "pass" not in verification.get("live", "").lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_apply.py::test_a_missing_dsn_yields_pending_live_not_a_pass -v`
Expected: FAIL — `live` is absent or claims success.

- [ ] **Step 3: Write minimal implementation**

Emit `[PENDING LIVE PROFILE]` when no DSN resolves; never synthesize a live result.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_apply.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_apply.py src/seshat/studio/apply.py
git commit -m "feat: mark live verification pending when no DSN resolves"
```

---

### Task 4.4: Client review scope exposes only in-scope decisions

- [ ] **Step 1: Write the failing test**

```python
def test_review_scope_hides_out_of_scope_decisions_and_tool_approval(
    studio_client, two_scoped_decisions
):
    response = studio_client.authenticated().get(
        "/api/v1/review?scope=sales_margin"
    )
    body = response.json()
    ids = {item["id"] for item in body["decisions"]}
    assert ids == {"sales_margin"}
    assert "tool_approval" not in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_review_scope.py -v`
Expected: FAIL — 404, route not registered.

- [ ] **Step 3: Write minimal implementation**

Create `src/seshat/studio/review_scope.py` filtering to the named scope. Filter
server-side; a client-side hide is not least privilege.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_studio_review_scope.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_studio_review_scope.py src/seshat/studio/review_scope.py src/seshat/studio/app.py
git commit -m "feat: scope client review to its selected decisions"
```

---

## Traceability

| Requirement | Task |
| --- | --- |
| FR-140-002 | 2.2 |
| FR-140-005 | 3.1 |
| FR-140-006 | 2.1, 3.1 |
| FR-140-008 | 3.2 |
| FR-140-009 | 3.3 |
| FR-140-010 | 1.1 |
| FR-140-011 | 1.2, 1.4 |
| FR-140-012 | 3.6 |
| FR-140-014 | 4.2 |
| FR-140-015 | 3.5 |
| FR-140-016 | 4.3 |
| FR-140-017 | 4.3 |
| FR-140-018 | 4.4 |
| FR-140-019 | 2.3 |
| FR-140-021 | 3.4 |
| FR-140-022 | 1.2, 1.3 |
| FR-140-023 | 1.5 |
| SC-140-003 | 3.5 |
| SC-140-004 | 3.3 |
| SC-140-005 | 4.2 |
| SC-140-006 | 3.6 |

FR-140-001, -003, -004, -007, -013, -020 are constraints on how the above are built
rather than separately testable units; they are enforced by the Phase gates and by
review of the contract, not by a dedicated task.
