"""Spec 149 T037-T039 -- capability drift blocks; `unknown` is never compatible."""

from __future__ import annotations

import pytest

from seshat.pbi_mcp_adapter import drift
from tests.unit._pbi_mcp_stub import STUB_TOOLS, StubTransport

pytestmark = pytest.mark.unit


def _profile(**kwargs: object) -> drift.RuntimeCapabilityProfile:
    params: dict[str, object] = {
        "observed_tools": STUB_TOOLS,
        "recorded_tools": STUB_TOOLS,
    }
    params.update(kwargs)
    return drift.RuntimeCapabilityProfile(**params)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# T037 -- drift is a blocker, not a warning
# --------------------------------------------------------------------------


def test_matching_capabilities_do_not_block() -> None:
    """The positive control -- without it, every drift test below is vacuous."""
    profile = _profile()
    assert not profile.drifted
    assert not profile.blocking
    assert profile.blockers == ()


def test_a_missing_capability_is_drift() -> None:
    profile = _profile(observed_tools=STUB_TOOLS[:-1])
    assert profile.drifted
    assert profile.blocking
    assert drift.BLOCKER_CAPABILITY_DRIFT in profile.blockers
    assert profile.missing_tools == (STUB_TOOLS[-1],)


def test_an_extra_capability_is_also_drift() -> None:
    """An extra tool means this is not the runtime we characterized.

    Its flag names may have moved too -- which matters, because the bypass-flag
    matcher pins literal flag spellings.
    """
    profile = _profile(observed_tools=(*STUB_TOOLS, "unexpected_tool"))
    assert profile.drifted
    assert drift.BLOCKER_CAPABILITY_DRIFT in profile.blockers
    assert profile.extra_tools == ("unexpected_tool",)


def test_reordering_is_not_drift() -> None:
    """Set comparison: a server may legitimately reorder its tool list."""
    profile = _profile(observed_tools=tuple(reversed(STUB_TOOLS)))
    assert not profile.drifted


def test_no_recorded_baseline_blocks() -> None:
    """Drift cannot be ruled out with nothing to compare against.

    Fails closed: absence of a baseline is not absence of drift.
    """
    profile = _profile(recorded_tools=())
    assert profile.blocking
    assert drift.BLOCKER_NO_RECORDED_BASELINE in profile.blockers


def test_drift_is_never_expressible_as_a_warning() -> None:
    profile = _profile(observed_tools=("only_one",))
    assert profile.blocking is True
    assert profile.blockers


# --------------------------------------------------------------------------
# T038 -- `unknown` is NEVER compatible
# --------------------------------------------------------------------------


def test_unknown_range_is_never_compatible() -> None:
    assert not _profile(supported_range=drift.UNKNOWN_RANGE).range_is_compatible


def test_empty_range_is_never_compatible() -> None:
    assert not _profile(supported_range="").range_is_compatible


def test_asking_whether_an_unknown_range_is_compatible_yields_a_blocker() -> None:
    """A caller cannot express "unknown, so we proceeded"."""
    assert drift.assert_range_never_assumed_compatible(drift.UNKNOWN_RANGE) == (
        drift.BLOCKER_RANGE_UNKNOWN_TREATED_AS_COMPATIBLE,
    )


def test_a_real_range_is_compatible() -> None:
    """The positive control, so the check is not simply always-false."""
    assert _profile(supported_range=">=1.0,<2.0").range_is_compatible
    assert drift.assert_range_never_assumed_compatible(">=1.0,<2.0") == ()


def test_the_default_range_is_unknown() -> None:
    """Both servers are unreleased previews, so this is the honest default."""
    assert _profile().supported_range == drift.UNKNOWN_RANGE


# --------------------------------------------------------------------------
# The deliberate separation: drift gates the write, version range does not
# --------------------------------------------------------------------------


def test_an_unknown_range_alone_does_not_block_a_write() -> None:
    """Resolves the tension the review flagged, explicitly.

    If the write gated on version compatibility, an `unknown` range would block
    forever -- and the range is `unknown` for the life of this spec. So the
    write gates on DRIFT, which is answerable today, while `unknown` still never
    counts as compatible.
    """
    profile = _profile(supported_range=drift.UNKNOWN_RANGE)
    assert not profile.range_is_compatible
    assert not profile.blocking, (
        "an unknown range must not block a write on its own, or nothing ever "
        "ships while the previews remain unreleased"
    )


def test_drift_blocks_even_when_the_range_looks_fine() -> None:
    profile = _profile(observed_tools=("drifted",), supported_range=">=1.0")
    assert profile.blocking


# --------------------------------------------------------------------------
# Built from the real preflight shape, not hand-invented
# --------------------------------------------------------------------------


def test_profile_can_be_built_from_the_stub_transport() -> None:
    """The drift seam the stub fixture was designed to feed (T003)."""
    observed = StubTransport().with_tools(("unexpected_tool",)).describe().tools
    profile = _profile(observed_tools=observed)
    assert profile.drifted


def test_every_blocker_id_has_readable_detail() -> None:
    ids = [
        value
        for name, value in vars(drift).items()
        if name.startswith("BLOCKER_") and isinstance(value, str)
    ]
    assert len(ids) == 3
    for blocker in ids:
        assert drift.BLOCKER_DETAIL.get(blocker)
        assert blocker.startswith("PBIMCP-DRIFT-")
