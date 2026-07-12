"""Integration test: blueprint approval versioning (spec 123, US6, T023).

FR-023/FR-024: a post-approval blueprint change MUST mark the prior
`dashboard_blueprint_approval` decision `superseded` (with `superseded_by`
referencing the new record per DS4), preserve history, and require renewed
approval before compilation; an UNCHANGED approved blueprint MUST NOT require
forced re-approval.

This REUSES the shipped DS4 machinery end-to-end -- it builds no second
supersession system:

* the static lint (`seshat.rules.decision_store.check_ds4`, backed by the
  shared `active_scope_conflicts` predicate) proves the supersession chain is
  structurally valid (refs resolve, no unresolved active-record conflict) and
  that an unresolved change (old still `approved`, no supersession) IS flagged
  as a conflict;
* the runtime gate (`seshat.decision_gate.compute_verdict` /
  `_FLOW_TO_SPINE`) proves the *behavioral* half: a pending renewal blocks
  `pbip_prototype_readiness` (the pre-compilation stage) naming the pending
  record, a freshly-approved renewal passes, and an unchanged single approval
  passes with no forced re-approval.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from seshat.decision_gate import verdict_for
from seshat.rules.decision_store import check_ds4

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLOW_REL = "contracts/knowledge/database-to-pbip-flow.yaml"
_AUTHORITY_REL = "contracts/knowledge/approval-authority.yaml"
_SEMANTIC = ".seshat/semantic-decisions.yaml"

_OLD_ID = "dashboard_blueprint_approval.branch_perf"
_NEW_ID = "dashboard_blueprint_approval.branch_perf.2"
_SCOPE = "{artifacts: [dashboard_blueprint.branch_perf]}"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo(tmp_path: Path, files: dict[str, str]) -> tuple[Path, tuple[str, ...]]:
    """Materialize a workspace carrying the real flow + authority contracts (the
    gate's fail-closed precondition needs both to resolve a verdict at all)."""
    all_files = dict(files)
    all_files[_FLOW_REL] = (_REPO_ROOT / _FLOW_REL).read_text(encoding="utf-8")
    all_files[_AUTHORITY_REL] = (_REPO_ROOT / _AUTHORITY_REL).read_text(
        encoding="utf-8"
    )
    tracked = []
    for rel, body in all_files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        tracked.append(rel)
    return tmp_path, tuple(tracked)


def _old_approved_block(ev_sha: str, *, status: str, extra: str = "") -> str:
    """The original approved `dashboard_blueprint_approval` record. Its approval
    block is retained even once superseded -- history is preserved, never
    erased (FR-023)."""
    return (
        f"  - id: {_OLD_ID}\n"
        "    decision_type: dashboard_blueprint_approval\n"
        "    statement: initial blueprint approval\n"
        f"    scope: {_SCOPE}\n"
        f"    status: {status}\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n' + extra + "    approval:\n"
        '      approved_by: "R. Owner (report_owner)"\n'
        '      approved_at: "2026-01-02"\n'
        "      source: interview\n"
        "      evidence: [ev.md]\n"
        f"      evidence_identity: {{ev.md: {ev_sha}}}\n"
        f"      reviewed_scope: {_SCOPE}\n"
    )


def _new_record(*, status: str, extra: str = "", approval_block: str = "") -> str:
    return (
        f"  - id: {_NEW_ID}\n"
        "    decision_type: dashboard_blueprint_approval\n"
        "    statement: renewed blueprint approval after change\n"
        f"    scope: {_SCOPE}\n"
        f"    status: {status}\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-03"\n' + extra + approval_block
    )


# ---------------------------------------------------------------------------
# DS4 static: supersession chain integrity + history preservation
# ---------------------------------------------------------------------------


def test_ds4_clean_supersession_chain_has_no_findings(tmp_path: Path) -> None:
    """Old superseded->new, new supersedes->old, both refs resolve, only one
    ACTIVE record on the scope -> DS4 is silent (the chain is well-formed and
    history -- the old record's full approval block -- is preserved on disk)."""
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("blueprint evidence v1\n", encoding="utf-8")
    sha = _sha(ev)

    old = _old_approved_block(
        sha, status="superseded", extra=f"    superseded_by: {_NEW_ID}\n"
    )
    new = _new_record(
        status="pending",
        extra=f"    supersedes: {_OLD_ID}\n",
    )
    body = "decisions:\n" + old + new

    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    findings = list(check_ds4(_ctx_from(root, tracked)))
    assert findings == [], [f.message for f in findings]

    # History preserved: the superseded record's own approval evidence is
    # still readable on disk, unmutated -- supersession never erases it.
    on_disk = (root / _SEMANTIC).read_text(encoding="utf-8")
    assert "renewed blueprint approval after change" in on_disk
    assert "initial blueprint approval" in on_disk
    assert "R. Owner (report_owner)" in on_disk  # old approval line intact


def test_ds4_flags_unresolved_change_as_a_conflict(tmp_path: Path) -> None:
    """The mutation-without-supersession case: old blueprint approval STILL
    `approved` (not superseded) while a second active record exists on the
    same scope, with no supersession link -- DS4 must flag this as a
    conflicting-active-records defect, proving an approved blueprint cannot
    be silently mutated out from under its approval (FR-023)."""
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("blueprint evidence v1\n", encoding="utf-8")
    sha = _sha(ev)

    old = _old_approved_block(sha, status="approved")  # NOT superseded
    new = _new_record(status="pending")  # NOT linked via supersedes/superseded_by
    body = "decisions:\n" + old + new

    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    findings = list(check_ds4(_ctx_from(root, tracked)))
    assert any("conflicting active" in f.message for f in findings), [
        f.message for f in findings
    ]


# ---------------------------------------------------------------------------
# Gate (runtime): renewed approval required before compilation
# ---------------------------------------------------------------------------


def test_pending_renewal_blocks_pre_compilation_stage(tmp_path: Path) -> None:
    """A post-approval blueprint change (old superseded, new renewal PENDING)
    must block `pbip_prototype_readiness` -- the stage that gates PBIR
    compilation -- naming the pending renewal record."""
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("blueprint evidence v1\n", encoding="utf-8")
    sha = _sha(ev)

    old = _old_approved_block(
        sha, status="superseded", extra=f"    superseded_by: {_NEW_ID}\n"
    )
    new = _new_record(status="pending", extra=f"    supersedes: {_OLD_ID}\n")
    body = "decisions:\n" + old + new

    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "pbip_prototype_readiness")
    assert v.verdict == "blocked"
    assert any(_NEW_ID in b.decision_id for b in v.blocking), v.blocking


def test_freshly_approved_renewal_passes_pre_compilation_stage(tmp_path: Path) -> None:
    """Once the renewal is itself approved (named report_owner, fresh
    evidence), the pre-compilation stage passes again -- renewed approval
    unblocks compilation."""
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("blueprint evidence v2\n", encoding="utf-8")
    sha = _sha(ev)

    old = _old_approved_block(
        sha, status="superseded", extra=f"    superseded_by: {_NEW_ID}\n"
    )
    new_approval = (
        "    approval:\n"
        '      approved_by: "R. Owner (report_owner)"\n'
        '      approved_at: "2026-01-04"\n'
        "      source: interview\n"
        "      evidence: [ev.md]\n"
        f"      evidence_identity: {{ev.md: {sha}}}\n"
        f"      reviewed_scope: {_SCOPE}\n"
    )
    new = _new_record(
        status="approved",
        extra=f"    supersedes: {_OLD_ID}\n",
        approval_block=new_approval,
    )
    body = "decisions:\n" + old + new

    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "pbip_prototype_readiness")
    assert v.verdict == "pass", v
    assert "ev.md" in v.evidence


def test_unchanged_approved_blueprint_needs_no_forced_reapproval(
    tmp_path: Path,
) -> None:
    """FR-024: a SINGLE approved `dashboard_blueprint_approval` that was never
    superseded (no blueprint change happened) passes the pre-compilation stage
    outright -- no renewal record is required."""
    ev = tmp_path / "ev.md"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text("blueprint evidence, never changed\n", encoding="utf-8")
    sha = _sha(ev)

    only = _old_approved_block(sha, status="approved")
    body = "decisions:\n" + only

    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    v = verdict_for(root, tracked, "pbip_prototype_readiness")
    assert v.verdict == "pass", v


# ---------------------------------------------------------------------------
# Test-local RuleContext helper (mirrors test_decision_store_rules.py's _ctx)
# ---------------------------------------------------------------------------


def _ctx_from(repo_root: Path, tracked_files: tuple[str, ...]):
    from seshat.core import RuleContext

    return RuleContext(repo_root=repo_root, tracked_files=tracked_files)
