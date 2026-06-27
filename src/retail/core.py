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
