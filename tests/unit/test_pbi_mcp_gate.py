"""Spec 149 T009-T014 -- the write preconditions, fail-closed.

US2 is built BEFORE US1 deliberately: the refusal path IS the governance, and
building the write path first would leave a window in which mutation exists
without a proven gate.

**The fixtures COMMIT their records.** An earlier draft of this suite wrote
readiness records to the worktree and asserted they cleared, which encoded the
worst fail-open in the feature -- an agent authoring its own approval -- as
correct behavior, with a green suite. ``committed_repo`` therefore runs real
``git`` commands, and ``test_uncommitted_but_passing_record_refuses`` is the
positive control that proves the committed-state check is load-bearing.

Two repo-earned bars enforced structurally, not by convention:

* **No absence-assertions.** Nothing asserts a symbol is missing; every test
  asserts an observable verdict, so it cannot go green when a capability ships in
  a different shape.
* **No vacuous branches.** The precondition suite is hold-N-break-one AND asserts
  a refusal COUNT, so a branch that stopped being exercised is visible.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate

pytestmark = pytest.mark.unit


TARGET = "sales_model"
OTHER_TARGET = "returns_model"
#: An operation id the committed allowlist approves for TARGET.
OPERATION = "update_measure"
#: A shape-valid owner: a named decider WITH an authority class. A bare name is
#: rejected by ``approval_is_shape_valid`` (issue #487), which is why the earlier
#: draft's ``owner: Ahmed Shaaban`` was itself wrong.
OWNER = "Ahmed Shaaban (data_owner)"


def _readiness_yaml(
    *,
    target: str = TARGET,
    semantic_status: str = "pass",
    approval_note: str | None = None,
    approval_stage: str = "publish_ready",
    owner: str = OWNER,
    include_approval: bool = True,
) -> str:
    note = (
        f"approved for {target}: {OPERATION}"
        if approval_note is None
        else approval_note
    )
    body = (
        "stages:\n"
        f"  semantic_model_ready:\n    status: {semantic_status}\n"
        "  publish_ready:\n    status: pass\n"
    )
    if include_approval:
        body += (
            "approvals:\n"
            f"  - stage: {approval_stage}\n"
            f"    owner: {owner!r}\n"
            "    at: '2026-08-18'\n"
            f"    note: {note!r}\n"
        )
    return body


def _allowlist_yaml(targets: tuple[str, ...] = (TARGET,)) -> str:
    if not targets:
        return "targets: []\n"
    rows = "".join(
        f"  - target_id: {name}\n"
        f"    path: models/{name}.tmdl\n"
        "    operations:\n"
        f"      - {OPERATION}\n"
        for name in targets
    )
    return f"targets:\n{rows}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def _write(repo: Path, relpath: str, text: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message, "--no-gpg-sign")


def _build_repo(
    tmp_path: Path,
    *,
    readiness: str | None = None,
    allowlist: str | None = None,
    artifacts: tuple[str, ...] = (TARGET,),
    target: str = TARGET,
    commit: bool = True,
) -> Path:
    """A repo with the requested state, committed unless told otherwise."""
    repo = _init_repo(tmp_path)
    if readiness is not None:
        _write(repo, f"mappings/{target}/readiness-status.yaml", readiness)
    if allowlist is not None:
        _write(repo, gate.TARGET_ALLOWLIST_RELPATH, allowlist)
    for name in artifacts:
        _write(repo, f"models/{name}.tmdl", f"// {name}\n")
    # A repo needs at least one commit for HEAD to resolve.
    _write(repo, "README.md", "fixture\n")
    if commit:
        _commit_all(repo)
    else:
        # Commit ONLY the baseline so HEAD exists; leave the state files untracked.
        _git(repo, "add", "README.md")
        for name in artifacts:
            _git(repo, "add", f"models/{name}.tmdl")
        if allowlist is not None:
            _git(repo, "add", gate.TARGET_ALLOWLIST_RELPATH)
        _git(repo, "commit", "-q", "-m", "baseline", "--no-gpg-sign")
    return repo


@pytest.fixture
def committed_repo(tmp_path: Path) -> Path:
    """A repo where every precondition holds, all state COMMITTED."""
    return _build_repo(
        tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
    )


def _evaluate(repo: Path, **kwargs: object) -> gate.GateVerdict:
    params: dict[str, object] = {
        "repo_root": repo,
        "target_id": TARGET,
        "operation_id": OPERATION,
        "tree_clean": True,
    }
    params.update(kwargs)
    return gate.evaluate(**params)  # type: ignore[arg-type]


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


def _repo_for_case(tmp_path: Path, label: str) -> tuple[Path, dict[str, object]]:
    """Build a repo breaking exactly ``label`` and return the evaluate kwargs."""
    if label == "stage_not_pass":
        repo = _build_repo(
            tmp_path,
            readiness=_readiness_yaml(semantic_status="warning"),
            allowlist=_allowlist_yaml(),
        )
        return repo, {}
    if label == "state_uncommitted":
        repo = _build_repo(
            tmp_path,
            readiness=_readiness_yaml(),
            allowlist=_allowlist_yaml(),
            commit=False,
        )
        return repo, {}
    if label == "approval_absent":
        repo = _build_repo(
            tmp_path,
            readiness=_readiness_yaml(include_approval=False),
            allowlist=_allowlist_yaml(),
        )
        return repo, {}
    if label == "approval_wrong_target":
        repo = _build_repo(
            tmp_path,
            readiness=_readiness_yaml(approval_note=f"approved for {OTHER_TARGET}"),
            allowlist=_allowlist_yaml(),
        )
        return repo, {}
    if label == "operation_unbound":
        repo = _build_repo(
            tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
        )
        return repo, {"operation_id": ""}
    if label == "target_not_allowlisted":
        repo = _build_repo(
            tmp_path,
            readiness=_readiness_yaml(),
            allowlist=_allowlist_yaml(targets=(OTHER_TARGET,)),
        )
        return repo, {}
    if label == "target_absent_on_disk":
        repo = _build_repo(
            tmp_path,
            readiness=_readiness_yaml(),
            allowlist=_allowlist_yaml(),
            artifacts=(),
        )
        return repo, {}
    if label == "git_dirty_no_backup":
        repo = _build_repo(
            tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
        )
        return repo, {"tree_clean": False, "backup_ref": None}
    raise AssertionError(f"unhandled case {label!r}")


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


# --------------------------------------------------------------------------
# CRITICAL-3 / T012 -- the allowlist is COMMITTED, never caller-supplied
# --------------------------------------------------------------------------


def test_target_not_in_the_committed_allowlist_refuses(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(targets=(OTHER_TARGET,)),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_evaluate_exposes_no_way_for_a_caller_to_widen_the_allowlist() -> None:
    """The provenance control CRITICAL-3 demanded.

    Asserted against the actual signature: if a future edit adds an allowlist
    parameter, the requesting party could supply the list permitting it, and
    FR-007 would authorize nothing. Pins the CAPABILITY (no caller-supplied
    allowlist) rather than the absence of one specific name.
    """
    import inspect

    params = set(inspect.signature(gate.evaluate).parameters)
    forbidden = {
        "allow",
        "allowlist",
        "target_allowlist",
        "allowed_targets",
        "allows",
        # Asserted-permission parameters: a caller that can pass these can lie.
        "operation_binds",
        "backup_declared",
        "approval_ok",
        "stage_pass",
    }
    leaked = params & forbidden
    assert not leaked, (
        f"gate.evaluate must not accept a caller-supplied allowlist; found {leaked}"
    )


def test_uncommitted_allowlist_widening_is_invisible(tmp_path: Path) -> None:
    """Adding a target to the allowlist without committing must not permit it."""
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(targets=(OTHER_TARGET,)),
    )
    _write(repo, gate.TARGET_ALLOWLIST_RELPATH, _allowlist_yaml(targets=(TARGET,)))
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_missing_allowlist_refuses_everything(tmp_path: Path) -> None:
    """No allowlist is a refusal, never an implicit permit-all."""
    repo = _build_repo(tmp_path, readiness=_readiness_yaml(), allowlist=None)
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_target_allowlisted_but_absent_on_disk_refuses(tmp_path: Path) -> None:
    """Refused as an undefined artifact -- never invented (FR-011)."""
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(),
        artifacts=(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ABSENT in verdict.blockers


# --------------------------------------------------------------------------
# FR-011a/c -- operation binding is distinct from target-naming
# --------------------------------------------------------------------------


def test_unbound_operation_refuses_even_with_a_valid_target_approval(
    committed_repo: Path,
) -> None:
    """Target-naming alone must NOT authorize an arbitrary mutation (FR-011c).

    This is the fail-open a caller holding one valid approval would otherwise
    exploit by substituting an unrelated operation.
    """
    verdict = _evaluate(committed_repo, operation_id="")
    assert not verdict.cleared
    assert verdict.approval_names_target, "the approval itself is valid"
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_omitting_the_operation_refuses(committed_repo: Path) -> None:
    """No operation id means nothing resolved; it never clears by omission."""
    verdict = gate.evaluate(committed_repo, TARGET, tree_clean=True)
    assert not verdict.cleared
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


# --------------------------------------------------------------------------
# T013 -- git safety
# --------------------------------------------------------------------------


def test_dirty_tree_without_declared_backup_refuses(committed_repo: Path) -> None:
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref=None)
    assert not verdict.cleared
    assert gate.BLOCKER_GIT_UNSAFE in verdict.blockers


def test_dirty_tree_with_declared_backup_clears(committed_repo: Path) -> None:
    """The declared-backup escape must actually work.

    Its absence would refuse every dirty tree, which the spec does not require.
    """
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert verdict.git_safe
    assert verdict.cleared


def test_clean_tree_clears_without_a_backup(committed_repo: Path) -> None:
    assert _evaluate(committed_repo, tree_clean=True, backup_ref=None).git_safe


# --------------------------------------------------------------------------
# T014 -- a refusal has no warning-level representation
# --------------------------------------------------------------------------


def test_non_empty_blockers_is_always_blocking(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(semantic_status="warning"),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert verdict.blockers
    assert not verdict.cleared
    assert verdict.blocking is True


def test_cleared_and_blocking_are_mutually_exclusive(committed_repo: Path) -> None:
    verdict = _evaluate(committed_repo)
    assert verdict.cleared is True
    assert verdict.blocking is False


def test_verdict_is_immutable(committed_repo: Path) -> None:
    """A caller cannot flip a refusal into a pass after the fact."""
    verdict = _evaluate(committed_repo)
    with pytest.raises(Exception):
        verdict.blockers = ()  # type: ignore[misc]


def test_verdict_carries_no_score(committed_repo: Path) -> None:
    """Hard rule #9 at the gate boundary: typed blockers, never a number."""
    verdict = _evaluate(committed_repo)
    for name, value in vars(verdict).items():
        if isinstance(value, bool):
            continue
        assert not isinstance(value, (int, float)), f"{name} looks like a score"


def test_every_blocker_id_has_readable_detail() -> None:
    """A typed blocker a human cannot read is not actionable."""
    ids = [
        value
        for name, value in vars(gate).items()
        if name.startswith("BLOCKER_") and isinstance(value, str)
    ]
    assert len(ids) == 15
    for blocker in ids:
        assert gate.BLOCKER_DETAIL.get(blocker), blocker
        assert blocker.startswith("PBIMCP-GATE-")


# --------------------------------------------------------------------------
# T019 -- the fail-open proof
# --------------------------------------------------------------------------


def test_committed_state_guard_is_what_produces_the_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable ONLY the committed-state guard; assert the old verdict returns.

    A refusal test alone cannot distinguish "the guard refused this" from "this
    would have been refused anyway for some other reason". This monkeypatches out
    exactly one thing and shows the same agent-authored, never-committed approval
    then CLEARS -- so the guard is load-bearing rather than incidental.
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(),
        commit=False,
    )

    guarded = _evaluate(repo)
    assert not guarded.cleared
    assert gate.BLOCKER_STATE_UNCOMMITTED in guarded.blockers

    monkeypatch.setattr(gate, "is_tracked_and_clean", lambda root, rel: True)
    monkeypatch.setattr(
        gate,
        "committed_text",
        lambda root, rel: (Path(root) / rel).read_text(encoding="utf-8"),
    )

    unguarded = _evaluate(repo)
    assert unguarded.cleared, (
        "expected the fail-open to reproduce once the guard is removed; if this "
        "fails the refusal above came from something other than the guard, and "
        "the guard is not actually protecting anything"
    )


# --------------------------------------------------------------------------
# Advisor findings 1-4: every precondition is DERIVED, never asserted
# --------------------------------------------------------------------------


def test_operation_must_resolve_against_the_committed_allowlist(
    tmp_path: Path,
) -> None:
    """An unlisted operation id refuses, even for a fully approved target.

    FR-011a: the operation is *resolved from* the committed set, never accepted
    as free-form input. An earlier draft took ``operation_binds: bool`` from the
    caller -- which is a request, not a gate.
    """
    repo = _build_repo(
        tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
    )
    verdict = _evaluate(repo, operation_id="drop_all_tables")
    assert not verdict.cleared
    assert not verdict.operation_binds
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_operation_approved_for_another_target_does_not_authorize_this_one(
    tmp_path: Path,
) -> None:
    """FR-011c: an operation approved elsewhere is not approved here.

    ``other_only`` is listed for OTHER_TARGET, so requesting it against TARGET
    must refuse even though both targets are allowlisted.
    """
    allowlist = (
        "targets:\n"
        f"  - target_id: {TARGET}\n    path: models/{TARGET}.tmdl\n"
        f"    operations:\n      - {OPERATION}\n"
        f"  - target_id: {OTHER_TARGET}\n    path: models/{OTHER_TARGET}.tmdl\n"
        "    operations:\n      - other_only\n"
    )
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=allowlist,
        artifacts=(TARGET, OTHER_TARGET),
    )
    verdict = _evaluate(repo, operation_id="other_only")
    assert not verdict.cleared
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_target_with_no_approved_operations_refuses_every_operation(
    tmp_path: Path,
) -> None:
    """An allowlist entry omitting ``operations`` permits nothing.

    A missing key must not read as "all operations allowed" -- that would make
    the safest-looking entry the most permissive.
    """
    allowlist = f"targets:\n  - target_id: {TARGET}\n    path: models/{TARGET}.tmdl\n"
    repo = _build_repo(tmp_path, readiness=_readiness_yaml(), allowlist=allowlist)
    verdict = _evaluate(repo, operation_id=OPERATION)
    assert not verdict.cleared
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_unprobed_git_state_refuses(committed_repo: Path) -> None:
    """``tree_clean=None`` means never probed, and refuses.

    A ``True`` default would let a caller that forgot to probe git clear the
    git-safety leg by omission -- a fail-open default next to a fail-closed one.
    """
    verdict = gate.evaluate(committed_repo, TARGET, OPERATION)
    assert not verdict.cleared
    assert not verdict.git_safe
    assert gate.BLOCKER_GIT_UNPROBED in verdict.blockers


def test_unresolvable_backup_ref_refuses(committed_repo: Path) -> None:
    """A backup must be VERIFIED, not attested.

    The operator names a ref; if it does not resolve, the precondition fails.
    A boolean ``--backup-declared`` let the requesting party satisfy the
    precondition protecting the request.
    """
    verdict = _evaluate(
        committed_repo, tree_clean=False, backup_ref="refs/tags/no-such-backup"
    )
    assert not verdict.cleared
    assert not verdict.git_safe
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in verdict.blockers


def test_resolvable_backup_ref_clears(committed_repo: Path) -> None:
    """The positive control: a real ref does satisfy the leg."""
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert verdict.git_safe
    assert verdict.cleared


def test_backup_ref_guard_is_load_bearing(
    committed_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable the ref checks one at a time; each refusal must disappear in turn.

    There are now TWO independent guards on a declared backup -- the ref must
    resolve, AND it must hold the target's current content. Disabling only the
    first leaves the second refusing, which is defence in depth working. So this
    proves each guard separately rather than asserting the whole leg clears.
    """
    bogus = "refs/tags/no-such-backup"

    # Guard 1: resolution.
    first = _evaluate(committed_repo, tree_clean=False, backup_ref=bogus)
    assert not first.cleared
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in first.blockers

    monkeypatch.setattr(gate, "_ref_resolves", lambda root, ref: True)

    # With resolution neutered the refusal MOVES to the custody guard -- proof
    # that guard 1 produced the first refusal and guard 2 is independent.
    second = _evaluate(committed_repo, tree_clean=False, backup_ref=bogus)
    assert not second.cleared
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE not in second.blockers
    assert gate.BLOCKER_BACKUP_MISSES_TARGET in second.blockers

    # Guard 2: custody. With both neutered the leg clears, so nothing incidental
    # was producing these refusals.
    monkeypatch.setattr(gate, "_ref_holds_target", lambda root, ref, rel: True)
    assert _evaluate(committed_repo, tree_clean=False, backup_ref=bogus).cleared


def test_uncommitted_allowlist_names_its_own_blocker(tmp_path: Path) -> None:
    """An uncommitted allowlist is reported DISTINCTLY from not-allowlisted.

    Collapsing both into ``TARGET_NOT_ALLOWLISTED`` would tell an operator to
    add a target they already added -- FR-009 requires the specific cause.
    """
    repo = _init_repo(tmp_path)
    _write(repo, f"mappings/{TARGET}/readiness-status.yaml", _readiness_yaml())
    _write(repo, f"models/{TARGET}.tmdl", "// m\n")
    _write(repo, "README.md", "x\n")
    _commit_all(repo)
    # Add the allowlist AFTER the commit: present in the worktree, not in HEAD.
    _write(repo, gate.TARGET_ALLOWLIST_RELPATH, _allowlist_yaml())
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_ALLOWLIST_UNCOMMITTED in verdict.blockers


def test_git_state_probe_failure_is_not_a_pass(committed_repo: Path) -> None:
    """A git failure while verifying a backup ref must refuse, not clear.

    ``dagster_adapter/evidence._is_workspace_dirty`` returns False (clean) on an
    exception; this asserts the opposite posture here.
    """

    def _boom(repo_root: Path, *args: str) -> None:
        raise OSError("git unavailable")

    import seshat.pbi_mcp_adapter.gate as gate_module

    original = gate_module.run_git
    try:
        gate_module.run_git = _boom  # type: ignore[assignment]
        verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    finally:
        gate_module.run_git = original  # type: ignore[assignment]
    assert not verdict.cleared
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in verdict.blockers


# --------------------------------------------------------------------------
# Containment: an allowlisted path must not escape the repository
# --------------------------------------------------------------------------


def _repo_with_escaping_path(tmp_path: Path, path_value: str) -> Path:
    """A committed allowlist whose entry points outside the repo."""
    outside = tmp_path / "outside.tmdl"
    outside.write_text("// outside the repo\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _write(repo, f"mappings/{TARGET}/readiness-status.yaml", _readiness_yaml())
    _write(
        repo,
        gate.TARGET_ALLOWLIST_RELPATH,
        f"targets:\n  - target_id: {TARGET}\n"
        f"    path: {path_value.replace('{OUT}', outside.as_posix())}\n"
        f"    operations:\n      - {OPERATION}\n",
    )
    _write(repo, f"models/{TARGET}.tmdl", "// inside\n")
    _write(repo, "README.md", "fixture\n")
    _commit_all(repo)
    return repo


@pytest.mark.parametrize(
    "path_value",
    [
        pytest.param("../outside.tmdl", id="parent-traversal"),
        pytest.param("models/../../outside.tmdl", id="traversal-via-subdir"),
        pytest.param("{OUT}", id="absolute-path"),
    ],
)
def test_allowlisted_path_escaping_the_repo_refuses(
    tmp_path: Path, path_value: str
) -> None:
    """A write target must be contained by the repo it is governed in.

    The allowlist is committed and reviewed, so an escaping entry would have to
    pass a human -- but "a reviewer would have noticed" is exactly the vigilance
    assumption this gate replaces. Found by attacking the gate after it was
    written: the escape CLEARED every precondition, because containment was
    trusted rather than enforced.
    """
    repo = _repo_with_escaping_path(tmp_path, path_value)
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ESCAPES_REPO in verdict.blockers


def test_escape_is_refused_for_escaping_not_for_being_absent(
    tmp_path: Path,
) -> None:
    """The blocker must name the real cause.

    An escaping path that happens not to exist would otherwise be refused as
    TARGET_ABSENT, telling the operator to create the file -- which is the wrong
    fix and hides the containment breach.
    """
    repo = _repo_with_escaping_path(tmp_path, "../outside.tmdl")
    (tmp_path / "outside.tmdl").unlink()
    verdict = _evaluate(repo)
    assert gate.BLOCKER_TARGET_ESCAPES_REPO in verdict.blockers
    assert gate.BLOCKER_TARGET_ABSENT not in verdict.blockers


def test_a_contained_path_still_clears(committed_repo: Path) -> None:
    """The positive control: containment must not refuse legitimate targets."""
    assert _evaluate(committed_repo).cleared


def test_the_repo_root_itself_is_not_a_valid_target(tmp_path: Path) -> None:
    """``path: .`` resolves to the root, which is not a writable artifact."""
    repo = _init_repo(tmp_path)
    _write(repo, f"mappings/{TARGET}/readiness-status.yaml", _readiness_yaml())
    _write(
        repo,
        gate.TARGET_ALLOWLIST_RELPATH,
        f"targets:\n  - target_id: {TARGET}\n    path: .\n"
        f"    operations:\n      - {OPERATION}\n",
    )
    _write(repo, "README.md", "fixture\n")
    _commit_all(repo)
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ESCAPES_REPO in verdict.blockers


# --------------------------------------------------------------------------
# CRITICAL: a declared backup must HOLD the target, not merely resolve
# --------------------------------------------------------------------------


def test_backup_ref_head_on_a_dirty_tree_refuses(committed_repo: Path) -> None:
    """``--backup-ref HEAD`` with uncommitted target changes must REFUSE.

    The seventh caller-satisfies-its-own-precondition hole, found by an
    independent review of the built code. HEAD resolves fine and backs up
    NOTHING -- it is precisely where the uncommitted content is not. Worse, the
    rollback guidance would then emit ``git restore --source=HEAD``, destroying
    the operator's uncommitted work and calling it recovery.

    Verifying that a ref RESOLVES is verifying the wrong property; custody is
    what matters.
    """
    target = committed_repo / "models" / f"{TARGET}.tmdl"
    target.write_text("// UNCOMMITTED WORK IN PROGRESS\n", encoding="utf-8")

    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert not verdict.cleared
    assert not verdict.git_safe
    assert gate.BLOCKER_BACKUP_MISSES_TARGET in verdict.blockers


def test_a_backup_ref_that_holds_the_target_clears(committed_repo: Path) -> None:
    """The positive control: a genuine backup DOES satisfy the leg.

    Without this the custody check could refuse every backup and still pass the
    test above. The tree is dirty in a file OTHER than the target, so HEAD
    genuinely holds the target's current content.
    """
    (committed_repo / "README.md").write_text("dirtied elsewhere\n", encoding="utf-8")
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert verdict.git_safe
    assert verdict.cleared


def test_a_stash_style_ref_capturing_the_change_clears(committed_repo: Path) -> None:
    """A ref created AFTER the edit holds it, so it is a real backup.

    Uses ``git stash create``, which writes a commit object without touching the
    worktree -- the realistic way an operator captures work in progress.
    """
    target = committed_repo / "models" / f"{TARGET}.tmdl"
    target.write_text("// work in progress\n", encoding="utf-8")
    created = subprocess.run(
        ["git", "stash", "create"],
        cwd=committed_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    stash_sha = created.stdout.strip()
    assert stash_sha, "git stash create produced no object"

    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref=stash_sha)
    assert verdict.git_safe, verdict.blockers
    assert verdict.cleared


# --------------------------------------------------------------------------
# HIGH: the named human must approve the OPERATION, not just the target
# --------------------------------------------------------------------------


def test_approval_naming_only_the_target_does_not_authorize_an_operation(
    tmp_path: Path,
) -> None:
    """One approval must not authorize every operation on a target forever.

    Before this check, "approved for sales_model" cleared any operation the
    allowlist happened to list -- so "approved" meant "committed to a YAML file",
    not "a named human ruled on this change". FR-011c requires BOTH checks.
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(approval_note=f"approved for {TARGET}"),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert verdict.approval_names_target, "the target IS named"
    assert not verdict.approval_names_operation
    assert gate.BLOCKER_APPROVAL_OPERATION in verdict.blockers


def test_approval_naming_target_and_operation_clears(committed_repo: Path) -> None:
    """The positive control for the operation-naming rule."""
    verdict = _evaluate(committed_repo)
    assert verdict.approval_names_operation
    assert verdict.cleared


def test_operation_must_be_named_as_a_whole_token_too(tmp_path: Path) -> None:
    """The same whole-token discipline applies to the operation name.

    An approval naming ``update_measure_draft`` must not authorize
    ``update_measure``.
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(
            approval_note=f"approved for {TARGET}: {OPERATION}_draft"
        ),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_APPROVAL_OPERATION in verdict.blockers
