"""Spec 149 T009-T014 -- the four write preconditions, fail-closed.

US2 is built BEFORE US1 deliberately: the refusal path IS the governance, and
building the write path first would leave a window in which mutation exists
without a proven gate.

Two repo-earned bars are enforced structurally here, not by convention:

* **No absence-assertions.** Nothing below asserts a symbol is missing. Each test
  asserts an observable verdict, so it cannot go green when the capability ships
  in a different shape.
* **No vacuous branches.** The precondition suite is hold-three-break-one AND
  asserts a refusal COUNT, so a branch that stopped being exercised is visible
  rather than silently skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# Fixture builders -- one happy-path repo, perturbed one precondition at a time
# --------------------------------------------------------------------------

TARGET = "sales_model"
OTHER_TARGET = "returns_model"


def _write_readiness(
    repo: Path,
    *,
    target: str = TARGET,
    semantic_status: str = "pass",
    approval_note: str | None = None,
    malformed: bool = False,
    omit: bool = False,
) -> None:
    """Write the per-target readiness record the gate reads.

    ``approval_note`` defaults to a note naming ``target`` exactly -- the
    happy path. Pass an explicit note to test the naming rule.
    """
    record = repo / "mappings" / target / "readiness-status.yaml"
    record.parent.mkdir(parents=True, exist_ok=True)
    if omit:
        return
    if malformed:
        record.write_text("stages: [this is: not valid: yaml\n", encoding="utf-8")
        return
    note = f"approved for {target}" if approval_note is None else approval_note
    record.write_text(
        "stages:\n"
        f"  semantic_model_ready:\n    status: {semantic_status}\n"
        "  publish_ready:\n    status: pass\n"
        "approvals:\n"
        "  - stage: publish_ready\n"
        "    owner: Ahmed Shaaban\n"
        "    at: '2026-08-18'\n"
        f"    note: {note!r}\n",
        encoding="utf-8",
    )


def _write_allowlist(repo: Path, targets: tuple[str, ...] = (TARGET,)) -> None:
    allowlist = repo / ".seshat" / "pbi-mcp-targets.yaml"
    allowlist.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        f"  - target_id: {name}\n    path: models/{name}.tmdl\n" for name in targets
    )
    allowlist.write_text(f"targets:\n{body}", encoding="utf-8")
    for name in targets:
        artifact = repo / "models" / f"{name}.tmdl"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(f"// {name}\n", encoding="utf-8")


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    """A repo where all four preconditions hold."""
    _write_readiness(tmp_path)
    _write_allowlist(tmp_path)
    return tmp_path


def _evaluate(repo: Path, **kwargs: object) -> gate.GateVerdict:
    """Evaluate the gate with happy-path defaults, overridable per test."""
    params: dict[str, object] = {
        "repo_root": repo,
        "target_id": TARGET,
        "backup_declared": False,
        "tree_clean": True,
    }
    params.update(kwargs)
    return gate.evaluate(**params)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# T009 -- hold three, break one (with an explicit refusal COUNT)
# --------------------------------------------------------------------------


def test_all_four_preconditions_holding_clears_the_gate(clean_repo: Path) -> None:
    """The positive control.

    Without this, every refusal test below could pass against a gate that
    refuses unconditionally -- the vacuity this suite is designed to expose.
    """
    verdict = _evaluate(clean_repo)
    assert verdict.cleared, f"expected cleared, blockers={verdict.blockers}"
    assert verdict.blockers == ()


#: Each case breaks exactly ONE precondition and names the blocker it must
#: produce. Named explicitly rather than generated, so that dropping a
#: precondition cannot hide behind a still-passing "all four" phrase (T009).
BREAK_ONE_CASES: tuple[tuple[str, dict[str, object], str], ...] = (
    ("stage_not_pass", {"semantic_status": "warning"}, gate.BLOCKER_STAGE_NOT_PASS),
    ("approval_wrong_target", {"approval_note": "approved for other"}, gate.BLOCKER_APPROVAL_TARGET),
    ("target_not_allowlisted", {"allowlist": ()}, gate.BLOCKER_TARGET_NOT_ALLOWLISTED),
    ("git_dirty_no_backup", {"tree_clean": False}, gate.BLOCKER_GIT_UNSAFE),
)


@pytest.mark.parametrize(
    ("label", "perturbation", "expected_blocker"),
    BREAK_ONE_CASES,
    ids=[case[0] for case in BREAK_ONE_CASES],
)
def test_hold_three_break_one(
    tmp_path: Path,
    label: str,
    perturbation: dict[str, object],
    expected_blocker: str,
) -> None:
    """Break exactly one precondition; assert refusal naming THAT precondition."""
    readiness_kwargs = {
        k: v for k, v in perturbation.items() if k in {"semantic_status", "approval_note"}
    }
    _write_readiness(tmp_path, **readiness_kwargs)  # type: ignore[arg-type]
    allowlist = perturbation.get("allowlist", (TARGET,))
    _write_allowlist(tmp_path, targets=allowlist)  # type: ignore[arg-type]

    verdict = _evaluate(tmp_path, tree_clean=perturbation.get("tree_clean", True))

    assert not verdict.cleared, f"{label}: expected refusal"
    assert expected_blocker in verdict.blockers, (
        f"{label}: expected blocker {expected_blocker!r}, got {verdict.blockers!r}"
    )


def test_every_precondition_has_its_own_break_case() -> None:
    """The anti-vacuity assertion: the refusal COUNT is pinned at four.

    If a precondition is ever dropped from the parameter list, this fails --
    which is the whole point. A suite that silently shrinks proves less each
    time while still reporting green.
    """
    assert len(BREAK_ONE_CASES) == 4
    assert len({case[2] for case in BREAK_ONE_CASES}) == 4, "blockers must be distinct"


def test_each_unmet_precondition_contributes_a_distinct_blocker(tmp_path: Path) -> None:
    """Break ALL four at once: four distinct blockers, not one generic failure."""
    _write_readiness(tmp_path, semantic_status="warning", approval_note="nothing named")
    _write_allowlist(tmp_path, targets=())
    verdict = _evaluate(tmp_path, tree_clean=False)
    assert not verdict.cleared
    assert len(set(verdict.blockers)) >= 4, verdict.blockers


# --------------------------------------------------------------------------
# T010 -- unreadable state fails CLOSED (three distinct cases)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "readiness_kwargs",
    [
        pytest.param({"omit": True}, id="absent"),
        pytest.param({"malformed": True}, id="malformed"),
    ],
)
def test_unreadable_state_refuses(
    tmp_path: Path, readiness_kwargs: dict[str, bool]
) -> None:
    """An unreadable gate is NEVER a passing gate (FR-005)."""
    _write_readiness(tmp_path, **readiness_kwargs)  # type: ignore[arg-type]
    _write_allowlist(tmp_path)
    verdict = _evaluate(tmp_path)
    assert not verdict.cleared
    assert not verdict.stage_readable
    assert gate.BLOCKER_STAGE_UNREADABLE in verdict.blockers


def test_unreadable_directory_refuses(tmp_path: Path) -> None:
    """A readiness path that is a DIRECTORY, not a file -- an OSError on read.

    Included as a third case because 'unreadable' in the spec is not only
    'absent' or 'malformed': a real filesystem produces read errors, and the
    fail-closed path must cover them rather than propagating an exception.
    """
    record = tmp_path / "mappings" / TARGET / "readiness-status.yaml"
    record.mkdir(parents=True)
    _write_allowlist(tmp_path)
    verdict = _evaluate(tmp_path)
    assert not verdict.cleared
    assert not verdict.stage_readable


# --------------------------------------------------------------------------
# T011 -- the approval note must name the target as a WHOLE TOKEN
# --------------------------------------------------------------------------


def test_approval_naming_a_prefix_does_not_authorize_the_longer_target(
    tmp_path: Path,
) -> None:
    """``sales_model`` must NOT authorize ``sales_model_v2`` (the prefix case).

    A bare substring check would let a loosely-worded note widen its own scope --
    the self-granted authority Principle V forbids.
    """
    longer = f"{TARGET}_v2"
    _write_readiness(tmp_path, target=longer, approval_note=f"approved for {TARGET}")
    _write_allowlist(tmp_path, targets=(longer,))
    verdict = _evaluate(tmp_path, target_id=longer)
    assert not verdict.cleared
    assert not verdict.approval_names_target
    assert gate.BLOCKER_APPROVAL_TARGET in verdict.blockers


def test_approval_naming_the_exact_token_authorizes_it(clean_repo: Path) -> None:
    """The exact-token case must CLEAR -- the other half of the rule.

    Without this, the matcher could refuse everything and still pass the prefix
    test above.
    """
    verdict = _evaluate(clean_repo)
    assert verdict.approval_names_target
    assert verdict.cleared


@pytest.mark.parametrize(
    "note",
    [
        pytest.param(f"approved for {TARGET}", id="whitespace-delimited"),
        pytest.param(f"{TARGET}", id="whole-note"),
        pytest.param(f"target: {TARGET}.", id="trailing-period"),
        pytest.param(f"({TARGET})", id="parenthesised"),
        pytest.param(f"apply to {TARGET}, per ADR", id="comma-delimited"),
    ],
)
def test_target_named_at_a_token_boundary_is_recognised(
    tmp_path: Path, note: str
) -> None:
    """Punctuation and whitespace are legitimate delimiters."""
    _write_readiness(tmp_path, approval_note=note)
    _write_allowlist(tmp_path)
    assert _evaluate(tmp_path).approval_names_target


@pytest.mark.parametrize(
    "note",
    [
        pytest.param(f"{TARGET}_v2", id="longer-token"),
        pytest.param(f"pre_{TARGET}", id="prefixed-token"),
        pytest.param(f"{TARGET}x", id="suffixed-no-delimiter"),
        pytest.param("approved for everything", id="generic-approval"),
        pytest.param("", id="empty-note"),
    ],
)
def test_target_not_named_at_a_boundary_is_refused(tmp_path: Path, note: str) -> None:
    """A generic or near-miss approval never authorizes this target (FR-006)."""
    _write_readiness(tmp_path, approval_note=note)
    _write_allowlist(tmp_path)
    assert not _evaluate(tmp_path).approval_names_target


def test_approval_for_a_different_stage_does_not_count(tmp_path: Path) -> None:
    """Only a ``publish_ready`` row authorizes a write.

    A ``semantic_model_ready`` approval naming the target must not be mistaken
    for publish authority.
    """
    record = tmp_path / "mappings" / TARGET / "readiness-status.yaml"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        "stages:\n  semantic_model_ready:\n    status: pass\n"
        "approvals:\n"
        "  - stage: semantic_model_ready\n"
        "    owner: Ahmed Shaaban\n"
        "    at: '2026-08-18'\n"
        f"    note: 'approved for {TARGET}'\n",
        encoding="utf-8",
    )
    _write_allowlist(tmp_path)
    verdict = _evaluate(tmp_path)
    assert not verdict.cleared
    assert verdict.approval is None


# --------------------------------------------------------------------------
# T012 -- allowlist, and allowlisted-but-absent
# --------------------------------------------------------------------------


def test_target_not_allowlisted_refuses(tmp_path: Path) -> None:
    _write_readiness(tmp_path)
    _write_allowlist(tmp_path, targets=(OTHER_TARGET,))
    verdict = _evaluate(tmp_path)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_target_allowlisted_but_absent_on_disk_refuses(tmp_path: Path) -> None:
    """Refused as an undefined artifact -- the adapter never invents it (FR-011)."""
    _write_readiness(tmp_path)
    _write_allowlist(tmp_path)
    (tmp_path / "models" / f"{TARGET}.tmdl").unlink()
    verdict = _evaluate(tmp_path)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ABSENT in verdict.blockers


def test_missing_allowlist_file_refuses(tmp_path: Path) -> None:
    """No allowlist at all is not an empty-allowlist pass -- it is a refusal."""
    _write_readiness(tmp_path)
    verdict = _evaluate(tmp_path)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


# --------------------------------------------------------------------------
# T013 -- git safety
# --------------------------------------------------------------------------


def test_dirty_tree_without_declared_backup_refuses(clean_repo: Path) -> None:
    verdict = _evaluate(clean_repo, tree_clean=False, backup_declared=False)
    assert not verdict.cleared
    assert gate.BLOCKER_GIT_UNSAFE in verdict.blockers


def test_dirty_tree_with_declared_backup_clears(clean_repo: Path) -> None:
    """The declared-backup escape is legitimate -- and must actually work.

    Its absence would make the gate refuse every dirty tree, which the spec
    does not require.
    """
    verdict = _evaluate(clean_repo, tree_clean=False, backup_declared=True)
    assert verdict.git_safe
    assert verdict.cleared


def test_clean_tree_clears_without_a_backup(clean_repo: Path) -> None:
    assert _evaluate(clean_repo, tree_clean=True, backup_declared=False).git_safe


# --------------------------------------------------------------------------
# T014 -- a refusal has no warning-level representation
# --------------------------------------------------------------------------


def test_non_empty_blockers_is_always_blocking(tmp_path: Path) -> None:
    """There is no 'warning' verdict a script could ignore (FR-009)."""
    _write_readiness(tmp_path, semantic_status="warning")
    _write_allowlist(tmp_path)
    verdict = _evaluate(tmp_path)
    assert verdict.blockers
    assert not verdict.cleared
    assert verdict.blocking is True


def test_cleared_and_blocking_are_mutually_exclusive(clean_repo: Path) -> None:
    """The two states cannot both hold -- degradation is unexpressible."""
    cleared = _evaluate(clean_repo)
    assert cleared.cleared is True
    assert cleared.blocking is False


def test_verdict_is_immutable(clean_repo: Path) -> None:
    """A caller cannot flip a refusal into a pass after the fact."""
    verdict = _evaluate(clean_repo)
    with pytest.raises(Exception):
        verdict.blockers = ()  # type: ignore[misc]


def test_verdict_carries_no_score(clean_repo: Path) -> None:
    """Hard rule #9 at the gate boundary: typed blockers, never a number."""
    verdict = _evaluate(clean_repo)
    for field_name in vars(verdict):
        assert not isinstance(getattr(verdict, field_name), (int, float)) or isinstance(
            getattr(verdict, field_name), bool
        ), f"{field_name} looks like a score"
