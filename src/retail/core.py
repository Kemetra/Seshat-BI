from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, TypedDict


class FindingDict(TypedDict):
    """Serialized shape of a :class:`Finding` (the ``check --format json`` payload)."""

    rule_id: str
    severity: str
    message: str
    locator: str


class Severity(str, Enum):
    ERROR = "error"  # fails the build (non-zero exit)
    WARNING = "warning"  # reported, does NOT fail the build
    INFO = "info"  # informational only


class RuleTier(str, Enum):
    """Which repos a rule is meaningful in (Spec A -- drop-in fitness).

    ``WORK_REPO`` (the default) is a PORTABLE rule: it checks a work artifact
    (SQL, PBIP, layout, gitattributes) that any BI repo can have, so it always
    runs. ``KIT_SELF`` checks one of the KIT's OWN internal manifests (route
    registry, status-claims, shared-spine, ...) which a repo the kit was merely
    downloaded into cannot have; such a rule SKIPs (one INFO finding) when the
    repo is not kit-bootstrapped, instead of ERROR-ing on an absent manifest.
    Mirrors kit_lint's "absence is not drift" (FR-006).
    """

    WORK_REPO = "work-repo"
    KIT_SELF = "kit-self"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    locator: str

    def to_dict(self) -> FindingDict:
        """Plain-dict view for structured (JSON) output.

        Severity is rendered as its string value (``"error"`` / ``"warning"`` /
        ``"info"``) so the JSON round-trips to the same Severity via the enum.
        """
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "locator": self.locator,
        }


@dataclass(frozen=True)
class RuleContext:
    repo_root: Path
    tracked_files: tuple[str, ...]
    commit_range: str | None = None
    commit_message: str | None = None


# Single source of truth for the committed-test-fixture exemption.
# tests/ holds intentionally non-conforming fixtures (golden PBIP with planted
# violations, absolute/byConnection .pbir, test *.sql) that exist to exercise
# the rules; they are not the live model, so the file-scanning rules skip them.
# Centralized here so future file-scanning rules inherit one consistent rule.
# NOTE: C2's content scan uses a *broader* exclusion (docs/, .superpowers/,
# .example as well) and intentionally does NOT route through this predicate.
def is_test_path(path: str) -> bool:
    """True if ``path`` (repo-relative POSIX) is a committed test fixture."""
    return path.startswith("tests/")


# A rule is a pure function: context in, findings out. No side effects.
Rule = Callable[[RuleContext], Iterable[Finding]]


@dataclass(frozen=True)
class RegisteredRule:
    id: str
    rule: Rule
    title: str
    # Spec A: defaults to WORK_REPO so every already-registered rule is a
    # portable rule that always gates -- existing kit behavior is unchanged.
    tier: RuleTier = RuleTier.WORK_REPO
