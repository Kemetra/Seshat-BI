# Tasks: Studio Governed Analyst Workbench

**Feature**: `specs/140-studio-governed-workbench/` | **Plan**: [plan.md](./plan.md) |
**Spec**: [spec.md](./spec.md) | **Boundary contract**:
[contracts/decision-write-boundary.md](./contracts/decision-write-boundary.md)

**Spec status**: `draft`. Phases 0 and 1 (research, design) are complete. **Every task
below is BLOCKED until a named human ratifies this package and the sole active Spec Kit
fence points at this plan** (FR-140-020).

**Progress**: 0 of 18 implementation tasks. Nothing started.

TDD order: the failing test comes before the code. A task is done only when its test
was seen RED, then GREEN. Nothing is marked done that was not observed.

Phase order is mandatory: **Phase A must be fully green before Phase C begins**, because
C's routes depend on A's invariants.

---

## Phase A -- Decision Store write path (no UI)

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
        decision_type="metric_definition",
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
        "status": "decided",
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
        decision_type="metric_definition",
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
        decision_type="non_critical_note",
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

from ruamel.yaml import YAML

_yaml = YAML()          # round-trip mode: preserves comments and key order
_yaml.preserve_quotes = True


def _atomic_append(path: Path, entry: dict[str, Any]) -> None:
    """Append one decision, then replace the file in a single atomic rename."""
    with path.open("r", encoding="utf-8") as handle:
        document = _yaml.load(handle) or {}
    document.setdefault("decisions", []).append(entry)

    directory = path.parent
    handle_fd, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as staged:
            _yaml.dump(document, staged)
        os.replace(temporary, path)      # atomic on POSIX and Windows
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
```

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
        decision_type="non_critical_note",
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
        decision_type="non_critical_note",
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
from seshat.studio import evidence


def test_a_table_with_malformed_evidence_reports_a_defect_not_a_pass(studio_snapshot):
    """Malformed evidence must surface as a defect. An empty success state here would
    present missing information as a clean bill of health."""
    bundle = evidence.bundle_for(studio_snapshot, "sales_malformed")
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
        defects=tuple(d for d in snapshot.defects if d.table_id == table_id),
        pending_live=tuple(
            stage.stage for stage in journey.stages if stage.pending_live
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
def test_every_claim_has_a_source_or_is_marked_pending_live(studio_snapshot):
    bundle = evidence.bundle_for(studio_snapshot, "sales")
    for stage in bundle.stages:
        assert stage.evidence or stage.stage in bundle.pending_live, (
            f"stage {stage.stage} displays a claim with no source reference"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_studio_evidence.py::test_every_claim_has_a_source_or_is_marked_pending_live -v`
Expected: FAIL until `pending_live` is populated from the live-boundary marker.

- [ ] **Step 3: Write minimal implementation**

Populate `pending_live` from the projection's existing `[PENDING LIVE PROFILE]` marker
rather than inferring it from an empty evidence list — an empty list means "no evidence",
which is a defect, not a pending boundary.

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
