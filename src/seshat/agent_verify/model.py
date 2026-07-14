"""Core model for `seshat agent verify` (spec 129).

Every check resolves to exactly one categorical verdict from a fixed,
three-value vocabulary -- PASS, BLOCKED, UNAVAILABLE -- never a score, rank,
pass-rate, grade, or rolled-up "certified" verdict (FR-002/FR-003). The
per-verdict invariant below is enforced at construction and is never
coerced: a check that could not run is UNAVAILABLE, never PASS; a check that
ran but did not pass is BLOCKED, never silently PASS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"
VERDICTS = ("PASS", "BLOCKED", "UNAVAILABLE")
EVIDENCE_CLASSES = ("per_target", "shared_baseline")

# The static-vs-live boundary this record's evidence sits on (FR-007): every
# verdict below is drawn from the installed bundle, its provenance manifest,
# and committed benchmark scenarios matched against the deterministic
# scripted reference -- never from launching or observing a live agent.
STATIC_VS_LIVE_BOUNDARY = (
    "static-only: verify inspects the installed bundle, its provenance "
    "manifest, and committed benchmark scenarios against the deterministic "
    "scripted reference participant; it never launches or observes a live "
    "agent"
)


class AgentVerifyError(ValueError):
    """Base error for agent-verify input defects (the CLI maps these to
    exit 2 -- an input defect, distinct from any check's own verdict)."""


@dataclass(frozen=True)
class PerCheckResult:
    """The categorical outcome of one required check on one target.

    Invariant (enforced here, never coerced):
      PASS        -> non-empty ``evidence`` and empty ``blocking_reasons``
                      and no ``unavailable_reason``.
      BLOCKED     -> at least one ``blocking_reasons`` entry and no
                      ``unavailable_reason``.
      UNAVAILABLE -> a non-empty ``unavailable_reason`` and empty
                      ``blocking_reasons``.
    """

    check_id: str
    verdict: str
    evidence_class: str
    evidence: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(
                f"{self.check_id}: verdict must be one of {VERDICTS}, "
                f"got {self.verdict!r}"
            )
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(
                f"{self.check_id}: evidence_class must be one of "
                f"{EVIDENCE_CLASSES}, got {self.evidence_class!r}"
            )
        if self.verdict == "PASS":
            if not self.evidence:
                raise ValueError(f"{self.check_id}: PASS requires non-empty evidence")
            if self.blocking_reasons:
                raise ValueError(
                    f"{self.check_id}: PASS must carry no blocking reasons"
                )
            if self.unavailable_reason is not None:
                raise ValueError(
                    f"{self.check_id}: PASS must carry no unavailable_reason"
                )
        elif self.verdict == "BLOCKED":
            if not self.blocking_reasons:
                raise ValueError(
                    f"{self.check_id}: BLOCKED requires >=1 blocking reason"
                )
            if self.unavailable_reason is not None:
                raise ValueError(
                    f"{self.check_id}: BLOCKED must carry no unavailable_reason"
                )
        else:  # UNAVAILABLE
            if not self.unavailable_reason:
                raise ValueError(
                    f"{self.check_id}: UNAVAILABLE requires an unavailable_reason"
                )
            if self.blocking_reasons:
                raise ValueError(
                    f"{self.check_id}: UNAVAILABLE must carry no blocking_reasons"
                )

    def to_document(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "verdict": self.verdict,
            "evidence_class": self.evidence_class,
            "evidence": list(self.evidence),
            "blocking_reasons": list(self.blocking_reasons),
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True)
class VerifyTargetSpec:
    """A named, shipped agent integration verify can inspect.

    Data-driven (see ``targets.py``): adding a third integration is a
    registry entry, not a code fork.
    """

    name: str
    manifest_path: str
    provenance_manifest: str
    version_source: str
    footprint_source: str
    operating_contract: str
    ide_surface: bool


@dataclass(frozen=True)
class VerifyRecord:
    """The portable, disclosure-safe snapshot of one verify run.

    ``to_document()`` emits NO aggregate/score/rank/pass-rate/grade/overall/
    certified field anywhere (FR-003); the per-check results carry the only
    truth this record asserts.
    """

    target: str
    tool_version: str
    generated_at: str
    results: tuple[PerCheckResult, ...] = field(default_factory=tuple)
    schema_version: str = SCHEMA_VERSION
    static_vs_live_boundary: str = STATIC_VS_LIVE_BOUNDARY

    def to_document(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "tool_version": self.tool_version,
            "generated_at": self.generated_at,
            "static_vs_live_boundary": self.static_vs_live_boundary,
            "results": [item.to_document() for item in self.results],
        }
