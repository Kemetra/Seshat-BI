"""Spec 149 T004/T005/T007 -- the bypass prohibition must cover invocation argv.

The shipped chokepoint in ``seshat.pbi_mcp.detect`` inspects the machine-local
``.mcp.json`` **config args** only. That was sufficient while nothing could be
invoked in write mode. Slice 5 makes write mode reachable, so the same matcher
must also judge an **invocation argv** (FR-002, FR-003).

Design constraint carried from the plan: extend the ONE existing matcher. A
second module or a second constant would be a second enforcement path for one
rule, which is the defect the plan explicitly cancelled.

These tests pin BEHAVIOR (a verdict is returned for a given argv), never the
absence of a symbol -- an absence assertion goes green the moment the capability
ships under a different name.
"""

from __future__ import annotations

import pytest

from seshat.pbi_mcp import detect

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# T004 -- the forbidden flag, passed as an invocation argument
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--skipconfirmation"], id="bare"),
        pytest.param(["--skipconfirmation=true"], id="value-form"),
        pytest.param(["--SKIPCONFIRMATION"], id="upper-case"),
        pytest.param(["--SkipConfirmation"], id="mixed-case"),
        pytest.param(["update_measure", "--skipconfirmation"], id="trailing"),
        pytest.param(["--skipconfirmation", "update_measure"], id="leading"),
        pytest.param(["--readonly", "--skipconfirmation"], id="alongside-readonly"),
    ],
)
def test_forbidden_flag_in_invocation_argv(argv: list[str]) -> None:
    """The bypass flag is refused however it is spelled or positioned.

    Case variants are included deliberately: the config path lowercases args in
    ``_server_args`` before matching, so an argv entry point that forgets to
    lowercase would reintroduce a case bypass that the config path does not have.
    """
    assert detect.classify_invocation_argv(argv) == detect.CONFIG_FORBIDDEN_FLAG


def test_forbidden_flag_wins_over_a_write_flag() -> None:
    """Fail-closed ordering matches the config path: forbidden beats write."""
    verdict = detect.classify_invocation_argv(["--readwrite", "--skipconfirmation"])
    assert verdict == detect.CONFIG_FORBIDDEN_FLAG


def test_negated_lookalike_is_not_a_false_positive() -> None:
    """``--no-skipconfirmation`` must not be read as the bypass flag.

    Guards against a matcher so loose it fires on any argument containing the
    word -- a refusal that cannot be avoided is as broken as one that never fires.
    """
    assert detect.classify_invocation_argv(["--no-skipconfirmation"]) != (
        detect.CONFIG_FORBIDDEN_FLAG
    )


# --------------------------------------------------------------------------
# T005 -- BOTH write-flag spellings, and their value forms
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--readwrite"], id="documented-spelling"),
        pytest.param(["--read-write"], id="repo-shipped-misspelling"),
        pytest.param(["--readwrite=true"], id="documented-value-form"),
        pytest.param(["--read-write=true"], id="misspelled-value-form"),
        pytest.param(["--ReadWrite"], id="mixed-case"),
        pytest.param(["--READWRITE"], id="upper-case"),
    ],
)
def test_both_write_flag_spellings_refused_in_argv(argv: list[str]) -> None:
    """Every spelling and form of write mode is detected as write mode.

    The hyphenated spelling is the one this repo itself once generated, so a
    matcher covering only the documented spelling fails open on a config the
    repo produced. The ``=true`` value forms are included because the shipped
    write-flag matcher is an EXACT membership test -- ``--readwrite=true``
    currently evaluates to *not* write mode, which is a real value-form gap that
    only matters once write mode is reachable.
    """
    assert detect.classify_invocation_argv(argv) == detect.CONFIG_WRITE_MODE


def test_empty_argv_is_read_only_not_write() -> None:
    """Mode defaulting: an invocation naming no mode resolves to read-only.

    Write mode is never reached by omission (FR-001).
    """
    assert detect.classify_invocation_argv([]) == detect.CONFIG_READ_ONLY


def test_explicit_readonly_argv_is_read_only() -> None:
    assert detect.classify_invocation_argv(["--readonly"]) == detect.CONFIG_READ_ONLY


def test_unrelated_args_do_not_imply_write_mode() -> None:
    """A plain operation argument is not a mode request."""
    verdict = detect.classify_invocation_argv(["update_measure", "--target", "sales"])
    assert verdict == detect.CONFIG_READ_ONLY


# --------------------------------------------------------------------------
# T007 -- detect.py is the SOLE bypass chokepoint
# --------------------------------------------------------------------------


def test_argv_and_config_paths_agree_on_the_forbidden_flag() -> None:
    """One rule, one matcher: both entry points must return the same verdict.

    This is the behavioral form of "sole chokepoint". If a future edit gave argv
    its own private matcher, the two paths could disagree -- and this test is
    what would catch it.
    """
    argv_verdict = detect.classify_invocation_argv(["--skipconfirmation"])
    config_verdict = detect._flag_verdict([["--skipconfirmation"]])
    assert argv_verdict == config_verdict == detect.CONFIG_FORBIDDEN_FLAG


def test_argv_and_config_paths_agree_on_write_mode() -> None:
    argv_verdict = detect.classify_invocation_argv(["--readwrite"])
    config_verdict = detect._flag_verdict([["--readwrite"]])
    assert argv_verdict == config_verdict == detect.CONFIG_WRITE_MODE


def test_argv_classifier_reuses_the_shipped_flag_constants() -> None:
    """Pin the CAPABILITY to the shipped constants, not to a copy.

    Asserted by behavior: whatever ``_FORBIDDEN_FLAG`` holds must be the token
    the argv path refuses. If someone renamed the constant and hardcoded the old
    literal in the argv path, this fails.
    """
    assert detect.classify_invocation_argv([detect._FORBIDDEN_FLAG]) == (
        detect.CONFIG_FORBIDDEN_FLAG
    )
    for write_flag in detect._WRITE_FLAGS:
        assert detect.classify_invocation_argv([write_flag]) == (
            detect.CONFIG_WRITE_MODE
        )


# --------------------------------------------------------------------------
# H3 -- the guard RAISES, so a callsite cannot inherit nothing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--skipconfirmation"], id="bare"),
        pytest.param(["--skipconfirmation=true"], id="value-form"),
        pytest.param(["--SkipConfirmation"], id="mixed-case"),
        pytest.param(["update_measure", "--skipconfirmation"], id="trailing"),
    ],
)
def test_refuse_if_bypass_flag_raises_on_argv(argv: list[str]) -> None:
    """The write path's guard cannot be ignored -- it raises, not returns.

    ``classify_*`` returns an advisory string each consumer must remember to
    compare; that is not a chokepoint. This is.
    """
    with pytest.raises(detect.BypassFlagRefused):
        detect.refuse_if_bypass_flag(argv)


def test_refuse_if_bypass_flag_raises_on_config_state() -> None:
    """The flag is refused however it arrives -- config as well as argv."""
    with pytest.raises(detect.BypassFlagRefused):
        detect.refuse_if_bypass_flag([], config_state=detect.CONFIG_FORBIDDEN_FLAG)


def test_refuse_if_bypass_flag_passes_a_clean_invocation() -> None:
    """The positive control: a clean run must not be blocked.

    Without this, a guard that raised unconditionally would pass every refusal
    test above while making the feature unusable.
    """
    assert (
        detect.refuse_if_bypass_flag([], config_state=detect.CONFIG_READ_ONLY) is None
    )
    assert detect.refuse_if_bypass_flag(["--readonly"]) is None
    assert detect.refuse_if_bypass_flag(["update_measure", "--target", "x"]) is None


def test_the_guard_is_what_refuses_not_incidental_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load-bearing proof: neuter ONLY the matcher and the refusal disappears.

    Replaces T007's import-coverage idea, which would go green on a module that
    imports ``detect`` and ignores its return value -- an import proves an import.
    """
    argv = ["--skipconfirmation"]
    with pytest.raises(detect.BypassFlagRefused):
        detect.refuse_if_bypass_flag(argv)

    monkeypatch.setattr(
        detect, "classify_invocation_argv", lambda _argv: detect.CONFIG_READ_ONLY
    )
    # With the matcher neutered the guard no longer fires -- proving the matcher,
    # not something incidental, is what produced the refusal above.
    assert detect.refuse_if_bypass_flag(argv) is None


def test_the_guard_returns_none_so_there_is_no_verdict_to_ignore() -> None:
    """A guard that returned a truthy verdict could be called and discarded.

    Pins the CAPABILITY: success is indistinguishable from "not checked" only if
    the guard returns something. It returns None and raises instead.
    """
    assert detect.refuse_if_bypass_flag([]) is None
