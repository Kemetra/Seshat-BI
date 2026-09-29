"""Spec 149 -- attributing a post-write finding to the write that caused it (#663).

One subject: the baseline diff. `semantic-check`'s corpus is repo-wide and cannot
be narrowed (discovery anchors on the git toplevel and refuses a subdirectory), so
a finding is blamed on this write only when it is ABSENT from a baseline captured
before the mutation.

Split from ``test_pbi_mcp_validation``, which proves the validator invocation and
the vacuous-pass guards. These tests share their own fixtures and none of that
module's, which is what Low Cohesion was correctly reporting.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import validation

pytestmark = pytest.mark.unit

TARGET_PATH = "models/sales_model.tmdl"


@pytest.fixture
def repo_with_target(tmp_path: Path) -> Path:
    """A repo holding the authorized target, so the artifact exists."""
    artifact = tmp_path / TARGET_PATH
    artifact.parent.mkdir(parents=True)
    artifact.write_text("// sales_model\n", encoding="utf-8")
    return tmp_path


# Issue #663 gap 3 -- attribute a finding to the write that caused it.

_PRE_EXISTING = (
    "[error] L3 measure 'Unapproved': no approved metric contract "
    "(Other.SemanticModel/definition/other.tmdl:2)"
)
_NEW = (
    "[error] L3 measure 'Broken': no approved metric contract "
    "(models/sales_model.tmdl:4)"
)


def _runner_printing(text: str, returncode: int):
    def invoke(_root, args):
        return subprocess.CompletedProcess(
            args=list(args), returncode=returncode, stdout=text, stderr=""
        )

    return invoke


def test_a_pre_existing_finding_does_not_block_the_write(
    repo_with_target: Path,
) -> None:
    """The gap-3 defect: an error in an UNTOUCHED model blocked a good write and
    offered rollback guidance that could not possibly fix it."""
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing(_PRE_EXISTING + "\n", 1),
            baseline=frozenset({_PRE_EXISTING}),
            examined=lambda _root, _artifact: True,
        ),
    )

    assert outcome.blocking is False, (
        f"a pre-existing finding blocked: {outcome.failed}"
    )
    assert outcome.rollback_guidance == (), "offered rollback for someone else's error"
    assert outcome.checks_skipped, "the pre-existing finding was silently dropped"


def test_a_finding_this_write_introduced_does_block(repo_with_target: Path) -> None:
    """The check must still work: a NEW finding blocks and carries rollback."""
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing(f"{_PRE_EXISTING}\n{_NEW}\n", 1),
            baseline=frozenset({_PRE_EXISTING}),
            examined=lambda _root, _artifact: True,
        ),
    )

    assert outcome.blocking is True
    assert any(_NEW in item for item in outcome.failed)
    assert not any(_PRE_EXISTING in item for item in outcome.failed), (
        "a pre-existing finding was reported as this write's failure"
    )
    assert outcome.rollback_guidance, "a failure must carry rollback guidance"


def test_an_unobtainable_baseline_blocks(repo_with_target: Path) -> None:
    """Fails CLOSED. An empty baseline makes every finding look new (noisy but
    safe); a silently-complete one makes every finding look pre-existing, hiding
    the exact regression this check exists to catch."""
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing("", 0),
            baseline=None,
            examined=lambda _root, _artifact: True,
        ),
    )

    assert outcome.blocking is True
    assert validation.BLOCKER_BASELINE_UNAVAILABLE in outcome.blockers
    assert outcome.rollback_guidance, "a blocking outcome must carry rollback guidance"


def test_the_baseline_helper_returns_none_when_it_cannot_run(
    repo_with_target: Path,
) -> None:
    """None and an empty set are NOT the same and must stay distinguishable."""

    def explode(_root, _args):
        raise OSError("validator missing")

    assert validation.semantic_baseline(repo_with_target, runner=explode) is None
    assert (
        validation.semantic_baseline(repo_with_target, runner=_runner_printing("", 0))
        == frozenset()
    )


def test_a_nonzero_exit_with_no_parseable_finding_still_blocks(
    repo_with_target: Path,
) -> None:
    """The baseline diff must not become a way to launder an unexplained failure.

    A validator that exits non-zero while printing nothing the diff can attribute
    has NOT been shown to be reporting a pre-existing problem. Treating it as
    pre-existing would both pass a failing run and fabricate the reason why.
    """
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing("", 1),
            baseline=frozenset(),
            examined=lambda _root, _artifact: True,
        ),
    )

    assert outcome.blocking is True, "an unexplained non-zero exit did not block"
    assert outcome.rollback_guidance, "a blocking outcome must carry rollback guidance"


def test_the_binding_and_value_legs_actually_run_on_a_clean_semantic_pass(
    repo_with_target: Path,
) -> None:
    """A validator nobody calls is a dead path with green tests.

    Pins that a clean semantic result REACHES the other two legs, so their
    skips/failures appear in the merged outcome.
    """
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing("", 0),
            baseline=frozenset(),
            examined=lambda _root, _artifact: True,
            env={},
        ),
    )

    skipped_checks = {check for check, _reason in outcome.checks_skipped}
    assert "value-check" in skipped_checks, (
        f"the value leg never ran: {outcome.checks_skipped}"
    )
    assert "pbir-validate-bindings" in skipped_checks, (
        f"the binding leg never ran: {outcome.checks_skipped}"
    )
    assert outcome.blocking is False, "loud skips must not block"


def test_a_blocking_semantic_result_short_circuits_the_other_legs(
    repo_with_target: Path,
) -> None:
    """Running more validators against an artifact already known bad adds noise."""
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing("", 0),
            baseline=None,
            examined=lambda _root, _artifact: True,
            env={},
        ),
    )

    assert outcome.blocking is True
    assert outcome.checks_skipped == (), "later legs ran despite a blocking result"


# The child reconfigures its stdout to UTF-8 on win32. Two bytes make this fail
# without the fix on EVERY platform: U+0641 (0xD9 0x81) is undecodable under
# cp1252, and a lone 0xFF is undecodable under strict UTF-8.
_NON_LOCALE_FINDING = (
    "import sys; sys.stdout.buffer.write("
    "b'[error] L3 measure \\xd9\\x81 \\xff (m.tmdl:1)\\n'); sys.stdout.flush()"
)


def test_the_validator_decodes_utf8_child_output(tmp_path: Path) -> None:
    """A finding outside the locale codec must still come back as text.

    Decoding with the locale codec killed subprocess's reader thread and left
    ``stdout`` as None, so the baseline collapsed to an empty set.
    """
    import sys

    completed = validation._run_validator(
        tmp_path, (sys.executable, "-c", _NON_LOCALE_FINDING)
    )

    assert completed.stdout is not None
    assert completed.stdout.startswith("[error] L3 measure")


def test_the_baseline_is_captured_from_non_locale_output(tmp_path: Path) -> None:
    import sys

    def invoke(root, _args):
        return validation._run_validator(
            root, (sys.executable, "-c", _NON_LOCALE_FINDING)
        )

    baseline = validation.semantic_baseline(tmp_path, runner=invoke)

    assert baseline is not None and len(baseline) == 1


def test_a_baseline_with_no_captured_stdout_is_unavailable_not_empty(
    repo_with_target: Path,
) -> None:
    """stdout=None means nothing was captured -- never an empty finding set."""
    assert (
        validation.semantic_baseline(repo_with_target, runner=_runner_printing(None, 0))
        is None
    )


def test_a_post_write_run_with_no_captured_stdout_blocks(
    repo_with_target: Path,
) -> None:
    """The post-write leg reads None the same way: the validator did not report."""
    outcome = validation.validate_semantic_model(
        repo_with_target,
        target_path=TARGET_PATH,
        context=validation.ValidationContext(
            runner=_runner_printing(None, 0),
            baseline=frozenset(),
            examined=lambda _root, _artifact: True,
            env={},
        ),
    )

    assert outcome.blocking is True
    assert validation.BLOCKER_VALIDATOR_ERROR in outcome.blockers
