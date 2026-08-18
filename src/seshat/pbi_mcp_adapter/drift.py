"""Spec 149 T037-T039 -- vendor preview drift is a blocker, not a warning.

Both official Microsoft servers are public preview with no published release, so
the supported-version range legitimately reads ``unknown`` for the life of this
spec -- and ``unknown`` is NEVER compatible (FR-020).

That creates a tension the review flagged, and it is resolved deliberately here
rather than left for an implementer to discover and quietly exempt:

* **Version compatibility** asks "is the vendor's released version inside a range
  we support?" With no published release the answer is permanently ``unknown``,
  so gating a write on it would block forever.
* **Capability drift** asks "does the runtime in front of me still look like the
  one we recorded?" That is answerable today, from the observed capability set.

So the write path gates on **drift**, not on version compatibility. A drifted
runtime blocks; an `unknown` range is reported honestly and never treated as
compatible, but it is not what stops a write.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The supported-version range while both servers remain unreleased previews.
UNKNOWN_RANGE = "unknown"

BLOCKER_CAPABILITY_DRIFT = "PBIMCP-DRIFT-01"
BLOCKER_NO_RECORDED_BASELINE = "PBIMCP-DRIFT-02"
BLOCKER_RANGE_UNKNOWN_TREATED_AS_COMPATIBLE = "PBIMCP-DRIFT-03"

BLOCKER_DETAIL: dict[str, str] = {
    BLOCKER_CAPABILITY_DRIFT: (
        "the runtime's capability set differs from the recorded baseline; the "
        "flag and tool names this adapter matches on may have changed"
    ),
    BLOCKER_NO_RECORDED_BASELINE: (
        "no recorded capability baseline exists to compare against, so drift "
        "cannot be ruled out"
    ),
    BLOCKER_RANGE_UNKNOWN_TREATED_AS_COMPATIBLE: (
        "the supported version range is 'unknown', which is never compatible"
    ),
}


@dataclass(frozen=True)
class RuntimeCapabilityProfile:
    """What the detected runtime actually offers, versus what we recorded."""

    observed_tools: tuple[str, ...]
    recorded_tools: tuple[str, ...]
    supported_range: str = UNKNOWN_RANGE

    @property
    def has_baseline(self) -> bool:
        return bool(self.recorded_tools)

    @property
    def drifted(self) -> bool:
        """Whether the observed capability set differs from the baseline.

        Set comparison, not ordering: a server is free to reorder its tool list.
        A MISSING tool and an EXTRA tool are both drift -- an extra capability
        means the runtime is not the one we characterized, and its flag names may
        have moved too.
        """
        return set(self.observed_tools) != set(self.recorded_tools)

    @property
    def missing_tools(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.recorded_tools) - set(self.observed_tools)))

    @property
    def extra_tools(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.observed_tools) - set(self.recorded_tools)))

    @property
    def range_is_compatible(self) -> bool:
        """An ``unknown`` range is never compatible (FR-020).

        Deliberately separate from :attr:`drifted`: this is what a *compatibility*
        question answers, and it is permanently False while the previews are
        unreleased. The write path must not gate on it, or nothing ever ships.
        """
        return self.supported_range != UNKNOWN_RANGE and bool(self.supported_range)

    @property
    def blockers(self) -> tuple[str, ...]:
        found: list[str] = []
        if not self.has_baseline:
            found.append(BLOCKER_NO_RECORDED_BASELINE)
        elif self.drifted:
            found.append(BLOCKER_CAPABILITY_DRIFT)
        return tuple(found)

    @property
    def blocking(self) -> bool:
        return bool(self.blockers)

    def detail_for(self, blocker: str) -> str:
        return BLOCKER_DETAIL.get(blocker, blocker)


def assert_range_never_assumed_compatible(supported_range: str) -> tuple[str, ...]:
    """Blockers for treating a range as compatible.

    Exists so a caller cannot express "the range was unknown, so we proceeded":
    asking the question at all yields a blocker when the answer is ``unknown``.
    """
    if supported_range == UNKNOWN_RANGE or not supported_range:
        return (BLOCKER_RANGE_UNKNOWN_TREATED_AS_COMPATIBLE,)
    return ()
