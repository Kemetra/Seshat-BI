"""Spec 149 -- the readiness and approval preconditions, fail-closed.

US2 is built BEFORE US1 deliberately: the refusal path IS the governance.

The fixtures COMMIT their records. An earlier draft wrote readiness records to
the worktree and asserted they cleared, which encoded the worst fail-open in the
feature -- an agent authoring its own approval -- as correct behavior, green.
Shared builders live in ``_pbi_mcp_gate_fixtures``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate
from tests.unit._pbi_mcp_gate_fixtures import (
    OTHER_TARGET,
    OWNER,
    TARGET,
    _allowlist_yaml,
    _build_repo,
    _commit_all,
    _evaluate,
    _readiness_yaml,
    _write,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def committed_repo(tmp_path: Path) -> Path:
    """A repo where every precondition holds, all state COMMITTED."""
    return _build_repo(
        tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
    )


# --------------------------------------------------------------------------
# The positive control -- without it, every refusal test below could pass
# against a gate that refuses unconditionally.
# --------------------------------------------------------------------------


def test_all_preconditions_holding_clears_the_gate(committed_repo: Path) -> None:
    verdict = _evaluate(committed_repo)
    assert verdict.cleared, f"expected cleared, blockers={verdict.blockers}"
    assert verdict.blockers == ()
    assert verdict.blocking is False


# --------------------------------------------------------------------------
# CRITICAL-1 -- the committed-state check. THE catching test.
# --------------------------------------------------------------------------


def test_uncommitted_but_passing_record_refuses(tmp_path: Path) -> None:
    """A VALID, PASSING, UNCOMMITTED readiness record must refuse.

    This is the whole reason the gate reads HEAD instead of the worktree. The
    record below would satisfy every other precondition; it is refused solely
    because it never entered audit history. If this test fails, the agent can
    author its own approval (#334).
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(),
        commit=False,
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert not verdict.state_committed
    assert gate.BLOCKER_STATE_UNCOMMITTED in verdict.blockers


def test_committed_then_locally_edited_record_refuses(committed_repo: Path) -> None:
    """A committed record edited in the worktree is also refused.

    ``is_tracked_and_clean`` covers tracked-but-dirty, not just untracked -- so a
    passing record cannot be produced by editing a committed one.
    """
    _write(
        committed_repo,
        f"mappings/{TARGET}/readiness-status.yaml",
        _readiness_yaml(approval_note="approved for anything at all"),
    )
    verdict = _evaluate(committed_repo)
    assert not verdict.cleared
    assert gate.BLOCKER_STATE_UNCOMMITTED in verdict.blockers


def test_the_gate_reads_head_not_the_worktree(committed_repo: Path) -> None:
    """Behavioral proof of provenance: HEAD's value is the one that counts.

    Commit a NON-passing record, then write a passing one in the worktree. A
    worktree reader would clear; a HEAD reader must refuse.
    """
    _write(
        committed_repo,
        f"mappings/{TARGET}/readiness-status.yaml",
        _readiness_yaml(semantic_status="warning"),
    )
    _commit_all(committed_repo, "commit a NOT-pass record")
    _write(
        committed_repo,
        f"mappings/{TARGET}/readiness-status.yaml",
        _readiness_yaml(semantic_status="pass"),
    )
    verdict = _evaluate(committed_repo)
    assert not verdict.cleared, "a worktree-only 'pass' must never clear the gate"


# --------------------------------------------------------------------------
# T009 -- hold the rest, break one (with an explicit refusal COUNT)
# --------------------------------------------------------------------------

#: Each case breaks exactly ONE precondition and names the blocker it must
#: produce. Named explicitly rather than generated, so dropping a precondition
#: cannot hide behind a still-passing "all of them" phrase.
BREAK_ONE_CASES: tuple[tuple[str, str], ...] = (
    ("stage_not_pass", gate.BLOCKER_STAGE_NOT_PASS),
    ("state_uncommitted", gate.BLOCKER_STATE_UNCOMMITTED),
    ("approval_absent", gate.BLOCKER_APPROVAL_ABSENT),
    ("approval_wrong_target", gate.BLOCKER_APPROVAL_TARGET),
    ("operation_unbound", gate.BLOCKER_OPERATION_UNBOUND),
    ("target_not_allowlisted", gate.BLOCKER_TARGET_NOT_ALLOWLISTED),
    ("target_absent_on_disk", gate.BLOCKER_TARGET_ABSENT),
    ("git_dirty_no_backup", gate.BLOCKER_GIT_UNSAFE),
)


#: label -> (readiness overrides, allowlist targets, evaluate overrides).
#: A table rather than an if-chain: each row IS the perturbation, so a reader sees
#: all eight break-one cases at once instead of tracing branches.
_CASE_TABLE: dict[
    str, tuple[dict[str, object], tuple[str, ...] | None, dict[str, object]]
] = {
    "stage_not_pass": ({"semantic_status": "warning"}, None, {}),
    "state_uncommitted": ({}, None, {"__commit__": False}),
    "approval_absent": ({"include_approval": False}, None, {}),
    "approval_wrong_target": (
        {"approval_note": f"approved for {OTHER_TARGET}"},
        None,
        {},
    ),
    "operation_unbound": ({}, None, {"operation_id": ""}),
    "target_not_allowlisted": ({}, (OTHER_TARGET,), {}),
    "target_absent_on_disk": ({}, None, {"__artifacts__": ()}),
    "git_dirty_no_backup": ({}, None, {"tree_clean": False, "backup_ref": None}),
}


def _repo_for_case(tmp_path: Path, label: str) -> tuple[Path, dict[str, object]]:
    """Build a repo breaking exactly ``label`` and return the evaluate kwargs."""
    if label not in _CASE_TABLE:
        raise AssertionError(f"unhandled case {label!r}")
    readiness_overrides, allowlist_targets, evaluate_kwargs = _CASE_TABLE[label]
    kwargs = dict(evaluate_kwargs)
    repo_overrides: dict[str, object] = {
        "readiness": _readiness_yaml(**readiness_overrides),
        "allowlist": _allowlist_yaml(
            targets=allowlist_targets if allowlist_targets is not None else (TARGET,)
        ),
    }
    if "__commit__" in kwargs:
        repo_overrides["commit"] = kwargs.pop("__commit__")
    if "__artifacts__" in kwargs:
        repo_overrides["artifacts"] = kwargs.pop("__artifacts__")
    return _build_repo(tmp_path, **repo_overrides), kwargs


@pytest.mark.parametrize(
    ("label", "expected_blocker"),
    BREAK_ONE_CASES,
    ids=[case[0] for case in BREAK_ONE_CASES],
)
def test_hold_the_rest_break_one(
    tmp_path: Path, label: str, expected_blocker: str
) -> None:
    """Break exactly one precondition; assert refusal naming THAT precondition."""
    repo, kwargs = _repo_for_case(tmp_path, label)
    verdict = _evaluate(repo, **kwargs)
    assert not verdict.cleared, f"{label}: expected refusal"
    assert expected_blocker in verdict.blockers, (
        f"{label}: expected {expected_blocker!r}, got {verdict.blockers!r}"
    )


def test_every_precondition_has_its_own_break_case() -> None:
    """The anti-vacuity assertion: the refusal COUNT is pinned.

    If a precondition is dropped from the case list this fails, which is the
    point -- a suite that silently shrinks proves less each time while still
    reporting green.
    """
    assert len(BREAK_ONE_CASES) == 8
    assert len({case[1] for case in BREAK_ONE_CASES}) == 8, "blockers must be distinct"


def test_each_break_case_is_actually_exercised(tmp_path: Path) -> None:
    """Every declared case must genuinely produce its blocker.

    Guards against a case whose fixture stopped breaking what it claims -- the
    branch would go unexercised while the parameterized test still passed for
    the wrong reason.
    """
    produced: set[str] = set()
    for label, expected in BREAK_ONE_CASES:
        case_root = tmp_path / label
        case_root.mkdir()
        repo, kwargs = _repo_for_case(case_root, label)
        verdict = _evaluate(repo, **kwargs)
        assert expected in verdict.blockers, label
        produced.add(expected)
    assert produced == {case[1] for case in BREAK_ONE_CASES}


def test_each_unmet_precondition_contributes_a_distinct_blocker(
    tmp_path: Path,
) -> None:
    """Break several at once: distinct blockers, not one generic failure."""
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(semantic_status="warning", approval_note="nothing"),
        allowlist=_allowlist_yaml(targets=()),
        artifacts=(),
    )
    verdict = _evaluate(repo, operation_id="", tree_clean=False)
    assert not verdict.cleared
    assert len(set(verdict.blockers)) >= 4, verdict.blockers


# --------------------------------------------------------------------------
# T010 -- unreadable state fails CLOSED
# --------------------------------------------------------------------------


def test_absent_readiness_record_refuses(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path, readiness=None, allowlist=_allowlist_yaml())
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert not verdict.stage_readable
    assert gate.BLOCKER_STAGE_UNREADABLE in verdict.blockers


def test_malformed_readiness_record_refuses_without_raising(tmp_path: Path) -> None:
    """Malformed YAML becomes a typed refusal, NOT an exception.

    ``dagster_adapter/gate.py`` calls ``yaml.safe_load`` unguarded, so a
    malformed record raises out of the reader. A traceback is not a refusal: it
    has no blocker and an undefined exit code.
    """
    repo = _build_repo(
        tmp_path,
        readiness="stages: [this is: not valid: yaml\n",
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)  # must not raise
    assert not verdict.cleared
    assert not verdict.stage_readable
    assert gate.BLOCKER_STAGE_UNREADABLE in verdict.blockers


def test_readiness_record_that_is_not_a_mapping_refuses(tmp_path: Path) -> None:
    """Valid YAML of the wrong TYPE is still unreadable state."""
    repo = _build_repo(
        tmp_path, readiness="- just\n- a\n- list\n", allowlist=_allowlist_yaml()
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert not verdict.stage_readable


def test_empty_readiness_record_refuses(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path, readiness="", allowlist=_allowlist_yaml())
    assert not _evaluate(repo).cleared


# --------------------------------------------------------------------------
# T011 -- the approval note must name the target as a WHOLE TOKEN
# --------------------------------------------------------------------------


def test_approval_naming_a_prefix_does_not_authorize_the_longer_target(
    tmp_path: Path,
) -> None:
    """``sales_model`` must NOT authorize ``sales_model_v2``.

    ``\\b`` alone would pass this wrongly: ``_`` is a word character in ``re``.
    """
    longer = f"{TARGET}_v2"
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(
            target=longer, approval_note=f"approved for {TARGET}"
        ),
        allowlist=_allowlist_yaml(targets=(longer,)),
        artifacts=(longer,),
        target=longer,
    )
    verdict = _evaluate(repo, target_id=longer)
    assert not verdict.cleared
    assert not verdict.approval_names_target
    assert gate.BLOCKER_APPROVAL_TARGET in verdict.blockers


def test_approval_naming_the_exact_token_authorizes_it(committed_repo: Path) -> None:
    """The exact-token case must CLEAR -- the other half of the rule.

    Without it, the matcher could refuse everything and still pass the prefix
    test above.
    """
    verdict = _evaluate(committed_repo)
    assert verdict.approval_names_target
    assert verdict.cleared


@pytest.mark.parametrize(
    "note",
    [
        pytest.param(f"approved for {TARGET}", id="whitespace-delimited"),
        pytest.param(TARGET, id="whole-note"),
        pytest.param(f"target: {TARGET}.", id="trailing-period"),
        pytest.param(f"({TARGET})", id="parenthesised"),
        pytest.param(f"apply to {TARGET}, per ADR", id="comma-delimited"),
        pytest.param(f"{TARGET}/measure", id="slash-delimited"),
    ],
)
def test_target_named_at_a_token_boundary_is_recognised(note: str) -> None:
    assert gate.note_names_target(note, TARGET)


@pytest.mark.parametrize(
    "note",
    [
        pytest.param(f"{TARGET}_v2", id="longer-token-suffix"),
        pytest.param(f"pre_{TARGET}", id="prefixed-token"),
        pytest.param(f"{TARGET}x", id="suffixed-no-delimiter"),
        pytest.param(f"x{TARGET}", id="prefixed-no-delimiter"),
        pytest.param(f"{TARGET}2", id="digit-suffix"),
        pytest.param("approved for everything", id="generic-approval"),
        pytest.param("", id="empty-note"),
    ],
)
def test_target_not_named_at_a_boundary_is_refused(note: str) -> None:
    assert not gate.note_names_target(note, TARGET)


def test_approval_for_a_different_stage_does_not_count(tmp_path: Path) -> None:
    """Only a ``publish_ready`` row authorizes a write."""
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(approval_stage="semantic_model_ready"),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert verdict.approval is None
    assert gate.BLOCKER_APPROVAL_ABSENT in verdict.blockers


# --------------------------------------------------------------------------
# HIGH-1 -- approval shape is the SHARED predicate (issue #487)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "owner",
    [
        pytest.param("data_owner", id="bare-role-token"),
        pytest.param("data owner", id="bare-role-spaced"),
        pytest.param("Ahmed Shaaban", id="name-with-no-authority-class"),
        pytest.param("owner (data_owner)", id="role-masquerading-as-name"),
        pytest.param("Ada (wizard)", id="unknown-authority-class"),
        pytest.param("", id="empty-owner"),
    ],
)
def test_approval_with_an_invalid_owner_shape_refuses(
    tmp_path: Path, owner: str
) -> None:
    """Delegated to ``approval_is_shape_valid`` -- one definition of named human.

    A local re-implementation would be a fourth predicate; issue #487 records
    three surfaces disagreeing and failing OPEN on the approval path.
    """
    repo = _build_repo(
        tmp_path, readiness=_readiness_yaml(owner=owner), allowlist=_allowlist_yaml()
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert verdict.approval is None
    assert gate.BLOCKER_APPROVAL_ABSENT in verdict.blockers


def test_approval_without_an_iso_date_refuses(tmp_path: Path) -> None:
    """A missing/unparseable ``at:`` is not shape-valid either."""
    readiness = (
        "stages:\n  semantic_model_ready:\n    status: pass\n"
        "approvals:\n"
        "  - stage: publish_ready\n"
        f"    owner: {OWNER!r}\n"
        "    at: 'not-a-date'\n"
        f"    note: 'approved for {TARGET}'\n"
    )
    repo = _build_repo(tmp_path, readiness=readiness, allowlist=_allowlist_yaml())
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert verdict.approval is None
